import uuid
from datetime import date
import pytest


@pytest.mark.asyncio
async def test_guest_list_sessions_unauthenticated(client):
    """Unauthenticated visitors can query doctor sessions without 401/403 error."""
    fake_doctor_id = str(uuid.uuid4())
    response = await client.get(
        "/api/v1/coordination/sessions",
        params={"doctor_id": fake_doctor_id, "date": date.today().isoformat()},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == []


@pytest.mark.asyncio
async def test_guest_create_request_requires_guest_fields(client):
    """Guest requests without personal information are rejected."""
    fake_session_id = str(uuid.uuid4())
    fake_service_id = str(uuid.uuid4())
    fake_specialty_id = str(uuid.uuid4())

    response = await client.post(
        "/api/v1/coordination/requests",
        json={
            "session_id": fake_session_id,
            "service_id": fake_service_id,
            "specialty_id": fake_specialty_id,
            "reason": "Đau bụng âm ỉ",
        },
    )
    assert response.status_code in (409, 422)
    payload = response.json()
    # Should indicate missing name or phone
    assert "họ và tên" in payload.get("message", "").lower() or "NAME_REQUIRED" in str(payload)


@pytest.mark.asyncio
async def test_guest_create_request_validates_phone(client):
    """Guest requests with invalid Vietnamese phone are rejected."""
    fake_session_id = str(uuid.uuid4())
    fake_service_id = str(uuid.uuid4())
    fake_specialty_id = str(uuid.uuid4())

    response = await client.post(
        "/api/v1/coordination/requests",
        json={
            "session_id": fake_session_id,
            "service_id": fake_service_id,
            "specialty_id": fake_specialty_id,
            "reason": "Đau bụng âm ỉ",
            "patient_name": "Nguyễn Văn A",
            "patient_phone": "12345",  # Invalid phone
            "gender": "male",
            "date_of_birth": "1995-05-15",
        },
    )
    assert response.status_code in (409, 422)
    payload = response.json()
    assert "định dạng" in payload.get("message", "") or "INVALID_PHONE" in str(payload)
