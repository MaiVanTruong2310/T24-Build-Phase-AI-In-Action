"""Tests for staff user lookup by UUID."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.api.dependencies import get_current_user
from src.api.endpoints.auth import get_auth_service
from src.core.exceptions import NotFoundError
from src.main import app
from src.models.user import User


class FakeUserLookupService:
    """Minimal service double for the staff lookup endpoint."""

    def __init__(self, user: User | None = None) -> None:
        self.user = user

    async def get_user_by_id(self, user_id):
        """Return the configured user or the public not-found error."""
        if self.user is None or self.user.id != user_id:
            raise NotFoundError("User not found")
        return self.user


def _active_staff() -> SimpleNamespace:
    """Build an authenticated staff dependency value."""
    return SimpleNamespace(role="staff", status="active")


@pytest.mark.asyncio
async def test_staff_can_lookup_user_by_id(client):
    """Staff receives the requested user in the unified response envelope."""
    user_id = uuid4()
    target = User(id=user_id, email="patient@example.com", role="patient", status="active", full_name="Patient")
    app.dependency_overrides[get_current_user] = _active_staff
    app.dependency_overrides[get_auth_service] = lambda: FakeUserLookupService(target)
    try:
        response = await client.get(f"/api/v1/users/{user_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["id"] == str(user_id)
    assert response.json()["data"]["role"] == "patient"


@pytest.mark.asyncio
async def test_patient_cannot_lookup_user_by_id(client):
    """Patients cannot read another user's profile through the lookup route."""
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="patient", status="active")
    try:
        response = await client.get(f"/api/v1/users/{uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"] == {"code": 403}


@pytest.mark.asyncio
async def test_staff_lookup_returns_not_found_for_unknown_user(client):
    """Unknown user IDs return the standard not-found envelope."""
    app.dependency_overrides[get_current_user] = _active_staff
    app.dependency_overrides[get_auth_service] = lambda: FakeUserLookupService()
    try:
        response = await client.get(f"/api/v1/users/{uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error"] == {"code": 404}
