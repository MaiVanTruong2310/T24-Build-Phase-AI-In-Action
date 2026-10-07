"""Persistence models for authenticated human-in-the-loop chat takeover."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ChatTakeoverCase(Base):
    """A staff workflow around one patient chat session."""

    __tablename__ = "chat_takeover_cases"
    __table_args__ = (
        UniqueConstraint("patient_user_id", "session_id", name="uq_chat_takeover_case_patient_session"),
        Index("ix_chat_takeover_cases_status_created", "status", "created_at"),
        Index("ix_chat_takeover_cases_assigned", "assigned_staff_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    workflow_status: Mapped[str] = mapped_column(String(64), nullable=False, default="HUMAN_HELP_REQUESTED")
    summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    assigned_staff_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ChatTakeoverMessage(Base):
    """Durable staff/system messages associated with a takeover case."""

    __tablename__ = "chat_takeover_messages"
    __table_args__ = (
        UniqueConstraint("case_id", "client_message_id", name="uq_chat_takeover_message_client_id"),
        Index("ix_chat_takeover_messages_case_created", "case_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chat_takeover_cases.id", ondelete="CASCADE"), nullable=False
    )
    author_type: Mapped[str] = mapped_column(String(16), nullable=False)
    author_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    client_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChatTakeoverAuditEvent(Base):
    """Minimal audit trail without storing raw clinical message content."""

    __tablename__ = "chat_takeover_audit_events"
    __table_args__ = (Index("ix_chat_takeover_audit_case_created", "case_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chat_takeover_cases.id", ondelete="CASCADE"), nullable=False
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
