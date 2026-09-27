"""Unit tests for authentication request validation."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from src.schemas.auth import OtpSendResponse, RegisterRequest


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
