import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from ..config import get_settings
from ..models.rbac import Subject, SubjectKind
from .rbac_service import RbacService

logger = logging.getLogger(__name__)

REQUESTS_CONFIGMAP = "clustervision-access-requests"

# Label used to find JIT-granted bindings cheaply (server-side selector)
# instead of listing every binding in the cluster.
JIT_LABEL = "clustervision.io/jit"
# Annotation carrying the expiry — not a label, since ISO timestamps contain
# characters (":") that aren't valid Kubernetes label values.
EXPIRES_ANNOTATION = "clustervision.io/expires-at"
REQUEST_ID_ANNOTATION = "clustervision.io/access-request-id"

_MAX_CONFLICT_RETRIES = 5


class AccessRequestError(Exception):
    """Raised for invalid state transitions or bad input — maps to a 400."""


class AccessRequestNotFoundError(AccessRequestError):
    """Maps to a 404."""


class AccessRequestService:
    def __init__(self, api_client: client.ApiClient):
        self.core_v1 = client.CoreV1Api(api_client)
        self.rbac = RbacService(api_client)
        self.settings = get_settings()

    # ── Registry (ConfigMap-backed, same optimistic-locking shape as
    # TokenService's history — one ConfigMap per target cluster, since every
    # service here is instantiated against a cluster-scoped api_client) ──────

    def _read_requests(self) -> tuple[list[dict], str | None]:
        try:
            cm = self.core_v1.read_namespaced_config_map(REQUESTS_CONFIGMAP, self.settings.registry_namespace)
            return json.loads((cm.data or {}).get("requests.json", "[]")), cm.metadata.resource_version
        except ApiException as e:
            if e.status == 404:
                return [], None
            raise

    def _load_requests(self) -> list[dict]:
        return self._read_requests()[0]

    def _update_requests(self, mutate) -> None:
        last_exc = None
        for _ in range(_MAX_CONFLICT_RETRIES):
            requests, rv = self._read_requests()
            data = {"requests.json": json.dumps(mutate(requests), indent=2)}
            try:
                if rv is None:
                    self.core_v1.create_namespaced_config_map(
                        self.settings.registry_namespace,
                        client.V1ConfigMap(
                            metadata=client.V1ObjectMeta(
                                name=REQUESTS_CONFIGMAP,
                                namespace=self.settings.registry_namespace,
                            ),
                            data=data,
                        ),
                    )
                else:
                    self.core_v1.patch_namespaced_config_map(
                        REQUESTS_CONFIGMAP,
                        self.settings.registry_namespace,
                        client.V1ConfigMap(metadata=client.V1ObjectMeta(resource_version=rv), data=data),
                    )
                return
            except ApiException as e:
                if e.status == 409:
                    last_exc = e
                    continue
                raise
        raise last_exc

    # ── Queries ──────────────────────────────────────────────────────────────

    def list_requests(self, requester: str | None = None) -> list[dict]:
        items = self._load_requests()
        if requester:
            items = [r for r in items if r["requester"] == requester]
        return list(reversed(items))  # newest first

    def get_request(self, request_id: str) -> dict:
        for r in self._load_requests():
            if r["id"] == request_id:
                return r
        raise AccessRequestNotFoundError(f"Access request '{request_id}' not found")

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def create_request(
        self,
        requester: str,
        target_username: str,
        user_kind: str,
        role_name: str,
        role_kind: str,
        ttl_minutes: int,
        reason: str,
        namespace: str | None = None,
        sa_namespace: str | None = None,
    ) -> dict:
        if role_kind == "Role" and not namespace:
            raise AccessRequestError("namespace is required when requesting a Role")

        record = {
            "id": str(uuid.uuid4()),
            "requester": requester,
            "target_username": target_username,
            "user_kind": user_kind,
            "sa_namespace": sa_namespace,
            "role_name": role_name,
            "role_kind": role_kind,
            "namespace": namespace,
            "ttl_minutes": ttl_minutes,
            "reason": reason,
            "status": "pending",
            "requested_at": datetime.now(UTC).isoformat(),
            "reviewed_by": None,
            "reviewed_at": None,
            "expires_at": None,
            "binding_name": None,
        }
        self._update_requests(lambda current: [*current, record])
        logger.info(
            "Access request created by %s: %s '%s' for %s (%s)",
            requester, role_kind, role_name, target_username, record["id"],
        )
        return record

    def approve_request(self, request_id: str, reviewer: str) -> dict:
        record = self.get_request(request_id)
        if record["status"] != "pending":
            raise AccessRequestError(f"Request is '{record['status']}', not pending")
        if record["requester"] == reviewer:
            raise AccessRequestError("Cannot approve your own request")

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=record["ttl_minutes"])
        binding_name = f"clustervision-jit-{record['id']}"
        subject = Subject(
            kind=SubjectKind(record["user_kind"]),
            name=record["target_username"],
            namespace=record["sa_namespace"],
        )
        annotations = {
            EXPIRES_ANNOTATION: expires_at.isoformat(),
            REQUEST_ID_ANNOTATION: record["id"],
        }
        labels = {JIT_LABEL: "true"}

        # A dedicated binding name per request (not the shared
        # `clustervision-{user}-{role}` used by permanent assignments) — the
        # cleanup job deletes by name, and a permanent grant of the same role
        # must never be caught in that blast radius.
        if record["namespace"]:
            self.rbac.create_role_binding(
                record["namespace"], binding_name, record["role_name"], record["role_kind"],
                [subject], extra_labels=labels, extra_annotations=annotations,
            )
        else:
            self.rbac.create_cluster_role_binding(
                binding_name, record["role_name"], [subject],
                extra_labels=labels, extra_annotations=annotations,
            )

        def _mutate(current: list[dict]) -> list[dict]:
            return [
                {
                    **r,
                    "status": "approved",
                    "reviewed_by": reviewer,
                    "reviewed_at": now.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "binding_name": binding_name,
                }
                if r["id"] == request_id else r
                for r in current
            ]
        self._update_requests(_mutate)
        logger.info("Access request %s approved by %s, expires %s", request_id, reviewer, expires_at.isoformat())
        return self.get_request(request_id)

    def deny_request(self, request_id: str, reviewer: str) -> dict:
        record = self.get_request(request_id)
        if record["status"] != "pending":
            raise AccessRequestError(f"Request is '{record['status']}', not pending")

        def _mutate(current: list[dict]) -> list[dict]:
            return [
                {**r, "status": "denied", "reviewed_by": reviewer, "reviewed_at": datetime.now(UTC).isoformat()}
                if r["id"] == request_id else r
                for r in current
            ]
        self._update_requests(_mutate)
        logger.info("Access request %s denied by %s", request_id, reviewer)
        return self.get_request(request_id)

    def revoke_request(self, request_id: str, reviewer: str) -> dict:
        """Revoke an active grant early, before its natural expiry."""
        record = self.get_request(request_id)
        if record["status"] != "approved":
            raise AccessRequestError(f"Request is '{record['status']}', not an active grant")

        try:
            if record["namespace"]:
                self.rbac.delete_role_binding(record["namespace"], record["binding_name"])
            else:
                self.rbac.delete_cluster_role_binding(record["binding_name"])
        except ApiException as e:
            if e.status != 404:
                raise

        def _mutate(current: list[dict]) -> list[dict]:
            return [
                {**r, "status": "revoked", "reviewed_at": datetime.now(UTC).isoformat()}
                if r["id"] == request_id else r
                for r in current
            ]
        self._update_requests(_mutate)
        logger.info("Access request %s revoked early by %s", request_id, reviewer)
        return self.get_request(request_id)

    def mark_expired(self) -> None:
        """Called by the cleanup job after deleting expired bindings, so the
        registry (and the UI reading it) doesn't keep showing a stale
        'approved' status for a grant that no longer exists."""
        now = datetime.now(UTC)

        def _mutate(current: list[dict]) -> list[dict]:
            updated = []
            for r in current:
                if r["status"] == "approved" and r["expires_at"] and datetime.fromisoformat(r["expires_at"]) <= now:
                    r = {**r, "status": "expired"}
                updated.append(r)
            return updated
        self._update_requests(_mutate)
