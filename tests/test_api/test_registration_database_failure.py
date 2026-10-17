"""Registration must surface a safe, readable error when the database is down."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import OperationalError

from src.api.endpoints import auth as auth_endpoints


@pytest.mark.asyncio
async def test_registration_connection_failure_returns_readable_cors_error(client, monkeypatch):
    """A database outage during registration returns the safe 503 contract with CORS."""
    failure = OperationalError("select", {}, Exception("private internal error"))
    monkeypatch.setattr(auth_endpoints, "register_email", AsyncMock(side_effect=failure))

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "example-password", "full_name": "Test User"},
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.json() == {
        "error_code": "DATABASE_UNAVAILABLE",
        "message": "Service temporarily unavailable",
    }
    assert "private internal error" not in response.text
