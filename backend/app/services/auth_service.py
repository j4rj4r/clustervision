import logging
import os

from sqlalchemy import select

from ..core.auth import hash_password, verify_password
from ..db.models import LocalUser
from ..db.session import new_session

logger = logging.getLogger(__name__)

_DUMMY_HASH = "$2b$12$Kix0GsNjGUDMHlTGtqKhCOSVRAf5Y/LNmXZnkgDlJwO7hzf5Q7Psy"


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
        db.add(LocalUser(username="admin", password_hash=hash_password(password), role="admin"))
        db.commit()
    except Exception as e:
        logger.warning("Could not initialize default admin: %s", e)
    finally:
        db.close()


def authenticate(username: str, password: str) -> dict | None:
    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        # Always run bcrypt to prevent username enumeration via timing
        if not verify_password(password, entry.password_hash if entry else _DUMMY_HASH):
            return None
        if not entry:
            return None
        return {"username": username, "role": entry.role}
    finally:
        db.close()


def get_user_entry(username: str) -> dict | None:
    """Current store entry for a user, or None if deleted — used to re-validate
    refresh tokens so removed/demoted users don't keep their old access."""
    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        return {"username": username, "role": entry.role} if entry else None
    finally:
        db.close()


def list_users() -> list[dict]:
    db = new_session()
    try:
        return [{"username": u.username, "role": u.role} for u in db.scalars(select(LocalUser))]
    finally:
        db.close()


def create_user(username: str, password: str, role: str) -> None:
    from fastapi import HTTPException

    db = new_session()
    try:
        if db.get(LocalUser, username) is not None:
            raise HTTPException(status_code=409, detail=f"User '{username}' already exists")
        db.add(LocalUser(username=username, password_hash=hash_password(password), role=role))
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
        entry.password_hash = hash_password(new_password)
        db.commit()
    finally:
        db.close()


def change_role(username: str, role: str) -> None:
    from fastapi import HTTPException

    db = new_session()
    try:
        entry = db.get(LocalUser, username)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        entry.role = role
        db.commit()
    finally:
        db.close()
