from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.medical_assistant.api import routes
from src.medical_assistant.domain.schemas import ChatRequest
from src.services.chat_history import STATE_FIELDS, graph_thread, health_record


def profile():
    return SimpleNamespace(
        id=uuid4(),
        full_name="Account name",
        phone="0912345678",
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


@pytest.mark.asyncio
async def test_completed_retry_does_not_invoke_agent(monkeypatch):
    invoke = AsyncMock()
    monkeypatch.setattr(routes.agent, "ainvoke", invoke)
    result = {"response": "Saved answer"}
    assert await routes.run_turn(ChatRequest(message="hi"), profile(), {}, {"cached": result}, None) == result
    invoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_active_takeover_pauses_agent_and_records_patient_message(monkeypatch):
    invoke = AsyncMock()
    monkeypatch.setattr(routes.agent, "ainvoke", invoke)
    takeover = SimpleNamespace(
        active_case_for_patient=AsyncMock(return_value=object()),
        record_patient_message=AsyncMock(),
    )
    monkeypatch.setattr(routes, "ChatTakeoverService", lambda session: takeover)
    service = SimpleNamespace(session=object(), complete=AsyncMock(), fail=AsyncMock())
    user = profile()
    request = ChatRequest(message="Tôi vẫn còn đau", session_id="same")

    response = await routes.run_turn(
        request, user, {}, {"checkpoint": {"workflow_status": "HUMAN_HELP_REQUESTED"}}, service
    )

    assert response["workflow_status"] == "HUMAN_HELP_REQUESTED"
    assert "nhân viên y tế" in response["response"]
    invoke.assert_not_awaited()
    takeover.record_patient_message.assert_awaited_once_with(
        user.id, request.session_id, request.message, str(request.request_id)
    )
    service.complete.assert_awaited_once()
