import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.core.dependencies import (
    auth_gate,
    instance_gate,
    require_admin,
    require_approver,
)
from app.models.auth import UserInfo


def _request(method: str) -> Request:
    return Request(
        {
            "type": "http",
            "path": "/x",
            "method": method,
            "query_string": b"",
            "headers": [],
        }
    )


def _user(**roles: str) -> UserInfo:
    return UserInfo(username="alice", roles=roles)


# ── require_admin (instance scope) ──────────────────────────────────────────


def test_require_admin_allows_instance_admin():
    user = _user(_instance="admin")
    assert require_admin(user) is user


@pytest.mark.parametrize("role", [None, "viewer", "operator", "approver"])
def test_require_admin_rejects_anything_but_instance_admin(role):
    roles = {"_instance": role} if role else {}
    with pytest.raises(HTTPException) as exc_info:
        require_admin(_user(**roles))
    assert exc_info.value.status_code == 403


# ── require_approver (instance scope) ───────────────────────────────────────


@pytest.mark.parametrize("role", ["admin", "approver"])
def test_require_approver_allows_admin_and_approver(role):
    user = _user(_instance=role)
    assert require_approver(user) is user


@pytest.mark.parametrize("role", [None, "viewer", "operator"])
def test_require_approver_rejects_others(role):
    roles = {"_instance": role} if role else {}
    with pytest.raises(HTTPException) as exc_info:
        require_approver(_user(**roles))
    assert exc_info.value.status_code == 403


# ── instance_gate ────────────────────────────────────────────────────────────


def test_instance_gate_allows_get_for_any_authenticated_user():
    user = _user()
    assert instance_gate(_request("GET"), user) is user


def test_instance_gate_blocks_mutation_without_instance_admin():
    with pytest.raises(HTTPException) as exc_info:
        instance_gate(_request("POST"), _user(_instance="viewer"))
    assert exc_info.value.status_code == 403


def test_instance_gate_allows_mutation_for_instance_admin():
    user = _user(_instance="admin")
    assert instance_gate(_request("DELETE"), user) is user


# ── auth_gate (cluster scope) ───────────────────────────────────────────────


def test_auth_gate_blocks_get_with_no_role_on_target_cluster():
    with pytest.raises(HTTPException) as exc_info:
        auth_gate(_request("GET"), "prod", _user(local="admin"))
    assert exc_info.value.status_code == 403


def test_auth_gate_allows_get_for_viewer_on_target_cluster():
    user = _user(prod="viewer")
    assert auth_gate(_request("GET"), "prod", user) is user


def test_auth_gate_blocks_mutation_for_viewer_on_target_cluster():
    with pytest.raises(HTTPException) as exc_info:
        auth_gate(_request("POST"), "prod", _user(prod="viewer"))
    assert exc_info.value.status_code == 403


@pytest.mark.parametrize("role", ["operator", "admin"])
def test_auth_gate_allows_mutation_for_operator_or_admin_on_target_cluster(role):
    user = _user(prod=role)
    assert auth_gate(_request("PUT"), "prod", user) is user


def test_auth_gate_is_scoped_per_cluster_not_global():
    """Admin on one cluster grants nothing on another — no more global role."""
    user = _user(prod="admin")
    with pytest.raises(HTTPException) as exc_info:
        auth_gate(_request("GET"), "staging", user)
    assert exc_info.value.status_code == 403
