"""Authentication and current-user endpoints.

Supabase Auth is the single identity provider. Sign-up, sign-in, email
confirmation, recovery and token refresh are delegated to the Supabase Auth REST
API; ``public.users`` only stores the application profile.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, oauth2_scheme, require_patient, require_staff
from src.api.response import success_response
from src.config import get_settings
from src.db.dependencies import get_auth_db_session
from src.models.user import User
from src.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    PortraitUpdateRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from src.schemas.common import ApiResponse
from src.services.auth import AuthService
from src.services.cookie_session import ACCESS_COOKIE, REFRESH_COOKIE, clear_session_cookies, token_result
from src.services.supabase_auth import (
    auth_call,
    authenticated_profile,
    login_email,
    register_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])
user_router = APIRouter(prefix="/users", tags=["users"])
patient_router = APIRouter(prefix="/patients", tags=["patients"])


def get_auth_service(session: AsyncSession = Depends(get_auth_db_session)) -> AuthService:
    """Build the profile service for the current request session."""
    return AuthService(session)


@router.post("/register", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_auth_db_session),
) -> ApiResponse[dict]:
    """Create the Supabase identity and the pending application profile."""
    result = await register_email(request, session)
    return success_response(result, "Vui lòng kiểm tra email để xác nhận tài khoản.", 201)


@router.post("/otp/send", response_model=ApiResponse[OtpSendResponse])
async def send_otp(request: OtpSendRequest) -> ApiResponse[OtpSendResponse]:
    """Resend the Supabase sign-up confirmation email."""
    if not request.email:
        raise HTTPException(status_code=400, detail="Vui lòng sử dụng email để xác thực.")
    await auth_call("/resend", {"type": "signup", "email": request.email})
    return success_response(OtpSendResponse(otp=None), "Email xác nhận đã được gửi")


@router.post("/otp/verify", response_model=ApiResponse[UserResponse])
async def verify_otp(
    request: OtpVerifyRequest,
    session: AsyncSession = Depends(get_auth_db_session),
) -> ApiResponse[UserResponse]:
    """Confirm the Supabase sign-up token and activate the application profile."""
    if not request.email or request.purpose != "register":
        raise HTTPException(status_code=400, detail="Vui lòng xác thực OTP đăng ký qua email.")
    tokens = await auth_call(
        "/verify", {"email": request.email.strip().lower(), "token": request.code, "type": "email"}
    )
    user = await authenticated_profile(tokens["access_token"], session)
    return success_response(UserResponse.model_validate(user), "Đã xác nhận email. Vui lòng đăng nhập.")


@router.post("/forgot-password", response_model=ApiResponse[OtpSendResponse])
async def forgot_password(request: ForgotPasswordRequest) -> ApiResponse[OtpSendResponse]:
    """Send the Supabase recovery email without revealing account existence."""
    if not request.email:
        raise HTTPException(status_code=400, detail="Vui lòng nhập email đăng ký.")
    redirect = get_settings().supabase_auth_redirect_url.rstrip("/") + "/forgot-password"
    await auth_call("/recover", {"email": request.email.strip().lower()}, params={"redirect_to": redirect})
    return success_response(
        OtpSendResponse(otp=None), "Nếu tài khoản tồn tại, liên kết khôi phục sẽ được gửi qua email."
    )


@router.post("/reset-password", response_model=ApiResponse[None])
async def reset_password(request: ResetPasswordRequest) -> ApiResponse[None]:
    """Reject OTP password reset; Supabase recovery links own this flow."""
    raise HTTPException(status_code=400, detail="Vui lòng mở liên kết khôi phục trong email.")


class PasswordChangeRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


@router.put("/password", response_model=ApiResponse[None])
async def change_password(request: PasswordChangeRequest, response: Response, token: str = Depends(oauth2_scheme)):
    """Set a new password through Supabase and end the current session."""
    await auth_call("/user", {"password": request.new_password}, token=token, method="PUT")
    await auth_call("/logout", token=token)
    clear_session_cookies(response)
    return success_response(None, "Đã cập nhật mật khẩu. Vui lòng đăng nhập lại.")


@router.post("/login", response_model=ApiResponse[dict])
async def login(
    request: LoginRequest,
    http_request: Request,
    response: Response,
    session: AsyncSession = Depends(get_auth_db_session),
):
    """Exchange an email and password for a Supabase session."""
    data = TokenResponse(**await login_email(request, session))
    return token_result(http_request, response, data)


@router.post("/refresh-token", response_model=ApiResponse[dict])
async def refresh_token(
    http_request: Request,
    response: Response,
    request: RefreshTokenRequest | None = None,
):
    """Rotate the Supabase refresh token and re-issue the session cookies."""
    value = http_request.cookies.get(REFRESH_COOKIE) or (request.refresh_token if request else None)
    if not value:
        raise HTTPException(401, "Không có phiên đăng nhập để gia hạn.")
    tokens = await auth_call("/token", {"refresh_token": value}, params={"grant_type": "refresh_token"})
    data = TokenResponse(**{key: tokens[key] for key in ("access_token", "refresh_token", "expires_in")})
    return token_result(http_request, response, data)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    http_request: Request,
    response: Response,
    request: RefreshTokenRequest | None = None,
):
    """End the Supabase session and clear the session cookies."""
    value = http_request.cookies.get(REFRESH_COOKIE) or (request.refresh_token if request else None)
    try:
        if value:
            access_token = http_request.cookies.get(ACCESS_COOKIE)
            if not access_token:
                tokens = await auth_call("/token", {"refresh_token": value}, params={"grant_type": "refresh_token"})
                access_token = tokens["access_token"]
            await auth_call("/logout", token=access_token)
    finally:
        clear_session_cookies(response)
    return success_response(None, "Logout successful")


@user_router.get("/me", response_model=ApiResponse[UserResponse])
@patient_router.get("/me", response_model=ApiResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)) -> ApiResponse[UserResponse]:
    """Return the authenticated user's profile."""
    return success_response(UserResponse.model_validate(current_user), "Profile retrieved")


@user_router.patch("/me", response_model=ApiResponse[UserResponse])
async def update_me(
    request: UpdateProfileRequest,
    current_user: User = Depends(require_patient),
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """Update and return the authenticated patient's profile."""
    user = await service.update_profile(current_user, request)
    return success_response(UserResponse.model_validate(user), "Profile updated")


@user_router.get("/me/portrait", response_model=ApiResponse[str | None])
async def get_portrait(current_user: User = Depends(get_current_user)):
    return success_response((current_user.patient_details or {}).get("portrait_image"), "Portrait retrieved")


@user_router.patch("/me/portrait", response_model=ApiResponse[str | None])
async def update_portrait(
    request: PortraitUpdateRequest,
    current_user: User = Depends(require_patient),
    service: AuthService = Depends(get_auth_service),
):
    await service.update_portrait(current_user, request.image)
    return success_response(request.image, "Portrait updated")


@user_router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user_by_id(
    user_id: UUID,
    _: User = Depends(require_staff),
    service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """Return one user for staff-owned lookup flows."""
    user = await service.get_user_by_id(user_id)
    return success_response(UserResponse.model_validate(user), "User retrieved")
