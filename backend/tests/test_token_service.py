from unittest.mock import MagicMock

from app.services.token_service import TokenService


def _svc(db_session):
    return TokenService(api_client=MagicMock(), db=db_session)


def test_record_and_list_history(db_session):
    svc = _svc(db_session)
    svc.record_generation("alice", "certificate", "default")
    svc.record_generation("bob", "service_account", "ns-a")

    history = svc.list_history()
    assert len(history) == 2
    assert history[0]["user"] == "bob"  # most recent first


def test_delete_history_entry(db_session):
    svc = _svc(db_session)
    svc.record_generation("alice", "certificate", "default")
    entry_id = svc.list_history()[0]["id"]

    svc.delete_history_entry(entry_id)
    assert svc.list_history() == []


def test_retention_cap_at_500(db_session):
    svc = _svc(db_session)
    for i in range(510):
        svc.record_generation(f"user{i}", "certificate", "default")
    assert len(svc.list_history()) == 500


def test_clear_history(db_session):
    svc = _svc(db_session)
    svc.record_generation("alice", "certificate", "default")
    svc.record_generation("bob", "certificate", "default")
    svc.clear_history()
    assert svc.list_history() == []
