"""Temporary capacity holds for the patient booking flow."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.booking import Booking
    from src.models.schedule import DoctorSchedule
    from src.models.service import Service
    from src.models.specialty import Specialty
    from src.models.user import User


class BookingHold(Base):
    """A short-lived reservation of one schedule's capacity."""

    __tablename__ = "booking_holds"
    __table_args__ = (
        Index("ix_booking_holds_schedule_status", "schedule_id", "status"),
        Index("ix_booking_holds_expires_at", "expires_at"),
        Index(
            "uq_booking_holds_active_user_schedule",
            "user_id",
            "schedule_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    schedule_id: Mapped[UUID] = mapped_column(
        ForeignKey("doctor_schedules.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    specialty_id: Mapped[UUID] = mapped_column(ForeignKey("specialties.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship()
    schedule: Mapped[DoctorSchedule] = relationship()
    service: Mapped[Service] = relationship()
    specialty: Mapped[Specialty] = relationship()
    booking: Mapped[Booking | None] = relationship(back_populates="hold")
