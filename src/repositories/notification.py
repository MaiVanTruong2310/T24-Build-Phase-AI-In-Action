"""Persistence queries for user notifications and reminder outbox records."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from src.models.notification import Notification


class NotificationRepository:
    """Database operations for durable in-app notifications."""

    def __init__(self, session):
        self.session = session

    async def add(self, notification: Notification) -> None:
        """Stage one notification in the caller's transaction."""
        self.session.add(notification)
        await self.session.flush()

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        unread_only: bool,
        offset: int,
        limit: int,
    ) -> list[Notification]:
        """List delivered notifications that are now visible to the user."""
        now = datetime.now(UTC)
        statement = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status == "delivered",
                Notification.available_at <= now,
            )
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if unread_only:
            statement = statement.where(Notification.read_at.is_(None))
        return list((await self.session.execute(statement)).scalars().all())

    async def get_for_user(self, notification_id: UUID, user_id: UUID, *, for_update: bool = False):
        """Fetch one notification only for its owner."""
        statement = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.status == "delivered",
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def mark_all_read(self, user_id: UUID, now: datetime) -> int:
        """Mark all delivered unread notifications as read."""
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status == "delivered",
                Notification.read_at.is_(None),
            )
            .values(read_at=now, updated_at=now)
        )
        return int(result.rowcount or 0)

    async def discard_reminders_for_booking(self, booking_id: UUID, now: datetime) -> int:
        """Hide reminders made stale by a reschedule or cancellation."""
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.booking_id == booking_id,
                Notification.kind == "appointment_reminder",
                Notification.status.in_(("pending", "delivered")),
            )
            .values(status="discarded", delivered_at=now, updated_at=now)
        )
        return int(result.rowcount or 0)

    async def claim_due_reminders(self, now: datetime, limit: int) -> list[Notification]:
        """Claim due reminders, discarding those whose booking is no longer confirmed."""
        statement = (
            select(Notification)
            .options(selectinload(Notification.booking))
            .where(
                Notification.kind == "appointment_reminder",
                Notification.status == "pending",
                Notification.available_at <= now,
            )
            .order_by(Notification.available_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        notifications = list((await self.session.execute(statement)).scalars().all())
        for notification in notifications:
            notification.status = (
                "delivered"
                if notification.booking is not None and notification.booking.status == "confirmed"
                else "discarded"
            )
            notification.delivered_at = now
        if notifications:
            await self.session.flush()
        return notifications
