"""User persistence model.

``auth.users`` (Supabase Auth) owns credentials and the confirmed email.
``public.users`` owns the application profile:

* ``auth_user_id`` links to ``auth.users.id`` (FK ON DELETE CASCADE, declared in
  the database migration rather than here so ``Base.metadata.create_all`` never
  has to know about the ``auth`` schema).
* ``email`` is a one-way mirror maintained by the ``auth.users`` trigger
  ``trg_sync_user_email_from_auth``; never write it from application code except
  when the profile row is first created.
* ``phone`` and ``full_name`` are application data, not auth identity.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class User(Base):
    """Application user with patient or staff access."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    auth_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(32), default="patient", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending_verification", nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(16))
    citizen_id: Mapped[str | None] = mapped_column(String(12), index=True)
    health_insurance_code: Mapped[str | None] = mapped_column(String(32), index=True)
    patient_details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
