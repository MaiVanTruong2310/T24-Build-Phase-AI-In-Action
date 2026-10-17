"""Coordinator regressions: mocked database, no external services."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from src.api.endpoints import workbench as routes
from src.db.dependencies import get_db_session
from src.schemas.workbench import CaseAction, VerifyInput
from src.services import workbench as svc


@pytest.mark.asyncio
async def test_queue_repeated_poll_is_read_only(monkeypatch):
    sync = AsyncMock()
    expire = AsyncMock()
    monkeypatch.setattr(svc, "sync_sources", sync)
    monkeypatch.setattr(svc, "expire_deposits", expire)
    count = SimpleNamespace(scalar_one=lambda: 0)
    rows = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))
    db = SimpleNamespace(execute=AsyncMock(side_effect=[count, rows] * 3))
    app = FastAPI()
    app.include_router(routes.router)
    identity = (SimpleNamespace(id=uuid4()), SimpleNamespace(facility_ids=[]))

    async def access():
        return identity

    async def database():
        yield db

    app.dependency_overrides[routes.access] = access
    app.dependency_overrides[get_db_session] = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for query in ("", "?q=test&mine=true", "?conversations=true&priority=0"):
            response = await client.get("/staff/workbench/cases" + query)
            assert response.status_code == 200
            assert response.json()["data"] == {"items": [], "total": 0}
    sync.assert_not_awaited()
    expire.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["cancelled", "completed", "confirmed", "planned", "deposit_late"])
async def test_verify_never_reopens_closed_or_ineligible_case(status):
    actor = SimpleNamespace(id=uuid4())
    case = SimpleNamespace(version=2, assigned_to=actor.id, status=status)
    db = SimpleNamespace(execute=AsyncMock())
    with pytest.raises(HTTPException) as error:
        await svc.verify_deposit(db, case, actor, VerifyInput(version=2, reference="bank-ref", evidence="bank-record"))
    assert error.value.status_code == 409
    assert case.status == status
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_emergency_is_rejected():
    actor = SimpleNamespace(id=uuid4())
    case = SimpleNamespace(version=1, assigned_to=actor.id, status="waiting_deposit", priority=0, ai_snapshot={})
    db = SimpleNamespace(execute=AsyncMock())
    with pytest.raises(HTTPException) as error:
        await svc.verify_deposit(db, case, actor, VerifyInput(version=1, reference="bank-ref", evidence="bank-record"))
    assert error.value.status_code == 409
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handover_requires_recipient_on_duty():
    actor = SimpleNamespace(id=uuid4())
    recipient = uuid4()
    case = SimpleNamespace(version=1, assigned_to=actor.id, status="contacting", facility_id=None)
    target = SimpleNamespace(enabled=True, on_duty=False, facility_ids=[])
    db = SimpleNamespace(get=AsyncMock(side_effect=[target, SimpleNamespace(status="active", role="staff")]))
    with pytest.raises(HTTPException) as error:
        await svc.action(
            db,
            case,
            actor,
            SimpleNamespace(on_duty=True),
            CaseAction(version=1, action="handover", assigned_to=recipient, note="Shift summary"),
        )
    assert error.value.status_code == 409
    assert case.assigned_to == actor.id
    assert case.version == 1


@pytest.mark.asyncio
async def test_claiming_emergency_acknowledges_and_assigns_in_one_action(monkeypatch):
    actor = SimpleNamespace(id=uuid4())
    member = SimpleNamespace(on_duty=False)
    case = SimpleNamespace(
        id=uuid4(),
        version=1,
        priority=0,
        assigned_to=None,
        status="waiting_patient",
        due_at=svc.now(),
        control="ai",
        updated_at=None,
    )
    db = SimpleNamespace(get=AsyncMock(return_value=member), add=lambda *_a: None)  # ensure_on_duty ghi nhật ký
    events = []
    monkeypatch.setattr(
        svc, "event", lambda _db, _case, _actor, action, note="", details=None: events.append((action, note))
    )

    await svc.action(db, case, actor, member, CaseAction(version=1, action="claim"))

    assert case.assigned_to == actor.id
    assert case.status == "emergency_active"
    assert case.due_at is None
    assert member.on_duty is True
    assert events[0][0] == "emergency_ack"
    assert events[0][1]


@pytest.mark.asyncio
async def test_emergency_transfer_requires_receiving_unit_or_person(monkeypatch):
    actor = SimpleNamespace(id=uuid4())
    case = SimpleNamespace(
        id=uuid4(),
        version=1,
        priority=0,
        assigned_to=actor.id,
        status="emergency_active",
        control="human",
        due_at=None,
        updated_at=None,
    )
    monkeypatch.setattr(svc, "event", lambda *_args, **_kwargs: None)

    with pytest.raises(HTTPException) as error:
        await svc.action(
            SimpleNamespace(),
            case,
            actor,
            SimpleNamespace(on_duty=True),
            CaseAction(version=1, action="emergency_transfer", note="Handoff time and receipt confirmed"),
        )

    assert error.value.status_code == 422
    assert case.status == "emergency_active"


@pytest.mark.asyncio
async def test_emergency_transfer_records_receiver_and_changes_status(monkeypatch):
    actor = SimpleNamespace(id=uuid4())
    case = SimpleNamespace(
        id=uuid4(),
        version=1,
        priority=0,
        assigned_to=actor.id,
        status="emergency_active",
        control="human",
        due_at=None,
        updated_at=None,
    )
    events = []
    monkeypatch.setattr(
        svc,
        "event",
        lambda _db, _case, _actor, action, note="", details=None: events.append((action, details)),
    )

    await svc.action(
        SimpleNamespace(),
        case,
        actor,
        SimpleNamespace(on_duty=True),
        CaseAction(
            version=1,
            action="emergency_transfer",
            note="Handoff time recorded; receiving unit confirmed receipt",
            reference="Emergency department",
        ),
    )

    assert case.status == "emergency_transferred"
    assert events[0][0] == "emergency_transfer"
    assert events[0][1]["reference"] == "Emergency department"


@pytest.mark.asyncio
async def test_handover_accepts_active_scoped_recipient(monkeypatch):
    actor = SimpleNamespace(id=uuid4())
    recipient = uuid4()
    facility = uuid4()
    case = SimpleNamespace(version=1, assigned_to=actor.id, status="contacting", facility_id=facility)
    target = SimpleNamespace(enabled=True, on_duty=True, facility_ids=[str(facility)])
    db = SimpleNamespace(get=AsyncMock(side_effect=[target, SimpleNamespace(status="active", role="staff")]))
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    await svc.action(
        db,
        case,
        actor,
        SimpleNamespace(on_duty=True),
        CaseAction(version=1, action="handover", assigned_to=recipient, note="Shift summary"),
    )
    assert case.assigned_to == recipient
    assert case.version == 2


@pytest.mark.asyncio
async def test_source_sync_skips_when_another_worker_holds_lock():
    db = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: False)))
    await svc.sync_sources(db)
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_doctor_conversations_filters_emergency_and_human_support_only():
    captured_statements = []

    async def fake_execute(statement, *args, **kwargs):
        captured_statements.append(statement)
        return SimpleNamespace(scalar_one=lambda: 0, scalars=lambda: SimpleNamespace(all=lambda: []))

    db = SimpleNamespace(execute=AsyncMock(side_effect=fake_execute))
    app = FastAPI()
    app.include_router(routes.router)
    identity = (SimpleNamespace(id=uuid4()), SimpleNamespace(facility_ids=[]))

    async def access():
        return identity

    async def database():
        yield db

    app.dependency_overrides[routes.access] = access
    app.dependency_overrides[get_db_session] = database

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Standard conversation view for doctor role
        res = await client.get("/staff/workbench/cases?conversations=true")
        assert res.status_code == 200

        # Verify the executed query compiles to SQL with source='chat' and emergency/support checks
        sql = str(captured_statements[0].compile(compile_kwargs={"literal_binds": True}))
        assert "coordination_cases.source = 'chat'" in sql
        assert "coordination_cases.priority = 0" in sql
        assert "coordination_cases.status != 'observing'" in sql
        assert "coordination_cases.control = 'human'" in sql

        # If a client attempts to query status=observing in conversations mode, it is blocked
        captured_statements.clear()
        res_obs = await client.get("/staff/workbench/cases?conversations=true&status=observing")
        assert res_obs.status_code == 200
        sql_obs = str(captured_statements[0].compile(compile_kwargs={"literal_binds": True}))
        assert "coordination_cases.status = '__none__'" in sql_obs


@pytest.mark.asyncio
async def test_capture_chat_escalates_on_human_support_request(monkeypatch):
    case = SimpleNamespace(
        id=uuid4(),
        version=1,
        status="observing",
        priority=3,
        checkpoint={},
        ai_snapshot={},
        due_at=None,
    )
    events = []
    monkeypatch.setattr(svc, "event", lambda db, c, actor, action, *a, **kwargs: events.append(action))
    monkeypatch.setattr(svc, "add_message", AsyncMock())
    monkeypatch.setattr(svc, "bump", lambda c: setattr(c, "version", c.version + 1))

    db = SimpleNamespace(get=AsyncMock(return_value=None))
    req = SimpleNamespace(request_id=uuid4())
    resp = {"response": "Support message"}

    # Patient requested human help via action
    state = {"workflow_status": "BOOKING_CONTACT_REQUIRED", "action": "request_human_help"}
    await svc.capture_chat(db, case, req, resp, state)

    assert case.status == "new"
    assert case.priority == 1
    assert "human_requested" in events


def test_guardrail_human_help_intents():
    from src.medical_assistant.domain.guardrail_service import get_guardrail_service

    svc_guard = get_guardrail_service()

    for phrase in [
        "Tôi muốn yêu cầu hỗ trợ",
        "Cho tôi gặp bác sĩ tư vấn",
        "Cần người hỗ trợ",
        "Tôi muốn gặp tư vấn viên",
        "Cho gặp bác sĩ",
    ]:
        intent = svc_guard.check_intent(phrase)
        assert intent is not None, f"Failed for phrase: {phrase}"
        assert intent.get("intent") == "BOOKING_CONTACT_REQUEST", f"Wrong intent for {phrase}: {intent}"


def _decline_case(**overrides):
    values = dict(
        id=uuid4(),
        version=1,
        assigned_to=None,
        status="new",
        priority=1,
        ai_snapshot={},
        plan={},
        session_id=None,
        control="ai",
        follow_up_at=None,
        booking_id=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"assigned_to": uuid4(), "status": "contacting"},  # ca của điều phối viên khác
        {"priority": 0},  # ca cấp cứu
        {"ai_snapshot": {"is_emergency": True}},
        {"status": "planned"},  # đã có phương án -> phải dùng Hủy ca
        {"status": "deposit_verified"},
        {"status": "cancelled"},
    ],
)
async def test_decline_rejects_other_owner_emergency_and_advanced_cases(overrides):
    actor = SimpleNamespace(id=uuid4())
    case = _decline_case(**overrides)
    before = (case.status, case.assigned_to, case.version)
    with pytest.raises(HTTPException) as error:
        await svc.action(SimpleNamespace(), case, actor, SimpleNamespace(), CaseAction(version=1, action="decline"))
    assert error.value.status_code == 409
    assert (case.status, case.assigned_to, case.version) == before


@pytest.mark.asyncio
async def test_decline_unassigned_new_case(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    actor = SimpleNamespace(id=uuid4())
    case = _decline_case()
    await svc.action(SimpleNamespace(), case, actor, SimpleNamespace(), CaseAction(version=1, action="decline"))
    assert case.status == "cancelled"
    assert case.control == "ai"


def test_bulk_decline_reason_matches_single_action():
    actor = SimpleNamespace(id=uuid4())
    assert svc.decline_error(_decline_case(), actor) is None
    assert svc.decline_error(_decline_case(assigned_to=actor.id, status="contacting"), actor) is None
    assert svc.decline_error(_decline_case(priority=0), actor)


@pytest.mark.asyncio
async def test_reopen_unowned_declined_case_assigns_actor(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    actor = SimpleNamespace(id=uuid4())
    case = _decline_case(status="cancelled")
    await svc.action(
        SimpleNamespace(),
        case,
        actor,
        SimpleNamespace(is_admin=False),
        CaseAction(version=1, action="reopen", note="Bệnh nhân gọi lại cần hỗ trợ"),
    )
    assert case.status == "contacting"
    assert case.assigned_to == actor.id


@pytest.mark.asyncio
async def test_reopen_case_owned_by_other_requires_admin(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    actor = SimpleNamespace(id=uuid4())
    case = _decline_case(status="cancelled", assigned_to=uuid4())
    payload = CaseAction(version=1, action="reopen", note="Mở lại")
    with pytest.raises(HTTPException) as error:
        await svc.action(SimpleNamespace(), case, actor, SimpleNamespace(is_admin=False), payload)
    assert error.value.status_code == 409
    await svc.action(SimpleNamespace(), case, actor, SimpleNamespace(is_admin=True), payload)
    assert case.assigned_to == actor.id


class _FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _realtime_case(**overrides):
    values = dict(
        id=uuid4(),
        version=1,
        status="observing",
        priority=3,
        control="ai",
        assigned_to=None,
        ai_snapshot={},
        checkpoint={},
        plan={},
        session_id="s1",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _patch_turn(monkeypatch, case, emergency):
    import sys

    from src.services import coordinator_chat

    monkeypatch.setattr(svc, "ensure_chat_case", AsyncMock(return_value=case))
    monkeypatch.setattr(svc, "add_message", AsyncMock(return_value=SimpleNamespace(id=uuid4())))
    monkeypatch.setattr(svc, "release_hold", AsyncMock())
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    triage = SimpleNamespace(is_emergency=emergency, patient_guidance="Gọi 115", ats_level=SimpleNamespace(value=1))
    fake = SimpleNamespace(get_triage_service=lambda: SimpleNamespace(evaluate_symptoms=lambda text: triage))
    monkeypatch.setitem(sys.modules, "src.medical_assistant.domain.triage_service", fake)
    case_update, message_event = AsyncMock(), AsyncMock()
    monkeypatch.setattr(coordinator_chat, "publish_workbench_case_update", case_update)
    monkeypatch.setattr(coordinator_chat, "publish_workbench_message", message_event)
    db = SimpleNamespace(begin=_FakeTransaction, get=AsyncMock(return_value=None))
    request = SimpleNamespace(request_id=uuid4(), message="tin nhắn", session_id="s1")
    return coordinator_chat, db, request, case_update, message_event


@pytest.mark.asyncio
async def test_before_turn_publishes_emergency_to_workbench(monkeypatch):
    case = _realtime_case()
    module, db, request, case_update, message_event = _patch_turn(monkeypatch, case, emergency=True)
    await module.before_turn(db, request, None, "guest")
    assert case.priority == 0
    case_update.assert_awaited_once_with(case)


@pytest.mark.asyncio
async def test_before_turn_publishes_patient_message_only_for_queued_cases(monkeypatch):
    observing = _realtime_case()
    module, db, request, case_update, message_event = _patch_turn(monkeypatch, observing, emergency=False)
    await module.before_turn(db, request, None, "guest")
    case_update.assert_not_awaited()
    message_event.assert_not_awaited()

    taken_over = _realtime_case(status="contacting", control="human")
    module, db, request, case_update, message_event = _patch_turn(monkeypatch, taken_over, emergency=False)
    await module.before_turn(db, request, None, "guest")
    message_event.assert_awaited_once()


@pytest.mark.asyncio
async def test_after_turn_publishes_when_ai_escalates_case(monkeypatch):
    from src.services import coordinator_chat

    case = _realtime_case()

    async def escalate(db, case_, request, response, state):
        case_.status, case_.priority = "new", 1

    monkeypatch.setattr(svc, "capture_chat", escalate)
    case_update = AsyncMock()
    monkeypatch.setattr(coordinator_chat, "publish_workbench_case_update", case_update)
    db = SimpleNamespace(
        begin=_FakeTransaction, execute=AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: case))
    )
    request = SimpleNamespace(request_id=uuid4(), session_id="s1")
    response = {"response": "AI trả lời"}
    state = {"workflow_status": "HUMAN_HELP_REQUESTED"}
    assert await coordinator_chat.after_turn(db, case.id, request, response, state) == response
    case_update.assert_awaited_once_with(case)


@pytest.mark.asyncio
async def test_after_turn_stays_quiet_for_plain_ai_chat(monkeypatch):
    from src.services import coordinator_chat

    case = _realtime_case()
    monkeypatch.setattr(svc, "capture_chat", AsyncMock())
    case_update = AsyncMock()
    monkeypatch.setattr(coordinator_chat, "publish_workbench_case_update", case_update)
    db = SimpleNamespace(
        begin=_FakeTransaction, execute=AsyncMock(return_value=SimpleNamespace(scalar_one=lambda: case))
    )
    request = SimpleNamespace(request_id=uuid4(), session_id="s1")
    await coordinator_chat.after_turn(db, case.id, request, {"response": "AI"}, {})
    case_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_patient_request_human_notifies_workbench(monkeypatch):
    case = _realtime_case()
    db = SimpleNamespace(
        begin=_FakeTransaction,
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: case)),
        get=AsyncMock(return_value=None),
    )
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    case_update = AsyncMock()
    monkeypatch.setattr(routes, "publish_workbench_case_update", case_update)
    app = FastAPI()
    app.include_router(routes.patient_router)

    async def identity():
        return "guest:test"

    async def database():
        yield db

    app.dependency_overrides[routes.patient_identity] = identity
    app.dependency_overrides[get_db_session] = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/coordination/live/s1/request-human")
        assert response.status_code == 200
        assert case.status == "new"
        case_update.assert_awaited_once_with(case)
        case_update.reset_mock()
        # Gọi lại khi ca đã trong hàng đợi: không phát trùng.
        assert (await client.post("/coordination/live/s1/request-human")).status_code == 200
        case_update.assert_not_awaited()


def _closed_case(**overrides):
    return _realtime_case(
        **{
            "status": "cancelled",
            "assigned_to": uuid4(),
            "follow_up_at": None,
            "due_at": None,
            "booking_id": None,
            **overrides,
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "state",
    [
        {"workflow_status": "HUMAN_HELP_REQUESTED"},
        {"action": "request_human_help"},
        {"is_emergency": True},
    ],
)
async def test_capture_chat_reopens_closed_case_when_patient_needs_help_again(monkeypatch, state):
    events = []
    monkeypatch.setattr(svc, "event", lambda db, c, actor, action, *a, **kw: events.append(action))
    monkeypatch.setattr(svc, "add_message", AsyncMock())
    case = _closed_case()
    db = SimpleNamespace(get=AsyncMock(return_value=None))
    await svc.capture_chat(db, case, SimpleNamespace(request_id=uuid4()), {"response": "AI"}, state)
    assert case.status == "new"
    assert case.assigned_to is None and case.control == "ai"
    assert case.priority == (0 if state.get("is_emergency") else 1)
    assert "takeover_reopened" in events


@pytest.mark.asyncio
async def test_capture_chat_reopen_keeps_confirmed_booking(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    monkeypatch.setattr(svc, "add_message", AsyncMock())
    case = _closed_case(status="completed", booking_id=uuid4())
    db = SimpleNamespace(get=AsyncMock(return_value=None))
    await svc.capture_chat(
        db, case, SimpleNamespace(request_id=uuid4()), {"response": "AI"}, {"workflow_status": "HUMAN_HELP_REQUESTED"}
    )
    assert case.status == "confirmed"
    assert case.assigned_to is None


@pytest.mark.asyncio
async def test_capture_chat_leaves_closed_case_closed_without_help_request(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    monkeypatch.setattr(svc, "add_message", AsyncMock())
    case = _closed_case()
    await svc.capture_chat(SimpleNamespace(), case, SimpleNamespace(request_id=uuid4()), {"response": "AI"}, {})
    assert case.status == "cancelled"


@pytest.mark.asyncio
async def test_patient_request_human_reopens_closed_case(monkeypatch):
    case = _closed_case()
    policy = SimpleNamespace(response_minutes=30, emergency_response_minutes=5)
    db = SimpleNamespace(
        begin=_FakeTransaction,
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: case)),
        get=AsyncMock(return_value=policy),
    )
    events = []
    monkeypatch.setattr(svc, "event", lambda db, c, actor, action, *a, **kw: events.append(action))
    case_update = AsyncMock()
    monkeypatch.setattr(routes, "publish_workbench_case_update", case_update)
    app = FastAPI()
    app.include_router(routes.patient_router)

    async def identity():
        return "guest:test"

    async def database():
        yield db

    app.dependency_overrides[routes.patient_identity] = identity
    app.dependency_overrides[get_db_session] = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/coordination/live/s1/request-human")
    assert response.status_code == 200
    assert case.status == "new" and case.assigned_to is None and case.priority == 1
    assert case.due_at is not None
    assert events == ["takeover_reopened"]
    case_update.assert_awaited_once_with(case)


def _consult_case(**overrides):
    values = dict(
        id=uuid4(),
        version=1,
        source="chat",
        status="contacting",
        priority=1,
        control="human",
        assigned_to=None,
        ai_snapshot={},
        plan={},
        booking_id=None,
        session_id="s1",
        follow_up_at=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _deposit_db(open_deposit=False):
    row = SimpleNamespace(first=lambda: ("deposit",) if open_deposit else None)
    return SimpleNamespace(execute=AsyncMock(return_value=row))


@pytest.mark.asyncio
async def test_complete_consult_only_chat_case(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    added = AsyncMock()
    monkeypatch.setattr(svc, "add_message", added)
    actor = SimpleNamespace(id=uuid4())
    case = _consult_case(assigned_to=actor.id)
    payload = CaseAction(version=1, action="complete", note="Đã tư vấn chọn chuyên khoa Tai Mũi Họng")
    await svc.action(_deposit_db(), case, actor, SimpleNamespace(), payload)
    assert case.status == "completed"
    assert case.control == "ai"
    assert case.ai_snapshot["handover_summary"] == payload.note
    added.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "open_deposit"),
    [
        ({"status": "planned"}, False),
        ({"plan": {"schedule_id": "x"}}, False),
        ({"booking_id": uuid4()}, False),
        ({"priority": 0}, False),
        ({"source": "consultation"}, False),
        ({}, True),
    ],
)
async def test_complete_rejects_case_with_plan_deposit_or_emergency(monkeypatch, overrides, open_deposit):
    monkeypatch.setattr(svc, "add_message", AsyncMock())
    actor = SimpleNamespace(id=uuid4())
    case = _consult_case(assigned_to=actor.id, **overrides)
    payload = CaseAction(version=1, action="complete", note="Kết thúc")
    with pytest.raises(HTTPException) as error:
        await svc.action(_deposit_db(open_deposit), case, actor, SimpleNamespace(), payload)
    assert error.value.status_code == 409
    assert case.status != "completed"


def _emergency_case(owner, **overrides):
    values = dict(
        id=uuid4(),
        version=1,
        source="chat",
        status="emergency_active",
        priority=0,
        control="human",
        assigned_to=owner,
        ai_snapshot={"is_emergency": True, "emergency_warning": "Gọi 115", "max_booking_days": 0, "ats_level": 2},
        checkpoint={"is_emergency": True, "emergency_warning": "Gọi 115", "max_booking_days": 0, "symptoms": ["ho"]},
        plan={},
        booking_id=None,
        session_id="s1",
        follow_up_at=None,
        due_at=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_emergency_dismiss_downgrades_and_records_reason(monkeypatch):
    events = []
    monkeypatch.setattr(svc, "event", lambda db, c, actor, action, *a, **kw: events.append(action))
    actor = SimpleNamespace(id=uuid4())
    case = _emergency_case(actor.id)
    payload = CaseAction(version=1, action="emergency_dismiss", note="Khám qua điện thoại: ho nhẹ, sinh hiệu ổn")
    await svc.action(SimpleNamespace(), case, actor, SimpleNamespace(), payload)
    assert case.priority == 1
    assert case.status == "contacting"
    assert case.ai_snapshot["is_emergency"] is False
    assert "max_booking_days" not in case.ai_snapshot and "emergency_warning" not in case.ai_snapshot
    assert case.ai_snapshot["emergency_dismissed"]["note"] == payload.note
    assert case.checkpoint["is_emergency"] is False and case.checkpoint["symptoms"] == ["ho"]
    assert events == ["emergency_dismiss"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "note", "status_code"),
    [
        ({"assigned_to": uuid4()}, "Lý do", 409),  # không phải người phụ trách
        ({"priority": 1, "ai_snapshot": {}}, "Lý do", 409),  # không có cảnh báo
        ({"status": "emergency_transferred"}, "Lý do", 409),  # đã bàn giao cấp cứu
        ({}, "", 422),  # thiếu lý do lâm sàng
    ],
)
async def test_emergency_dismiss_guards(overrides, note, status_code):
    actor = SimpleNamespace(id=uuid4())
    case = _emergency_case(actor.id, **overrides)
    with pytest.raises(HTTPException) as error:
        await svc.action(
            SimpleNamespace(),
            case,
            actor,
            SimpleNamespace(),
            CaseAction(version=1, action="emergency_dismiss", note=note),
        )
    assert error.value.status_code == status_code


@pytest.mark.asyncio
async def test_sticky_ai_emergency_flag_does_not_undo_dismissal(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    monkeypatch.setattr(svc, "add_message", AsyncMock())
    case = _emergency_case(
        uuid4(),
        status="contacting",
        priority=1,
        ai_snapshot={"is_emergency": False, "emergency_dismissed": {"note": "nhầm"}, "sos": {"maps_url": "x"}},
    )
    # Trạng thái AI còn dính cờ cấp cứu từ lượt trước.
    state = {"is_emergency": True, "max_booking_days": 0, "emergency_warning": "Gọi 115", "symptoms": ["ho"]}
    await svc.capture_chat(
        SimpleNamespace(get=AsyncMock(return_value=None)),
        case,
        SimpleNamespace(request_id=uuid4()),
        {"response": "AI"},
        state,
    )
    assert case.priority == 1
    assert case.ai_snapshot["is_emergency"] is False
    assert "max_booking_days" not in case.ai_snapshot
    assert case.ai_snapshot["sos"] == {"maps_url": "x"}
    assert case.checkpoint["is_emergency"] is False


@pytest.mark.asyncio
async def test_fresh_rule_emergency_cancels_dismissal(monkeypatch):
    case = _realtime_case(
        status="contacting", priority=1, ai_snapshot={"is_emergency": False, "emergency_dismissed": {"note": "nhầm"}}
    )
    module, db, request, case_update, message_event = _patch_turn(monkeypatch, case, emergency=True)
    await module.before_turn(db, request, None, "guest")
    assert case.priority == 0
    assert case.ai_snapshot["is_emergency"] is True
    assert "emergency_dismissed" not in case.ai_snapshot


@pytest.mark.asyncio
async def test_capture_chat_keeps_coordinator_handover_summary(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    monkeypatch.setattr(svc, "add_message", AsyncMock())
    case = _realtime_case(
        status="contacting",
        priority=1,
        ai_snapshot={"handover_summary": "Đã tư vấn khám Tai Mũi Họng", "takeover_summary": {"patient_name": "A"}},
    )
    for _ in range(2):  # nhiều lượt chat liên tiếp
        await svc.capture_chat(
            SimpleNamespace(get=AsyncMock(return_value=None)),
            case,
            SimpleNamespace(request_id=uuid4()),
            {"response": "AI"},
            {"symptoms": ["đau họng"]},
        )
    assert case.ai_snapshot["handover_summary"] == "Đã tư vấn khám Tai Mũi Họng"
    assert case.ai_snapshot["takeover_summary"] == {"patient_name": "A"}
    assert case.ai_snapshot["symptoms"] == ["đau họng"]


# ---- L8: gửi lại form đặt khám không lùi trạng thái ----


def _intake_env(monkeypatch, case):
    import sys
    from datetime import date, timedelta

    import src.services.patient_profiles as profiles

    fake = SimpleNamespace(PHONE_PATTERN=__import__("re").compile(r"0\d{9}"), _is_minor=lambda dob, today: False)
    monkeypatch.setitem(sys.modules, "src.medical_assistant.domain.booking_request_service", fake)
    monkeypatch.setattr(profiles, "resolve_booking_payload", AsyncMock(return_value=(None, None)))
    events = []
    monkeypatch.setattr(svc, "event", lambda db, c, actor, action, *a, **kw: events.append(action))
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: case)),
        get=AsyncMock(return_value=SimpleNamespace(response_minutes=30, emergency_response_minutes=5)),
    )
    request = SimpleNamespace(
        session_id="s1",
        patient_name="Nguyễn Văn A",
        patient_phone="0912345678",
        patient_email=None,
        date_of_birth=date(1990, 1, 1),
        gender="male",
        guardian_name=None,
        guardian_phone=None,
        preferred_date=date.today() + timedelta(days=3),
        preferred_period="morning",
        facility_preference=None,
        contact_time_preference=None,
        patient_notes="Cập nhật số điện thoại",
    )
    return db, request, events


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["planned", "waiting_deposit", "deposit_verified", "deposit_expired"])
async def test_resubmitted_intake_keeps_plan_and_deposit_status(monkeypatch, status):
    case = _realtime_case(status=status, priority=3, assigned_to=uuid4(), patient={}, patient_id=None, due_at=None)
    db, request, events = _intake_env(monkeypatch, case)
    await svc.intake(db, request, None, "guest", {})
    assert case.status == status
    assert case.patient["phone"] == "0912345678"
    assert events == ["intake_updated"]


@pytest.mark.asyncio
async def test_first_intake_queues_case_with_due_time(monkeypatch):
    case = _realtime_case(status="observing", priority=3, patient={}, patient_id=None, due_at=None)
    db, request, events = _intake_env(monkeypatch, case)
    await svc.intake(db, request, None, "guest", {})
    assert case.status == "new"
    assert case.due_at is not None
    assert events == ["intake_submitted"]


# ---- L9/L16: nhận ca ----


@pytest.mark.asyncio
async def test_claim_rejects_case_patient_never_escalated():
    actor = SimpleNamespace(id=uuid4())
    case = _realtime_case(status="observing", priority=3)
    with pytest.raises(HTTPException) as error:
        await svc.action(SimpleNamespace(), case, actor, SimpleNamespace(), CaseAction(version=1, action="claim"))
    assert error.value.status_code == 409
    assert case.assigned_to is None and case.control == "ai"


@pytest.mark.asyncio
async def test_claim_auto_starts_duty_with_audit(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    actor = SimpleNamespace(id=uuid4())
    db_member = SimpleNamespace(on_duty=False)
    added = []
    db = SimpleNamespace(get=AsyncMock(return_value=db_member), add=added.append)
    member = SimpleNamespace(on_duty=False)
    case = _realtime_case(status="new", priority=1, due_at=None)
    await svc.action(db, case, actor, member, CaseAction(version=1, action="claim"))
    assert case.assigned_to == actor.id and case.status == "contacting" and case.control == "human"
    assert db_member.on_duty and member.on_duty
    assert [a.action for a in added] == ["duty_started"]


def test_claim_error_allows_emergency_without_patient_request():
    assert svc.claim_error(_realtime_case(status="observing", priority=0), uuid4()) is None


# ---- L10: bảo trì định kỳ ----


@pytest.mark.asyncio
async def test_run_maintenance_expires_syncs_and_notifies(monkeypatch):
    import src.services.chat_takeover as takeover

    case = _realtime_case(status="deposit_expired")
    monkeypatch.setattr(svc, "expire_deposits", AsyncMock(return_value=[case]))
    sync = AsyncMock()
    monkeypatch.setattr(svc, "sync_sources", sync)
    publish = AsyncMock()
    monkeypatch.setattr(takeover, "publish_workbench_case_update", publish)

    class Session(_FakeTransaction):
        def begin(self):
            return _FakeTransaction()

    assert await svc.run_maintenance(Session) == 1
    sync.assert_awaited_once()
    publish.assert_awaited_once_with(case)


@pytest.mark.asyncio
async def test_expire_deposits_returns_expired_cases(monkeypatch):
    monkeypatch.setattr(svc, "event", lambda *args, **kwargs: None)
    monkeypatch.setattr(svc, "release_hold", AsyncMock())
    case = _realtime_case(status="waiting_deposit")
    deposit = SimpleNamespace(status="requested")
    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [case])),
                SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: deposit)),
            ]
        )
    )
    assert await svc.expire_deposits(db) == [case]
    assert case.status == "deposit_expired" and deposit.status == "expired"


# ---- L11: bộ lọc chẩn đoán/kê đơn ----


@pytest.mark.parametrize(
    "text",
    [
        "Bạn đã được chẩn đoán tiểu đường chưa?",
        "Bạn đang uống thuốc 500mg nào?",
        "Anh có bị viêm họng không?",
        "Chị nên khám chuyên khoa Tai Mũi Họng trong 3 ngày tới.",
    ],
)
def test_guidance_allows_history_questions(text):
    from src.services.coordinator_chat import validate_guidance

    validate_guidance(text)


@pytest.mark.parametrize(
    "text",
    [
        "Bạn bị viêm phổi rồi.",
        "Uống paracetamol 500mg mỗi 6 giờ.",
        "Bạn bị viêm phổi, uống 500mg nhé ạ.",
        "Bạn đã được chẩn đoán tiểu đường chưa? Uống metformin 500 mg sáng tối.",
    ],
)
def test_guidance_still_blocks_diagnosis_and_dosage(text):
    from src.services.coordinator_chat import validate_guidance

    with pytest.raises(HTTPException) as error:
        validate_guidance(text)
    assert error.value.status_code == 422


# ---- L12: tin nhắn khi đang tiếp quản hiện trong khung điều phối ----


@pytest.mark.asyncio
async def test_patient_chat_during_takeover_goes_to_coordinator_channel(monkeypatch):
    case = _realtime_case(status="contacting", control="human", priority=1)
    module, db, request, case_update, message_event = _patch_turn(monkeypatch, case, emergency=False)
    await module.before_turn(db, request, None, "guest")
    assert svc.add_message.await_args.kwargs["channel"] == "coordinator_chat"

    case = _realtime_case()
    module, db, request, case_update, message_event = _patch_turn(monkeypatch, case, emergency=False)
    await module.before_turn(db, request, None, "guest")
    assert svc.add_message.await_args.kwargs["channel"] == "ai_chat"


# ---- L13: hạn phản hồi ----


@pytest.mark.asyncio
async def test_reset_due_only_tightens_and_skips_assigned_cases():
    from datetime import UTC, datetime, timedelta

    policy = SimpleNamespace(response_minutes=60, emergency_response_minutes=5)
    db = SimpleNamespace(get=AsyncMock(return_value=policy))
    case = _realtime_case(priority=1, due_at=None)
    await svc.reset_due(db, case)
    normal_due = case.due_at
    assert normal_due is not None
    case.priority = 0
    await svc.reset_due(db, case)
    assert case.due_at < normal_due  # cấp cứu rút ngắn hạn
    tight = case.due_at
    case.priority = 1
    await svc.reset_due(db, case)
    assert case.due_at == tight  # không kéo dài hạn đang có
    owned = _realtime_case(priority=0, assigned_to=uuid4(), due_at=None)
    await svc.reset_due(db, owned)
    assert owned.due_at is None
    assert tight - datetime.now(UTC) < timedelta(minutes=6)


# ---- L14: bệnh nhân chỉ thấy trường cần thiết ----


def test_patient_snapshot_hides_internal_fields():
    snapshot = {
        "symptoms": ["ho"],
        "suggested_department_name": "Hô hấp",
        "is_emergency": False,
        "critic_critique": "nội bộ",
        "conflict_reason": "nội bộ",
        "routing_candidates": [],
        "handover_summary": "ghi chú bác sĩ",
        "emergency_dismissed": {"note": "nội bộ"},
    }
    assert routes.patient_snapshot(snapshot) == {
        "symptoms": ["ho"],
        "suggested_department_name": "Hô hấp",
        "is_emergency": False,
    }
    assert routes.patient_snapshot(None) == {}


# ---- L15: không bàn giao ca đã đóng ----


@pytest.mark.asyncio
async def test_handover_rejected_on_closed_case():
    actor = SimpleNamespace(id=uuid4())
    case = _realtime_case(status="completed", assigned_to=actor.id)
    with pytest.raises(HTTPException) as error:
        await svc.action(
            SimpleNamespace(),
            case,
            actor,
            SimpleNamespace(),
            CaseAction(version=1, action="handover", assigned_to=uuid4(), note="Bàn giao"),
        )
    assert error.value.status_code == 409
    assert case.assigned_to == actor.id


# ---- L18: không còn chuỗi lỗi vỡ mã hóa ----


def test_workbench_messages_have_no_mojibake():
    import inspect

    source = inspect.getsource(svc)
    for broken in ("Ã", "Æ°", "á»", "Ä‘"):
        assert broken not in source
