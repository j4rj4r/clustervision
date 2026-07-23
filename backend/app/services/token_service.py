import json
import uuid
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from ..config import get_settings

logger = logging.getLogger(__name__)

HISTORY_CONFIGMAP = "clustervision-token-history"


class TokenService:
    def __init__(self, api_client: client.ApiClient):
        self.core_v1 = client.CoreV1Api(api_client)
        self.settings = get_settings()

    # ── History ───────────────────────────────────────────────────────────────

    def _read_history(self) -> tuple[list[dict], str | None]:
        try:
            cm = self.core_v1.read_namespaced_config_map(
                HISTORY_CONFIGMAP, self.settings.registry_namespace
            )
            return json.loads((cm.data or {}).get("history.json", "[]")), cm.metadata.resource_version
        except ApiException as e:
            if e.status == 404:
                return [], None
            raise

    def _load_history(self) -> list[dict]:
        return self._read_history()[0]

    def _update_history(self, mutate):
        """Atomically update the history ConfigMap with optimistic locking —
        retried on resourceVersion conflicts."""
        last_exc = None
        for _ in range(5):
            history, rv = self._read_history()
            data = {"history.json": json.dumps(mutate(history), indent=2)}
            try:
                if rv is None:
                    self.core_v1.create_namespaced_config_map(
                        self.settings.registry_namespace,
                        client.V1ConfigMap(
                            metadata=client.V1ObjectMeta(
                                name=HISTORY_CONFIGMAP,
                                namespace=self.settings.registry_namespace,
                            ),
                            data=data,
                        ),
                    )
                else:
                    self.core_v1.patch_namespaced_config_map(
                        HISTORY_CONFIGMAP,
                        self.settings.registry_namespace,
                        client.V1ConfigMap(
                            metadata=client.V1ObjectMeta(resource_version=rv),
                            data=data,
                        ),
                    )
                return
            except ApiException as e:
                if e.status == 409:
                    last_exc = e
                    continue
                raise
        raise last_exc

    def record_generation(self, user: str, user_type: str, namespace: str):
        entry = {
            "id": str(uuid.uuid4()),
            "user": user,
            "user_type": user_type,
            "namespace": namespace,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._update_history(lambda history: (history + [entry])[-500:])

    def list_history(self) -> list[dict]:
        return list(reversed(self._load_history()))

    def delete_history_entry(self, entry_id: str):
        self._update_history(lambda history: [e for e in history if e.get("id") != entry_id])

    def clear_history(self):
        self._update_history(lambda history: [])

    # ── SA token secrets ──────────────────────────────────────────────────────

    def list_sa_tokens(self) -> list[dict]:
        secrets = self.core_v1.list_secret_for_all_namespaces(
            label_selector="managed-by=clustervision"
        )
        result = []
        for s in secrets.items:
            if s.type != "kubernetes.io/service-account-token":
                continue
            sa_name = (s.metadata.annotations or {}).get("kubernetes.io/service-account.name", "")
            result.append({
                "secret_name": s.metadata.name,
                "sa_name": sa_name,
                "namespace": s.metadata.namespace,
                "created_at": s.metadata.creation_timestamp.isoformat()
                    if s.metadata.creation_timestamp else None,
                "token_present": bool((s.data or {}).get("token")),
            })
        return result

    def _read_managed_token_secret(self, secret_name: str, namespace: str) -> client.V1Secret:
        """Fetch a Secret and refuse to touch it unless it is a ClusterVision-managed
        service-account token — the app's RBAC can delete any secret cluster-wide,
        so this API must not become an arbitrary-secret-deletion endpoint."""
        try:
            secret = self.core_v1.read_namespaced_secret(secret_name, namespace)
        except ApiException as e:
            if e.status == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Secret '{secret_name}' not found in namespace '{namespace}'",
                )
            raise
        labels = secret.metadata.labels or {}
        if (
            secret.type != "kubernetes.io/service-account-token"
            or labels.get("managed-by") != "clustervision"
        ):
            raise HTTPException(
                status_code=403,
                detail=f"Secret '{secret_name}' is not a ClusterVision-managed SA token",
            )
        return secret

    def revoke_sa_token(self, secret_name: str, namespace: str):
        self._read_managed_token_secret(secret_name, namespace)
        self.core_v1.delete_namespaced_secret(secret_name, namespace)
        logger.info("Revoked SA token secret %s in %s", secret_name, namespace)

    def rotate_sa_token(self, secret_name: str, sa_name: str, namespace: str):
        existing = self._read_managed_token_secret(secret_name, namespace)
        annotated_sa = (existing.metadata.annotations or {}).get(
            "kubernetes.io/service-account.name"
        )
        if annotated_sa != sa_name:
            raise HTTPException(
                status_code=400,
                detail=f"Secret '{secret_name}' belongs to ServiceAccount "
                       f"'{annotated_sa}', not '{sa_name}'",
            )
        try:
            self.core_v1.delete_namespaced_secret(secret_name, namespace)
        except ApiException as e:
            if e.status != 404:
                raise
        self.core_v1.create_namespaced_secret(
            namespace,
            client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=secret_name,
                    namespace=namespace,
                    annotations={"kubernetes.io/service-account.name": sa_name},
                    labels={"managed-by": "clustervision"},
                ),
                type="kubernetes.io/service-account-token",
            ),
        )
        logger.info("Rotated SA token secret %s in %s", secret_name, namespace)
