"""Booking route and contract tests."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.api.dependencies import get_current_user
from src.api.endpoints.notification import get_notification_service
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
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


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


@pytest.mark.asyncio
async def test_staff_booking_routes_reject_non_staff_users(client):
    """The staff namespace remains protected even when common bookings are not role-gated."""
    from types import SimpleNamespace

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role="patient", status="active")
    app.dependency_overrides[get_db_session] = override_db_session
    try:
        response = await client.get("/api/v1/staff/bookings")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN"


def test_booking_routes_are_mounted_under_api_v1():
    """The direct booking API exposes the agreed patient routes."""
    paths = app.openapi()["paths"]

    assert {
        ("POST", "/api/v1/bookings"),
        ("POST", "/api/v1/bookings/{booking_id}/reschedule"),
        ("GET", "/api/v1/bookings"),
        ("GET", "/api/v1/bookings/{booking_id}"),
        ("POST", "/api/v1/bookings/{booking_id}/cancel"),
    }.issubset({(method.upper(), path) for path, operations in paths.items() for method in operations})

    assert {
        ("POST", "/api/v1/bookings/hold"),
        ("DELETE", "/api/v1/bookings/holds/{hold_id}"),
        ("GET", "/api/v1/staff/bookings"),
        ("GET", "/api/v1/staff/bookings/{booking_id}"),
        ("PATCH", "/api/v1/staff/bookings/{booking_id}/status"),
    }.issubset({(method.upper(), path) for path, operations in paths.items() for method in operations})


@pytest.mark.asyncio
async def test_hold_route_requires_patient_authentication(client):
    """Unauthenticated users cannot reserve booking capacity."""
    response = await client.post("/api/v1/bookings/hold", json={})

    assert response.status_code == 401
    assert response.json()["error"] == {"code": 401}


@pytest.mark.asyncio
async def test_notification_route_requires_authentication(client):
    """Unauthenticated users cannot read notification records."""
    response = await client.get("/api/v1/notifications")

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


@pytest.mark.asyncio
async def test_notification_route_returns_booking_expired_kind(client):
    """Delivered expiry notifications serialize through the shared response contract."""
    notification = SimpleNamespace(
        id=uuid4(),
        booking_id=uuid4(),
        kind="booking_expired",
        title="Lịch khám đã hết hạn",
        message="Lịch khám chưa được duyệt trong thời hạn 24 giờ.",
        available_at=datetime.now(UTC),
        read_at=None,
        created_at=datetime.now(UTC),
    )

    class NotificationServiceStub:
        async def list_for_user(self, *_args, **_kwargs):
            return [notification]

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role="patient", status="active")
    app.dependency_overrides[get_notification_service] = NotificationServiceStub
    try:
        response = await client.get("/api/v1/notifications?unread_only=false&offset=0&limit=50")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"][0]["kind"] == "booking_expired"
