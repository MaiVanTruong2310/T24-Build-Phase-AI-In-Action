"""In-app booking notifications and patient email outbox records."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.models.booking import Booking
    from src.models.user import User


class Notification(Base):
    """A durable in-app notification or patient email delivery command."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_status_available", "user_id", "status", "available_at"),
        Index("ix_notifications_booking_id", "booking_id"),
        Index("ix_notifications_delivery_queue", "status", "available_at", "dead_letter"),
        Index("uq_notifications_user_dedupe_key", "user_id", "dedupe_key", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id: Mapped[UUID | None] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), server_default="in_app", nullable=False)
    provider: Mapped[str] = mapped_column(String(64), server_default="database", nullable=False)
    status: Mapped[str] = mapped_column(String(16), server_default="pending", nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    dead_letter: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship()
    booking: Mapped[Booking | None] = relationship()
