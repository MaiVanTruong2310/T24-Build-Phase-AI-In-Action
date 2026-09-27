"""Authentication and current-user endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.api.response import success_response
from src.db.dependencies import get_db_session
from src.models.user import User
from src.schemas.auth import (
    LoginRequest,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    RefreshTokenRequest,
    RegisterRequest,
    SessionResponse,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from src.schemas.common import ApiResponse
from src.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
user_router = APIRouter(prefix="/users", tags=["users"])


def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    """Build the authentication service for the current request session."""
    return AuthService(session)


@router.post("/register", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """Register a pending user account."""
    user = await service.register(request)
    return success_response(UserResponse.model_validate(user), "Registration created", 201)


@router.post("/otp/send", response_model=ApiResponse[OtpSendResponse])
async def send_otp(
    request: OtpSendRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[OtpSendResponse]:
    """Send an OTP and expose it only while the mock provider is active."""
    otp = await service.send_otp(request.email, request.phone, request.purpose)
    return success_response(OtpSendResponse(otp=otp), "OTP sent")


@router.post("/otp/verify", response_model=ApiResponse[UserResponse])
async def verify_otp(
    request: OtpVerifyRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """Verify a registration OTP and activate the account."""
    user = await service.verify_registration_otp(request.email, request.phone, request.code)
    return success_response(UserResponse.model_validate(user), "OTP verified")


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[TokenResponse]:
    """Authenticate a user and return access and refresh tokens."""
    _, access_token, refresh_token, access_expires_at, _ = await service.login(request)
    expires_in = max(0, int((access_expires_at - datetime.now(UTC)).total_seconds()))
    data = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )
    return success_response(data, "Login successful")


@router.post("/refresh-token", response_model=ApiResponse[TokenResponse])
async def refresh_token(
    request: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[TokenResponse]:
    """Rotate a refresh token and return the new token pair."""
    _, access_token, new_refresh_token, access_expires_at = await service.refresh(request.refresh_token)
    expires_in = max(0, int((access_expires_at - datetime.now(UTC)).total_seconds()))
    data = TokenResponse(access_token=access_token, refresh_token=new_refresh_token, expires_in=expires_in)
    return success_response(data, "Token refreshed")


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    request: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[None]:
    """Revoke the refresh session supplied by the client."""
    await service.logout(request.refresh_token)
    return success_response(None, "Logout successful")


@router.get("/sessions", response_model=ApiResponse[list[SessionResponse]])
async def sessions(
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[list[SessionResponse]]:
    """List refresh sessions for the authenticated user."""
    values = await service.list_sessions(current_user.id)
    data = [SessionResponse(id=str(item.id), expires_at=item.expires_at, revoked_at=item.revoked_at) for item in values]
    return success_response(data, "Sessions retrieved")


@router.delete("/sessions/{session_id}", response_model=ApiResponse[None])
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[None]:
    """Revoke one refresh session owned by the authenticated user."""
    await service.revoke_session(current_user.id, session_id)
    return success_response(None, "Session revoked")


@user_router.get("/me", response_model=ApiResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)) -> ApiResponse[UserResponse]:
    """Return the authenticated user's profile."""
    return success_response(UserResponse.model_validate(current_user), "Profile retrieved")


@user_router.patch("/me", response_model=ApiResponse[UserResponse])
async def update_me(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """Update and return the authenticated user's profile."""
    user = await service.update_profile(current_user, request)
    return success_response(UserResponse.model_validate(user), "Profile updated")
