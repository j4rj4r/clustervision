from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.db.models import AccessRequestRecord
from app.services.access_request_service import (
    AccessRequestError,
    AccessRequestNotFoundError,
    AccessRequestService,
)


@pytest.fixture
def svc(db_session):
    service = AccessRequestService(api_client=MagicMock(), db=db_session)
    # Never let a test accidentally reach the real Kubernetes client.
    service.rbac.create_role_binding = MagicMock()
    service.rbac.create_cluster_role_binding = MagicMock()
    service.rbac.delete_role_binding = MagicMock()
    service.rbac.delete_cluster_role_binding = MagicMock()
    return service


def _create(svc, **overrides):
    payload = dict(
        requester="alice", target_username="sa-ci", user_kind="ServiceAccount",
        role_name="edit", role_kind="ClusterRole", ttl_minutes=60, reason="incident #1",
        namespace=None, sa_namespace="default",
    )
    payload.update(overrides)
    return svc.create_request(**payload)


def test_create_request_starts_pending(svc):
    record = _create(svc)
    assert record["status"] == "pending"
    assert record["requester"] == "alice"
    assert record["binding_name"] is None


def test_role_kind_role_requires_namespace(svc):
    with pytest.raises(AccessRequestError):
        _create(svc, role_kind="Role", namespace=None)


def test_list_requests_filters_by_requester(svc):
    _create(svc, requester="alice")
    _create(svc, requester="bob")
    assert len(svc.list_requests()) == 2
    assert len(svc.list_requests(requester="alice")) == 1


def test_get_nonexistent_request_raises_not_found(svc):
    with pytest.raises(AccessRequestNotFoundError):
        svc.get_request("does-not-exist")


def test_approve_creates_cluster_role_binding_and_updates_status(svc):
    record = _create(svc, namespace=None, role_kind="ClusterRole")
    approved = svc.approve_request(record["id"], reviewer="admin1")

    assert approved["status"] == "approved"
    assert approved["reviewed_by"] == "admin1"
    assert approved["binding_name"] == f"clustervision-jit-{record['id']}"
    svc.rbac.create_cluster_role_binding.assert_called_once()
    svc.rbac.create_role_binding.assert_not_called()


def test_approve_namespaced_role_creates_role_binding(svc):
    record = _create(svc, role_kind="Role", namespace="team-a", user_kind="User", sa_namespace=None)
    svc.approve_request(record["id"], reviewer="admin1")
    svc.rbac.create_role_binding.assert_called_once()
    svc.rbac.create_cluster_role_binding.assert_not_called()


def test_approved_binding_name_is_never_the_shared_permanent_name(svc):
    """A JIT grant must never collide with the `clustervision-{user}-{role}`
    name used by permanent assignments — the cleanup job deleting an expired
    JIT binding must not be able to touch a permanent one."""
    record = _create(svc, target_username="sa-ci", role_name="edit")
    approved = svc.approve_request(record["id"], reviewer="admin1")
    assert approved["binding_name"] != "clustervision-sa-ci-edit"
    assert approved["binding_name"].startswith("clustervision-jit-")


def test_cannot_approve_own_request(svc):
    record = _create(svc, requester="admin1")
    with pytest.raises(AccessRequestError):
        svc.approve_request(record["id"], reviewer="admin1")
    assert svc.get_request(record["id"])["status"] == "pending"


def test_cannot_approve_already_approved_request(svc):
    record = _create(svc)
    svc.approve_request(record["id"], reviewer="admin1")
    with pytest.raises(AccessRequestError):
        svc.approve_request(record["id"], reviewer="admin2")


def test_deny_only_from_pending(svc):
    record = _create(svc)
    denied = svc.deny_request(record["id"], reviewer="admin1")
    assert denied["status"] == "denied"
    assert denied["reviewed_by"] == "admin1"

    with pytest.raises(AccessRequestError):
        svc.deny_request(record["id"], reviewer="admin1")


def test_revoke_only_from_approved(svc):
    record = _create(svc)
    with pytest.raises(AccessRequestError):
        svc.revoke_request(record["id"], reviewer="admin1")

    svc.approve_request(record["id"], reviewer="admin1")
    revoked = svc.revoke_request(record["id"], reviewer="admin1")
    assert revoked["status"] == "revoked"
    svc.rbac.delete_cluster_role_binding.assert_called_once()


def test_revoke_deletes_namespaced_binding_when_namespaced(svc):
    record = _create(svc, role_kind="Role", namespace="team-a", user_kind="User", sa_namespace=None)
    svc.approve_request(record["id"], reviewer="admin1")
    svc.revoke_request(record["id"], reviewer="admin1")
    svc.rbac.delete_role_binding.assert_called_once()
    svc.rbac.delete_cluster_role_binding.assert_not_called()


def test_default_policy_allows_any_role_within_global_max(svc):
    record = _create(svc, role_name="edit", ttl_minutes=1440)  # global max
    assert record["status"] == "pending"


