"""Shared authentication dependencies."""

from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AuthenticationError, AuthorizationError
from src.core.security import decode_access_token
from src.db.dependencies import get_auth_db_session
from src.models.user import User
from src.repositories.user import UserRepository


async def oauth2_scheme(request: Request) -> str:
    from src.services.cookie_session import request_token
    token = request_token(request)
    if not token:
        raise AuthenticationError("NOT_AUTHENTICATED", "Vui lòng đăng nhập.")
    return token


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_auth_db_session),
) -> User:
    """Resolve the active user from a valid access token."""
    from src.services.supabase_auth import authenticated_profile, native_auth_enabled
    if native_auth_enabled():
        try:
            local_payload = decode_access_token(token)
        except AuthenticationError:
            local_payload = None
        if local_payload is not None:
            try:
                local_user = await UserRepository(session).get_by_id(UUID(str(local_payload["sub"])))
            except ValueError as exc:
                raise AuthenticationError("INVALID_TOKEN", "Invalid access token") from exc
            await session.commit()
            if local_user is None or local_user.status != "active" or local_user.role != "staff" or local_user.phone != "admin123":
                raise AuthenticationError("INVALID_TOKEN", "Invalid staff session")
            return local_user
        return await authenticated_profile(token, session)
    payload = decode_access_token(token)
    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("INVALID_TOKEN", "Invalid access token") from exc
    user = await UserRepository(session).get_by_id(user_id)
    # SQLAlchemy starts an implicit read transaction for ``session.get``.
    # Staff write services open their own explicit transaction on this same
    # request-scoped session, so close the read-only transaction first. The
    # session factory uses ``expire_on_commit=False``, so the loaded user
    # remains available after this read-only commit.
    await session.commit()

    if user is None or user.status != "active":
        raise AuthenticationError("INVALID_TOKEN", "User is not active")
    return user


async def require_staff(user: User = Depends(get_current_user)) -> User:
    """Require the staff role."""
    if user.role != "staff":
        raise AuthorizationError()
    return user


async def require_patient(user: User = Depends(get_current_user)) -> User:
    """Require a patient role for patient-owned booking endpoints."""
    if user.role != "patient":
        raise AuthorizationError()
    return user


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_auth_db_session),
) -> User | None:
    """Optionally resolve the active user from cookie or token if present."""
    from src.services.cookie_session import request_token

    token = request_token(request)
    if not token:
        return None
    try:
        return await get_current_user(token, session)
    except Exception:
        return None

