"""Persistence queries for user notifications and reminder outbox records."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from src.models.notification import Notification
from src.models.user import User


class NotificationRepository:
    """Database operations for in-app notifications and email delivery."""

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
        """List visible in-app notifications for the user."""
        now = datetime.now(UTC)
        statement = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.channel == "in_app",
                Notification.status.in_(("pending", "delivered")),
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
            Notification.channel == "in_app",
            Notification.status.in_(("pending", "delivered")),
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def mark_all_read(self, user_id: UUID, now: datetime) -> int:
        """Mark all visible unread notifications as read."""
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.channel == "in_app",
                Notification.status.in_(("pending", "delivered")),
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
                Notification.status.in_(("pending", "processing", "failed", "delivered")),
            )
            .values(status="discarded", delivered_at=now, updated_at=now)
        )
        return int(result.rowcount or 0)

    async def list_active_staff_ids(self) -> list[UUID]:
        """Return all active staff recipients for the temporary global rollout."""
        statement = select(User.id).where(User.role == "staff", User.status == "active")
        return list((await self.session.execute(statement)).scalars().all())

    async def get_user_email(self, user_id: UUID) -> str | None:
        """Return a patient's current email address for outbox creation."""
        statement = select(User.email).where(User.id == user_id)
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def claim_email_pending(self, now: datetime, limit: int) -> list[Notification]:
        """Claim due email rows so only one maintenance loop delivers each row."""
        statement = (
            select(Notification)
            .options(selectinload(Notification.user))
            .where(
                Notification.channel == "email",
                Notification.status.in_(("pending", "failed")),
                Notification.available_at <= now,
                Notification.dead_letter.is_(False),
            )
            .order_by(Notification.available_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        notifications = list((await self.session.execute(statement)).scalars().all())
        for notification in notifications:
            notification.status = "processing"
            notification.attempt_count += 1
        if notifications:
            await self.session.flush()
        return notifications

    async def mark_email_delivered(self, notification_id: UUID, now: datetime) -> None:
        """Mark an email delivered only after SMTP accepts it."""
        await self.session.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.status == "processing")
            .values(status="delivered", delivered_at=now, updated_at=now)
        )

    async def mark_email_failed(
        self,
        notification_id: UUID,
        error: str,
        now: datetime,
        *,
        max_attempts: int,
        retry_backoff_seconds: int,
        retry_backoff_max_seconds: int,
    ) -> None:
        """Schedule a bounded retry without persisting provider credentials."""
        statement = select(Notification).where(
            Notification.id == notification_id,
            Notification.channel == "email",
            Notification.status == "processing",
        )
        notification = (await self.session.execute(statement)).scalar_one_or_none()
        if notification is None:
            return
        notification.status = "failed"
        notification.error = error[:2000]
        notification.dead_letter = notification.attempt_count >= max_attempts
        delay = min(
            retry_backoff_seconds * (2 ** max(notification.attempt_count - 1, 0)),
            retry_backoff_max_seconds,
        )
        notification.available_at = now + timedelta(seconds=delay)
        await self.session.flush()

    async def discard_email(self, notification_id: UUID, now: datetime, reason: str) -> None:
        """Discard an email that has no current recipient address."""
        await self.session.execute(
            update(Notification)
            .where(Notification.id == notification_id, Notification.status == "processing")
            .values(status="discarded", error=reason[:2000], delivered_at=now, updated_at=now)
        )

    async def requeue_stale_email(self, now: datetime, timeout_seconds: int) -> int:
        """Return email rows abandoned by a crashed maintenance loop to the queue."""
        stale_before = now - timedelta(seconds=timeout_seconds)
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.channel == "email",
                Notification.status == "processing",
                Notification.updated_at <= stale_before,
            )
            .values(status="pending", available_at=now, updated_at=now)
        )
        return int(result.rowcount or 0)
