from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.api.endpoints import auth
from src.core.exceptions import AppError
from src.models.user import User
from src.schemas.auth import OtpVerifyRequest


@pytest.mark.asyncio
async def test_email_otp_confirms_with_supabase_before_activating_profile(monkeypatch):
    monkeypatch.setattr(auth, "native_auth_enabled", lambda: True)
    remote = AsyncMock(return_value={"access_token": "test-access-token"})
    profile = User(id=uuid4(), email="test@example.com", role="patient", status="active")
    verified = AsyncMock(return_value=profile)
    monkeypatch.setattr(auth, "auth_call", remote)
    monkeypatch.setattr(auth, "authenticated_profile", verified)
    service = AsyncMock()
    result = await auth.verify_otp(OtpVerifyRequest(email="Test@example.com", code="012345"), service)
    remote.assert_awaited_once_with("/verify", {"email": "test@example.com", "token": "012345", "type": "email"})
    verified.assert_awaited_once_with("test-access-token", service.session)
    assert result.data.status == "active"
    service.verify_registration_otp.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalid_email_otp_never_activates_profile(monkeypatch):
    monkeypatch.setattr(auth, "native_auth_enabled", lambda: True)
    monkeypatch.setattr(
        auth, "auth_call", AsyncMock(side_effect=AppError("otp_expired", "Mã OTP không đúng hoặc hết hạn.", 403))
    )
    verified = AsyncMock()
    monkeypatch.setattr(auth, "authenticated_profile", verified)
    with pytest.raises(AppError):
        await auth.verify_otp(OtpVerifyRequest(email="test@example.com", code="012345"), AsyncMock())
    verified.assert_not_awaited()
