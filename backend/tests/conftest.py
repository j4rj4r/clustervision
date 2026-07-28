import os

# Several modules read settings at import time (e.g. core/auth.py's
# CV_JWT_SECRET), so these must be set before anything under app/ is
# imported — conftest.py is guaranteed to load first.
os.environ.setdefault("CV_JWT_SECRET", "test-secret-not-for-production-but-long-enough")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base


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
