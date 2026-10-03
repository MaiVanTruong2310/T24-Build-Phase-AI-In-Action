"""Notification API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

NotificationKind = Literal[
    "booking_pending_approval",
    "booking_confirmed",
    "booking_rejected",
    "booking_expired",
    "appointment_reminder",
]


class NotificationResponse(BaseModel):
    """A delivered notification visible to its owner."""

    id: UUID
    booking_id: UUID | None
    kind: NotificationKind
    title: str
    message: str
    available_at: datetime
    read_at: datetime | None
    created_at: datetime
