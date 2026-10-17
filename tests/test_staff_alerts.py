from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.endpoints import workbench as routes
from src.db.dependencies import get_db_session
from src.services import coordinator_chat, staff_alerts, workbench


@pytest.mark.asyncio
async def test_alert_payload_is_allowlisted_and_staff_room_only(monkeypatch):
    event = SimpleNamespace(
        id=uuid4(), action="emergency_detected", note="raw patient message", details={}, created_at=datetime.now(UTC)
    )
    case = SimpleNamespace(
        id=uuid4(),
        legacy_takeover_case_id=None,
        session_id="patient-session-secret",
        patient={"name": "Synthetic Patient"},
        ai_snapshot={"emergency_warning": "Saved emergency guidance"},
    )
    publish_staff = AsyncMock()
    publish_session = AsyncMock()
    monkeypatch.setattr(staff_alerts.chat_takeover_manager, "publish_staff", publish_staff)
    monkeypatch.setattr(staff_alerts.chat_takeover_manager, "publish_session", publish_session)

    await staff_alerts.publish_staff_assistant_alert(event, case)

    payload = publish_staff.await_args.args[0]
    assert payload["type"] == "staff_assistant.alert"
    assert payload["alert"]["event_id"] == str(event.id)
    assert payload["alert"]["reason"] == "Saved emergency guidance"
    assert set(payload["alert"]) == {"event_id", "case_id", "event_type", "reason", "created_at"}
    assert "raw patient message" not in str(payload)
    assert "Synthetic Patient" not in str(payload)
    assert "patient-session-secret" not in str(payload)
    publish_session.assert_not_awaited()


@pytest.mark.parametrize(
    ("action", "details", "workflow", "reason"),
    [
        (
            "human_requested",
            {"workflow_status": "SAFETY_REVIEW"},
            "HUMAN_HELP_REQUESTED",
            "Ca cần nhân viên xem xét an toàn.",
        ),
        ("routing_conflict", {}, "", "Đã lưu xung đột điều phối cần nhân viên kiểm tra."),
        ("emergency_detected", {"alert_reason": "Persisted reason"}, "", "Persisted reason"),
    ],
)
def test_alert_reason_uses_persisted_allowlisted_details(action, details, workflow, reason):
    event = SimpleNamespace(id=uuid4(), action=action, details=details, created_at=datetime.now(UTC))
    case = SimpleNamespace(
        id=uuid4(),
        legacy_takeover_case_id=None,
        ai_snapshot={"workflow_status": workflow, "emergency_warning": "Newer snapshot"},
    )

    assert staff_alerts.alert_payload(event, case)["reason"] == reason


@pytest.mark.asyncio
async def test_capture_chat_alerts_only_on_human_support_or_emergency_transition(monkeypatch):
    case = SimpleNamespace(
        id=uuid4(),
        version=1,
        status="observing",
        priority=3,
        checkpoint={},
        ai_snapshot={},
        due_at=None,
    )
    recorded = []

    def record_event(_db, _case, _actor, action, *_args, **_kwargs):
        event = SimpleNamespace(action=action)
        recorded.append(event)
        return event

    monkeypatch.setattr(workbench, "event", record_event)
    monkeypatch.setattr(workbench, "add_message", AsyncMock())
    monkeypatch.setattr(workbench, "bump", lambda target: setattr(target, "version", target.version + 1))
    db = SimpleNamespace(get=AsyncMock(return_value=None))
    request = SimpleNamespace(request_id=uuid4())
    response = {"response": "Synthetic response"}

    first = await workbench.capture_chat(
        db,
        case,
        request,
        response,
        {"workflow_status": "BOOKING_CONTACT_REQUIRED", "action": "request_human_help"},
    )
    repeated = await workbench.capture_chat(
        db,
        case,
        request,
        response,
        {"workflow_status": "BOOKING_CONTACT_REQUIRED", "action": "request_human_help"},
    )
    assert [event.action for event in first] == ["human_requested"]
    assert repeated == []

    case.status = "observing"
    case.ai_snapshot = {}
    emergency = await workbench.capture_chat(db, case, request, response, {"is_emergency": True})
    again = await workbench.capture_chat(db, case, request, response, {"is_emergency": True})
    assert [event.action for event in emergency] == ["emergency_detected"]
    assert again == []
    assert [event.action for event in recorded] == ["human_requested", "emergency_detected"]


