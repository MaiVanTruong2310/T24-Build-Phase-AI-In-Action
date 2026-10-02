from uuid import uuid4

import pytest

from src.models.chat_takeover import ChatTakeoverCase
from src.realtime.chat_takeover import ChatTakeoverConnectionManager
from src.services.chat_takeover import case_payload, priority_for_result


def test_priority_is_derived_from_safety_result():
    assert priority_for_result({"is_emergency": True}) == "critical"
    assert priority_for_result({"ats_level": 2}) == "critical"
    assert priority_for_result({"ats_level": 3}) == "high"
    assert priority_for_result({"ats_level": 5}) == "normal"


def test_case_payload_does_not_expose_raw_message_fields():
    case = ChatTakeoverCase(
        id=uuid4(),
        patient_user_id=uuid4(),
        session_id="web-session",
        status="queued",
        priority="normal",
        workflow_status="HUMAN_HELP_REQUESTED",
        summary={"patient_message": "need support"},
    )
    payload = case_payload(case)
    assert payload["session_id"] == "web-session"
    assert payload["summary"]["patient_message"] == "need support"
    assert "password" not in payload


class FakeWebSocket:
    def __init__(self):
        self.accepted = False
        self.events = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        self.events.append(payload)


@pytest.mark.asyncio
async def test_takeover_manager_fans_out_to_session_and_staff_rooms():
    manager = ChatTakeoverConnectionManager()
    session_socket = FakeWebSocket()
    staff_socket = FakeWebSocket()

    await manager.connect_session("session-1", session_socket)
    await manager.connect_staff(staff_socket)
    await manager.publish_session("session-1", {"type": "takeover.message_created"})
    await manager.publish_staff({"type": "takeover.case_updated"})

    assert session_socket.accepted and staff_socket.accepted
    assert session_socket.events == [{"type": "takeover.message_created"}]
    assert staff_socket.events == [{"type": "takeover.case_updated"}]
