"""Doctor schedule persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.doctor import Doctor
    from src.models.facility import Facility
    from src.models.service import Service


class DoctorSchedule(Base):
    """A capacity-limited appointment slot."""

    __tablename__ = "doctor_schedules"
    __table_args__ = (
        UniqueConstraint("source_system", "external_schedule_id", name="uq_schedule_external_identity"),
        ExcludeConstraint(
            ("doctor_id", "="),
            (text("tstzrange(starts_at, ends_at, '[)')"), "&&"),
            where=text("status <> 'cancelled'"),
            using="gist",
            name="excl_doctor_schedule_time",
        ),
        CheckConstraint("ends_at > starts_at", name="ck_schedule_time_order"),
        CheckConstraint("capacity >= 0", name="ck_schedule_capacity_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="available", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(64))
    external_schedule_id: Mapped[str | None] = mapped_column(String(128))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    updated_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    service_id: Mapped[UUID | None] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), index=True)
    busy_reason: Mapped[str | None] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    doctor: Mapped[Doctor] = relationship(back_populates="schedules")
    facility: Mapped[Facility] = relationship(back_populates="schedules")
    service: Mapped[Service | None] = relationship("Service")
