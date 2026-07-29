import logging
import uuid
from datetime import UTC, datetime, timedelta

from kubernetes import client
from kubernetes.client.exceptions import ApiException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import AccessRequestRecord, JitRolePolicy
from ..models.access_request import MAX_TTL_MINUTES
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

    def export_requests(self, since: datetime | None = None, until: datetime | None = None) -> list[dict]:
        """Unpaginated — for CSV export (access-review evidence), not the list view."""
        filters = []
        if since:
            filters.append(AccessRequestRecord.requested_at >= since)
        if until:
            filters.append(AccessRequestRecord.requested_at <= until)
        stmt = select(AccessRequestRecord).where(*filters).order_by(AccessRequestRecord.requested_at)
        return [r.to_dict() for r in self.db.scalars(stmt)]

    def _get_or_404(self, request_id: str, *, for_update: bool = False) -> AccessRequestRecord:
        if for_update:
            # Row lock so concurrent approve/deny/revoke calls on the same
            # request serialize instead of racing: two admins clicking
            # approve/deny at once must not both pass the "pending" check
            # before either commits — the second one blocks here until the
            # first transaction commits, then re-reads the now-updated status
            # and correctly rejects instead of silently overwriting it (or,
            # for approve/approve, both hitting Kubernetes with the same
            # deterministic binding name).
            stmt = select(AccessRequestRecord).where(AccessRequestRecord.id == request_id).with_for_update()
            record = self.db.scalars(stmt).one_or_none()
        else:
            record = self.db.get(AccessRequestRecord, request_id)
        if not record:
            raise AccessRequestNotFoundError(f"Access request '{request_id}' not found")
        return record

    def _check_policy(self, role_kind: str, role_name: str, ttl_minutes: int) -> None:
        """Absence of a policy row means the default applies (eligible, capped at
        MAX_TTL_MINUTES) — this is a denylist/cap model, not an allowlist, so
        existing JIT usage keeps working unless an admin explicitly restricts a role."""
        policy = self.db.get(JitRolePolicy, (role_kind, role_name))
        if policy and not policy.eligible:
            raise AccessRequestError(f"{role_kind} '{role_name}' is not eligible for JIT access requests")
        max_ttl = policy.max_ttl_minutes if policy and policy.max_ttl_minutes is not None else MAX_TTL_MINUTES
        if ttl_minutes > max_ttl:
            raise AccessRequestError(
                f"Requested duration ({ttl_minutes} min) exceeds the {max_ttl}-minute limit for "
                f"{role_kind} '{role_name}'"
            )

    def list_policies(self) -> list[dict]:
        stmt = select(JitRolePolicy).order_by(JitRolePolicy.role_kind, JitRolePolicy.role_name)
        return [p.to_dict() for p in self.db.scalars(stmt)]

    def set_policy(self, role_kind: str, role_name: str, eligible: bool, max_ttl_minutes: int | None) -> dict:
        policy = self.db.get(JitRolePolicy, (role_kind, role_name))
        if policy is None:
            policy = JitRolePolicy(role_kind=role_kind, role_name=role_name)
            self.db.add(policy)
        policy.eligible = eligible
        policy.max_ttl_minutes = max_ttl_minutes
        self.db.commit()
        logger.info(
            "JIT policy set for %s '%s': eligible=%s max_ttl_minutes=%s",
            role_kind, role_name, eligible, max_ttl_minutes,
        )
        return policy.to_dict()

    def delete_policy(self, role_kind: str, role_name: str) -> None:
        policy = self.db.get(JitRolePolicy, (role_kind, role_name))
        if policy:
            self.db.delete(policy)
            self.db.commit()
            logger.info("JIT policy override removed for %s '%s'", role_kind, role_name)

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
        self._check_policy(role_kind, role_name, ttl_minutes)

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
        record = self._get_or_404(request_id, for_update=True)
        if record.status != "pending":
            raise AccessRequestError(f"Request is '{record.status}', not pending")
        if record.requester == reviewer:
            raise AccessRequestError("Cannot approve your own request")
        # Re-validate in case policy tightened between request and approval —
        # never silently truncate what was requested, fail loudly instead.
        self._check_policy(record.role_kind, record.role_name, record.ttl_minutes)

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
        record = self._get_or_404(request_id, for_update=True)
        if record.status != "pending":
            raise AccessRequestError(f"Request is '{record.status}', not pending")

        record.status = "denied"
        record.reviewed_by = reviewer
        record.reviewed_at = datetime.now(UTC)
        self.db.commit()
        logger.info("Access request %s denied by %s", request_id, reviewer)
        return record.to_dict()

    def revoke_request(self, request_id: str, reviewer: str) -> dict:
        record = self._get_or_404(request_id, for_update=True)
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
