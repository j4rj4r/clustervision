import logging
from datetime import UTC, datetime

from fastapi import HTTPException
from kubernetes import client
from kubernetes.client.exceptions import ApiException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models import TokenHistoryEntry

logger = logging.getLogger(__name__)


class TokenService:
    def __init__(self, api_client: client.ApiClient, db: Session):
        self.core_v1 = client.CoreV1Api(api_client)
        self.db = db

    # ── History ───────────────────────────────────────────────────────────────

    def record_generation(self, user: str, user_type: str, namespace: str):
        self.db.add(TokenHistoryEntry(
            user=user, user_type=user_type, namespace=namespace, generated_at=datetime.now(UTC),
        ))
        # Same 500-entry retention the ConfigMap version had — old entries are
        # pure audit noise past that point.
        ids = self.db.scalars(
            select(TokenHistoryEntry.id).order_by(TokenHistoryEntry.generated_at.desc()).offset(500)
        ).all()
        if ids:
            self.db.execute(delete(TokenHistoryEntry).where(TokenHistoryEntry.id.in_(ids)))
        self.db.commit()

    def list_history(self) -> list[dict]:
        rows = self.db.scalars(select(TokenHistoryEntry).order_by(TokenHistoryEntry.generated_at.desc()))
        return [r.to_dict() for r in rows]

    def delete_history_entry(self, entry_id: str):
        self.db.execute(delete(TokenHistoryEntry).where(TokenHistoryEntry.id == entry_id))
        self.db.commit()

    def clear_history(self):
        self.db.execute(delete(TokenHistoryEntry))
        self.db.commit()

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
