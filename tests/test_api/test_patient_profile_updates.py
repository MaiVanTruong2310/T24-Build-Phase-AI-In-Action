from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.user import User
from src.schemas.auth import UpdateProfileRequest
from src.services.auth import AuthService


@pytest.mark.asyncio
async def test_partial_health_edit_preserves_other_profile_data():
    session = AsyncMock()
    session.begin = MagicMock(return_value=AsyncMock())
    user = User(
        id=uuid4(),
        full_name="Profile Test",
        role="patient",
        patient_details={"blood_type": "O+", "emergency_name": "Contact Test"},
    )
    await AuthService(session).update_profile(
        user, UpdateProfileRequest(patient_details={"allergies": "Patient-reported value"})
    )
    assert user.patient_details == {
        "blood_type": "O+",
        "emergency_name": "Contact Test",
        "allergies": "Patient-reported value",
    }
    assert user.role == "patient" and user.full_name == "Profile Test"
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_clearing_a_field_does_not_clear_other_details():
    session = AsyncMock()
    session.begin = MagicMock(return_value=AsyncMock())
    user = User(id=uuid4(), patient_details={"address": "Test location", "blood_type": "O+"})
    await AuthService(session).update_profile(user, UpdateProfileRequest(patient_details={"address": None}))
    assert user.patient_details == {"address": None, "blood_type": "O+"}


@pytest.mark.parametrize(
    "payload",
    [
        {"role": "staff"},
        {"email": "new@example.invalid"},
        {"patient_details": {"role": "admin"}},
        {"patient_details": {"weight_kg": -1}},
        {"phone": "abc"},
        {"citizen_id": "123"},
    ],
)
def test_profile_update_rejects_unsafe_or_invalid_fields(payload):
    with pytest.raises(ValidationError):
        UpdateProfileRequest(**payload)
