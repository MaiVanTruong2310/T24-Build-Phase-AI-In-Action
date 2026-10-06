"""SQLAlchemy Models for Cross-session Patient Memory & Open Loops."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

DOC = JSON().with_variant(JSONB, "postgresql")


class PatientMemoryItem(Base):
    __tablename__ = "patient_memory_items"
    __table_args__ = (
        Index("ix_patient_memory_user_category", "user_id", "category"),
        Index("ix_patient_memory_user_key", "user_id", "fact_key", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(100), nullable=False)
    fact_value: Mapped[dict] = mapped_column(DOC, default=dict, nullable=False)
    provenance: Mapped[str] = mapped_column(String(50), default="patient_reported", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    taint_status: Mapped[str] = mapped_column(String(30), default="clean", nullable=False)
    source_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PatientOpenLoop(Base):
    __tablename__ = "patient_open_loops"
    __table_args__ = (
        Index("ix_patient_open_loops_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    loop_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(DOC, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


MEMORY_TABLES = [PatientMemoryItem.__table__, PatientOpenLoop.__table__]
