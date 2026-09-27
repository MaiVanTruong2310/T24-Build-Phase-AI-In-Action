import asyncio
import json

import pytest
from fastapi.exceptions import RequestValidationError

from src.api.endpoints.auth import logout, send_otp
from src.api.handlers import app_error_handler, validation_error_handler
from src.api.response import error_response, success_response
from src.core.exceptions import AuthenticationError
from src.schemas.auth import OtpSendRequest, RefreshTokenRequest


class FakeAuthService:
    """Minimal service double for endpoint response tests."""

    async def send_otp(self, email: str | None, phone: str | None, purpose: str) -> str:
        """Return a deterministic mock OTP."""
        del email, phone, purpose
        return "654321"

    async def logout(self, refresh_token: str) -> None:
        """Accept the refresh token as the logout credential."""
        self.logout_token = refresh_token


def test_success_response_has_unified_envelope():
    response = success_response({"id": "123"}, "Created", 201)

    assert response.status == 201
    assert response.message == "Created"
    assert response.error is None
    assert response.data == {"id": "123"}
    assert response.timestamp.tzinfo is not None


def test_send_otp_endpoint_returns_mock_code_in_data():
    """The OTP endpoint exposes the mock code through the response data field."""
    response = asyncio.run(
        send_otp(
            OtpSendRequest(email="user@example.com", purpose="login"),
            FakeAuthService(),
        )
    )

    assert response.data is not None
    assert response.data.otp == "654321"


def test_logout_endpoint_uses_refresh_token_without_access_token():
    """The logout endpoint forwards the refresh token directly to the service."""
    service = FakeAuthService()

    response = asyncio.run(logout(RefreshTokenRequest(refresh_token="r" * 32), service))

    assert response.message == "Logout successful"
    assert service.logout_token == "r" * 32


def test_error_response_has_unified_envelope():
    response = error_response(401, "Invalid credentials", 401)

    assert response.status == 401
    assert response.error is not None
    assert response.error.code == 401
    assert "details" not in response.error.model_dump()
    assert response.data is None


@pytest.mark.parametrize("status", [400, 404, 429, 408, 401, 403])
def test_error_response_supports_public_client_error_codes(status):
    """Error payloads expose only one of the supported HTTP error codes."""
    response = error_response(status, "Request failed", status)

    assert response.error is not None
    assert response.error.model_dump() == {"code": status}


def test_app_error_handler_exposes_http_code_only():
    """Application errors expose the HTTP code without internal error details."""
    response = asyncio.run(app_error_handler(None, AuthenticationError("INVALID_TOKEN", "Invalid token")))
    payload = json.loads(response.body)

    assert response.status_code == 401
    assert payload["error"] == {"code": 401}
    assert "details" not in payload["error"]


def test_validation_error_handler_returns_bad_request_code():
    """Validation failures use the public 400 error code."""
    response = asyncio.run(validation_error_handler(None, RequestValidationError([])))
    payload = json.loads(response.body)

    assert response.status_code == 400
    assert payload["error"] == {"code": 400}
