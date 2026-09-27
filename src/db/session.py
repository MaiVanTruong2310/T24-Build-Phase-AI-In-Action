"""Async SQLAlchemy engine and session factory for PostgreSQL."""

from functools import lru_cache
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import get_settings


def _async_database_url(database_url: str) -> str:
    """Convert a standard PostgreSQL URL to the psycopg async dialect."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


@lru_cache
def get_engine():
    """Create the shared async database engine lazily."""
    settings = get_settings()
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
