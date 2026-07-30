"""Full Alembic migration round trip against a real Postgres instance.

SQLite (what the rest of the suite runs against) can't reproduce the
failure modes this guards against — e.g. upgrading a database that
already had the pre-Alembic schema and needs a manual stamp first. Skipped
unless DATABASE_URL points at a real Postgres database, which only happens
in CI's dedicated migration-smoke-test step (the `postgres:16` service
container) — there's nothing to run this against otherwise.
"""
import os

import pytest
from alembic.config import Config

from alembic import command
from app.db.session import _ALEMBIC_INI

pytestmark = pytest.mark.skipif(
    "postgresql" not in os.environ.get("DATABASE_URL", ""),
    reason="requires a real Postgres DATABASE_URL (set by the CI migration-smoke-test step)",
)


def _alembic_config() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_ALEMBIC_INI.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return cfg


def test_upgrade_downgrade_upgrade_round_trip():
    """Upgrade to head, downgrade all the way to base, upgrade back to
    head — this exact sequence is what would have caught the "upgrading an
    already-existing pre-Alembic schema needs a stamp first" failure mode
    during the ConfigMap -> Postgres migration."""
    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
