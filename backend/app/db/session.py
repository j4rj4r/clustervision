import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings

logger = logging.getLogger(__name__)

_ALEMBIC_INI = Path(__file__).resolve().parent.parent.parent / "alembic.ini"


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def init_db() -> None:
    """Bring the schema up to the latest Alembic revision. Safe to call on
    every startup — a no-op once the database is already at head.

    A first-time database (no `alembic_version` table yet) starts from
    revision 0001 and applies every migration in order, so a fresh install
    needs nothing extra. A database that already had the pre-Alembic schema
    (created by the old create_all()-based init_db()) needs a one-time
    `alembic stamp 0001_initial_schema` run against it before upgrading —
    see the README."""
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_ALEMBIC_INI.parent / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(cfg, "head")
    logger.info("Database schema up to date")


def new_session() -> Session:
    return _session_factory()()
