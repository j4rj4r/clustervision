import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.db.models import LoginAttempt
from app.services import auth_service
from app.services.ldap_service import LdapAuthResult


def test_create_and_authenticate_local_user(db_session):
    auth_service.create_user("admin", "localpass123")
    result = auth_service.authenticate("admin", "localpass123")
    assert result == {"username": "admin", "roles": {}}


def test_authenticate_wrong_password_fails(db_session):
    auth_service.create_user("admin", "localpass123")
    assert auth_service.authenticate("admin", "wrong") is None


def test_authenticate_unknown_user_ldap_disabled(db_session):
    assert auth_service.authenticate("nobody", "x") is None


def test_create_user_duplicate_raises_409(db_session):
    auth_service.create_user("admin", "pw")
    with pytest.raises(HTTPException) as exc_info:
        auth_service.create_user("admin", "pw2")
    assert exc_info.value.status_code == 409


def test_delete_user(db_session):
    auth_service.create_user("bob", "pw")
    auth_service.delete_user("bob")
    assert auth_service.get_user_entry("bob") is None


def test_delete_user_cascades_scope_roles(db_session):
    auth_service.create_user("bob", "pw")
    auth_service.set_scope_role("bob", "prod", "operator")
    auth_service.delete_user("bob")
    with pytest.raises(HTTPException) as exc_info:
        auth_service.list_scope_roles("bob")
    assert exc_info.value.status_code == 404


def test_delete_nonexistent_user_raises_404(db_session):
    with pytest.raises(HTTPException) as exc_info:
        auth_service.delete_user("nobody")
    assert exc_info.value.status_code == 404


def test_change_password_for_local_user(db_session):
    auth_service.create_user("bob", "oldpass123")
    auth_service.change_password("bob", "newpass456")
    assert auth_service.authenticate("bob", "oldpass123") is None
    assert auth_service.authenticate("bob", "newpass456") is not None


# ── Scope role assignments ───────────────────────────────────────────────────

def test_set_and_list_scope_roles(db_session):
    auth_service.create_user("bob", "pw")
    auth_service.set_scope_role("bob", "prod", "operator")
    auth_service.set_scope_role("bob", "_instance", "viewer")
    assert auth_service.list_scope_roles("bob") == [
        {"scope": "_instance", "role": "viewer"},
        {"scope": "prod", "role": "operator"},
    ]
    assert auth_service.get_user_entry("bob")["roles"] == {"_instance": "viewer", "prod": "operator"}


def test_set_scope_role_upserts(db_session):
    auth_service.create_user("bob", "pw")
    auth_service.set_scope_role("bob", "prod", "viewer")
    auth_service.set_scope_role("bob", "prod", "admin")
    assert auth_service.list_scope_roles("bob") == [{"scope": "prod", "role": "admin"}]


def test_delete_scope_role(db_session):
    auth_service.create_user("bob", "pw")
    auth_service.set_scope_role("bob", "prod", "operator")
    auth_service.delete_scope_role("bob", "prod")
    assert auth_service.list_scope_roles("bob") == []


def test_delete_nonexistent_scope_role_raises_404(db_session):
    auth_service.create_user("bob", "pw")
    with pytest.raises(HTTPException) as exc_info:
        auth_service.delete_scope_role("bob", "prod")
    assert exc_info.value.status_code == 404


def test_scope_role_rejected_for_nonexistent_user(db_session):
    with pytest.raises(HTTPException) as exc_info:
        auth_service.set_scope_role("nobody", "prod", "operator")
    assert exc_info.value.status_code == 404


def test_scope_role_rejected_for_ldap_account(db_session, monkeypatch):
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="viewer"),
    )
    auth_service.authenticate("alice", "adpass")

    with pytest.raises(HTTPException) as exc_info:
        auth_service.set_scope_role("alice", "prod", "admin")
    assert exc_info.value.status_code == 400


def test_list_scopes_includes_instance_local_and_registered_clusters(db_session):
    from app.db.models import RegisteredCluster

    db_session.add(RegisteredCluster(name="prod", api_url="https://prod", ca_data="", token=""))
    db_session.commit()
    assert auth_service.list_scopes() == ["_instance", "local", "prod"]


def test_ensure_default_admin_creates_once(db_session, monkeypatch):
    monkeypatch.setenv("CV_ADMIN_PASSWORD", "bootstrap-pass-123")
    auth_service.ensure_default_admin()
    assert auth_service.authenticate("admin", "bootstrap-pass-123") is not None
    assert auth_service.get_user_entry("admin")["roles"] == {"_instance": "admin", "local": "admin"}

    # Second call must not reset an already-customized admin
    auth_service.change_password("admin", "changed-by-user-456")
    auth_service.ensure_default_admin()
    assert auth_service.authenticate("admin", "changed-by-user-456") is not None
    os.environ.pop("CV_ADMIN_PASSWORD", None)


