"""Isolated persistence checks for confirmed staff booking reviews."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.core.exceptions import AuthorizationError, ConflictError
from src.models.conversation import Conversation, StaffAgentContext
from src.models.user import User
from src.schemas.staff_agent import StaffAgentActionRequest
from src.services import staff_agent as staff_agent_module
from src.services.booking import BookingService
from src.services.staff_agent import StaffAgentService


@pytest_asyncio.fixture
async def staff_agent_db():
    pytest.importorskip("aiosqlite")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.execute(
            text("""CREATE TABLE conversations (
            id CHAR(32) PRIMARY KEY, category VARCHAR(32) NOT NULL, mode VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL, patient_id CHAR(32), created_by_type VARCHAR(32) NOT NULL,
            created_by_id CHAR(32), created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
            closed_at DATETIME)""")
        )
        await connection.execute(
            text("""CREATE TABLE staff_agent_context (
            conversation_id CHAR(32) PRIMARY KEY, staff_id CHAR(32) NOT NULL UNIQUE,
            context_patient_id CHAR(32), context_booking_id CHAR(32), context_department_id CHAR(32),
            task_type VARCHAR(64), context_data JSON, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)""")
        )
        await connection.execute(
            text("""CREATE TABLE messages (
            id CHAR(32) PRIMARY KEY, conversation_id CHAR(32) NOT NULL, sender_type VARCHAR(32) NOT NULL,
            sender_id CHAR(32), message_type VARCHAR(32) NOT NULL, content TEXT, metadata JSON, created_at DATETIME NOT NULL)""")
        )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


async def seed_proposal(factory, *, expires_at: datetime | None = None, decision: str = "confirmed"):
    staff_id, conversation_id, action_id, booking_id = (uuid4() for _ in range(4))
    now = datetime.now(UTC)
    proposal = {
        "id": str(action_id),
        "booking_id": str(booking_id),
        "decision": decision,
        "reason": None,
        "expires_at": (expires_at or now + timedelta(minutes=5)).isoformat(),
        "state": "pending",
    }
    async with factory() as session, session.begin():
        session.add(
            Conversation(
                id=conversation_id,
                category="STAFF_ASSISTANT",
                mode="AI",
                status="ACTIVE",
                created_by_type="STAFF",
                created_by_id=staff_id,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            StaffAgentContext(
                conversation_id=conversation_id,
                staff_id=staff_id,
                context_data={"pending_action": proposal},
                created_at=now,
                updated_at=now,
            )
        )
    return staff_id, conversation_id, action_id, booking_id


def action_request(conversation_id, action_id):
    return StaffAgentActionRequest(conversation_id=conversation_id, pending_action_id=action_id)


@pytest.mark.asyncio
async def test_confirm_approval_persists_consumption_and_replay_cannot_call_service_again(staff_agent_db, monkeypatch):
    staff_id, conversation_id, action_id, booking_id = await seed_proposal(staff_agent_db)
    review = AsyncMock()

    class ConfirmingBookingService:
        def __init__(self, _session):
            self.review = review

    monkeypatch.setattr(staff_agent_module, "BookingService", ConfirmingBookingService)
    async with staff_agent_db() as session:
        result = await StaffAgentService(session).confirm_action(
            User(id=staff_id, role="staff"), action_request(conversation_id, action_id)
        )

    review.assert_awaited_once()
    assert review.await_args.args[:2] == (booking_id, staff_id)
    assert review.await_args.args[2].status == "confirmed"
    assert result.assistant_text == "Đã xác nhận lịch khám."
    async with staff_agent_db() as session:
        context = await session.get(StaffAgentContext, conversation_id)
        messages = (await session.execute(text("SELECT content FROM messages"))).all()
        assert context.context_data == {}
        assert [row.content for row in messages] == ["Đã xác nhận lịch khám."]
        with pytest.raises(ConflictError, match="no longer available"):
            await StaffAgentService(session).confirm_action(
                User(id=staff_id, role="staff"), action_request(conversation_id, action_id)
            )
    review.assert_awaited_once()


@pytest.mark.asyncio
async def test_expired_confirmation_is_consumed_and_never_calls_booking_service(staff_agent_db, monkeypatch):
    staff_id, conversation_id, action_id, _ = await seed_proposal(
        staff_agent_db, expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )
    review = AsyncMock()
    monkeypatch.setattr(staff_agent_module, "BookingService", lambda _session: SimpleNamespace(review=review))
    request = action_request(conversation_id, action_id)

    async with staff_agent_db() as session:
        with pytest.raises(ConflictError, match="has expired"):
            await StaffAgentService(session).confirm_action(User(id=staff_id, role="staff"), request)
    async with staff_agent_db() as session:
        context = await session.get(StaffAgentContext, conversation_id)
        assert context.context_data == {}
    review.assert_not_awaited()


@pytest.mark.asyncio
async def test_non_staff_cannot_confirm_or_consume_persisted_proposal(staff_agent_db, monkeypatch):
    staff_id, conversation_id, action_id, _ = await seed_proposal(staff_agent_db)
    review = AsyncMock()
    monkeypatch.setattr(staff_agent_module, "BookingService", lambda _session: SimpleNamespace(review=review))

    async with staff_agent_db() as session:
        with pytest.raises(AuthorizationError):
            await StaffAgentService(session).confirm_action(
                User(id=staff_id, role="patient"), action_request(conversation_id, action_id)
            )
    async with staff_agent_db() as session:
        context = await session.get(StaffAgentContext, conversation_id)
        assert context.context_data["pending_action"]["state"] == "pending"
    review.assert_not_awaited()


@pytest.mark.asyncio
async def test_booking_service_already_reviewed_conflict_is_not_reported_as_success(staff_agent_db, monkeypatch):
    staff_id, conversation_id, action_id, booking_id = await seed_proposal(staff_agent_db)
    get_booking = AsyncMock(return_value=SimpleNamespace(id=booking_id, status="confirmed"))

    def already_reviewed_service(session):
        service = BookingService(session)
        service.bookings.get_for_staff = get_booking
        return service

    monkeypatch.setattr(staff_agent_module, "BookingService", already_reviewed_service)
    async with staff_agent_db() as session:
        with pytest.raises(ConflictError, match="Only pending bookings can be reviewed"):
            await StaffAgentService(session).confirm_action(
                User(id=staff_id, role="staff"), action_request(conversation_id, action_id)
            )

    get_booking.assert_awaited_once_with(booking_id, for_update=True)
    async with staff_agent_db() as session:
        context = await session.get(StaffAgentContext, conversation_id)
        messages = (await session.execute(text("SELECT content FROM messages"))).all()
        assert context.context_data == {}
        assert messages == []
