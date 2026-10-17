"""Recurring doctor shifts, dated sessions and coordinator-owned requests."""

from datetime import date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class WeeklyShift(Base):
    __tablename__ = "weekly_shifts"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_weekly_shifts_weekday"),
        CheckConstraint("slot_count BETWEEN 1 AND 20", name="ck_weekly_shifts_slot_count"),
        CheckConstraint("slot_minutes BETWEEN 5 AND 240", name="ck_weekly_shifts_slot_minutes"),
        CheckConstraint("period IN ('morning','afternoon')", name="ck_weekly_shifts_period"),
        UniqueConstraint("doctor_id", "weekday", "period", name="uq_weekly_shift_doctor_day_period"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[str] = mapped_column(String(12), nullable=False)
    start_time: Mapped[time] = mapped_column(Time(timezone=False), nullable=False)
    slot_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    slot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_until: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class ConsultationSession(Base):
    __tablename__ = "consultation_sessions"
    __table_args__ = (
        UniqueConstraint("doctor_id", "session_date", "period", name="uq_consultation_session_doctor_date_period"),
        CheckConstraint("period IN ('morning','afternoon')", name="ck_consultation_sessions_period"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    weekly_shift_id: Mapped[UUID] = mapped_column(ForeignKey("weekly_shifts.id", ondelete="RESTRICT"), nullable=False)
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ConsultationSlot(Base):
    __tablename__ = "consultation_slots"
    __table_args__ = (
        UniqueConstraint("session_id", "ordinal", name="uq_consultation_slot_ordinal"),
        UniqueConstraint("schedule_id", name="uq_consultation_slot_schedule"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("consultation_sessions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    schedule_id: Mapped[UUID] = mapped_column(ForeignKey("doctor_schedules.id", ondelete="RESTRICT"), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)


class ConsultationRequest(Base):
    __tablename__ = "consultation_requests"
    __table_args__ = (
        Index("ix_consultation_requests_session_status", "session_id", "status"),
        Index("ix_consultation_requests_patient_created", "patient_id", "created_at"),
        Index(
            "uq_consultation_requests_active_patient_session",
            "patient_id",
            "session_id",
            unique=True,
            postgresql_where=text("status IN ('pending','confirmed')"),
        ),
        Index(
            "uq_consultation_requests_confirmed_slot",
            "assigned_slot_id",
            unique=True,
            postgresql_where=text("status = 'confirmed'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="RESTRICT"), index=True
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("consultation_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    specialty_id: Mapped[UUID] = mapped_column(ForeignKey("specialties.id", ondelete="RESTRICT"), nullable=False)
    encounter_type: Mapped[str] = mapped_column(String(20), nullable=False, default="in_person")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    patient_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    assigned_slot_id: Mapped[UUID | None] = mapped_column(ForeignKey("consultation_slots.id", ondelete="RESTRICT"))
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey("bookings.id", ondelete="RESTRICT"), unique=True)
    staff_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ConsultationRequestEvent(Base):
    __tablename__ = "consultation_request_events"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("consultation_requests.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
