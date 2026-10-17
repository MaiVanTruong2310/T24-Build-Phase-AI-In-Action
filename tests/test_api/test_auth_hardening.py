"""Đăng nhập/đăng ký: 7 lỗi rà soát ngày 14/10/2026."""

import base64
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

import src.api.endpoints.auth as auth_endpoints
import src.services.supabase_auth as gateway
from src.core.exceptions import AppError
from src.schemas.auth import LoginRequest, RegisterRequest, UpdateProfileRequest, phone_variants


class Result:
    def __init__(self, value=None, row=None):
        self.value, self.row = value, row

    def scalar_one_or_none(self):
        return self.value

    def first(self):
        return self.row


class FakeSession:
    """Trả lần lượt các kết quả execute; ghi lại add/commit."""

    def __init__(self, *results, commit_error=None):
        self.results = list(results)
        self.added = []
        self.commit = AsyncMock(side_effect=commit_error)
        self.rollback = AsyncMock()

    async def execute(self, _stmt):
        return self.results.pop(0) if self.results else Result()

    def add(self, obj):
        self.added.append(obj)


def _profile(**kw):
    base = dict(
        id=uuid4(),
        status="active",
        auth_user_id=None,
        role="patient",
        full_name=None,
        gender=None,
        date_of_birth=None,
        phone=None,
        citizen_id=None,
        health_insurance_code=None,
        patient_details={},
    )
    return SimpleNamespace(**{**base, **kw})


def _confirmed(auth_id, email="a@example.com"):
    return {"id": str(auth_id), "email": email, "email_confirmed_at": "2026-10-14T00:00:00Z"}


# ------------------------------------------------------------------ 1. mật khẩu không bị cắt khoảng trắng
def test_login_keeps_password_whitespace_but_normalizes_email():
    req = LoginRequest(email="  A@Example.com ", password="  mat khau  ")
    assert req.password == "  mat khau  " and req.email == "a@example.com"


# ------------------------------------------------------------------ 2. một dạng SĐT chuẩn
@pytest.mark.parametrize("raw", ["+84912345678", "0912345678", "0912.345.678", "+84 912 345 678"])
def test_phone_is_stored_in_one_canonical_form(raw):
    assert RegisterRequest(email="a@example.com", password="x" * 8, phone=raw).phone == "0912345678"


def test_profile_update_normalizes_phone_and_lookup_covers_legacy_forms():
    assert UpdateProfileRequest(phone="+84912345678").phone == "0912345678"
    assert set(phone_variants("0912345678")) == {"0912345678", "+84912345678", "84912345678"}


# ------------------------------------------------------------------ 3–5. đăng ký: không giữ chỗ, không dò được
@pytest.mark.asyncio
async def test_register_never_checks_or_claims_identifiers(monkeypatch):
    monkeypatch.setattr(gateway, "auth_call", AsyncMock(return_value={"id": str(uuid4()), "identities": [{"id": "x"}]}))
    session = FakeSession(Result(None))  # chưa có hồ sơ cho email này
    result = await gateway.register_email(
        RegisterRequest(email="a@example.com", password="x" * 8, phone="+84912345678", citizen_id="012345678901"),
        session,
    )
    assert result == {"confirmation_required": True, "email": "a@example.com"}
    (profile,) = session.added
    # SĐT/CCCD chỉ nằm trong bản nháp, cột chính để trống; chưa gắn auth_user_id trước khi xác nhận email
    assert profile.phone is None and profile.citizen_id is None and profile.auth_user_id is None
    assert profile.patient_details["pending_registration"]["phone"] == "0912345678"
    assert profile.status == "pending_verification"


@pytest.mark.asyncio
async def test_register_does_not_touch_an_active_profile(monkeypatch):
    monkeypatch.setattr(gateway, "auth_call", AsyncMock(return_value={"id": str(uuid4()), "identities": [{}]}))
    existing = _profile(status="active", patient_details={"address": "cũ"})
    session = FakeSession(Result(existing))
    await gateway.register_email(RegisterRequest(email="a@example.com", password="x" * 8, phone="0912345678"), session)
    assert existing.patient_details == {"address": "cũ"} and existing.auth_user_id is None


