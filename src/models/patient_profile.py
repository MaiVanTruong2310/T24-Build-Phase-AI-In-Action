"""Patient identity and delegated booking access, separate from login credentials."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    # Compatibility identity for existing clinical tables; dependents have no login credentials.
    patient_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    linked_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(120))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(24))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    citizen_id: Mapped[str | None] = mapped_column(String(12))
    health_insurance_code: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PatientRelationship(Base):
    __tablename__ = "patient_relationships"
    __table_args__ = (UniqueConstraint("user_id", "patient_profile_id", name="uq_patient_relationship"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    patient_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("patient_profiles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    relationship: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    can_book: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Booking permission does not grant access to medical records of another account.
    can_view_medical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
