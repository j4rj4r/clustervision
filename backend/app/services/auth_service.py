import json
import base64
import logging
import os

from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException

from ..core.kubernetes_client import get_local_api_client
from ..core.auth import hash_password, verify_password

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


def _read_users() -> dict:
    try:
        secret = _core_v1().read_namespaced_secret(_SECRET_NAME, _NAMESPACE)
        raw = (secret.data or {}).get("users.json", "")
        return json.loads(base64.b64decode(raw).decode()) if raw else {}
    except ApiException as e:
        if e.status == 404:
            return {}
        raise


def _write_users(users: dict) -> None:
    encoded = base64.b64encode(json.dumps(users).encode()).decode()
    body = k8s_client.V1Secret(
        metadata=k8s_client.V1ObjectMeta(name=_SECRET_NAME, namespace=_NAMESPACE),
        data={"users.json": encoded},
    )
    try:
        _core_v1().replace_namespaced_secret(_SECRET_NAME, _NAMESPACE, body)
    except ApiException as e:
        if e.status == 404:
            _core_v1().create_namespaced_secret(_NAMESPACE, body)
        else:
            raise


def ensure_default_admin() -> None:
    """Create initial admin from CV_ADMIN_PASSWORD env var if no users exist yet."""
    password = os.environ.get("CV_ADMIN_PASSWORD")
    if not password:
        return
    try:
        users = _read_users()
        if not users:
            logger.info("Creating default admin from CV_ADMIN_PASSWORD")
            users["admin"] = {"hash": hash_password(password), "role": "admin"}
            _write_users(users)
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


def list_users() -> list[dict]:
    users = _read_users()
    return [{"username": u, "role": v["role"]} for u, v in users.items()]


def create_user(username: str, password: str, role: str) -> None:
    users = _read_users()
    if username in users:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=f"User '{username}' already exists")
    users[username] = {"hash": hash_password(password), "role": role}
    _write_users(users)


def delete_user(username: str) -> None:
    users = _read_users()
    if username not in users:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    del users[username]
    _write_users(users)


def change_password(username: str, new_password: str) -> None:
    users = _read_users()
    if username not in users:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    users[username]["hash"] = hash_password(new_password)
    _write_users(users)


def change_role(username: str, role: str) -> None:
    users = _read_users()
    if username not in users:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")
    users[username]["role"] = role
    _write_users(users)
