"""RBAC and API-surface tests for the medical catalog."""

from datetime import UTC, date, datetime
from types import SimpleNamespace

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