def test_default_policy_rejects_ttl_above_global_max(svc):
    with pytest.raises(AccessRequestError):
        _create(svc, role_name="edit", ttl_minutes=1441)


def test_ineligible_role_blocks_request_creation(svc):
    svc.set_policy("ClusterRole", "cluster-admin", eligible=False, max_ttl_minutes=None)
    with pytest.raises(AccessRequestError):
        _create(svc, role_name="cluster-admin")


def test_eligible_role_with_lower_ttl_cap_rejects_longer_requests(svc):
    svc.set_policy("ClusterRole", "edit", eligible=True, max_ttl_minutes=60)
    with pytest.raises(AccessRequestError):
        _create(svc, role_name="edit", ttl_minutes=120)
    # exactly at the cap is fine
    record = _create(svc, role_name="edit", ttl_minutes=60)
    assert record["status"] == "pending"


def test_policy_is_scoped_by_role_kind(svc):
    """A ClusterRole policy must not affect a Role of the same name."""
    svc.set_policy("ClusterRole", "edit", eligible=False, max_ttl_minutes=None)
    record = _create(svc, role_name="edit", role_kind="Role", namespace="team-a")
    assert record["status"] == "pending"


def test_approve_reraises_if_policy_tightened_after_request(svc):
    record = _create(svc, role_name="edit", ttl_minutes=120)
    svc.set_policy("ClusterRole", "edit", eligible=True, max_ttl_minutes=60)
    with pytest.raises(AccessRequestError):
        svc.approve_request(record["id"], reviewer="admin1")
    assert svc.get_request(record["id"])["status"] == "pending"


def test_set_policy_upserts(svc):
    first = svc.set_policy("ClusterRole", "view", eligible=True, max_ttl_minutes=30)
    assert first == {"role_kind": "ClusterRole", "role_name": "view", "eligible": True, "max_ttl_minutes": 30}
    second = svc.set_policy("ClusterRole", "view", eligible=False, max_ttl_minutes=None)
    assert second["eligible"] is False
    assert len(svc.list_policies()) == 1


def test_delete_policy_reverts_to_default(svc):
    svc.set_policy("ClusterRole", "cluster-admin", eligible=False, max_ttl_minutes=None)
    svc.delete_policy("ClusterRole", "cluster-admin")
    assert svc.list_policies() == []
    record = _create(svc, role_name="cluster-admin")
    assert record["status"] == "pending"


def test_delete_nonexistent_policy_is_a_noop(svc):
    svc.delete_policy("ClusterRole", "does-not-exist")  # must not raise


def test_export_requests_is_unpaginated_and_ordered(svc):
    for i in range(5):
        _create(svc, role_name=f"edit-{i}")
    rows = svc.export_requests()
    assert len(rows) == 5
    assert rows == sorted(rows, key=lambda r: r["requested_at"])


def test_export_requests_filters_by_date_range(svc, db_session):
    now = datetime.now(UTC)
    in_range = AccessRequestRecord(
        id="in-range", requester="a", target_username="t", user_kind="User",
        role_name="view", role_kind="ClusterRole", ttl_minutes=60, reason="x",
        status="pending", requested_at=now - timedelta(hours=1),
    )
    too_old = AccessRequestRecord(
        id="too-old", requester="a", target_username="t", user_kind="User",
        role_name="view", role_kind="ClusterRole", ttl_minutes=60, reason="x",
        status="pending", requested_at=now - timedelta(days=10),
    )
    db_session.add_all([in_range, too_old])
    db_session.commit()

    rows = svc.export_requests(since=now - timedelta(hours=2))
    assert [r["id"] for r in rows] == ["in-range"]


def test_mark_expired_only_touches_approved_and_past_expiry(svc, db_session):
    now = datetime.now(UTC)

    still_active = AccessRequestRecord(
        id="still-active", requester="a", target_username="t", user_kind="User",
        role_name="view", role_kind="ClusterRole", ttl_minutes=60, reason="x",
        status="approved", requested_at=now, expires_at=now + timedelta(minutes=30),
    )
    already_expired = AccessRequestRecord(
        id="already-expired", requester="a", target_username="t", user_kind="User",
        role_name="view", role_kind="ClusterRole", ttl_minutes=60, reason="x",
        status="approved", requested_at=now, expires_at=now - timedelta(minutes=5),
    )
    denied_long_ago = AccessRequestRecord(
        id="denied", requester="a", target_username="t", user_kind="User",
        role_name="view", role_kind="ClusterRole", ttl_minutes=60, reason="x",
        status="denied", requested_at=now, expires_at=now - timedelta(days=1),
    )
    db_session.add_all([still_active, already_expired, denied_long_ago])
    db_session.commit()

    svc.mark_expired()

    assert svc.get_request("still-active")["status"] == "approved"
    assert svc.get_request("already-expired")["status"] == "expired"
    assert svc.get_request("denied")["status"] == "denied"
