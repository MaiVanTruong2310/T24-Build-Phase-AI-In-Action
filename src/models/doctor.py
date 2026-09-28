"""Doctor and doctor-assignment persistence models."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.facility import Facility
    from src.models.schedule import DoctorSchedule
    from src.models.service import Service
    from src.models.specialty import Specialty


class Doctor(Base):
    """Doctor profile and public booking state."""

    __tablename__ = "doctors"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(64), unique=True)
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(32))
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    gender: Mapped[str | None] = mapped_column(String(16))
    title: Mapped[str | None] = mapped_column(String(64))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="approved", nullable=False)
    booking_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    specialties: Mapped[list[DoctorSpecialty]] = relationship(back_populates="doctor", cascade="all, delete-orphan")
    facilities: Mapped[list[DoctorFacility]] = relationship(back_populates="doctor", cascade="all, delete-orphan")
    services: Mapped[list[DoctorService]] = relationship(back_populates="doctor", cascade="all, delete-orphan")
    schedules: Mapped[list[DoctorSchedule]] = relationship(back_populates="doctor")


class DoctorSpecialty(Base):
    """Doctor-to-specialty assignment."""

    __tablename__ = "doctor_specialties"
    __table_args__ = (UniqueConstraint("doctor_id", "specialty_id", name="uq_doctor_specialty"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    specialty_id: Mapped[UUID] = mapped_column(
        ForeignKey("specialties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    doctor: Mapped[Doctor] = relationship(back_populates="specialties")
    specialty: Mapped[Specialty] = relationship(back_populates="doctors")


class DoctorFacility(Base):
    """Doctor-to-facility assignment and operational location."""

    __tablename__ = "doctor_facilities"
    __table_args__ = (UniqueConstraint("doctor_id", "facility_id", name="uq_doctor_facility"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department: Mapped[str | None] = mapped_column(String(160))
    room: Mapped[str | None] = mapped_column(String(64))
    active_from: Mapped[date | None] = mapped_column(Date)
    active_to: Mapped[date | None] = mapped_column(Date)

    doctor: Mapped[Doctor] = relationship(back_populates="facilities")
    facility: Mapped[Facility] = relationship(back_populates="doctors")


class DoctorService(Base):
    """Doctor-to-service assignment."""

    __tablename__ = "doctor_services"
    __table_args__ = (UniqueConstraint("doctor_id", "service_id", name="uq_doctor_service"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    doctor: Mapped[Doctor] = relationship(back_populates="services")
    service: Mapped[Service] = relationship(back_populates="doctors")
