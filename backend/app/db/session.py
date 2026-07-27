import logging
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings
from .models import Base

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def init_db() -> None:
    """Create tables if they don't exist yet. A plain create_all is enough
    for a single-table schema — introduce Alembic if/when real migrations
    (altering existing columns, not just adding tables) are needed."""
    Base.metadata.create_all(get_engine())
    logger.info("Database schema ensured")


def new_session() -> Session:
    return _session_factory()()
