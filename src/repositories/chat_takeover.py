"""Database operations for human-in-the-loop chat takeover."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from src.models.chat_takeover import ChatTakeoverAuditEvent, ChatTakeoverCase, ChatTakeoverMessage


class ChatTakeoverRepository:
    """Keep takeover persistence queries separate from workflow decisions."""

    def __init__(self, session):
        self.session = session

    async def get_case(self, case_id: UUID, *, for_update: bool = False) -> ChatTakeoverCase | None:
        statement = select(ChatTakeoverCase).where(ChatTakeoverCase.id == case_id)
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_by_patient_session(
        self, patient_user_id: UUID, session_id: str, *, for_update: bool = False
    ) -> ChatTakeoverCase | None:
        statement = select(ChatTakeoverCase).where(
            ChatTakeoverCase.patient_user_id == patient_user_id,
            ChatTakeoverCase.session_id == session_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_cases(self, statuses: tuple[str, ...], offset: int, limit: int) -> list[ChatTakeoverCase]:
        statement = (
            select(ChatTakeoverCase)
            .where(ChatTakeoverCase.status.in_(statuses))
            .order_by(ChatTakeoverCase.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def list_messages(self, case_id: UUID, limit: int) -> list[ChatTakeoverMessage]:
        statement = (
            select(ChatTakeoverMessage)
            .where(ChatTakeoverMessage.case_id == case_id)
            .order_by(ChatTakeoverMessage.created_at.asc(), ChatTakeoverMessage.id.asc())
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def get_message_by_client_id(self, case_id: UUID, client_message_id: str) -> ChatTakeoverMessage | None:
        statement = select(ChatTakeoverMessage).where(
            ChatTakeoverMessage.case_id == case_id,
            ChatTakeoverMessage.client_message_id == client_message_id,
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def add_audit(self, case_id: UUID, actor_user_id: UUID | None, event_type: str, metadata: dict | None = None) -> None:
        self.session.add(
            ChatTakeoverAuditEvent(
                case_id=case_id,
                actor_user_id=actor_user_id,
                event_type=event_type,
                event_metadata=metadata,
            )
        )
        await self.session.flush()

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)
