"""Booking route and contract tests."""

from uuid import uuid4

import pytest

from src.api.dependencies import get_current_user
from src.db.dependencies import get_db_session
from src.main import app


class EmptyResult:
    def scalars(self):
        return self

    def all(self):
        return []


class EmptySession:
    async def execute(self, _statement):
        return EmptyResult()


async def override_db_session():
    """Keep authorization contract tests independent of PostgreSQL configuration."""
    yield EmptySession()


@pytest.mark.asyncio
async def test_booking_routes_require_authentication(client):
    """Unauthenticated users cannot access booking endpoints."""
    response = await client.get("/api/v1/bookings")

    assert response.status_code == 401
    assert response.json()["error"] == {"code": 401}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["patient", "staff", "doctor"])
async def test_authenticated_roles_can_access_booking_routes(client, role):
    """Every authenticated role can use the common booking endpoints."""
    from types import SimpleNamespace

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role=role, status="active")
    app.dependency_overrides[get_db_session] = override_db_session
    try:
        response = await client.get("/api/v1/bookings")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


def test_booking_routes_are_mounted_under_api_v1():
    """The direct booking API exposes the agreed patient routes."""
    paths = app.openapi()["paths"]

    assert {
        ("POST", "/api/v1/bookings"),
        ("GET", "/api/v1/bookings"),
        ("GET", "/api/v1/bookings/{booking_id}"),
        ("POST", "/api/v1/bookings/{booking_id}/cancel"),
    }.issubset({(method.upper(), path) for path, operations in paths.items() for method in operations})

    assert {
        ("GET", "/api/v1/staff/bookings"),
        ("GET", "/api/v1/staff/bookings/{booking_id}"),
        ("PATCH", "/api/v1/staff/bookings/{booking_id}/status"),
    }.issubset({(method.upper(), path) for path, operations in paths.items() for method in operations})
