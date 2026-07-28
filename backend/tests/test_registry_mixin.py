from datetime import UTC, datetime

from app.core.registry import RegistryMixin


class _Registry(RegistryMixin):
    """Bare test double — RegistryMixin only needs self.db."""
    def __init__(self, db):
        self.db = db


def _user(name, type_="certificate", namespace="default", **extra):
    return {
        "name": name,
        "type": type_,
        "groups": [],
        "namespace": namespace,
        "created_at": datetime.now(UTC).isoformat(),
        **extra,
    }


def test_empty_registry(db_session):
    registry = _Registry(db_session)
    assert registry._load_registry() == []


def test_create_entry(db_session):
    registry = _Registry(db_session)
    registry._update_registry(lambda cur: [*cur, _user("alice")])
    loaded = registry._load_registry()
    assert len(loaded) == 1
    assert loaded[0]["name"] == "alice"
    assert loaded[0]["type"] == "certificate"


def test_same_name_different_namespace_coexist(db_session):
    """SA names are only unique per namespace — the compound key must allow
    this, unlike a naive name-only primary key."""
    registry = _Registry(db_session)
    registry._update_registry(lambda cur: [
        *cur,
        _user("sa-a", type_="service_account", namespace="ns-a"),
        _user("sa-a", type_="service_account", namespace="ns-b"),
    ])
    loaded = registry._load_registry()
    assert len(loaded) == 2
    namespaces = {u["namespace"] for u in loaded}
    assert namespaces == {"ns-a", "ns-b"}


def test_update_existing_entry(db_session):
    registry = _Registry(db_session)
    registry._update_registry(lambda cur: [*cur, _user("alice", groups=["dev"])])
    registry._update_registry(lambda cur: [
        {**u, "groups": ["dev", "ops"]} if u["name"] == "alice" else u
        for u in cur
    ])
    loaded = registry._load_registry()
    assert loaded[0]["groups"] == ["dev", "ops"]


def test_delete_entry(db_session):
    registry = _Registry(db_session)
    registry._update_registry(lambda cur: [*cur, _user("alice"), _user("bob")])
    registry._update_registry(lambda cur: [u for u in cur if u["name"] != "alice"])
    loaded = registry._load_registry()
    assert [u["name"] for u in loaded] == ["bob"]


def test_optional_fields_round_trip(db_session):
    registry = _Registry(db_session)
    registry._update_registry(lambda cur: [*cur, _user(
        "alice", csr_name="clustervision:alice", cert_expiry=datetime.now(UTC).isoformat(),
    )])
    loaded = registry._load_registry()[0]
    assert loaded["csr_name"] == "clustervision:alice"
    assert "cert_expiry" in loaded


def test_imported_flag_only_present_when_true(db_session):
    registry = _Registry(db_session)
    registry._update_registry(lambda cur: [*cur, _user("alice")])
    assert "imported" not in registry._load_registry()[0]

    registry._update_registry(lambda cur: [*cur, _user("bob", imported=True)])
    loaded = {u["name"]: u for u in registry._load_registry()}
    assert loaded["bob"]["imported"] is True
    assert "imported" not in loaded["alice"]


def test_type_isolation_between_cert_and_sa_users(db_session):
    """Both certificate and ServiceAccount users share one table — callers
    (CertificateService/ServiceAccountService) filter by type themselves."""
    registry = _Registry(db_session)
    registry._update_registry(lambda cur: [
        *cur,
        _user("alice", type_="certificate"),
        _user("sa-ci", type_="service_account"),
    ])
    loaded = registry._load_registry()
    cert_users = [u for u in loaded if u["type"] == "certificate"]
    sa_users = [u for u in loaded if u["type"] == "service_account"]
    assert len(cert_users) == 1
    assert len(sa_users) == 1
