import json
import uuid
import logging
from datetime import datetime, timezone

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

    def _load_history(self) -> list[dict]:
        try:
            cm = self.core_v1.read_namespaced_config_map(
                HISTORY_CONFIGMAP, self.settings.registry_namespace
            )
            return json.loads(cm.data.get("history.json", "[]"))
        except ApiException as e:
            if e.status == 404:
                return []
            raise

    def _save_history(self, history: list[dict]):
        data = {"history.json": json.dumps(history, indent=2)}
        try:
            self.core_v1.patch_namespaced_config_map(
                HISTORY_CONFIGMAP,
                self.settings.registry_namespace,
                client.V1ConfigMap(data=data),
            )
        except ApiException as e:
            if e.status == 404:
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
                raise

    def record_generation(self, user: str, user_type: str, namespace: str):
        history = self._load_history()
        history.append({
            "id": str(uuid.uuid4()),
            "user": user,
            "user_type": user_type,
            "namespace": namespace,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })
        if len(history) > 500:
            history = history[-500:]
        self._save_history(history)

    def list_history(self) -> list[dict]:
        return list(reversed(self._load_history()))

    def delete_history_entry(self, entry_id: str):
        history = self._load_history()
        self._save_history([e for e in history if e.get("id") != entry_id])

    def clear_history(self):
        self._save_history([])

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

    def revoke_sa_token(self, secret_name: str, namespace: str):
        self.core_v1.delete_namespaced_secret(secret_name, namespace)
        logger.info(f"Revoked SA token secret {secret_name} in {namespace}")

    def rotate_sa_token(self, secret_name: str, sa_name: str, namespace: str):
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
        logger.info(f"Rotated SA token secret {secret_name} in {namespace}")
