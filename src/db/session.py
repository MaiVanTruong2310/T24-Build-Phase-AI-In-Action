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


def _shared_database_url(database_url: str, auth_database_url: str) -> str | None:
    """Reuse one pool when both URLs address the same DB and only SSL differs."""
    if not database_url or not auth_database_url:
        return None
    if database_url == auth_database_url:
        return database_url
    catalog_base, _, catalog_query = database_url.partition("?")
    auth_base, _, auth_query = auth_database_url.partition("?")
    if catalog_base != auth_base or {catalog_query, auth_query} != {"", "sslmode=require"}:
        return None
    return auth_database_url if auth_query == "sslmode=require" else database_url


@lru_cache
def get_engine():
    """Create the shared async database engine lazily."""
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be configured")
    database_url = _shared_database_url(settings.database_url, settings.auth_database_url) or settings.database_url
    return create_async_engine(
        _async_database_url(database_url),
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=min(settings.database_pool_recycle_seconds, 60),
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


@lru_cache
def get_auth_engine():
    """Allow account data on Supabase while the catalog database remains separate."""
    settings = get_settings()
    if not settings.auth_database_url:
        return get_engine()
    if _shared_database_url(settings.database_url, settings.auth_database_url):
        return get_engine()
    return create_async_engine(
        _async_database_url(settings.auth_database_url),
        pool_pre_ping=True,
        pool_size=min(settings.database_pool_size, 2),
        max_overflow=min(settings.database_max_overflow, 1),
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=min(settings.database_pool_recycle_seconds, 60),
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )


@lru_cache
def get_auth_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_auth_engine(), expire_on_commit=False)


async def get_auth_db_session(session: AsyncSession | None = None) -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    if not settings.auth_database_url or _shared_database_url(settings.database_url, settings.auth_database_url):
        if session is not None:
            yield session
            return
        async for s in get_db_session():
            yield s
        return
    async with get_auth_session_factory()() as auth_session:
        yield auth_session


async def initialize_database() -> None:
    """Create missing ORM tables during the first application startup."""
    engine = get_engine()
    table_names = sorted(Base.metadata.tables)
    logger.info("database.initialize_database creating missing tables", extra={"table_count": len(table_names)})
    async with engine.begin() as connection:
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
    if settings.auth_database_url and get_auth_engine() is not get_engine():
        await get_auth_engine().dispose()
