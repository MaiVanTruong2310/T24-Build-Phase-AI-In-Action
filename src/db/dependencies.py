"""FastAPI dependencies related to persistence."""

from collections.abc import AsyncIterator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import (
    get_auth_db_session as _get_auth_db_session,
    get_db_session,
)


async def get_auth_db_session(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[AsyncSession]:
    """Yield database session for auth operations, reusing request session when DB is shared."""
    async for s in _get_auth_db_session(session=session):
        yield s


__all__ = ["get_db_session", "get_auth_db_session"]
