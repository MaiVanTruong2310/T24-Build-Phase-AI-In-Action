"""Regression tests for the removed local-JWT staff backdoor.

The legacy stack minted local JWTs and trusted their ``sub``/``role`` claims
(plus a hard-coded ``phone == "admin123"`` staff bypass). Supabase Auth is now
the only identity provider, so a locally signed token must never authenticate a
request on its own.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.api.dependencies import get_current_user
from src.core.exceptions import AppError
from src.core.security import create_access_token
from src.db.dependencies import get_auth_db_session
from src.main import app
from src.models.user import User
from src.services import supabase_auth as gateway


class _ScalarResult:
    """Minimal SQLAlchemy result exposing the single-row lookup."""

    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        """Return the configured row."""
        return self._value


@pytest.mark.asyncio
async def test_locally_signed_staff_jwt_is_not_accepted_as_a_session(client, monkeypatch):
    """A locally signed staff token is rejected by Supabase instead of being trusted."""
    token, _ = create_access_token(subject=str(uuid4()), role="staff")
    remote = AsyncMock(side_effect=AppError("invalid_claim", "Invalid token", 401))
    monkeypatch.setattr(gateway, "auth_call", remote)

    response = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    # The token is treated as an opaque Supabase credential, never decoded locally.
    assert remote.await_args.kwargs["token"] == token
    assert remote.await_args.args[0] == "/user"


@pytest.mark.asyncio
async def test_locally_signed_staff_jwt_is_refused_by_a_staff_only_route(client, monkeypatch):
    """The staff claim in a local JWT never grants access to staff-only routes."""
    token, _ = create_access_token(subject=str(uuid4()), role="staff")
    patient = User(id=uuid4(), email="patient@example.com", role="patient", status="active")
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(patient)
    identity = {
        "id": str(uuid4()),
        "email": "patient@example.com",
        "email_confirmed_at": "2026-10-01T00:00:00Z",
    }
    monkeypatch.setattr(gateway, "auth_call", AsyncMock(return_value=identity))

    previous_session = app.dependency_overrides.get(get_auth_db_session)
    previous_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_auth_db_session] = lambda: session
    try:
        response = await client.get(f"/api/v1/users/{uuid4()}", headers={"Authorization": f"Bearer {token}"})
    finally:
        if previous_session is None:
            app.dependency_overrides.pop(get_auth_db_session, None)
        else:
            app.dependency_overrides[get_auth_db_session] = previous_session
        if previous_user is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = previous_user

    assert response.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN"
