"""RBAC and API-surface tests for the medical catalog."""

from datetime import UTC, date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.api.dependencies import get_current_user
from src.api.endpoints.catalog import _availability_window, get_catalog_service
from src.main import app


class EmptyCatalogService:
    """Catalog service double for an authorized staff request."""

    async def list_services(self, *, public_only, offset, limit):
        assert public_only is False
        assert offset == 0
        assert limit == 100
        return []


class EmptyPublicCatalogService:
    """Catalog service double for public patient catalog requests."""

    async def list_services(self, *, public_only, offset, limit, name=None, category=None):
        assert public_only is True
        assert offset == 0
        assert limit == 50
        assert name is None
        assert category is None
        return []

    async def get_service(self, resource_id, *, public_only):
        assert resource_id
        assert public_only is True
        now = datetime.now(UTC)
        return SimpleNamespace(
            id=resource_id,
            code="CONSULT",
            name="General consultation",
            description=None,
            duration_minutes=30,
            price=100000,
            original_price=None,
            category="consultation",
            features=[],
            patient_count=0,
            satisfaction_rate=5.0,
            status="active",
            created_at=now,
            updated_at=now,
        )


@pytest.mark.asyncio
async def test_staff_catalog_requires_authentication(client):
    """Unauthenticated staff catalog requests return the auth contract."""
    response = await client.get("/api/v1/staff/services")

    assert response.status_code == 401
    assert response.json()["error"] == {"code": 401}


@pytest.mark.asyncio
async def test_patient_cannot_access_staff_catalog(client):
    """Authenticated patients receive 403 from staff-only catalog routes."""
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="patient", status="active")
    try:
        response = await client.get("/api/v1/staff/services")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"] == {"code": 403}


@pytest.mark.asyncio
async def test_staff_can_access_staff_catalog(client):
    """Staff users can access the staff catalog API."""
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="staff", status="active")
    app.dependency_overrides[get_catalog_service] = lambda: EmptyCatalogService()
    try:
        response = await client.get("/api/v1/staff/services")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_authenticated_patient_can_access_public_services(client):
    """Patients can read active services without staff permissions."""
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="patient", status="active")
    app.dependency_overrides[get_catalog_service] = lambda: EmptyPublicCatalogService()
    try:
        response = await client.get("/api/v1/services")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"] == []


@pytest.mark.asyncio
async def test_authenticated_patient_can_read_one_public_service(client):
    """Patients can read one active service through the public detail API."""
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="patient", status="active")
    app.dependency_overrides[get_catalog_service] = lambda: EmptyPublicCatalogService()
    service_id = uuid4()
    try:
        response = await client.get(f"/api/v1/services/{service_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(service_id)


def test_availability_window_uses_business_timezone_for_date_range():
    """A date range is converted from Vietnam local midnights to UTC."""
    starts_from, starts_to = _availability_window(date(2026, 9, 28), date(2026, 9, 29), None)

    assert starts_from == datetime(2026, 9, 27, 17, tzinfo=UTC)
    assert starts_to == datetime(2026, 9, 29, 17, tzinfo=UTC)


def test_availability_window_for_selected_date_covers_one_local_day():
    """A selected Vietnam date covers exactly that local calendar day."""
    starts_from, starts_to = _availability_window(None, None, date(2026, 9, 28))

    assert starts_from == datetime(2026, 9, 27, 17, tzinfo=UTC)
    assert starts_to == datetime(2026, 9, 28, 17, tzinfo=UTC)


def test_availability_window_accepts_datetime_range_with_timezone():
    """Availability supports precise local time ranges and normalizes them to UTC."""
    local_tz = timezone(timedelta(hours=7))

    starts_from, starts_to = _availability_window(
        datetime(2026, 9, 28, 8, 30, tzinfo=local_tz),
        datetime(2026, 9, 28, 12, tzinfo=local_tz),
        None,
    )

    assert starts_from == datetime(2026, 9, 28, 1, 30, tzinfo=UTC)
    assert starts_to == datetime(2026, 9, 28, 5, tzinfo=UTC)


@pytest.mark.parametrize(
    ("from_value", "to_value", "selected_date", "message"),
    [
        (datetime(2026, 9, 28, 8, 30), None, None, "from and to must be provided together"),
        (datetime(2026, 9, 28, 12), datetime(2026, 9, 28, 8), None, "to must be after from"),
        (datetime(2026, 9, 28, 8), datetime(2026, 9, 28, 9), date(2026, 9, 28), "Use either date or from/to, not both"),
    ],
)
def test_availability_window_rejects_ambiguous_or_invalid_ranges(from_value, to_value, selected_date, message):
    """Availability rejects incomplete, reversed, and mixed time filters."""
    with pytest.raises(ValueError, match=message):
        _availability_window(from_value, to_value, selected_date)
