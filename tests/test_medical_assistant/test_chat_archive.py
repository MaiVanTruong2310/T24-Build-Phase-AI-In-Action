from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.db import session as db_session
from src.medical_assistant.api import routes
from src.medical_assistant.domain.schemas import ChatRequest
from src.services.chat_history import STATE_FIELDS, graph_thread, health_record


def profile():
    return SimpleNamespace(
        id=uuid4(),
        full_name="Account name",
        phone="0912345678",
        role="patient",
        date_of_birth=None,
        gender=None,
        patient_details={
            "medical_history": [{"name": "Past condition", "status": "recovered"}],
            "allergies": "Test allergy",
            "address": "Private address",
            "emergency_phone": "Private contact",
        },
    )


def test_health_record_and_checkpoint_minimize_identity():
    user = profile()
    record = health_record(user)
    assert record["medical_history"][0]["status"] == "recovered"
    assert record["allergies"] == "Test allergy"
    assert not {"address", "phone", "emergency_phone", "email"} & record.keys()
    assert not {"analysis", "patient_profile", "patient_health_record", "user_id"} & STATE_FIELDS
    assert graph_thread("same", user) != graph_thread("same", profile())
    assert graph_thread("same", user) != graph_thread("same")


@pytest.mark.asyncio
async def test_authenticated_turn_uses_verified_owner_and_restored_context(monkeypatch):
    service = SimpleNamespace(
        begin_turn=AsyncMock(return_value={"checkpoint": {"clinical_facts": {"duration": "two days"}}})
    )
    monkeypatch.setattr(routes, "ChatHistoryService", lambda session: service)
    profile_db = AsyncMock()
    profile_db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)
    profile_session = AsyncMock()
    profile_session.__aenter__.return_value = profile_db
    monkeypatch.setattr(db_session, "get_session_factory", lambda: lambda: profile_session)
    memory = SimpleNamespace(
        get_patient_profile=AsyncMock(return_value=[]),
        get_active_open_loops=AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "src.medical_assistant.domain.patient_memory_service.get_patient_memory_service", lambda: memory
    )
    user = profile()
    request = ChatRequest(
        message="Follow up",
        session_id="same",
        user_id=str(uuid4()),
        patient_profile={"name": "Forged name", "phone": "0987654321"},
    )
    payload, _, _ = await routes.prepare_turn(request, user, None)
    assert payload["user_id"] == str(user.id)
    assert payload["patient_profile"] == {"name": user.full_name, "phone": user.phone}
    assert payload["clinical_facts"] == {"duration": "two days"}
    assert payload["patient_health_record"]["allergies"] == "Test allergy"
    profile_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_completed_retry_does_not_invoke_agent(monkeypatch):
    invoke = AsyncMock()
    monkeypatch.setattr(routes.agent, "ainvoke", invoke)
    result = {"response": "Saved answer"}
    assert await routes.run_turn(ChatRequest(message="hi"), profile(), {}, {"cached": result}, None) == result
    invoke.assert_not_awaited()
