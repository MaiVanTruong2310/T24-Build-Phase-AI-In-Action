"""Async SQLAlchemy engine and session factory for PostgreSQL."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src import models as _models  # noqa: F401
from src.config import get_settings
from src.core.logging import get_logger
from src.db.base import Base

logger = get_logger(__name__)


def _async_database_url(database_url: str) -> str:
    """Convert a standard PostgreSQL URL to the psycopg async dialect."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


@lru_cache
def get_engine():
    """Create the shared async database engine lazily."""
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be configured")
    return create_async_engine(
        _async_database_url(settings.database_url),
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield one database session for a FastAPI dependency."""
    async with get_session_factory()() as session:
        yield session


async def initialize_database() -> None:
    """Create missing ORM tables during the first application startup."""
    engine = get_engine()
    table_names = sorted(Base.metadata.tables)
    logger.info("database.initialize_database creating missing tables", extra={"table_count": len(table_names)})
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await connection.run_sync(Base.metadata.create_all)
    logger.info("database.initialize_database tables ready", extra={"table_count": len(table_names)})
