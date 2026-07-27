import logging
import uuid
from datetime import UTC, datetime, timedelta

from kubernetes import client
from kubernetes.client.exceptions import ApiException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import AccessRequestRecord
from ..models.rbac import Subject, SubjectKind
from .rbac_service import RbacService

logger = logging.getLogger(__name__)

# Label used to find JIT-granted bindings cheaply (server-side selector)
# instead of listing every binding in the cluster.
JIT_LABEL = "clustervision.io/jit"
# Annotation carrying the expiry — not a label, since ISO timestamps contain
# characters (":") that aren't valid Kubernetes label values.
EXPIRES_ANNOTATION = "clustervision.io/expires-at"
REQUEST_ID_ANNOTATION = "clustervision.io/access-request-id"


class AccessRequestError(Exception):
    """Raised for invalid state transitions or bad input — maps to a 400."""


class AccessRequestNotFoundError(AccessRequestError):
    """Maps to a 404."""


class AccessRequestService:
    """K8s binding creation (the actual grant) is done through RbacService;
    the request registry itself is stored in the `access_requests` table."""

    def __init__(self, api_client: client.ApiClient, db: Session):
        self.rbac = RbacService(api_client)
        self.db = db

    def list_requests(self, requester: str | None = None) -> list[dict]:
        stmt = select(AccessRequestRecord).order_by(AccessRequestRecord.requested_at.desc())
        if requester:
            stmt = stmt.where(AccessRequestRecord.requester == requester)
        return [r.to_dict() for r in self.db.scalars(stmt)]

    def get_request(self, request_id: str) -> dict:
        return self._get_or_404(request_id).to_dict()

    def _get_or_404(self, request_id: str) -> AccessRequestRecord:
        record = self.db.get(AccessRequestRecord, request_id)
        if not record:
            raise AccessRequestNotFoundError(f"Access request '{request_id}' not found")
        return record

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

        record = AccessRequestRecord(
            id=str(uuid.uuid4()),
            requester=requester,
            target_username=target_username,
            user_kind=user_kind,
            sa_namespace=sa_namespace,
            role_name=role_name,
            role_kind=role_kind,
            namespace=namespace,
            ttl_minutes=ttl_minutes,
            reason=reason,
            status="pending",
            requested_at=datetime.now(UTC),
        )
        self.db.add(record)
        self.db.commit()
        logger.info(
            "Access request created by %s: %s '%s' for %s (%s)",
            requester, role_kind, role_name, target_username, record.id,
        )
        return record.to_dict()

    def approve_request(self, request_id: str, reviewer: str) -> dict:
        record = self._get_or_404(request_id)
        if record.status != "pending":
            raise AccessRequestError(f"Request is '{record.status}', not pending")
        if record.requester == reviewer:
            raise AccessRequestError("Cannot approve your own request")

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=record.ttl_minutes)
        binding_name = f"clustervision-jit-{record.id}"
        subject = Subject(
            kind=SubjectKind(record.user_kind),
            name=record.target_username,
            namespace=record.sa_namespace,
        )
        annotations = {
            EXPIRES_ANNOTATION: expires_at.isoformat(),
            REQUEST_ID_ANNOTATION: record.id,
        }
        labels = {JIT_LABEL: "true"}

        if record.namespace:
            self.rbac.create_role_binding(
                record.namespace, binding_name, record.role_name, record.role_kind,
                [subject], extra_labels=labels, extra_annotations=annotations,
            )
        else:
            self.rbac.create_cluster_role_binding(
                binding_name, record.role_name, [subject],
                extra_labels=labels, extra_annotations=annotations,
            )

        record.status = "approved"
        record.reviewed_by = reviewer
        record.reviewed_at = now
        record.expires_at = expires_at
        record.binding_name = binding_name
        self.db.commit()
        logger.info("Access request %s approved by %s, expires %s", request_id, reviewer, expires_at.isoformat())
        return record.to_dict()

    def deny_request(self, request_id: str, reviewer: str) -> dict:
        record = self._get_or_404(request_id)
        if record.status != "pending":
            raise AccessRequestError(f"Request is '{record.status}', not pending")

        record.status = "denied"
        record.reviewed_by = reviewer
        record.reviewed_at = datetime.now(UTC)
        self.db.commit()
        logger.info("Access request %s denied by %s", request_id, reviewer)
        return record.to_dict()

    def revoke_request(self, request_id: str, reviewer: str) -> dict:
        record = self._get_or_404(request_id)
        if record.status != "approved":
            raise AccessRequestError(f"Request is '{record.status}', not an active grant")

        try:
            if record.namespace:
                self.rbac.delete_role_binding(record.namespace, record.binding_name)
            else:
                self.rbac.delete_cluster_role_binding(record.binding_name)
        except ApiException as e:
            if e.status != 404:
                raise

        record.status = "revoked"
        record.reviewed_at = datetime.now(UTC)
        self.db.commit()
        logger.info("Access request %s revoked early by %s", request_id, reviewer)
        return record.to_dict()

    def mark_expired(self) -> None:
        now = datetime.now(UTC)
        stmt = select(AccessRequestRecord).where(
            AccessRequestRecord.status == "approved",
            AccessRequestRecord.expires_at <= now,
        )
        for record in self.db.scalars(stmt):
            record.status = "expired"
        self.db.commit()
