"""Booking route and contract tests."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.api.dependencies import get_current_user
from src.api.endpoints.notification import get_notification_service
from src.db.dependencies import get_db_session
from src.main import app
from src.utils.response_mappers import curated_ai_triage


def test_staff_booking_triage_mapper_exposes_only_approved_snapshot_fields():
    result = curated_ai_triage({"ats_level": 2, "symptoms": "headache", "checkpoint": {"private": True}})
    assert result == {"ats_level": 2, "symptoms": "headache"}
    assert curated_ai_triage({}) is None


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


@pytest.mark.asyncio
async def test_patient_cannot_cancel_from_staff_appointments(client):
    """The staff cancellation route remains protected by the staff role gate."""
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role="patient", status="active")
    app.dependency_overrides[get_db_session] = override_db_session
    try:
        response = await client.post(f"/api/v1/staff/bookings/{uuid4()}/cancel", json={"reason": "Đổi lịch"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_staff_can_cancel_appointment_through_staff_api(client, monkeypatch):
    """The staff route forwards the authenticated actor and required reason."""
    from src.api.endpoints import booking as booking_endpoint
    from src.schemas.booking import StaffBookingResponse

    actor_id, booking_id, user_id = uuid4(), uuid4(), uuid4()
    response_data = StaffBookingResponse(
        id=booking_id,
        user_id=user_id,
        status="cancelled",
        patient_name="Nguyen An",
        patient_email=None,
        patient_phone=None,
        patient_date_of_birth=None,
        patient_gender=None,
        patient_citizen_id=None,
        patient_health_insurance_code=None,
        doctor_name="Doctor",
        doctor_title=None,
        doctor_avatar=None,
        specialty_name="Internal Medicine",
        service_name="Consultation",
        facility_name="Times City",
        facility_address=None,
        room=None,
    )
    calls = []

    class FakeBookingService:
        async def cancel_for_staff(self, requested_id, requested_actor, reason):
            calls.append((requested_id, requested_actor, reason))
            return object()

    monkeypatch.setattr(booking_endpoint, "staff_booking_response", lambda _value: response_data)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=actor_id, role="staff", status="active")
    app.dependency_overrides[booking_endpoint.get_booking_service] = FakeBookingService
    try:
        response = await client.post(f"/api/v1/staff/bookings/{booking_id}/cancel", json={"reason": "  Bác sĩ nghỉ  "})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "cancelled"
    assert calls == [(booking_id, actor_id, "Bác sĩ nghỉ")]


@pytest.mark.asyncio
async def test_staff_appointment_api_is_documented(client):
    """The staff appointment API remains visible in the interactive docs."""
    docs_response, openapi_response = await client.get("/docs"), await client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert openapi_response.status_code == 200
    assert "/api/v1/staff/bookings/{booking_id}/cancel" in openapi_response.json()["paths"]


@pytest.mark.asyncio
async def test_staff_booking_search_returns_paged_envelope(client):
    """Staff booking filters map to the paged queue contract."""
    from types import SimpleNamespace

    from src.api.endpoints.booking import get_booking_service

    calls = []

    class FakeBookingService:
        async def list_for_staff(self, *args):
            calls.append(args)
            return [], 23, {"all": 23, "pending_approval": 12, "confirmed": 8, "rejected": 3}, {}

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role="staff", status="active")
    app.dependency_overrides[get_booking_service] = FakeBookingService
    try:
        response = await client.get(
            "/api/v1/staff/bookings",
            params={
                "q": "Nguyen",
                "service_id": str(uuid4()),
                "status": "confirmed",
                "offset": 20,
                "limit": 20,
                "scheduled_only": "true",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"] == {
        "items": [],
        "total": 23,
        "offset": 20,
        "limit": 20,
        "status_counts": {"all": 23, "pending_approval": 12, "confirmed": 8, "rejected": 3},
    }
    assert calls[0][0] == "confirmed"
    assert calls[0][2:4] == (20, 20)
    assert calls[0][4] == "Nguyen"
    assert calls[0][6] is True


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
        ("POST", "/api/v1/staff/bookings/{booking_id}/cancel"),
    }.issubset({(method.upper(), path) for path, operations in paths.items() for method in operations})


def test_staff_cancellation_requires_nonblank_reason():
    """Staff cannot cancel an appointment with a missing or blank reason."""
    from pydantic import ValidationError

    from src.schemas.booking import StaffBookingCancelRequest

    with pytest.raises(ValidationError):
        StaffBookingCancelRequest(reason="   ")


@pytest.mark.asyncio
async def test_hold_route_requires_patient_authentication(client):
    """Unauthenticated users cannot reserve booking capacity."""
    response = await client.post("/api/v1/bookings/hold", json={})

    assert response.status_code == 401
    assert response.json()["error"] == {"code": 401}


@pytest.mark.asyncio
async def test_requested_time_check_requires_patient_authentication(client):
    response = await client.get(
        f"/api/v1/doctors/{uuid4()}/availability/check",
        params={
            "facility_id": str(uuid4()),
            "starts_at": "2030-01-01T09:00:00+07:00",
            "ends_at": "2030-01-01T09:30:00+07:00",
        },
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "NOT_AUTHENTICATED"


@pytest.mark.asyncio
async def test_requested_time_check_returns_only_availability(client, monkeypatch):
    from src.services.booking import BookingService

    async def unavailable(self, *_args):
        del self
        return False

    monkeypatch.setattr(BookingService, "requested_time_available", unavailable)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4(), role="patient", status="active")
    app.dependency_overrides[get_db_session] = override_db_session
    try:
        response = await client.get(
            f"/api/v1/doctors/{uuid4()}/availability/check",
            params={
                "facility_id": str(uuid4()),
                "starts_at": "2030-01-01T09:00:00+07:00",
                "ends_at": "2030-01-01T09:30:00+07:00",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"] == {"available": False}
    assert "schedule_id" not in response.json()["data"]


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
