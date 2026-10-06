"""Staff sessions remain valid but cannot edit patient medical profiles."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.api.dependencies import get_current_user
from src.api.endpoints.auth import get_auth_service
from src.main import app
from src.models.user import User


@pytest.mark.asyncio
async def test_staff_can_restore_session_but_cannot_edit_patient_profile(client):
    staff = User(id=uuid4(), role="staff", status="active", full_name="Điều phối viên", phone="admin123")
    service = AsyncMock()
    previous_user = app.dependency_overrides.get(get_current_user)
    previous_service = app.dependency_overrides.get(get_auth_service)
    app.dependency_overrides[get_current_user] = lambda: staff
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        restored = await client.get("/api/v1/users/me")
        assert restored.status_code == 200
        assert restored.json()["data"]["role"] == "staff"

        profile = await client.patch("/api/v1/users/me", json={"full_name": "Tên sai"})
        portrait = await client.patch("/api/v1/users/me/portrait", json={"image": None})
        assert profile.status_code == 403
        assert portrait.status_code == 403
        service.update_profile.assert_not_awaited()
        service.update_portrait.assert_not_awaited()
    finally:
        if previous_user is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous_user
        if previous_service is None:
            app.dependency_overrides.pop(get_auth_service, None)
        else:
            app.dependency_overrides[get_auth_service] = previous_service
