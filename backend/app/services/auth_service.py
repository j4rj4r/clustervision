import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from ..core.auth import hash_password, verify_password
from ..db.models import (
    LocalUser,
    LoginAttempt,
    ManagedUser,
    RegisteredCluster,
    ScopeRoleAssignment,
)
from ..db.session import new_session
from . import ldap_service

logger = logging.getLogger(__name__)

_DUMMY_HASH = "$2b$12$Kix0GsNjGUDMHlTGtqKhCOSVRAf5Y/LNmXZnkgDlJwO7hzf5Q7Psy"

_LOGIN_RATE_LIMIT = 10  # max attempts
_LOGIN_RATE_WINDOW = timedelta(minutes=5)

INSTANCE_SCOPE = "_instance"


def check_login_rate_limit(ip: str) -> None:
    """Raise 429 if `ip` has made too many login attempts in the trailing
    window. Backed by Postgres (the `login_attempts` table) rather than an
    in-process dict, so the limit holds across backend replicas and doesn't
    reset every time a pod restarts."""
    from fastapi import HTTPException, status

    now = datetime.now(UTC)
    window_start = now - _LOGIN_RATE_WINDOW

    db = new_session()
    try:
        # Prune this IP's expired attempts first so the table stays bounded —
        # mirrors the stale-bucket cleanup the in-memory version did.
        db.query(LoginAttempt).filter(
            LoginAttempt.ip == ip, LoginAttempt.attempted_at < window_start
        ).delete()

        count = db.scalar(
            select(func.count()).select_from(LoginAttempt).where(LoginAttempt.ip == ip)
        )
        if count >= _LOGIN_RATE_LIMIT:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts — try again later",
                headers={"Retry-After": str(int(_LOGIN_RATE_WINDOW.total_seconds()))},
            )

        db.add(LoginAttempt(id=str(uuid.uuid4()), ip=ip, attempted_at=now))
        db.commit()
    finally:
        db.close()


def _roles_for(db, username: str) -> dict[str, str]:
    rows = db.scalars(
        select(ScopeRoleAssignment).where(ScopeRoleAssignment.username == username)
    )
    return {r.scope: r.role for r in rows}


def _linked_dict(entry: LocalUser) -> dict | None:
    if entry.linked_managed_user is None:
        return None
    return {
        "name": entry.linked_managed_user,
        "namespace": entry.linked_managed_user_namespace,
    }


def _all_scopes(db) -> list[str]:
    cluster_names = db.scalars(select(RegisteredCluster.name)).all()
    return [INSTANCE_SCOPE, "local", *cluster_names]


def _resync_ldap_roles(db, username: str, role: str) -> None:
    """Re-derive every scope this account holds from its single AD-group-
    derived role, replacing whatever was there before — mirrors the
    "re-derived from AD group membership on every login, never trusted from
    cache" property the role itself already had."""
    db.query(ScopeRoleAssignment).filter(
        ScopeRoleAssignment.username == username
    ).delete()
    for scope in _all_scopes(db):
        db.add(ScopeRoleAssignment(username=username, scope=scope, role=role))


def ensure_default_admin() -> None:
    """Create initial admin from CV_ADMIN_PASSWORD env var if no users exist yet."""
    password = os.environ.get("CV_ADMIN_PASSWORD")
    if not password:
        return

    db = new_session()
    try:
        if db.scalar(select(LocalUser).limit(1)) is not None:
            return
        logger.info("Creating default admin from CV_ADMIN_PASSWORD")
        db.add(
            LocalUser(
                username="admin", password_hash=hash_password(password), source="local"
            )
        )
        # Full access out of the box — nothing else exists to scope it to yet.
        db.add(
            ScopeRoleAssignment(username="admin", scope=INSTANCE_SCOPE, role="admin")
        )
        db.add(ScopeRoleAssignment(username="admin", scope="local", role="admin"))
        db.commit()
    except Exception as e:
        logger.warning("Could not initialize default admin: %s", e)
    finally:
        db.close()


def authenticate(username: str, password: str) -> dict | None:
    """Local accounts (source="local") are checked against their stored hash.
    Anyone else (no local account, or an account previously provisioned via
    LDAP) is checked against Active Directory if LDAP is enabled — an
    LDAP-sourced account is always re-validated against the directory, never
    trusted from a local cache, so a disabled AD account or a group-membership
    change takes effect on the very next login."""
    db = new_session()
    try:
        entry = db.get(LocalUser, username)

        if entry is not None and entry.source == "local":
            # Always run bcrypt to prevent username enumeration via timing
            if not verify_password(password, entry.password_hash or _DUMMY_HASH):
                return None
            entry.last_login_at = datetime.now(UTC)
            db.commit()
            return {"username": username, "roles": _roles_for(db, username)}

        ldap_result = ldap_service.authenticate(username, password)
        if ldap_result is None:
            verify_password(password, _DUMMY_HASH)  # keep rough timing parity
            return None

        now = datetime.now(UTC)
        if entry is None:
            db.add(
                LocalUser(
                    username=username,
                    password_hash=None,
                    source="ldap",
                    last_login_at=now,
                )
            )
        else:
            entry.last_login_at = now
        db.flush()  # scope rows FK to local_users — the row above must exist first
        _resync_ldap_roles(db, username, ldap_result.role)
        db.commit()
        return {"username": username, "roles": _roles_for(db, username)}
    finally:
        db.close()


