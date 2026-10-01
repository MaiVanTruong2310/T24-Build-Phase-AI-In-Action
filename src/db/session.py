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
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=settings.database_pool_recycle_seconds,
        pool_use_lifo=True,
        connect_args={
            "connect_timeout": settings.database_connect_timeout_seconds,
            "application_name": settings.app_name[:63],
        },
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
    """Create missing ORM tables for explicit local bootstrap only.

    Alembic is the normal schema-management path. The advisory transaction
    lock keeps this legacy opt-in path safe when multiple API processes start
    at the same time.
    """
    engine = get_engine()
    table_names = sorted(Base.metadata.tables)
    logger.info("database.initialize_database creating missing tables", extra={"table_count": len(table_names)})
    async with engine.begin() as connection:
        await connection.execute(text("SELECT pg_advisory_xact_lock(124001)"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await connection.run_sync(Base.metadata.create_all)
    logger.info("database.initialize_database tables ready", extra={"table_count": len(table_names)})


async def check_database_connection() -> None:
    """Run the smallest useful query for readiness checks."""
    async with get_engine().connect() as connection:
        await connection.execute(text("SELECT 1"))


async def close_database() -> None:
    """Release pooled PostgreSQL connections during application shutdown."""
    settings = get_settings()
    if settings.database_url:
        await get_engine().dispose()
