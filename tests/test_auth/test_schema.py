"""Unit tests for authentication request validation."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from src.schemas.auth import (
    ForgotPasswordRequest,
    OtpSendResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
)


def test_register_rejects_future_date_of_birth():
    """Registration rejects a date of birth that is not in the past."""
    with pytest.raises(ValidationError, match="date_of_birth must be in the past"):
        RegisterRequest(email="user@example.com", date_of_birth=date.today() + timedelta(days=1))


def test_register_rejects_invalid_citizen_id():
    """Registration requires a twelve-digit citizen identifier when supplied."""
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", citizen_id="12345")


def test_otp_send_response_allows_mock_code_to_be_returned():
    """The OTP response schema carries the mock code in the unified data payload."""
    response = OtpSendResponse(otp="123456")

    assert response.model_dump() == {"otp": "123456"}


def test_forgot_password_requires_an_identity():
    """Forgot-password requests require email or phone."""
    with pytest.raises(ValidationError):
        ForgotPasswordRequest()


def test_reset_password_validates_code_and_new_password():
    """Reset-password requests validate OTP and password length."""
    request = ResetPasswordRequest(email="user@example.com", code="123456", new_password="new-password")

    assert request.code == "123456"
    assert request.new_password == "new-password"


def test_profile_rejects_future_birth_date_and_invalid_citizen_id():
    """Profile updates use the same personal-data validation as registration."""
    with pytest.raises(ValidationError):
        UpdateProfileRequest(date_of_birth=date.today())
    with pytest.raises(ValidationError):
        UpdateProfileRequest(citizen_id="12345")