def get_user_entry(username: str) -> dict | None:
    """Current store entry for a user, or None if deleted — used to re-validate
    refresh tokens so removed/demoted users don't keep their old access."""
    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        if entry is None:
            return None
        return {
            "username": username,
            "roles": _roles_for(db, username),
            "linked_managed_user": _linked_dict(entry),
        }
    finally:
        db.close()


def list_users() -> list[dict]:
    db = new_session()
    try:
        return [
            {
                "username": u.username,
                "roles": _roles_for(db, u.username),
                "source": u.source,
                "last_login_at": u.last_login_at.isoformat()
                if u.last_login_at
                else None,
                "linked_managed_user": _linked_dict(u),
            }
            for u in db.scalars(select(LocalUser))
        ]
    finally:
        db.close()


def create_user(username: str, password: str) -> None:
    from fastapi import HTTPException

    db = new_session()
    try:
        if db.get(LocalUser, username) is not None:
            raise HTTPException(
                status_code=409, detail=f"User '{username}' already exists"
            )
        db.add(
            LocalUser(
                username=username, password_hash=hash_password(password), source="local"
            )
        )
        db.commit()
    finally:
        db.close()


def delete_user(username: str) -> None:
    from fastapi import HTTPException

    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        # Postgres' ON DELETE CASCADE would handle this too, but SQLite (the
        # test suite's backend) doesn't enforce FKs by default — do it
        # explicitly so behavior doesn't depend on that.
        db.query(ScopeRoleAssignment).filter(
            ScopeRoleAssignment.username == username
        ).delete()
        db.delete(entry)
        db.commit()
    finally:
        db.close()


def change_password(username: str, new_password: str) -> None:
    from fastapi import HTTPException

    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        if entry.source != "local":
            raise HTTPException(
                status_code=400,
                detail=f"'{username}' is an LDAP-managed account and has no local password",
            )
        entry.password_hash = hash_password(new_password)
        db.commit()
    finally:
        db.close()


def list_scope_roles(username: str) -> list[dict]:
    from fastapi import HTTPException

    db = new_session()
    try:
        if db.get(LocalUser, username) is None:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        return [
            {"scope": scope, "role": role}
            for scope, role in sorted(_roles_for(db, username).items())
        ]
    finally:
        db.close()


def set_scope_role(username: str, scope: str, role: str) -> None:
    from fastapi import HTTPException

    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        if entry.source != "local":
            raise HTTPException(
                status_code=400,
                detail=f"'{username}'s roles are managed via AD group membership",
            )
        existing = db.get(ScopeRoleAssignment, (username, scope))
        if existing is None:
            db.add(ScopeRoleAssignment(username=username, scope=scope, role=role))
        else:
            existing.role = role
        db.commit()
    finally:
        db.close()


def delete_scope_role(username: str, scope: str) -> None:
    from fastapi import HTTPException

    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        if entry.source != "local":
            raise HTTPException(
                status_code=400,
                detail=f"'{username}'s roles are managed via AD group membership",
            )
        existing = db.get(ScopeRoleAssignment, (username, scope))
        if existing is None:
            raise HTTPException(
                status_code=404, detail=f"'{username}' has no role on scope '{scope}'"
            )
        db.delete(existing)
        db.commit()
    finally:
        db.close()


def list_scopes() -> list[str]:
    db = new_session()
    try:
        return _all_scopes(db)
    finally:
        db.close()


def get_linked_user(username: str) -> dict | None:
    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        return _linked_dict(entry) if entry else None
    finally:
        db.close()


def set_linked_user(username: str, name: str, namespace: str) -> None:
    from fastapi import HTTPException

    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        if db.get(ManagedUser, (name, namespace)) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Managed user '{name}' not found in namespace '{namespace}'",
            )
        entry.linked_managed_user = name
        entry.linked_managed_user_namespace = namespace
        db.commit()
    finally:
        db.close()


def clear_linked_user(username: str) -> None:
    from fastapi import HTTPException

    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        entry.linked_managed_user = None
        entry.linked_managed_user_namespace = None
        db.commit()
    finally:
        db.close()


def clear_links_to(name: str, namespace: str) -> None:
    """Called when a managed user is deleted — accounts linked to it just
    silently lose the shortcut rather than pointing at a dead reference."""
    db = new_session()
    try:
        db.query(LocalUser).filter(
            LocalUser.linked_managed_user == name,
            LocalUser.linked_managed_user_namespace == namespace,
        ).update({"linked_managed_user": None, "linked_managed_user_namespace": None})
        db.commit()
    finally:
        db.close()
