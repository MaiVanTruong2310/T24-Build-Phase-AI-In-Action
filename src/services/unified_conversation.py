"""Unified Conversation Service handling patient support, handoffs, and messages."""

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import desc, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger, log_event
from src.models.conversation import (
    Conversation,
    ConversationParticipant,
    Handoff,
    Message,
    PatientChatContext,
    StaffAgentContext,
)

logger = get_logger(__name__)


class UnifiedConversationService:
    """Orchestrates conversations, messages, context, and human-in-the-loop handoffs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_conversation(
        self,
        user_id: UUID | None,
        session_id: str,
        title: str = "",
        patient_profile_id: UUID | None = None,
        category: str = "PATIENT_SUPPORT",
    ) -> Conversation:
        """Find an existing active conversation by session_id or create a new one atomically."""
        # 1. Look for existing conversation via patient_chat_context containing session_id
        stmt = (
            select(Conversation)
            .join(PatientChatContext, PatientChatContext.conversation_id == Conversation.id)
            .where(
                PatientChatContext.context_data["session_id"].as_string() == session_id
            )
            .order_by(desc(Conversation.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        conv = result.scalar_one_or_none()

        if conv:
            return conv

        # 2. Create new conversation
        conv_id = uuid4()
        now = datetime.now(timezone.utc)
        conv = Conversation(
            id=conv_id,
            category=category,
            mode="AI",
            status="ACTIVE",
            patient_id=user_id,
            created_by_type="PATIENT" if user_id else "SYSTEM",
            created_by_id=user_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(conv)

        # 3. Add participants
        if user_id:
            self.session.add(
                ConversationParticipant(
                    id=uuid4(),
                    conversation_id=conv_id,
                    participant_type="PATIENT",
                    participant_id=user_id,
                    role="patient",
                    joined_at=now,
                )
            )

        self.session.add(
            ConversationParticipant(
                id=uuid4(),
                conversation_id=conv_id,
                participant_type="AGENT",
                participant_id=None,
                role="assistant",
                joined_at=now,
            )
        )

        # 4. Add patient chat context
        ctx_data = {
            "session_id": session_id,
            "title": title[:80] if title else "",
            "patient_profile_id": str(patient_profile_id) if patient_profile_id else None,
        }
        self.session.add(
            PatientChatContext(
                conversation_id=conv_id,
                patient_id=user_id,
                current_stage="GENERAL_SUPPORT",
                context_data=ctx_data,
                updated_at=now,
            )
        )

        await self.session.flush()
        return conv

    async def append_message(
        self,
        conversation_id: UUID,
        sender_type: str,
        content: str | None,
        sender_id: UUID | None = None,
        message_type: str = "TEXT",
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Append a new message to the conversation and touch updated_at."""
        now = datetime.now(timezone.utc)
        msg = Message(
            id=uuid4(),
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            message_type=message_type,
            content=content,
            msg_metadata=metadata,
            created_at=now,
        )
        self.session.add(msg)

        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=now)
        )
        await self.session.flush()
        return msg

    async def get_messages(
        self,
        conversation_id: UUID,
        limit: int = 100,
    ) -> list[Message]:
        """Fetch chronological messages for a given conversation."""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def request_handoff(
        self,
        conversation_id: UUID,
        reason: str = "MANUAL_REVIEW",
        agent_confidence: float | None = None,
        assigned_staff_id: UUID | None = None,
    ) -> Handoff:
        """Trigger handoff from Agent to Staff."""
        now = datetime.now(timezone.utc)
        handoff = Handoff(
            id=uuid4(),
            conversation_id=conversation_id,
            from_actor_type="AGENT",
            to_actor_type="STAFF",
            reason=reason,
            agent_confidence=agent_confidence,
            requested_by_type="AGENT",
            assigned_staff_id=assigned_staff_id,
            status="ASSIGNED" if assigned_staff_id else "REQUESTED",
            requested_at=now,
            accepted_at=now if assigned_staff_id else None,
        )
        self.session.add(handoff)

        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(mode="HUMAN", status="WAITING_FOR_STAFF", updated_at=now)
        )
        await self.session.flush()
        return handoff

    async def resolve_handoff(
        self,
        conversation_id: UUID,
    ) -> None:
        """Resolve any pending handoffs and transition conversation back to AI or RESOLVED."""
        now = datetime.now(timezone.utc)
        await self.session.execute(
            update(Handoff)
            .where(
                Handoff.conversation_id == conversation_id,
                Handoff.status.in_(["REQUESTED", "ASSIGNED", "ACCEPTED"]),
            )
            .values(status="RESOLVED", resolved_at=now)
        )
        await self.session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(mode="AI", status="ACTIVE", updated_at=now)
        )
        await self.session.flush()
