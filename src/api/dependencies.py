"""Shared authentication dependencies."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AuthenticationError, AuthorizationError
from src.db.dependencies import get_auth_db_session, get_db_session
from src.models.user import User


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
    """Resolve the active profile from a Supabase access token."""
    from src.services.supabase_auth import authenticated_profile

    return await authenticated_profile(token, session)


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


async def require_coordination_admin(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)
):
    from src.services.workbench import member_for

    member = await member_for(db, user)
    allowed = member.is_admin and not member.facility_ids
    await db.commit()
    if not allowed:
        raise AuthorizationError()
    return user