@pytest.mark.asyncio
async def test_after_turn_publishes_only_after_persisting_transition(monkeypatch):
    event = SimpleNamespace(action="human_requested")
    case = SimpleNamespace(id=uuid4(), control="ai", status="observing", priority=3, plan={})
    state = {"is_emergency": False}

    class Transaction:
        def __init__(self, db):
            self.db = db

        async def __aenter__(self):
            self.db.in_transaction = True

        async def __aexit__(self, *_args):
            self.db.in_transaction = False

    db = SimpleNamespace(in_transaction=False, begin=None)
    db.begin = lambda: Transaction(db)
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: case))
    monkeypatch.setattr(workbench, "capture_chat", AsyncMock(return_value=[event]))
    published = []

    async def publish(alert_event, alert_case):
        assert not db.in_transaction
        published.append((alert_event, alert_case))

    monkeypatch.setattr(staff_alerts, "publish_staff_assistant_alert", publish)
    request = SimpleNamespace(session_id="synthetic-session")
    response = {"response": "Synthetic response"}

    result = await coordinator_chat.after_turn(db, case.id, request, response, state)

    assert result is response
    assert published == [(event, case)]


@pytest.mark.asyncio
async def test_recovery_endpoint_scopes_to_authorized_member_and_returns_alerts():
    event = SimpleNamespace(
        id=uuid4(), action="human_requested", note="private note", details={}, created_at=datetime.now(UTC)
    )
    case = SimpleNamespace(
        id=uuid4(),
        legacy_takeover_case_id=None,
        source="chat",
        assigned_to=None,
        status="new",
        facility_id=uuid4(),
        ai_snapshot={"workflow_status": "SAFETY_REVIEW"},
    )
    statement = []

    async def execute(query):
        statement.append(query)
        return SimpleNamespace(all=lambda: [(event, case)])

    db = SimpleNamespace(execute=AsyncMock(side_effect=execute))
    member = SimpleNamespace(facility_ids=[str(case.facility_id)])
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")

    async def access():
        return SimpleNamespace(id=uuid4()), member

    async def database():
        yield db

    app.dependency_overrides[routes.access] = access
    app.dependency_overrides[get_db_session] = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/staff/workbench/assistant-alerts?limit=20")

    assert response.status_code == 200
    alert = response.json()["data"][0]
    assert alert["event_id"] == str(event.id)
    assert alert["reason"] == "Ca cần nhân viên xem xét an toàn."
    sql = str(statement[0].compile(compile_kwargs={"literal_binds": True}))
    assert "coordination_cases.source = 'chat'" in sql
    assert "coordination_cases.assigned_to IS NULL" in sql
    assert "coordination_cases.status NOT IN" in sql
    assert case.facility_id.hex in sql
    assert "coordination_events.action IN" in sql
    assert "ORDER BY coordination_events.created_at, coordination_events.id" in sql


@pytest.mark.asyncio
async def test_publish_failure_is_swallowed_for_committed_alert(monkeypatch):
    monkeypatch.setattr(staff_alerts.chat_takeover_manager, "publish_staff", AsyncMock(side_effect=OSError("offline")))
    event = SimpleNamespace(id=uuid4(), action="human_requested", created_at=datetime.now(UTC))
    case = SimpleNamespace(
        id=uuid4(), legacy_takeover_case_id=None, ai_snapshot={"workflow_status": "HUMAN_HELP_REQUESTED"}
    )

    await staff_alerts.publish_staff_assistant_alert(event, case)
