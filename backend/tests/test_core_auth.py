from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import HTTPException

from app.core import auth


def test_hash_password_roundtrip():
    hashed = auth.hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert auth.verify_password("correct-horse-battery-staple", hashed)
    assert not auth.verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = auth.create_access_token("alice", "admin")
    payload = auth.decode_token(token, expected_type="access")
    assert payload["sub"] == "alice"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip():
    token = auth.create_refresh_token("bob", "viewer")
    payload = auth.decode_token(token, expected_type="refresh")
    assert payload["sub"] == "bob"
    assert payload["role"] == "viewer"


def test_register_token_scoped_to_cluster_name():
    token = auth.create_register_token("prod-cluster")
    payload = auth.decode_token(token, expected_type="cluster_register")
    assert payload["sub"] == "prod-cluster"


def test_decode_token_rejects_wrong_type():
    token = auth.create_access_token("alice", "admin")
    with pytest.raises(HTTPException) as exc_info:
        auth.decode_token(token, expected_type="refresh")
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_expired():
    payload = {
        "sub": "alice",
        "role": "admin",
        "exp": datetime.now(UTC) - timedelta(minutes=1),
        "type": "access",
    }
    expired = jwt.encode(payload, auth._JWT_SECRET, algorithm=auth._JWT_ALGORITHM)
    with pytest.raises(HTTPException) as exc_info:
        auth.decode_token(expired, expected_type="access")
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_garbage():
    with pytest.raises(HTTPException) as exc_info:
        auth.decode_token("not-a-jwt", expected_type="access")
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_wrong_signature():
    forged = jwt.encode(
        {"sub": "alice", "role": "admin", "type": "access",
         "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "a-different-secret",
        algorithm=auth._JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc_info:
        auth.decode_token(forged, expected_type="access")
    assert exc_info.value.status_code == 401
