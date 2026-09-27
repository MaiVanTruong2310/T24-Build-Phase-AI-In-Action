"""Shared authentication dependencies."""

from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AuthenticationError, AuthorizationError
from src.core.security import decode_access_token
from src.db.dependencies import get_db_session
from src.models.user import User
from src.repositories.user import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Resolve the active user from a valid access token."""
    payload = decode_access_token(token)
    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("INVALID_TOKEN", "Invalid access token") from exc
    user = await UserRepository(session).get_by_id(user_id)

    if user is None or user.status != "active":
        raise AuthenticationError("INVALID_TOKEN", "User is not active")
    return user


async def require_staff(user: User = Depends(get_current_user)) -> User:
    """Require the staff role."""
    if user.role != "staff":
        raise AuthorizationError()
    return user
