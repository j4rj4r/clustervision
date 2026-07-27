import base64
import json
import logging
import os

from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException

from ..core.auth import hash_password, verify_password
from ..core.kubernetes_client import get_local_api_client

logger = logging.getLogger(__name__)

_SECRET_NAME = "clustervision-auth"

# Read namespace from in-cluster serviceaccount file, fall back to env var
try:
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as _f:
        _NAMESPACE = _f.read().strip()
except FileNotFoundError:
    _NAMESPACE = os.environ.get("NAMESPACE", "default")


def _core_v1() -> k8s_client.CoreV1Api:
    return k8s_client.CoreV1Api(api_client=get_local_api_client())


_MAX_CONFLICT_RETRIES = 5


def _read_users_with_rv() -> tuple[dict, str | None]:
    try:
        secret = _core_v1().read_namespaced_secret(_SECRET_NAME, _NAMESPACE)
        raw = (secret.data or {}).get("users.json", "")
        users = json.loads(base64.b64decode(raw).decode()) if raw else {}
        return users, secret.metadata.resource_version
    except ApiException as e:
        if e.status == 404:
            return {}, None
        raise


def _read_users() -> dict:
    return _read_users_with_rv()[0]


def _update_users(mutate) -> None:
    """Atomically update the auth secret with optimistic locking.

    `mutate` receives the freshly-loaded users dict and returns the new one,
    or None to abort without writing. Retried on resourceVersion conflicts,
    so `mutate` must re-check its preconditions against its input.
    """
    last_exc = None
    for _ in range(_MAX_CONFLICT_RETRIES):
        users, rv = _read_users_with_rv()
        updated = mutate(users)
        if updated is None:
            return
        encoded = base64.b64encode(json.dumps(updated).encode()).decode()
        body = k8s_client.V1Secret(
            metadata=k8s_client.V1ObjectMeta(
                name=_SECRET_NAME, namespace=_NAMESPACE, resource_version=rv
            ),
            data={"users.json": encoded},
        )
        try:
            if rv is None:
                _core_v1().create_namespaced_secret(_NAMESPACE, body)
            else:
                _core_v1().replace_namespaced_secret(_SECRET_NAME, _NAMESPACE, body)
            return
        except ApiException as e:
            # 409 = stale resourceVersion or concurrent create — reload and retry
            if e.status == 409:
                last_exc = e
                continue
            raise
    raise last_exc


def ensure_default_admin() -> None:
    """Create initial admin from CV_ADMIN_PASSWORD env var if no users exist yet."""
    password = os.environ.get("CV_ADMIN_PASSWORD")
    if not password:
        return

    def _init(users: dict) -> dict | None:
        if users:
            return None
        logger.info("Creating default admin from CV_ADMIN_PASSWORD")
        return {"admin": {"hash": hash_password(password), "role": "admin"}}

    try:
        _update_users(_init)
    except Exception as e:
        logger.warning("Could not initialize default admin: %s", e)


_DUMMY_HASH = "$2b$12$Kix0GsNjGUDMHlTGtqKhCOSVRAf5Y/LNmXZnkgDlJwO7hzf5Q7Psy"


def authenticate(username: str, password: str) -> dict | None:
    users = _read_users()
    entry = users.get(username)
    # Always run bcrypt to prevent username enumeration via timing
    if not verify_password(password, entry["hash"] if entry else _DUMMY_HASH):
        return None
    if not entry:
        return None
    return {"username": username, "role": entry["role"]}


def get_user_entry(username: str) -> dict | None:
    """Current store entry for a user, or None if deleted — used to re-validate
    refresh tokens so removed/demoted users don't keep their old access."""
    entry = _read_users().get(username)
    return {"username": username, "role": entry["role"]} if entry else None


def list_users() -> list[dict]:
    users = _read_users()
    return [{"username": u, "role": v["role"]} for u, v in users.items()]


def create_user(username: str, password: str, role: str) -> None:
    hashed = hash_password(password)

    def _create(users: dict) -> dict:
        if username in users:
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail=f"User '{username}' already exists")
        return {**users, username: {"hash": hashed, "role": role}}

    _update_users(_create)


def delete_user(username: str) -> None:
    def _delete(users: dict) -> dict:
        if username not in users:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        return {u: v for u, v in users.items() if u != username}

    _update_users(_delete)


def change_password(username: str, new_password: str) -> None:
    hashed = hash_password(new_password)

    def _change(users: dict) -> dict:
        if username not in users:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        return {**users, username: {**users[username], "hash": hashed}}

    _update_users(_change)


def change_role(username: str, role: str) -> None:
    def _change(users: dict) -> dict:
        if username not in users:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"User '{username}' not found")
        return {**users, username: {**users[username], "role": role}}

    _update_users(_change)
