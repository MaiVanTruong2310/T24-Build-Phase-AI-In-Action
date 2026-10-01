"""Authentication and current-user endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_staff, oauth2_scheme
from src.api.response import success_response
from src.db.dependencies import get_auth_db_session
from src.models.user import User
from src.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionResponse,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from src.schemas.common import ApiResponse
from src.config import get_settings
from pydantic import BaseModel, Field
from src.services.auth import AuthService
from src.services.supabase_auth import native_auth_enabled, register_email, login_email, auth_call, authenticated_profile

router = APIRouter(prefix="/auth", tags=["auth"])
user_router = APIRouter(prefix="/users", tags=["users"])


def get_auth_service(session: AsyncSession = Depends(get_auth_db_session)) -> AuthService:
    """Build the authentication service for the current request session."""
    return AuthService(session)


@router.post("/register", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """Register a pending user account."""
    if native_auth_enabled():
        result = await register_email(request, service.session)
        return success_response(result, "Vui lòng kiểm tra email để xác nhận tài khoản.", 201)
    user = await service.register(request)
    return success_response(UserResponse.model_validate(user).model_dump(mode="json"), "Registration created", 201)


@router.post("/otp/send", response_model=ApiResponse[OtpSendResponse])
async def send_otp(
    request: OtpSendRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[OtpSendResponse]:
    """Send an OTP and expose it only while the mock provider is active."""
    if native_auth_enabled():
        if not request.email:
            raise HTTPException(status_code=400, detail="Vui lòng sử dụng email để xác thực.")
        await auth_call("/resend", {"type": "signup", "email": request.email})
        return success_response(OtpSendResponse(otp=None), "Email xác nhận đã được gửi")
    otp = await service.send_otp(request.email, request.phone, request.purpose)
    return success_response(OtpSendResponse(otp=otp), "OTP sent")


@router.post("/otp/verify", response_model=ApiResponse[UserResponse])
async def verify_otp(
    request: OtpVerifyRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """Verify a registration OTP and activate the account."""
    if native_auth_enabled():
        if not request.email or request.purpose != "register":
            raise HTTPException(status_code=400, detail="Vui lòng xác thực OTP đăng ký qua email.")
        tokens = await auth_call("/verify", {"email": request.email.strip().lower(), "token": request.code, "type": "email"})
        user = await authenticated_profile(tokens["access_token"], service.session)
        return success_response(UserResponse.model_validate(user), "Đã xác nhận email. Vui lòng đăng nhập.")
    user = await service.verify_registration_otp(request.email, request.phone, request.code)
    return success_response(UserResponse.model_validate(user), "OTP verified")


@router.post("/forgot-password", response_model=ApiResponse[OtpSendResponse])
async def forgot_password(
    request: ForgotPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[OtpSendResponse]:
    """Issue a password-reset OTP without revealing account existence."""
    if native_auth_enabled():
        if not request.email:
            raise HTTPException(status_code=400, detail="Vui lòng nhập email đăng ký.")
        redirect = get_settings().supabase_auth_redirect_url.rstrip("/") + "/forgot-password"
        await auth_call("/recover", {"email": request.email.strip().lower()}, params={"redirect_to": redirect})
        return success_response(OtpSendResponse(otp=None), "Nếu tài khoản tồn tại, liên kết khôi phục sẽ được gửi qua email.")
    otp = await service.request_password_reset(request.email, request.phone)
    return success_response(OtpSendResponse(otp=otp), "If the account exists, an OTP was sent")


@router.post("/reset-password", response_model=ApiResponse[None])
async def reset_password(
    request: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[None]:
    """Reset the password after validating the reset OTP."""
    if native_auth_enabled():
        raise HTTPException(status_code=400, detail="Vui lòng mở liên kết khôi phục trong email.")
    await service.reset_password(request.email, request.phone, request.code, request.new_password)
    return success_response(None, "Password reset successful")


class PasswordChangeRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


@router.put("/password", response_model=ApiResponse[None])
async def change_password(request: PasswordChangeRequest, token: str = Depends(oauth2_scheme)):
    if not native_auth_enabled():
        raise HTTPException(status_code=400, detail="Sử dụng chức năng khôi phục bằng OTP.")
    await auth_call("/user", {"password": request.new_password}, token=token, method="PUT")
    await auth_call("/logout", token=token)
    return success_response(None, "Đã cập nhật mật khẩu. Vui lòng đăng nhập lại.")


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[TokenResponse]:
    """Authenticate a user and return access and refresh tokens."""
    if native_auth_enabled():
        return success_response(TokenResponse(**await login_email(request, service.session)), "Login successful")
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
    if native_auth_enabled():
        tokens = await auth_call("/token", {"refresh_token": request.refresh_token}, params={"grant_type": "refresh_token"})
        return success_response(TokenResponse(**{k: tokens[k] for k in ("access_token", "refresh_token", "expires_in")}), "Token refreshed")
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
    if native_auth_enabled():
        tokens = await auth_call("/token", {"refresh_token": request.refresh_token}, params={"grant_type": "refresh_token"})
        await auth_call("/logout", token=tokens["access_token"])
        return success_response(None, "Logout successful")
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


@user_router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user_by_id(
    user_id: UUID,
    _: User = Depends(require_staff),
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """Return one user for staff-owned lookup flows."""
    user = await service.get_user_by_id(user_id)
    return success_response(UserResponse.model_validate(user), "User retrieved")