@pytest.mark.asyncio
async def test_confirmed_login_applies_draft_but_skips_identifier_owned_by_someone_else(monkeypatch):
    auth_id = uuid4()
    monkeypatch.setattr(gateway, "verified_identity", AsyncMock(return_value=_confirmed(auth_id)))
    monkeypatch.setattr(gateway, "invalidate_profile", AsyncMock())
    draft = {"full_name": "Lan", "phone": "0912345678", "citizen_id": "012345678901", "address": "HN"}
    profile = _profile(status="pending_verification", patient_details={"pending_registration": draft})
    session = FakeSession(
        Result(None),  # theo auth_user_id: chưa liên kết
        Result(profile),  # theo email: hồ sơ nháp
        Result(row=(uuid4(),)),  # SĐT đã thuộc hồ sơ khác
        Result(row=None),  # CCCD còn trống
    )
    actual = await gateway.authenticated_profile("tok", session)
    assert actual.status == "active" and actual.auth_user_id == auth_id and actual.full_name == "Lan"
    assert actual.phone is None and actual.citizen_id == "012345678901"
    assert actual.patient_details == {"address": "HN"}
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unique_race_at_activation_keeps_login_working(monkeypatch):
    auth_id = uuid4()
    monkeypatch.setattr(gateway, "verified_identity", AsyncMock(return_value=_confirmed(auth_id)))
    monkeypatch.setattr(gateway, "invalidate_profile", AsyncMock())
    profile = _profile(status="pending_verification", patient_details={"pending_registration": {"phone": "0912345678"}})
    reloaded = _profile(status="pending_verification", auth_user_id=auth_id, patient_details={})
    session = FakeSession(Result(None), Result(profile), Result(row=None), Result(reloaded))
    session.commit = AsyncMock(side_effect=[IntegrityError("x", {}, Exception()), None])
    actual = await gateway.authenticated_profile("tok", session)
    assert actual is reloaded and actual.status == "active" and actual.phone is None
    session.rollback.assert_awaited_once()


# ------------------------------------------------------------------ 6. request thường không ghi DB
@pytest.mark.asyncio
async def test_authenticated_request_without_changes_keeps_cache_but_closes_transaction(monkeypatch):
    auth_id = uuid4()
    monkeypatch.setattr(gateway, "verified_identity", AsyncMock(return_value=_confirmed(auth_id)))
    invalidate = AsyncMock()
    monkeypatch.setattr(gateway, "invalidate_profile", invalidate)
    session = FakeSession(Result(_profile(status="active", auth_user_id=auth_id)))
    await gateway.authenticated_profile("tok", session)
    invalidate.assert_not_awaited()
    # Phải đóng transaction tự mở bởi SELECT: /patient-profiles và /chat dùng `session.begin()` ngay sau đó
    # (lỗi prod 14/10/2026: bỏ commit → 500 "transaction already begun" cho mọi người đã đăng nhập).
    session.commit.assert_awaited_once()


# ------------------------------------------------------------------ 7. đổi mật khẩu cần mật khẩu hiện tại
def _jwt(amr):
    body = base64.urlsafe_b64encode(json.dumps({"amr": amr}).encode()).decode().rstrip("=")
    return f"h.{body}.s"


@pytest.mark.asyncio
async def test_change_password_in_normal_session_requires_current_password(monkeypatch):
    monkeypatch.setattr(auth_endpoints, "verified_identity", AsyncMock(return_value={"email": "a@example.com"}))
    calls = AsyncMock(return_value={})
    monkeypatch.setattr(auth_endpoints, "auth_call", calls)
    token = _jwt([{"method": "password", "timestamp": time.time()}])
    with pytest.raises(AppError) as err:
        await auth_endpoints.change_password(
            auth_endpoints.PasswordChangeRequest(new_password="y" * 8), MagicMock(), token
        )
    assert err.value.error_code == "CURRENT_PASSWORD_REQUIRED"
    calls.assert_not_awaited()


@pytest.mark.asyncio
async def test_change_password_with_wrong_current_password_is_rejected(monkeypatch):
    monkeypatch.setattr(auth_endpoints, "verified_identity", AsyncMock(return_value={"email": "a@example.com"}))
    wrong = AppError("invalid_credentials", "Email hoặc mật khẩu không đúng.", 400)
    calls = AsyncMock(side_effect=wrong)
    monkeypatch.setattr(auth_endpoints, "auth_call", calls)
    token = _jwt([{"method": "password", "timestamp": time.time()}])
    with pytest.raises(AppError) as err:
        await auth_endpoints.change_password(
            auth_endpoints.PasswordChangeRequest(new_password="y" * 8, current_password="sai"), MagicMock(), token
        )
    assert err.value.error_code == "CURRENT_PASSWORD_INVALID"
    assert calls.await_count == 1  # không gọi PUT /user


@pytest.mark.asyncio
async def test_recent_recovery_link_can_set_password_without_current(monkeypatch):
    monkeypatch.setattr(auth_endpoints, "verified_identity", AsyncMock(return_value={"email": "a@example.com"}))
    calls = AsyncMock(return_value={})
    monkeypatch.setattr(auth_endpoints, "auth_call", calls)
    token = _jwt([{"method": "recovery", "timestamp": time.time() - 60}])
    await auth_endpoints.change_password(auth_endpoints.PasswordChangeRequest(new_password="y" * 8), MagicMock(), token)
    assert [c.args[0] for c in calls.await_args_list] == ["/user", "/logout"]


def test_old_recovery_session_is_not_trusted():
    assert not auth_endpoints._recent_email_link_session(
        _jwt([{"method": "recovery", "timestamp": time.time() - 7200}])
    )
    assert not auth_endpoints._recent_email_link_session("not-a-jwt")
