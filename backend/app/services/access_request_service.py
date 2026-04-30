import json
import logging
import os
import uuid
from datetime import datetime, timezone

from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException

from ..core.kubernetes_client import get_local_api_client

logger = logging.getLogger(__name__)

_CM_NAME = "clustervision-access-requests"

try:
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as _f:
        _NAMESPACE = _f.read().strip()
except FileNotFoundError:
    _NAMESPACE = os.environ.get("NAMESPACE", "default")


def _core_v1() -> k8s_client.CoreV1Api:
    return k8s_client.CoreV1Api(api_client=get_local_api_client())


def _load() -> list[dict]:
    try:
        cm = _core_v1().read_namespaced_config_map(_CM_NAME, _NAMESPACE)
        raw = (cm.data or {}).get("requests.json", "[]")
        return json.loads(raw)
    except ApiException as e:
        if e.status == 404:
            return []
        raise


def _save(requests: list[dict]) -> None:
    payload = {"requests.json": json.dumps(requests)}
    try:
        cm = _core_v1().read_namespaced_config_map(_CM_NAME, _NAMESPACE)
        cm.data = payload
        _core_v1().replace_namespaced_config_map(_CM_NAME, _NAMESPACE, cm)
    except ApiException as e:
        if e.status == 404:
            _core_v1().create_namespaced_config_map(
                _NAMESPACE,
                k8s_client.V1ConfigMap(
                    metadata=k8s_client.V1ObjectMeta(
                        name=_CM_NAME,
                        labels={"managed-by": "clustervision"},
                    ),
                    data=payload,
                ),
            )
        else:
            raise


def list_requests(username: str | None = None, status: str | None = None) -> list[dict]:
    reqs = _load()
    if username:
        reqs = [r for r in reqs if r["requester"] == username]
    if status:
        reqs = [r for r in reqs if r["status"] == status]
    return sorted(reqs, key=lambda r: r["created_at"], reverse=True)


def create_request(
    requester: str,
    role_name: str,
    role_kind: str,
    namespace: str | None,
    justification: str,
) -> dict:
    req = {
        "id": str(uuid.uuid4()),
        "requester": requester,
        "role_name": role_name,
        "role_kind": role_kind,
        "namespace": namespace,
        "justification": justification,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "resolved_by": None,
        "denial_reason": None,
    }
    reqs = _load()
    reqs.append(req)
    _save(reqs)
    logger.info("Access request created: %s by %s for %s", req["id"], requester, role_name)
    return req


def resolve_request(request_id: str, admin: str, approved: bool, denial_reason: str | None = None) -> dict:
    reqs = _load()
    req = next((r for r in reqs if r["id"] == request_id), None)
    if not req:
        raise KeyError(request_id)
    if req["status"] != "pending":
        raise ValueError("Request is not pending")
    req["status"] = "approved" if approved else "denied"
    req["resolved_at"] = datetime.now(timezone.utc).isoformat()
    req["resolved_by"] = admin
    req["denial_reason"] = denial_reason
    _save(reqs)
    return req


def cancel_request(request_id: str, requester: str) -> None:
    reqs = _load()
    req = next((r for r in reqs if r["id"] == request_id), None)
    if not req:
        raise KeyError(request_id)
    if req["requester"] != requester:
        raise PermissionError("Cannot cancel another user's request")
    if req["status"] != "pending":
        raise ValueError("Only pending requests can be cancelled")
    updated = [r for r in reqs if r["id"] != request_id]
    _save(updated)
