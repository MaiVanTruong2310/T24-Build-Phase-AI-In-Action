"""Unified Conversation schema models according to P124_chat_conversation_schema."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

DOC = JSON().with_variant(JSONB, "postgresql")


class Conversation(Base):
    """Central conversation entity representing chat sessions across Patient and Staff actors."""

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_patient_created", "patient_id", "created_at"),
        Index("ix_conversations_status", "status"),
        Index("ix_conversations_category", "category"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="PATIENT_SUPPORT")
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="AI")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    created_by_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PATIENT")
    created_by_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConversationParticipant(Base):
    """Actors associated with a conversation."""

    __tablename__ = "conversation_participants"
    __table_args__ = (
        Index("ix_participants_conv_type", "conversation_id", "participant_type"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    participant_type: Mapped[str] = mapped_column(String(32), nullable=False)
    participant_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Message(Base):
    """Unified message store across patient, staff, agent, and system events."""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conv_created", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sender_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, default="TEXT")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    msg_metadata: Mapped[dict | None] = mapped_column("metadata", DOC, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Handoff(Base):
    """Transfers between AI and Human coordinators."""

    __tablename__ = "handoffs"
    __table_args__ = (
        Index("ix_handoffs_conv_status", "conversation_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    from_actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="AGENT")
    to_actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="STAFF")
    reason: Mapped[str] = mapped_column(String(64), nullable=False, default="MANUAL_REVIEW")
    agent_confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    requested_by_type: Mapped[str] = mapped_column(String(32), nullable=False, default="AGENT")
    requested_by_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    assigned_staff_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PatientChatContext(Base):
    """Business context for patient support workflows."""

    __tablename__ = "patient_chat_context"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    booking_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    specialty_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="GENERAL_SUPPORT")
    context_data: Mapped[dict | None] = mapped_column(DOC, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StaffAgentContext(Base):
    """Operational context for staff copilot assistant."""

    __tablename__ = "staff_agent_context"

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    context_patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    context_booking_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    context_department_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    task_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context_data: Mapped[dict | None] = mapped_column(DOC, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
