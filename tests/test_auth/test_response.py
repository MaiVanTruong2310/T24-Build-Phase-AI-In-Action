import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import Response

from src.api.endpoints import auth as auth_endpoints
from src.api.handlers import app_error_handler, validation_error_handler
from src.api.response import error_response, success_response
from src.core.exceptions import AuthenticationError
from src.schemas.auth import ForgotPasswordRequest, OtpSendRequest, RefreshTokenRequest, ResetPasswordRequest

RECOVERY_MESSAGE = "Vui lòng mở liên kết khôi phục trong email."


def test_success_response_has_unified_envelope():
    response = success_response({"id": "123"}, "Created", 201)

    assert response.status == 201
    assert response.message == "Created"
    assert response.error is None
    assert response.data == {"id": "123"}
    assert response.timestamp.tzinfo is not None


def test_send_otp_endpoint_delegates_to_supabase_and_never_exposes_a_code(monkeypatch):
    """OTP delivery is a Supabase resend; the API never returns a code."""
    remote = AsyncMock(return_value={})
    monkeypatch.setattr(auth_endpoints, "auth_call", remote)

    response = asyncio.run(auth_endpoints.send_otp(OtpSendRequest(email="user@example.com", purpose="login")))

    assert response.data is not None
    assert response.data.otp is None
    remote.assert_awaited_once_with("/resend", {"type": "signup", "email": "user@example.com"})


def test_send_otp_endpoint_requires_an_email_target():
    """A phone-only OTP request is refused because Supabase owns email delivery."""
    with pytest.raises(HTTPException) as error:
        asyncio.run(auth_endpoints.send_otp(OtpSendRequest(phone="0900000000", purpose="login")))

    assert error.value.status_code == 400


def test_logout_endpoint_exchanges_refresh_token_and_clears_session(monkeypatch):
    """Logout uses the refresh token directly and ends the Supabase session."""
    remote = AsyncMock(return_value={"access_token": "supabase-access-token"})
    monkeypatch.setattr(auth_endpoints, "auth_call", remote)

    response = asyncio.run(
        auth_endpoints.logout(
            Request({"type": "http", "headers": []}),
            Response(),
            RefreshTokenRequest(refresh_token="r" * 32),
        )
    )

    assert response.message == "Logout successful"
    assert remote.await_args_list[0].args == ("/token", {"refresh_token": "r" * 32})
    assert remote.await_args_list[0].kwargs == {"params": {"grant_type": "refresh_token"}}
    assert remote.await_args_list[1].args[0] == "/logout"
    assert remote.await_args_list[1].kwargs["token"] == "supabase-access-token"


def test_forgot_password_endpoint_uses_supabase_recovery_email(monkeypatch):
    """Recovery is delegated to Supabase and never returns an OTP."""
    remote = AsyncMock(return_value={})
    monkeypatch.setattr(auth_endpoints, "auth_call", remote)

    response = asyncio.run(auth_endpoints.forgot_password(ForgotPasswordRequest(email=" User@Example.com ")))

    assert response.data is not None
    assert response.data.otp is None
    assert remote.await_args.args == ("/recover", {"email": "user@example.com"})
    assert remote.await_args.kwargs["params"]["redirect_to"].endswith("/forgot-password")


def test_reset_password_endpoint_rejects_otp_reset_with_recovery_link_message():
    """OTP password reset is removed; callers must open the emailed recovery link."""
    request = ResetPasswordRequest(email="user@example.com", code="123456", new_password="new-password")

    with pytest.raises(HTTPException) as error:
        asyncio.run(auth_endpoints.reset_password(request))

    assert error.value.status_code == 400
    assert error.value.detail == RECOVERY_MESSAGE


@pytest.mark.asyncio
async def test_reset_password_route_returns_the_recovery_link_error(client):
    """The HTTP contract of POST /auth/reset-password is the recovery-link 400."""
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"email": "user@example.com", "code": "123456", "new_password": "new-password"},
    )

    assert response.status_code == 400
    assert response.json()["message"] == RECOVERY_MESSAGE


def test_error_response_has_stable_code_and_message():
    response = error_response("INVALID_CREDENTIALS", "Invalid credentials", 401)

    assert response.model_dump() == {
        "error_code": "INVALID_CREDENTIALS",
        "message": "Invalid credentials",
    }


@pytest.mark.parametrize("error_code", ["VALIDATION_ERROR", "NOT_FOUND", "CONFLICT", "RATE_LIMITED"])
def test_error_response_supports_stable_client_error_codes(error_code):
    """Error payloads expose the stable cause code, not an HTTP status number."""
    response = error_response(error_code, "Request failed")

    assert response.model_dump() == {"error_code": error_code, "message": "Request failed"}


def test_app_error_handler_exposes_exception_contract():
    """Application errors preserve the defined public code and message."""
    response = asyncio.run(app_error_handler(None, AuthenticationError("INVALID_TOKEN", "Invalid token")))
    payload = json.loads(response.body)

    assert response.status_code == 401
    assert payload == {"error_code": "INVALID_TOKEN", "message": "Invalid token"}


def test_validation_error_handler_returns_generic_validation_error():
    """Validation failures use one stable message without field details."""
    response = asyncio.run(validation_error_handler(None, RequestValidationError([])))
    payload = json.loads(response.body)

    assert response.status_code == 400
    assert payload == {"error_code": "VALIDATION_ERROR", "message": "Request validation failed"}
