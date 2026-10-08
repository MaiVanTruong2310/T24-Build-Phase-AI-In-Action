"""Supabase-managed email/password identity, with private application profiles."""

import asyncio
import ssl
from datetime import datetime
from hashlib import sha256
from uuid import UUID

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.exceptions import AppError, AuthenticationError, ConflictError
from src.models.user import User


def native_auth_enabled() -> bool:
    return get_settings().auth_provider == "supabase"


# Share only concurrent checks. Completed results are discarded, so each later
# request still asks Supabase whether the token is valid.
_pending_user_checks: dict[bytes, asyncio.Task[dict]] = {}


async def verified_identity(token: str) -> dict:
    key = sha256(token.encode()).digest()
    task = _pending_user_checks.get(key)
    if task is None:
        task = asyncio.create_task(auth_call("/user", token=token, method="GET"))
        _pending_user_checks[key] = task
        task.add_done_callback(
            lambda completed: (
                _pending_user_checks.pop(key, None) if _pending_user_checks.get(key) is completed else None
            )
        )
    return await asyncio.shield(task)


_ssl_context: ssl.SSLContext | None = None


def _get_auth_ssl_context() -> ssl.SSLContext:
    global _ssl_context
    if _ssl_context is None:
        _ssl_context = ssl.create_default_context()
        _ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    return _ssl_context


async def auth_call(
    path: str, body: dict | None = None, token: str | None = None, method: str = "POST", params: dict | None = None
) -> dict:
    settings = get_settings()
    headers = {"apikey": settings.supabase_key}
    if token:
        headers["Authorization"] = "Bearer " + token
    ssl_ctx = _get_auth_ssl_context()
    response = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=20, verify=ssl_ctx) as client:
                response = await client.request(
                    method,
                    settings.supabase_url.rstrip("/") + "/auth/v1" + path,
                    json=body,
                    headers=headers,
                    params=params,
                )
            break
        except (httpx.HTTPError, ssl.SSLError, OSError) as exc:
            if attempt == 0:
                await asyncio.sleep(0.2)
                continue
            raise AppError(
                "AUTH_UNAVAILABLE", "Không thể kết nối dịch vụ xác thực. Vui lòng thử lại sau.", 503
            ) from exc
    payload = response.json() if response.content else {}
    if response.is_error:
        code = payload.get("error_code") or payload.get("code")
        messages = {
            "otp_expired": "Mã OTP không đúng hoặc đã hết hạn. Vui lòng kiểm tra mã hoặc yêu cầu gửi lại.",
            "email_not_confirmed": "Bạn cần xác nhận email trước khi đăng nhập.",
            "invalid_credentials": "Email hoặc mật khẩu không đúng.",
            "over_email_send_rate_limit": "Đã vượt giới hạn gửi email. Vui lòng thử lại sau.",
            "email_exists": "Email đã được đăng ký. Vui lòng đăng nhập hoặc đặt lại mật khẩu.",
            "user_already_exists": "Email đã được đăng ký.",
            "email_address_invalid": "Địa chỉ email không hợp lệ.",
        }
        raise AppError(
            str(code or "AUTH_ERROR"),
            messages.get(code, "Không thể xử lý yêu cầu xác thực. Vui lòng kiểm tra thông tin hoặc thử lại sau."),
            response.status_code if response.status_code < 500 else 503,
        )
    return payload


