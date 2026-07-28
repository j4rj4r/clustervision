from app.core.audit_middleware import _actor_from_header, _redact
from app.core.auth import create_access_token


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


def test_actor_from_header_decodes_valid_bearer_token():
    token = create_access_token("alice", "admin")
    actor, role = _actor_from_header(f"Bearer {token}")
    assert (actor, role) == ("alice", "admin")


def test_actor_from_header_none_without_bearer_prefix():
    assert _actor_from_header("not-a-bearer-token") == (None, None)


def test_actor_from_header_none_without_header():
    assert _actor_from_header(None) == (None, None)


def test_actor_from_header_none_on_garbage_token():
    assert _actor_from_header("Bearer not.a.valid.jwt") == (None, None)


def test_actor_from_header_none_on_wrong_token_type():
    from app.core.auth import create_register_token

    token = create_register_token("some-cluster")
    assert _actor_from_header(f"Bearer {token}") == (None, None)
