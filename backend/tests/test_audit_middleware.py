from starlette.requests import Request

from app.core.audit_middleware import _actor_from_request, _redact
from app.core.auth import create_access_token


def _request(path: str = "/api/v1/admin/vault/config", query_string: str = "", bearer: str | None = None) -> Request:
    headers = [(b"authorization", f"Bearer {bearer}".encode())] if bearer else []
    scope = {
        "type": "http",
        "path": path,
        "query_string": query_string.encode(),
        "headers": headers,
    }
    return Request(scope)


def test_redact_masks_known_sensitive_keys():
    payload = {"username": "alice", "password": "hunter2", "role": "admin"}
    assert _redact(payload) == {"username": "alice", "password": "***redacted***", "role": "admin"}


def test_redact_is_case_insensitive():
    assert _redact({"Password": "x", "TOKEN": "y"}) == {"Password": "***redacted***", "TOKEN": "***redacted***"}


def test_redact_recurses_into_nested_dicts_and_lists():
    payload = {"outer": {"token": "abc"}, "items": [{"secret": "x"}, {"keep": "y"}]}
    assert _redact(payload) == {
        "outer": {"token": "***redacted***"},
        "items": [{"secret": "***redacted***"}, {"keep": "y"}],
    }


def test_redact_leaves_non_sensitive_values_untouched():
    payload = {"name": "my-role", "rules": [{"verbs": ["get"], "resources": ["pods"]}]}
    assert _redact(payload) == payload


def test_actor_from_request_reads_instance_role_for_instance_scoped_path():
    token = create_access_token("alice", {"_instance": "admin", "prod": "operator"})
    actor, role = _actor_from_request(_request(path="/api/v1/admin/vault/config", bearer=token))
    assert (actor, role) == ("alice", "admin")


def test_actor_from_request_reads_cluster_role_for_cluster_scoped_path():
    token = create_access_token("alice", {"_instance": "admin", "prod": "operator"})
    actor, role = _actor_from_request(
        _request(path="/api/v1/rbac/roles", query_string="cluster=prod", bearer=token)
    )
    assert (actor, role) == ("alice", "operator")


def test_actor_from_request_defaults_cluster_scoped_path_to_local():
    token = create_access_token("alice", {"local": "viewer", "prod": "admin"})
    actor, role = _actor_from_request(_request(path="/api/v1/users", bearer=token))
    assert (actor, role) == ("alice", "viewer")


def test_actor_from_request_none_without_bearer_prefix():
    assert _actor_from_request(_request(bearer=None)) == (None, None)


def test_actor_from_request_none_without_header():
    assert _actor_from_request(_request()) == (None, None)


def test_actor_from_request_none_on_garbage_token():
    req = Request({"type": "http", "path": "/x", "query_string": b"", "headers": [(b"authorization", b"Bearer not.a.valid.jwt")]})
    assert _actor_from_request(req) == (None, None)


def test_actor_from_request_none_on_wrong_token_type():
    from app.core.auth import create_register_token

    token = create_register_token("some-cluster")
    actor, role = _actor_from_request(_request(bearer=token))
    assert (actor, role) == (None, None)
