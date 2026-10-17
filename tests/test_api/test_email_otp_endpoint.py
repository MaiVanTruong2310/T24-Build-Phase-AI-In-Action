"""Supabase-confirmed email OTP verification for the registration flow."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.endpoints import auth
from src.core.exceptions import AppError
from src.models.user import User
from src.schemas.auth import OtpVerifyRequest


@pytest.mark.asyncio
async def test_email_otp_confirms_with_supabase_before_activating_profile(monkeypatch):
    """Supabase verifies the sign-up token; only then is the profile activated."""
    remote = AsyncMock(return_value={"access_token": "test-access-token"})
    profile = User(id=uuid4(), email="test@example.com", role="patient", status="active")
    verified = AsyncMock(return_value=profile)
    session = AsyncMock()
    monkeypatch.setattr(auth, "auth_call", remote)
    monkeypatch.setattr(auth, "authenticated_profile", verified)

    result = await auth.verify_otp(OtpVerifyRequest(email="Test@example.com", code="012345"), session)

    remote.assert_awaited_once_with("/verify", {"email": "test@example.com", "token": "012345", "type": "email"})
    verified.assert_awaited_once_with("test-access-token", session)
    assert result.data.status == "active"


@pytest.mark.asyncio
async def test_invalid_email_otp_never_activates_profile(monkeypatch):
    """A rejected Supabase token leaves the application profile untouched."""
    monkeypatch.setattr(
        auth, "auth_call", AsyncMock(side_effect=AppError("otp_expired", "Mã OTP không đúng hoặc hết hạn.", 403))
    )
    verified = AsyncMock()
    monkeypatch.setattr(auth, "authenticated_profile", verified)

    with pytest.raises(AppError):
        await auth.verify_otp(OtpVerifyRequest(email="test@example.com", code="012345"), AsyncMock())

    verified.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_registration_purpose_never_calls_supabase(monkeypatch):
    """Only sign-up confirmation is verified here; every other purpose is refused."""
    remote = AsyncMock()
    monkeypatch.setattr(auth, "auth_call", remote)

    with pytest.raises(HTTPException) as error:
        await auth.verify_otp(OtpVerifyRequest(email="test@example.com", code="012345", purpose="login"), AsyncMock())

    assert error.value.status_code == 400
    remote.assert_not_awaited()


@pytest.mark.asyncio
async def test_phone_otp_verification_is_refused(monkeypatch):
    """Phone confirmation is no longer an identity path, so it is refused early."""
    remote = AsyncMock()
    monkeypatch.setattr(auth, "auth_call", remote)

    with pytest.raises(HTTPException) as error:
        await auth.verify_otp(OtpVerifyRequest(phone="0900000000", code="012345"), AsyncMock())

    assert error.value.status_code == 400
    remote.assert_not_awaited()
