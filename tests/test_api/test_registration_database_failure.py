import pytest
from unittest.mock import AsyncMock
from sqlalchemy.exc import OperationalError
from src.main import app
from src.api.endpoints.auth import get_auth_service


@pytest.mark.asyncio
async def test_registration_connection_failure_returns_readable_cors_error(client, monkeypatch):
    monkeypatch.setattr("src.api.endpoints.auth.native_auth_enabled", lambda: False)
    service = AsyncMock()
    service.register.side_effect = OperationalError("select", {}, Exception("private internal error"))
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        response = await client.post(
            "/api/v1/auth/register",
            json={"phone": "0900000000", "full_name": "Test User"},
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 503
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "Vui lòng thử lại sau" in response.json()["message"]
        assert "private internal error" not in response.text
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
