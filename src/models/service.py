"""Medical service persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, Float, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.doctor import DoctorService


class Service(Base):
    """Bookable medical service."""

    __tablename__ = "services"
    __table_args__ = (CheckConstraint("booking_mode IN ('group', 'doctor_visit')", name="ck_services_booking_mode"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    original_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    category: Mapped[str | None] = mapped_column(String(100))
    booking_mode: Mapped[str] = mapped_column(String(20), default="group", nullable=False)
    features: Mapped[list[str] | None] = mapped_column(JSON)
    patient_count: Mapped[int | None] = mapped_column(Integer, default=0)
    satisfaction_rate: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    doctors: Mapped[list[DoctorService]] = relationship(back_populates="service")
