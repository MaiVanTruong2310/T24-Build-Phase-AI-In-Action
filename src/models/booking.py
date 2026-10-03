"""Appointment booking persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.doctor import Doctor
    from src.models.facility import Facility
    from src.models.schedule import DoctorSchedule
    from src.models.service import Service
    from src.models.specialty import Specialty
    from src.models.user import User


class Booking(Base):
    """A user booking tied to a published schedule or a requested time."""

    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_schedule_status", "schedule_id", "status"),
        Index("ix_bookings_user_created_at", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    schedule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("doctor_schedules.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True)
    specialty_id: Mapped[UUID] = mapped_column(
        ForeignKey("specialties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    encounter_type: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    patient_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="pending_approval", nullable=False, index=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    staff_note: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    schedule: Mapped[DoctorSchedule | None] = relationship()
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    doctor: Mapped[Doctor] = relationship(foreign_keys=[doctor_id])
    facility: Mapped[Facility] = relationship(foreign_keys=[facility_id])
    service: Mapped[Service] = relationship()
    specialty: Mapped[Specialty] = relationship()
