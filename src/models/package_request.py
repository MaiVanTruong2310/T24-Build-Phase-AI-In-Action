"""Package request persistence model for health packages and pathways."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class PackageRequest(Base):
    """Patient request to register for a health package / pathway."""

    __tablename__ = "package_requests"
    __table_args__ = (
        Index("ix_package_requests_patient_created", "patient_id", "created_at"),
        Index("ix_package_requests_service", "service_id"),
        Index("ix_package_requests_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    patient_profile_id: Mapped[UUID | None] = mapped_column(ForeignKey("patient_profiles.id", ondelete="RESTRICT"), index=True)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    service_id: Mapped[UUID] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False)
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False)
    preferred_period: Mapped[str] = mapped_column(String(12), nullable=False, default="morning")
    patient_name: Mapped[str | None] = mapped_column(String(120))
    patient_phone: Mapped[str | None] = mapped_column(String(20))
    patient_email: Mapped[str | None] = mapped_column(String(320))
    gender: Mapped[str | None] = mapped_column(String(16))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    staff_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
