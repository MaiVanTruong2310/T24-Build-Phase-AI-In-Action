"""Booking route and contract tests."""

import pytest

from src.api.dependencies import get_current_user
from src.main import app


@pytest.mark.asyncio
async def test_booking_routes_require_authentication(client):
    """Unauthenticated patients cannot access booking endpoints."""
    response = await client.get("/api/v1/bookings")

    assert response.status_code == 401
    assert response.json()["error"] == {"code": 401}


@pytest.mark.asyncio
async def test_staff_cannot_access_patient_booking_routes(client):
    """Staff requests do not bypass patient booking ownership rules."""
    from types import SimpleNamespace

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="staff-id", role="staff", status="active")
    try:
        response = await client.get("/api/v1/bookings")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"] == {"code": 403}


def test_booking_routes_are_mounted_under_api_v1():
    """The direct booking API exposes the agreed patient routes."""
    paths = app.openapi()["paths"]

    assert {
        ("POST", "/api/v1/bookings"),
        ("GET", "/api/v1/bookings"),
        ("GET", "/api/v1/bookings/{booking_id}"),
        ("POST", "/api/v1/bookings/{booking_id}/cancel"),
    }.issubset({(method.upper(), path) for path, operations in paths.items() for method in operations})
