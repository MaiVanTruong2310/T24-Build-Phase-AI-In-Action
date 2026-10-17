"""Supabase-managed email/password identity, with private application profiles."""

import asyncio
import ssl
from datetime import date
from hashlib import sha256
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.staff_agent_cache import invalidate_profile
from src.config import get_settings
from src.core.exceptions import AppError, AuthenticationError
from src.models.user import User
from src.schemas.auth import phone_variants

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


PENDING_KEY = "pending_registration"
IDENTITY_FIELDS = ("phone", "citizen_id", "health_insurance_code")


async def register_email(request, session: AsyncSession) -> dict:
    """Tạo danh tính Supabase; thông tin hồ sơ chỉ là BẢN NHÁP cho tới khi email được xác nhận.

    Không kiểm tra trùng SĐT/CCCD/BHYT ở đây và không ghi chúng vào cột chính: trước đây ai cũng có thể đăng ký
    (không cần xác nhận email) với SĐT/CCCD của người khác để giữ chỗ, và thông báo lỗi riêng cho từng loại trùng
    cho phép dò xem một SĐT/CCCD đã có trong hệ thống chưa. Cũng không gắn hồ sơ có sẵn trước khi xác nhận email."""
    email = (request.email or "").strip().lower()
    if "@" not in email or not request.password:
        raise AppError("EMAIL_REQUIRED", "Vui lòng nhập email và mật khẩu để đăng ký.", 400)
    settings = get_settings()
    redirect = settings.supabase_auth_redirect_url.rstrip("/") + "/login"
    result = await auth_call(
        "/signup",
        {"email": email, "password": request.password, "data": {"full_name": request.full_name or ""}},
        params={"redirect_to": redirect},
    )
    auth_user = result.get("user") or result
    if auth_user.get("id") and auth_user.get("identities") != []:
        draft = {
            "full_name": request.full_name,
            "date_of_birth": request.date_of_birth.isoformat() if request.date_of_birth else None,
            "gender": request.gender,
            "address": request.address,
            "phone": request.phone,
            "citizen_id": request.citizen_id,
            "health_insurance_code": request.health_insurance_code,
        }
        draft = {k: v for k, v in draft.items() if v}
        profile = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if profile is None:
            session.add(
                User(email=email, role="patient", status="pending_verification", patient_details={PENDING_KEY: draft})
            )
        elif profile.auth_user_id is None and profile.status == "pending_verification":
            # Bản nháp chưa được ai xác nhận: lần đăng ký mới nhất thay bản cũ. Hồ sơ đang hoạt động không bị đụng.
            profile.patient_details = {**(profile.patient_details or {}), PENDING_KEY: draft}
        await session.commit()
    return {"confirmation_required": True, "email": email}


async def _identity_taken(session: AsyncSession, profile: User, field: str, value: str) -> bool:
    column = getattr(User, field)
    condition = column.in_(phone_variants(value)) if field == "phone" else column == value
    owner = (await session.execute(select(User.id).where(condition, User.id != profile.id).limit(1))).first()
    return owner is not None


async def _apply_pending_registration(session: AsyncSession, profile: User) -> bool:
    """Sau khi email đã xác nhận: chuyển bản nháp đăng ký vào hồ sơ. Chỉ điền ô còn trống; SĐT/CCCD/BHYT đã thuộc
    hồ sơ khác thì bỏ qua (người dùng bổ sung ở trang hồ sơ), không làm hỏng đăng nhập."""
    details = profile.patient_details if isinstance(profile.patient_details, dict) else {}
    draft = details.get(PENDING_KEY)
    if not isinstance(draft, dict):
        return False
    for field in ("full_name", "gender"):
        if draft.get(field) and not getattr(profile, field):
            setattr(profile, field, draft[field])
    if draft.get("date_of_birth") and not profile.date_of_birth:
        profile.date_of_birth = date.fromisoformat(draft["date_of_birth"])
    for field in IDENTITY_FIELDS:
        value = draft.get(field)
        if value and not getattr(profile, field) and not await _identity_taken(session, profile, field, value):
            setattr(profile, field, value)
    remaining = {k: v for k, v in details.items() if k != PENDING_KEY}
    if draft.get("address") and not remaining.get("address"):
        remaining["address"] = draft["address"]
    profile.patient_details = remaining
    return True


async def authenticated_profile(token: str, session: AsyncSession) -> User:
    identity = await verified_identity(token)
    if not identity.get("email_confirmed_at"):
        raise AuthenticationError("EMAIL_NOT_CONFIRMED", "Bạn cần xác nhận email trước khi đăng nhập.")
    auth_id = UUID(identity["id"])
    changed = False
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
        changed = True
    if profile.status not in ("active", "pending_verification"):
        raise AuthenticationError("ACCOUNT_DISABLED", "Tài khoản không hoạt động.")
    if profile.status != "active":
        profile.status = "active"
        changed = True
    if await _apply_pending_registration(session, profile):
        changed = True
    # Hàm này chạy ở MỌI request đã đăng nhập: chỉ xóa cache hồ sơ khi thật sự có thay đổi
    # (trước đây mỗi request đều invalidate_profile, làm cache Redis của staff agent mất tác dụng).
    # Vẫn luôn commit để đóng transaction tự mở bởi các SELECT ở trên — endpoint phía sau dùng
    # `async with session.begin()` trên cùng session sẽ lỗi "transaction already begun" nếu bỏ qua (không có
    # thay đổi thì COMMIT không ghi dòng nào).
    try:
        await session.commit()
    except IntegrityError:
        # Hai tài khoản cùng nhận một SĐT/CCCD trong cùng lúc: kích hoạt tài khoản, bỏ phần định danh trùng.
        await session.rollback()
        profile = await _activate_without_identity(session, auth_id)
        changed = True
    if changed:
        await invalidate_profile(profile.id)
    return profile


async def _activate_without_identity(session: AsyncSession, auth_id: UUID) -> User:
    profile = (await session.execute(select(User).where(User.auth_user_id == auth_id))).scalar_one_or_none()
    if profile is None:
        raise AppError("PROFILE_CONFLICT", "Không thể kích hoạt hồ sơ lúc này. Vui lòng thử lại.", 409)
    profile.status = "active"
    details = profile.patient_details if isinstance(profile.patient_details, dict) else {}
    profile.patient_details = {k: v for k, v in details.items() if k != PENDING_KEY}
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
