"""Standalone cleanup job — deletes JIT-granted RoleBindings/ClusterRoleBindings
past their `clustervision.io/expires-at` annotation, across the local cluster
and every registered remote cluster.

Run as a Kubernetes CronJob using the same image and ServiceAccount as the
backend Deployment: `python -m app.jobs.expire_access_bindings`.
"""

import logging
from datetime import UTC, datetime

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from ..core.kubernetes_client import get_local_api_client
from ..db.session import init_db, new_session
from ..services.access_request_service import (
    EXPIRES_ANNOTATION,
    JIT_LABEL,
    AccessRequestService,
)
from ..services.cluster_service import get_cluster_service

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def _is_expired(annotations: dict | None, now: datetime) -> bool:
    expiry = (annotations or {}).get(EXPIRES_ANNOTATION)
    if not expiry:
        return False
    try:
        return datetime.fromisoformat(expiry) <= now
    except ValueError:
        logger.warning("Unparseable %s annotation: %r", EXPIRES_ANNOTATION, expiry)
        return False


def _reconcile(api_client: client.ApiClient, cluster_label: str) -> int:
    rbac_v1 = client.RbacAuthorizationV1Api(api_client)
    now = datetime.now(UTC)
    revoked = 0

    for crb in rbac_v1.list_cluster_role_binding(label_selector=f"{JIT_LABEL}=true").items:
        if not _is_expired(crb.metadata.annotations, now):
            continue
        try:
            rbac_v1.delete_cluster_role_binding(crb.metadata.name)
            revoked += 1
            logger.info("[%s] Expired ClusterRoleBinding deleted: %s", cluster_label, crb.metadata.name)
        except ApiException as e:
            if e.status != 404:
                raise

    for rb in rbac_v1.list_role_binding_for_all_namespaces(label_selector=f"{JIT_LABEL}=true").items:
        if not _is_expired(rb.metadata.annotations, now):
            continue
        try:
            rbac_v1.delete_namespaced_role_binding(rb.metadata.name, rb.metadata.namespace)
            revoked += 1
            logger.info("[%s] Expired RoleBinding deleted: %s/%s", cluster_label, rb.metadata.namespace, rb.metadata.name)
        except ApiException as e:
            if e.status != 404:
                raise

    return revoked


def main() -> None:
    init_db()

    total = _reconcile(get_local_api_client(), "local")

    cluster_svc = get_cluster_service()
    for c in cluster_svc.list_clusters():
        try:
            total += _reconcile(cluster_svc.get_api_client(c["name"]), c["name"])
        except Exception:
            logger.exception("Failed to reconcile cluster %s", c["name"])

    # The request registry is a single central database (unlike the old
    # per-cluster ConfigMaps), so this only needs to run once regardless of
    # how many clusters were reconciled above.
    if total:
        db = new_session()
        try:
            # api_client isn't used by mark_expired() — the local client is
            # enough to satisfy the constructor.
            AccessRequestService(get_local_api_client(), db).mark_expired()
        finally:
            db.close()

    logger.info("JIT access cleanup complete — %d binding(s) revoked", total)


if __name__ == "__main__":
    main()
