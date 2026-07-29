from datetime import UTC, datetime, timedelta

from app.db.models import AuditLogEntry
from app.services.audit_service import AuditService


def _entry(db_session, *, actor, path, method="POST", status_code=200, minutes_ago=0, payload=None):
    entry = AuditLogEntry(
        timestamp=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        actor=actor,
        actor_role="admin",
        method=method,
        path=path,
        status_code=status_code,
        payload=payload,
    )
    db_session.add(entry)
    db_session.commit()
    return entry


def test_list_entries_empty_by_default(db_session):
    items, total = AuditService(db_session).list_entries()
    assert items == []
    assert total == 0


def test_list_entries_orders_newest_first(db_session):
    _entry(db_session, actor="alice", path="/api/v1/rbac/roles", minutes_ago=10)
    _entry(db_session, actor="alice", path="/api/v1/rbac/roles", minutes_ago=1)
    items, total = AuditService(db_session).list_entries()
    assert total == 2
    assert items[0]["path"] == "/api/v1/rbac/roles"
    assert items[0]["timestamp"] > items[1]["timestamp"]


def test_list_entries_filters_by_actor(db_session):
    _entry(db_session, actor="alice", path="/api/v1/rbac/roles")
    _entry(db_session, actor="bob", path="/api/v1/rbac/roles")
    items, total = AuditService(db_session).list_entries(actor="bob")
    assert total == 1
    assert items[0]["actor"] == "bob"


def test_list_entries_filters_by_path_substring(db_session):
    _entry(db_session, actor="alice", path="/api/v1/rbac/roles")
    _entry(db_session, actor="alice", path="/api/v1/tokens/xyz")
    items, total = AuditService(db_session).list_entries(path_contains="rbac")
    assert total == 1
    assert items[0]["path"] == "/api/v1/rbac/roles"


def test_list_entries_pagination(db_session):
    for i in range(5):
        _entry(db_session, actor="alice", path=f"/api/v1/rbac/roles/{i}", minutes_ago=i)
    items, total = AuditService(db_session).list_entries(limit=2, offset=2)
    assert total == 5
    assert len(items) == 2


def test_list_entries_preserves_redacted_payload(db_session):
    _entry(db_session, actor="alice", path="/api/v1/auth/users", payload={"username": "bob", "password": "***redacted***"})
    items, _ = AuditService(db_session).list_entries()
    assert items[0]["payload"] == {"username": "bob", "password": "***redacted***"}


def test_list_entries_includes_denied_attempts(db_session):
    _entry(db_session, actor="viewer1", path="/api/v1/admin/vault/config", method="DELETE", status_code=403)
    items, total = AuditService(db_session).list_entries()
    assert total == 1
    assert items[0]["status_code"] == 403


def test_export_entries_is_unpaginated(db_session):
    for i in range(60):
        _entry(db_session, actor="alice", path=f"/api/v1/rbac/roles/{i}", minutes_ago=i)
    rows = AuditService(db_session).export_entries()
    assert len(rows) == 60


def test_export_entries_orders_oldest_first(db_session):
    _entry(db_session, actor="alice", path="/newer", minutes_ago=1)
    _entry(db_session, actor="alice", path="/older", minutes_ago=10)
    rows = AuditService(db_session).export_entries()
    assert rows[0]["path"] == "/older"
    assert rows[1]["path"] == "/newer"


def test_export_entries_filters_by_date_range(db_session):
    from datetime import UTC, datetime, timedelta

    _entry(db_session, actor="alice", path="/in-range", minutes_ago=60)
    _entry(db_session, actor="alice", path="/too-old", minutes_ago=200)
    now = datetime.now(UTC)
    rows = AuditService(db_session).export_entries(since=now - timedelta(minutes=90))
    assert [r["path"] for r in rows] == ["/in-range"]


def test_export_entries_filters_by_actor_and_path(db_session):
    _entry(db_session, actor="alice", path="/api/v1/rbac/roles")
    _entry(db_session, actor="bob", path="/api/v1/rbac/roles")
    _entry(db_session, actor="alice", path="/api/v1/tokens/xyz")
    rows = AuditService(db_session).export_entries(actor="alice", path_contains="rbac")
    assert len(rows) == 1
    assert rows[0]["actor"] == "alice"
