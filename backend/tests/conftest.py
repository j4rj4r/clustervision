import os

# Several modules read settings at import time (e.g. core/auth.py's
# CV_JWT_SECRET), so these must be set before anything under app/ is
# imported — conftest.py is guaranteed to load first.
os.environ.setdefault("CV_JWT_SECRET", "test-secret-not-for-production-but-long-enough")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import allure
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base

# Auto-labels every test with an Allure feature + severity based on which
# file it lives in — one place to maintain instead of decorating each of the
# (currently 109) test functions individually. Security-relevant modules
# default to CRITICAL; everything else is NORMAL. A handful of standout
# tests are bumped to BLOCKER by name in _SEVERITY_OVERRIDES below — kept
# here rather than as @allure.severity(...) decorators on the test functions
# themselves, so there's never more than one severity marker per item and no
# ambiguity about which one wins.
_FEATURE_BY_MODULE = {
    "test_core_auth": "Auth — JWT & passwords",
    "test_auth_service": "Authentication",
    "test_ldap_service": "LDAP",
    "test_registry_mixin": "Registry",
    "test_access_request_service": "Access Requests",
    "test_token_service": "Tokens",
    "test_cluster_service": "Clusters",
    "test_vault_service": "Vault Integration",
    "test_audit_middleware": "Audit Log",
    "test_audit_service": "Audit Log",
    "test_csv_export": "Compliance Exports",
}

_CRITICAL_MODULES = {
    "test_core_auth",
    "test_auth_service",
    "test_ldap_service",
    "test_audit_middleware",
}

_SEVERITY_OVERRIDES = {
    # LDAP injection guard — the single test that would matter most if it
    # ever silently started failing.
    ("test_ldap_service", "test_username_is_escaped_in_search_filter"): allure.severity_level.BLOCKER,
}


def pytest_collection_modifyitems(items):
    for item in items:
        module_name = item.module.__name__.rsplit(".", 1)[-1]
        feature = _FEATURE_BY_MODULE.get(module_name)
        if feature:
            item.add_marker(allure.feature(feature))

        default_severity = allure.severity_level.CRITICAL if module_name in _CRITICAL_MODULES else allure.severity_level.NORMAL
        severity = _SEVERITY_OVERRIDES.get((module_name, item.originalname or item.name), default_severity)
        item.add_marker(allure.severity(severity))


@pytest.fixture
def engine():
    """A single shared in-memory SQLite database for the test — StaticPool
    keeps one physical connection alive so every session sees the same data
    (a plain sqlite:///:memory: engine would hand out a fresh, empty database
    per connection)."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def patch_new_session(monkeypatch, session_factory):
    """Services that manage their own session lifecycle (auth_service,
    cluster_service, vault_service — all module-level singletons, not
    request-scoped) call new_session() internally rather than taking one as
    a constructor argument. Point every copy of that name at this test's
    in-memory database instead of the real one DATABASE_URL would open."""
    fake = lambda: session_factory()  # noqa: E731
    monkeypatch.setattr("app.db.session.new_session", fake)
    monkeypatch.setattr("app.services.auth_service.new_session", fake)
    monkeypatch.setattr("app.services.cluster_service.new_session", fake)


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """get_settings() is process-wide lru_cache'd — without this, a test
    that sets LDAP_* env vars would leak its Settings instance into whatever
    test runs next, regardless of file."""
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
