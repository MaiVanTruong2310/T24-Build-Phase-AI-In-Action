"""Durable coordinator workbench; all access is mediated by the backend."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

DOC = JSON().with_variant(JSONB, "postgresql")


class CoordinatorMember(Base):
    __tablename__ = "coordinator_members"
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    on_duty: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    facility_ids: Mapped[list] = mapped_column(DOC, default=list, nullable=False)
    clinical_qualification: Mapped[str] = mapped_column(String(200), nullable=False)


class CoordinationCase(Base):
    __tablename__ = "coordination_cases"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_case_source"),
        UniqueConstraint("owner_key", "session_id", name="uq_case_conversation"),
        Index("ix_case_queue", "status", "priority", "created_at"),
        Index("ix_case_assignee_due", "assigned_to", "due_at"),
        CheckConstraint("priority BETWEEN 0 AND 3", name="ck_case_priority"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_key: Mapped[str | None] = mapped_column(String(100))
    session_id: Mapped[str | None] = mapped_column(String(200))
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    patient_profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="RESTRICT"), index=True
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    patient: Mapped[dict] = mapped_column(DOC, default=dict, nullable=False)
    ai_snapshot: Mapped[dict] = mapped_column(DOC, default=dict, nullable=False)
    checkpoint: Mapped[dict] = mapped_column(DOC, default=dict, nullable=False)
    plan: Mapped[dict] = mapped_column(DOC, default=dict, nullable=False)
    facility_id: Mapped[UUID | None] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"))
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="new", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    control: Mapped[str] = mapped_column(String(12), default="ai", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"))
    legacy_takeover_case_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CoordinationEvent(Base):
    __tablename__ = "coordination_events"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("coordination_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    details: Mapped[dict] = mapped_column(DOC, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CoordinationMessage(Base):
    __tablename__ = "coordination_messages"
    __table_args__ = (UniqueConstraint("case_id", "client_id", name="uq_case_message_client"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("coordination_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    client_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sender: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CoordinationDeposit(Base):
    __tablename__ = "coordination_deposits"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_deposit_amount"),
        UniqueConstraint("transaction_reference", name="uq_deposit_transaction"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("coordination_cases.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="requested", nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    refund_policy: Mapped[str] = mapped_column(Text, nullable=False)
    transaction_reference: Mapped[str | None] = mapped_column(String(200))
    refund_reference: Mapped[str | None] = mapped_column(String(200), unique=True)
    evidence: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CoordinationPolicy(Base):
    __tablename__ = "coordination_policy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hold_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    response_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    emergency_response_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    refund_policy: Mapped[str] = mapped_column(Text, nullable=False)


WORKBENCH_TABLES = [
    CoordinatorMember.__table__,
    CoordinationCase.__table__,
    CoordinationEvent.__table__,
    CoordinationDeposit.__table__,
    CoordinationPolicy.__table__,
]
