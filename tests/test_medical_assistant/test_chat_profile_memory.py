import uuid
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.api.routes import chat_agent_input
from src.medical_assistant.domain.schemas import ChatPatientProfile, ChatRequest


def test_profile_validation_and_structured_transport():
    request = ChatRequest(
        message="Chào bạn",
        session_id="profile-test",
        patient_profile={"name": "  Nguyễn   An ", "phone": "0912 345 678"},
    )
    payload = chat_agent_input(request)
    assert payload["query"] == "Chào bạn"
    assert payload["patient_name"] == "Nguyễn An"
    assert payload["patient_phone"] == "0912345678"
    assert "patient_profile" not in chat_agent_input(ChatRequest(message="hi"))
    with pytest.raises(ValidationError):
        ChatPatientProfile(name=" ", phone="not-a-phone")


@pytest.mark.asyncio
async def test_identity_survives_truncated_history_and_is_isolated():
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    first = await agent.ainvoke(
        chat_agent_input(ChatRequest(message="Chào bạn", patient_profile={"name": "Nguyễn An", "phone": "0912345678"})),
        config,
    )
    assert "Nguyễn An" in first["response"]
    for _ in range(11):
        await agent.ainvoke({"query": "Xin chào"}, config)
    result = await agent.ainvoke({"query": "Tên tôi và số điện thoại của tôi là gì?"}, config)
    assert "Nguyễn An" in result["response"]
    assert "0912345678" in result["response"]
    assert result["patient_profile"] == {"name": "Nguyễn An", "phone": "0912345678"}
    assert len(result["messages"]) <= 20
    other = await agent.ainvoke({"query": "Xin chào"}, {"configurable": {"thread_id": str(uuid.uuid4())}})
    assert "Nguyễn An" not in other["response"]
    assert not other.get("patient_phone")


@pytest.mark.asyncio
async def test_json_and_stream_forward_same_profile(client, monkeypatch):
    from src.medical_assistant.api import routes

    mocked = AsyncMock(return_value={"response": "Xin chào", "metadata": {}})
    monkeypatch.setattr(routes.agent, "ainvoke", mocked)
    payload = {
        "message": "hi",
        "session_id": "profile-request",
        "patient_profile": {"name": "Nguyễn An", "phone": "0912345678"},
    }
    for endpoint in ("/api/v1/chat", "/api/v1/chat/stream"):
        response = await client.post(endpoint, json=payload)
        assert response.status_code == 200
        args = mocked.call_args.args[0]
        assert args["patient_profile"] == payload["patient_profile"]
        assert args["patient_phone"] == "0912345678"


@pytest.mark.asyncio
async def test_booking_form_reuses_profile_fields():
    from src.medical_assistant.agent.nodes.example_node import respond_node

    result = await respond_node(
        {
            "query": "để lại thông tin",
            "workflow_status": "BOOKING_CONTACT_REQUIRED",
            "patient_name": "Nguyễn An",
            "patient_phone": "0912345678",
            "patient_profile": {"name": "Nguyễn An", "phone": "0912345678"},
            "metadata": {},
        }
    )
    intake = result["metadata"]["booking_intake"]
    assert intake["patient_name"] == "Nguyễn An"
    assert intake["patient_phone"] == "0912345678"
