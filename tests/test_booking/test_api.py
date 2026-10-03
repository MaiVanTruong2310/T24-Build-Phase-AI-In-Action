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
    assert response.json()["error"] == {"code": 401}


@pytest.mark.asyncio
async def test_cancel_booking_supports_coordination_case(client):
    """When a booking_id is not in bookings, cancellation falls back to coordination_cases."""
    from datetime import datetime, UTC
    from types import SimpleNamespace

    user_id = uuid4()
    case_id = uuid4()

    mock_case = SimpleNamespace(
        id=case_id,
        patient_id=user_id,
        owner_key=f"user:{user_id}",
        status="new",
        control="ai",
        version=1,
        facility_id=None,
        booking_id=None,
        follow_up_at=None,
        patient={"name": "Nguyễn Văn A", "phone": "0987654321"},
        ai_snapshot={},
        plan={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    class CaseSession:
        def __init__(self):
            self.added = []

        def begin(self):
            class Tx:
                async def __aenter__(self):
                    return None

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    return None

            return Tx()

        async def execute(self, statement):
            stmt_str = str(statement)
            if "coordination_cases" in stmt_str:
                class SingleResult:
                    def scalar_one_or_none(self):
                        return mock_case

                return SingleResult()
            class ListResult:
                def scalars(self):
                    return self

                def all(self):
                    return []

                def scalar_one_or_none(self):
                    return None

            return ListResult()

        def add(self, entity):
            self.added.append(entity)

        async def flush(self):
            pass

        async def commit(self):
            pass

    async def override_db():
        yield CaseSession()

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=user_id, role="patient", status="active", full_name="Nguyễn Văn A")
    app.dependency_overrides[get_db_session] = override_db
    try:
        response = await client.post(f"/api/v1/bookings/{case_id}/cancel", json={"reason": "Bận việc đột xuất"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(case_id)
    assert data["status"] == "cancelled"
    assert data["cancellation_reason"] == "Bận việc đột xuất"
    assert mock_case.status == "cancelled"
