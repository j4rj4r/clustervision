import os

import pytest
from fastapi import HTTPException

from app.services import auth_service
from app.services.ldap_service import LdapAuthResult


def test_create_and_authenticate_local_user(db_session):
    auth_service.create_user("admin", "localpass123", "admin")
    result = auth_service.authenticate("admin", "localpass123")
    assert result == {"username": "admin", "role": "admin"}


def test_authenticate_wrong_password_fails(db_session):
    auth_service.create_user("admin", "localpass123", "admin")
    assert auth_service.authenticate("admin", "wrong") is None


def test_authenticate_unknown_user_ldap_disabled(db_session):
    assert auth_service.authenticate("nobody", "x") is None


def test_create_user_duplicate_raises_409(db_session):
    auth_service.create_user("admin", "pw", "admin")
    with pytest.raises(HTTPException) as exc_info:
        auth_service.create_user("admin", "pw2", "admin")
    assert exc_info.value.status_code == 409


def test_delete_user(db_session):
    auth_service.create_user("bob", "pw", "viewer")
    auth_service.delete_user("bob")
    assert auth_service.get_user_entry("bob") is None


def test_delete_nonexistent_user_raises_404(db_session):
    with pytest.raises(HTTPException) as exc_info:
        auth_service.delete_user("nobody")
    assert exc_info.value.status_code == 404


def test_change_password_and_role_for_local_user(db_session):
    auth_service.create_user("bob", "oldpass123", "viewer")
    auth_service.change_password("bob", "newpass456")
    assert auth_service.authenticate("bob", "oldpass123") is None
    assert auth_service.authenticate("bob", "newpass456") is not None

    auth_service.change_role("bob", "admin")
    assert auth_service.get_user_entry("bob")["role"] == "admin"


def test_ensure_default_admin_creates_once(db_session, monkeypatch):
    monkeypatch.setenv("CV_ADMIN_PASSWORD", "bootstrap-pass-123")
    auth_service.ensure_default_admin()
    assert auth_service.authenticate("admin", "bootstrap-pass-123") is not None

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
    assert result == {"username": "alice", "role": "viewer"}

    users = {u["username"]: u for u in auth_service.list_users()}
    assert users["alice"]["source"] == "ldap"
    assert users["alice"]["last_login_at"] is not None


def test_ldap_role_re_derived_on_every_login(db_session, monkeypatch):
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="viewer"),
    )
    auth_service.authenticate("alice", "adpass")
    assert auth_service.get_user_entry("alice")["role"] == "viewer"

    # AD group membership changed since — role must follow on next login,
    # not stay cached from the first provisioning
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="admin"),
    )
    auth_service.authenticate("alice", "adpass")
    assert auth_service.get_user_entry("alice")["role"] == "admin"


def test_ldap_wrong_password_denied(db_session, monkeypatch):
    monkeypatch.setattr(auth_service.ldap_service, "authenticate", lambda u, p: None)
    assert auth_service.authenticate("alice", "wrongpass") is None


def test_local_account_never_falls_back_to_ldap(db_session, monkeypatch):
    """A local account's own username must never be re-checked against LDAP,
    even if LDAP would happily authenticate someone by that name — local
    always wins for its own username."""
    auth_service.create_user("admin", "localpass123", "admin")
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
        auth_service.create_user("alice", "somepassword", "admin")
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


def test_change_role_rejected_for_ldap_account(db_session, monkeypatch):
    monkeypatch.setattr(
        auth_service.ldap_service, "authenticate",
        lambda u, p: LdapAuthResult(username=u, role="viewer"),
    )
    auth_service.authenticate("alice", "adpass")

    with pytest.raises(HTTPException) as exc_info:
        auth_service.change_role("alice", "admin")
    assert exc_info.value.status_code == 400