def test_ensure_default_admin_noop_without_env(db_session, monkeypatch):
    monkeypatch.delenv("CV_ADMIN_PASSWORD", raising=False)
    auth_service.ensure_default_admin()
    assert auth_service.list_users() == []


# ── LDAP integration ─────────────────────────────────────────────────────────

def test_ldap_first_login_provisions_local_user(db_session, monkeypatch):
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="viewer") if (u, p) == ("alice", "adpass") else None,
    )
    result = auth_service.authenticate("alice", "adpass")
    assert result == {"username": "alice", "roles": {"_instance": "viewer", "local": "viewer"}}

    users = {u["username"]: u for u in auth_service.list_users()}
    assert users["alice"]["source"] == "ldap"
    assert users["alice"]["last_login_at"] is not None


def test_ldap_role_re_derived_on_every_login(db_session, monkeypatch):
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="viewer"),
    )
    auth_service.authenticate("alice", "adpass")
    assert auth_service.get_user_entry("alice")["roles"] == {"_instance": "viewer", "local": "viewer"}

    # AD group membership changed since — role must follow on next login,
    # not stay cached from the first provisioning
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="admin"),
    )
    auth_service.authenticate("alice", "adpass")
    assert auth_service.get_user_entry("alice")["roles"] == {"_instance": "admin", "local": "admin"}


def test_ldap_role_resync_picks_up_registered_clusters(db_session, monkeypatch):
    from app.db.models import RegisteredCluster

    db_session.add(RegisteredCluster(name="prod", api_url="https://prod", ca_data="", token=""))
    db_session.commit()
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="admin"),
    )
    auth_service.authenticate("alice", "adpass")
    assert auth_service.get_user_entry("alice")["roles"] == {
        "_instance": "admin", "local": "admin", "prod": "admin",
    }


def test_ldap_wrong_password_denied(db_session, monkeypatch):
    monkeypatch.setattr(auth_service.ldap_service, "authenticate", lambda u, p: None)
    assert auth_service.authenticate("alice", "wrongpass") is None


def test_local_account_never_falls_back_to_ldap(db_session, monkeypatch):
    """A local account's own username must never be re-checked against LDAP,
    even if LDAP would happily authenticate someone by that name — local
    always wins for its own username."""
    auth_service.create_user("admin", "localpass123")
    ldap_was_called = False

    def fake_ldap(u, p):
        nonlocal ldap_was_called
        ldap_was_called = True
        return LdapAuthResult(username=u, role="admin")

    monkeypatch.setattr(auth_service.ldap_service, "authenticate", fake_ldap)
    assert auth_service.authenticate("admin", "wrong-local-password") is None
    assert ldap_was_called is False


def test_cannot_create_local_account_shadowing_ldap_account(db_session, monkeypatch):
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="viewer"),
    )
    auth_service.authenticate("alice", "adpass")  # provisions alice as source=ldap

    with pytest.raises(HTTPException) as exc_info:
        auth_service.create_user("alice", "somepassword")
    assert exc_info.value.status_code == 409


def test_change_password_rejected_for_ldap_account(db_session, monkeypatch):
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="viewer"),
    )
    auth_service.authenticate("alice", "adpass")

    with pytest.raises(HTTPException) as exc_info:
        auth_service.change_password("alice", "newpass")
    assert exc_info.value.status_code == 400


def test_check_login_rate_limit_allows_up_to_the_limit(db_session):
    for _ in range(10):
        auth_service.check_login_rate_limit("203.0.113.1")  # doesn't raise


def test_check_login_rate_limit_blocks_after_limit(db_session):
    for _ in range(10):
        auth_service.check_login_rate_limit("203.0.113.2")

    with pytest.raises(HTTPException) as exc_info:
        auth_service.check_login_rate_limit("203.0.113.2")
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "300"


def test_check_login_rate_limit_is_per_ip(db_session):
    for _ in range(10):
        auth_service.check_login_rate_limit("203.0.113.3")

    auth_service.check_login_rate_limit("203.0.113.4")  # separate bucket, doesn't raise


def test_check_login_rate_limit_ignores_attempts_outside_the_window(db_session):
    stale = datetime.now(UTC) - timedelta(minutes=10)
    for _ in range(10):
        db_session.add(LoginAttempt(id=str(uuid.uuid4()), ip="203.0.113.5", attempted_at=stale))
    db_session.commit()

    auth_service.check_login_rate_limit("203.0.113.5")  # stale attempts don't count, doesn't raise

    remaining = db_session.query(LoginAttempt).filter(LoginAttempt.ip == "203.0.113.5").all()
    assert len(remaining) == 1  # the 10 stale rows were pruned, only the fresh one remains
