from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.api.endpoints import auth
from src.core.exceptions import AppError
from src.models.user import User
from src.services import cookie_session
from src.services import supabase_auth as gateway
from src.services.cookie_session import ACCESS_COOKIE, REFRESH_COOKIE, cookie_options

TOKENS = {"access_token": "test-access-cookie", "refresh_token": "r" * 40, "expires_in": 3600}
HEADERS = {"Origin": "http://localhost:5173", "X-Auth-Transport": "cookie"}


@pytest.fixture
def cookie_auth(monkeypatch):
    monkeypatch.setattr(
        cookie_session,
        "get_settings",
        lambda: SimpleNamespace(
            auth_cookie_secure=False,
            auth_cookie_samesite="lax",
            app_env="test",
            jwt_refresh_token_expire_days=30,
        ),
    )
    monkeypatch.setattr(auth, "login_email", AsyncMock(return_value=TOKENS))
    remote = AsyncMock(return_value={**TOKENS, "access_token": "rotated-access", "refresh_token": "s" * 40})
    monkeypatch.setattr(auth, "auth_call", remote)
    profile = User(
        id=uuid4(),
        email="cookie@example.invalid",
        full_name="Cookie test",
        role="patient",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    verified = AsyncMock(return_value=profile)
    monkeypatch.setattr(gateway, "authenticated_profile", verified)
    yield remote, verified


@pytest.mark.asyncio
async def test_cookie_login_reload_refresh_and_logout(client, cookie_auth):
    remote, verified = cookie_auth
    response = await client.post(
        "/api/v1/auth/login", json={"email": "cookie@example.invalid", "password": "example-password"}, headers=HEADERS
    )
    assert response.status_code == 200
    assert response.json()["data"]["authenticated"] is True
    assert "access_token" not in response.json()["data"] and "refresh_token" not in response.json()["data"]
    headers = response.headers.get_list("set-cookie")
    assert len(headers) == 2 and all("HttpOnly" in value and "SameSite=lax" in value for value in headers)
    assert "Path=/api/v1;" in headers[0] and "Path=/api/v1/auth;" in headers[1]
    assert response.headers["cache-control"] == "no-store"
    for _ in range(2):
        me = await client.get("/api/v1/users/me")
        assert me.status_code == 200
        assert verified.call_args.args[0] == TOKENS["access_token"]
    client.cookies.delete(ACCESS_COOKIE)
    assert (await client.get("/api/v1/users/me")).status_code == 401
    refreshed = await client.post("/api/v1/auth/refresh-token", headers=HEADERS)
    assert refreshed.status_code == 200 and refreshed.json()["data"]["authenticated"]
    assert remote.call_args.args[1]["refresh_token"] == TOKENS["refresh_token"]
    assert client.cookies.get(ACCESS_COOKIE) == "rotated-access"
    await client.get("/api/v1/users/me")
    assert verified.call_args.args[0] == "rotated-access"
    result = await client.post("/api/v1/auth/logout", headers=HEADERS)
    assert (
        result.status_code == 200 and not client.cookies.get(ACCESS_COOKIE) and not client.cookies.get(REFRESH_COOKIE)
    )
    assert (await client.get("/api/v1/users/me")).status_code == 401


@pytest.mark.asyncio
async def test_origin_blocks_cookie_csrf_and_allows_preflight(client, cookie_auth):
    for origin in (None, "https://evil.example"):
        headers = {"X-Auth-Transport": "cookie"}
        if origin:
            headers["Origin"] = origin
        result = await client.post(
            "/api/v1/auth/login",
            json={"email": "cookie@example.invalid", "password": "example-password"},
            headers=headers,
        )
        assert result.status_code == 403 and not result.headers.get_list("set-cookie")
    preflight = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": HEADERS["Origin"],
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-auth-transport,content-type",
        },
    )
    assert preflight.status_code == 200 and preflight.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_refresh_transient_keeps_cookies_invalid_clears(client, cookie_auth):
    remote, _ = cookie_auth
    await client.post(
        "/api/v1/auth/login", json={"email": "cookie@example.invalid", "password": "example-password"}, headers=HEADERS
    )
    remote.side_effect = AppError("AUTH_UNAVAILABLE", "Temporary error", 503)
    result = await client.post("/api/v1/auth/refresh-token", headers=HEADERS)
    assert result.status_code == 503 and client.cookies.get(REFRESH_COOKIE)
    remote.side_effect = AppError("INVALID_REFRESH", "Expired", 400)
    result = await client.post("/api/v1/auth/refresh-token", headers=HEADERS)
    assert result.status_code == 400 and not client.cookies.get(REFRESH_COOKIE)


@pytest.mark.asyncio
async def test_logout_provider_failure_still_clears_browser_cookie(client, cookie_auth):
    remote, _ = cookie_auth
    await client.post(
        "/api/v1/auth/login", json={"email": "cookie@example.invalid", "password": "example-password"}, headers=HEADERS
    )
    remote.side_effect = AppError("AUTH_UNAVAILABLE", "Temporary error", 503)
    result = await client.post("/api/v1/auth/logout", headers=HEADERS)
    assert (
        result.status_code == 503 and not client.cookies.get(REFRESH_COOKIE) and not client.cookies.get(ACCESS_COOKIE)
    )


@pytest.mark.asyncio
async def test_expired_cookie_chat_never_becomes_guest(client, cookie_auth):
    result = await client.post(
        "/api/v1/chat",
        json={"message": "hi", "session_id": "cookie-expired"},
        headers={**HEADERS, "X-Session-Expected": "1"},
    )
    assert result.status_code == 401


def test_production_cookie_settings(monkeypatch):
    from types import SimpleNamespace

    from src.services import cookie_session

    monkeypatch.setattr(
        cookie_session,
        "get_settings",
        lambda: SimpleNamespace(auth_cookie_secure=None, app_env="production", auth_cookie_samesite="lax"),
    )
    assert cookie_options()["secure"] is True