async def register_email(request, session: AsyncSession) -> dict:
    email = (request.email or "").strip().lower()
    if "@" not in email or not request.password:
        raise AppError("EMAIL_REQUIRED", "Vui lòng nhập email và mật khẩu để đăng ký.", 400)
    # Check application identity conflicts before requesting an email.
    if request.phone:
        existing_phone = (await session.execute(select(User).where(User.phone == request.phone))).scalar_one_or_none()
        if existing_phone and (existing_phone.email or "").lower() != email:
            raise ConflictError("PHONE_EXISTS", "Số điện thoại đã thuộc một hồ sơ khác.")
    if request.citizen_id:
        existing_cid = (
            await session.execute(select(User).where(User.citizen_id == request.citizen_id))
        ).scalar_one_or_none()
        if existing_cid and (existing_cid.email or "").lower() != email:
            raise ConflictError("CITIZEN_ID_EXISTS", "Số CCCD đã thuộc một hồ sơ khác.")
    if request.health_insurance_code:
        existing_bhyt = (
            await session.execute(select(User).where(User.health_insurance_code == request.health_insurance_code))
        ).scalar_one_or_none()
        if existing_bhyt and (existing_bhyt.email or "").lower() != email:
            raise ConflictError("HEALTH_INSURANCE_EXISTS", "Số thẻ bảo hiểm y tế đã thuộc một hồ sơ khác.")
    await session.commit()
    settings = get_settings()
    redirect = settings.supabase_auth_redirect_url.rstrip("/") + "/login"
    result = await auth_call(
        "/signup",
        {"email": email, "password": request.password, "data": {"full_name": request.full_name or ""}},
        params={"redirect_to": redirect},
    )
    auth_user = result.get("user") or result
    auth_id = auth_user.get("id")
    if auth_id and auth_user.get("identities") != []:
        # Supabase obfuscates duplicate signups. Verify a real identity exists before linking.
        real = (
            await session.execute(
                text("SELECT id FROM auth.users WHERE id=:id AND lower(email)=:email"),
                {"id": UUID(auth_id), "email": email},
            )
        ).first()
        if real:
            profile = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
            if profile and profile.auth_user_id and str(profile.auth_user_id) != auth_id:
                raise ConflictError("PROFILE_BOUND", "Hồ sơ đã liên kết với một tài khoản khác.")
            if not profile:
                profile = User(
                    email=email,
                    phone=request.phone,
                    full_name=request.full_name,
                    role="patient",
                    status="pending_verification",
                    date_of_birth=request.date_of_birth,
                    gender=request.gender,
                    citizen_id=request.citizen_id,
                    health_insurance_code=request.health_insurance_code,
                    patient_details={"address": request.address} if request.address else {},
                )
                session.add(profile)
            profile.auth_user_id = UUID(auth_id)
            await session.commit()
    return {"confirmation_required": True, "email": email}


async def authenticated_profile(token: str, session: AsyncSession) -> User:
    identity = await verified_identity(token)
    if not identity.get("email_confirmed_at"):
        raise AuthenticationError("EMAIL_NOT_CONFIRMED", "Bạn cần xác nhận email trước khi đăng nhập.")
    auth_id = UUID(identity["id"])
    profile = (await session.execute(select(User).where(User.auth_user_id == auth_id))).scalar_one_or_none()
    if profile is None:
        # A verified email may claim an unlinked legacy profile, preserving booking IDs.
        email = (identity.get("email") or "").lower()
        profile = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if profile and profile.auth_user_id:
            raise AuthenticationError("PROFILE_BOUND", "Hồ sơ đã liên kết với tài khoản khác.")
        if profile is None:
            profile = User(
                email=email,
                full_name=(identity.get("user_metadata") or {}).get("full_name"),
                role="patient",
                status="pending_verification",
            )
            session.add(profile)
        profile.auth_user_id = auth_id
    if profile.status not in ("active", "pending_verification"):
        raise AuthenticationError("ACCOUNT_DISABLED", "Tài khoản không hoạt động.")
    profile.status = "active"
    profile.verified_at = datetime.fromisoformat(identity["email_confirmed_at"].replace("Z", "+00:00"))
    await session.commit()
    return profile


async def login_email(request, session: AsyncSession) -> dict:
    if not request.email or not request.password:
        raise AppError("EMAIL_REQUIRED", "Vui lòng đăng nhập bằng email và mật khẩu.", 400)
    tokens = await auth_call(
        "/token",
        {"email": request.email.strip().lower(), "password": request.password},
        params={"grant_type": "password"},
    )
    await authenticated_profile(tokens["access_token"], session)
    return {key: tokens[key] for key in ("access_token", "refresh_token", "expires_in")}
