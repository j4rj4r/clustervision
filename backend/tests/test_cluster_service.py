import pytest

from app.services.cluster_service import ClusterService


@pytest.fixture
def svc(monkeypatch):
    service = ClusterService()
    # add_cluster probes real connectivity before persisting — irrelevant to
    # the registry CRUD logic under test here, and there's no real cluster
    # to reach in a unit test.
    monkeypatch.setattr(service, "verify_connectivity", lambda *a, **k: None)
    return service


def test_empty_registry(svc, db_session):
    assert svc.list_clusters() == []


def test_add_cluster(svc, db_session):
    result = svc.add_cluster("prod", "https://prod:6443", "Y2E=", "tok1")
    assert result == {"name": "prod", "api_url": "https://prod:6443", "is_local": False}
    assert svc.list_clusters() == [{"name": "prod", "api_url": "https://prod:6443", "is_local": False}]


def test_add_cluster_rejects_duplicate_name(svc, db_session):
    svc.add_cluster("prod", "https://prod:6443", "Y2E=", "tok1")
    with pytest.raises(ValueError):
        svc.add_cluster("prod", "https://other:6443", "Y2E=", "tok2")


def test_add_cluster_rejects_reserved_local_name(svc, db_session):
    with pytest.raises(ValueError):
        svc.add_cluster("local", "https://x:6443", "Y2E=", "tok")


def test_remove_cluster(svc, db_session):
    svc.add_cluster("prod", "https://prod:6443", "Y2E=", "tok1")
    svc.remove_cluster("prod")
    assert svc.list_clusters() == []


def test_remove_nonexistent_cluster_raises(svc, db_session):
    with pytest.raises(ValueError):
        svc.remove_cluster("does-not-exist")


def test_update_configs_credential_rotation(svc, db_session):
    """_update_configs must apply targeted changes (e.g. a token rotation)
    without disturbing other registered clusters."""
    svc.add_cluster("prod", "https://prod:6443", "Y2E=", "old-token")
    svc.add_cluster("staging", "https://staging:6443", "Y2E=", "staging-token")

    svc._update_configs(lambda cur: [
        {**c, "token": "new-token"} if c["name"] == "prod" else c for c in cur
    ])

    configs = {c["name"]: c for c in svc._load_configs()}
    assert configs["prod"]["token"] == "new-token"
    assert configs["staging"]["token"] == "staging-token"
