"""Staff assistant endpoint authorization and response contract."""

from uuid import uuid4

import pytest

from src.api.dependencies import get_current_user
from src.api.endpoints.staff_agent import get_staff_agent_service
from src.main import app
from src.models.user import User
from src.schemas.staff_agent import StaffAgentActionResponse, StaffAgentChatResponse


@pytest.mark.asyncio
async def test_staff_agent_chat_returns_read_only_contract(client):
    staff = User(id=uuid4(), role="staff", status="active")

    class Service:
        async def chat(self, actor, request):
            assert actor.id == staff.id
            assert request.message == "Tra cứu lịch khám"
            return StaffAgentChatResponse(
                conversation_id=uuid4(),
                assistant_text="Đã tra cứu lịch khám.",
                tool_states=[{"tool": "search_staff_bookings", "status": "success"}],
            )

    old_user = app.dependency_overrides.get(get_current_user)
    old_service = app.dependency_overrides.get(get_staff_agent_service)
    app.dependency_overrides[get_current_user] = lambda: staff
    app.dependency_overrides[get_staff_agent_service] = lambda: Service()
    try:
        response = await client.post(
            "/api/v1/staff/assistant/chat",
            json={"message": "  Tra cứu lịch khám  "},
        )
    finally:
        if old_user is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = old_user
        if old_service is None:
            app.dependency_overrides.pop(get_staff_agent_service, None)
        else:
            app.dependency_overrides[get_staff_agent_service] = old_service

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["assistant_text"] == "Đã tra cứu lịch khám."
    assert data["tool_states"][0]["tool"] == "search_staff_bookings"
    assert "citations" not in data and "sources" not in data and data["pending_action"] is None


@pytest.mark.asyncio
async def test_patient_is_forbidden_from_staff_agent_chat(client):
    patient = User(id=uuid4(), role="patient", status="active")
    old_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: patient
    try:
        response = await client.post("/api/v1/staff/assistant/chat", json={"message": "Tra cứu lịch khám"})
        payload = {"conversation_id": str(uuid4()), "pending_action_id": str(uuid4())}
        confirm = await client.post("/api/v1/staff/assistant/chat/confirm", json=payload)
        cancel = await client.post("/api/v1/staff/assistant/chat/cancel", json=payload)
    finally:
        if old_user is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = old_user

    assert response.status_code == confirm.status_code == cancel.status_code == 403
    assert response.json()["error_code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_staff_action_endpoints_accept_only_server_bound_identifiers(client):
    staff = User(id=uuid4(), role="staff", status="active")
    conversation_id, action_id = uuid4(), uuid4()

    class Service:
        async def confirm_action(self, actor, request):
            assert actor.id == staff.id
            assert request.conversation_id == conversation_id
            assert request.pending_action_id == action_id
            return StaffAgentActionResponse(conversation_id=conversation_id, assistant_text="Đã xác nhận lịch khám.")

        async def cancel_action(self, actor, request):
            assert actor.id == staff.id
            assert request.conversation_id == conversation_id
            assert request.pending_action_id == action_id
            return StaffAgentActionResponse(conversation_id=conversation_id, assistant_text="Đã hủy đề xuất.")

    old_user = app.dependency_overrides.get(get_current_user)
    old_service = app.dependency_overrides.get(get_staff_agent_service)
    app.dependency_overrides[get_current_user] = lambda: staff
    app.dependency_overrides[get_staff_agent_service] = lambda: Service()
    try:
        payload = {"conversation_id": str(conversation_id), "pending_action_id": str(action_id)}
        confirm = await client.post("/api/v1/staff/assistant/chat/confirm", json=payload)
        cancel = await client.post("/api/v1/staff/assistant/chat/cancel", json=payload)
        invalid = await client.post("/api/v1/staff/assistant/chat/confirm", json={**payload, "decision": "confirmed"})
    finally:
        if old_user is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = old_user
        if old_service is None:
            app.dependency_overrides.pop(get_staff_agent_service, None)
        else:
            app.dependency_overrides[get_staff_agent_service] = old_service

    assert confirm.status_code == cancel.status_code == 200
    assert invalid.status_code == 400


@pytest.mark.asyncio
async def test_health_docs_and_openapi_expose_staff_chat(client):
    health = await client.get("/health")
    docs = await client.get("/docs")
    openapi = await client.get("/openapi.json")

    assert health.status_code == 200
    assert docs.status_code == 200
    assert openapi.status_code == 200
    assert "/api/v1/staff/assistant/chat" in openapi.json()["paths"]
    assert "/api/v1/staff/assistant/chat/stream" in openapi.json()["paths"]
    assert "/api/v1/staff/assistant/chat/confirm" in openapi.json()["paths"]
    assert "/api/v1/staff/assistant/chat/cancel" in openapi.json()["paths"]


@pytest.mark.asyncio
async def test_staff_agent_chat_stream_endpoint(client):
    staff = User(id=uuid4(), role="staff", status="active")

    class Service:
        async def chat_stream(self, actor, request):
            assert actor.id == staff.id
            yield 'event: status\ndata: {"status": "processing"}\n\n'
            yield 'event: token\ndata: {"token": "Xin chào"}\n\n'
            yield 'event: done\ndata: {"conversation_id": "123", "assistant_text": "Xin chào"}\n\n'

    old_user = app.dependency_overrides.get(get_current_user)
    old_service = app.dependency_overrides.get(get_staff_agent_service)
    app.dependency_overrides[get_current_user] = lambda: staff
    app.dependency_overrides[get_staff_agent_service] = lambda: Service()
    try:
        response = await client.post(
            "/api/v1/staff/assistant/chat/stream",
            json={"message": "Xin chào"},
        )
    finally:
        if old_user is None:
            app.dependency_overrides.pop(get_current_user, None)
        else:
            app.dependency_overrides[get_current_user] = old_user
        if old_service is None:
            app.dependency_overrides.pop(get_staff_agent_service, None)
        else:
            app.dependency_overrides[get_staff_agent_service] = old_service

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    assert "event: token" in response.text
