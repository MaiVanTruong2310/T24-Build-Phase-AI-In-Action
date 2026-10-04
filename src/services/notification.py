"""Booking notification lifecycle with direct database and WebSocket delivery."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.config import Settings, get_settings
from src.core.exceptions import NotFoundError
from src.core.logging import get_logger, log_event
from src.models.booking import Booking
from src.models.notification import Notification
from src.realtime.notifications import notification_manager
from src.repositories.booking import BookingRepository
from src.repositories.notification import NotificationRepository
from src.services.email import GmailEmailSender

logger = get_logger(__name__)


class NotificationService:
    """Create in-app notifications and queue patient email delivery."""

    def __init__(
        self,
        session,
        *,
        settings: Settings | None = None,
        email_sender: GmailEmailSender | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.bookings = BookingRepository(session)
        self.notifications = NotificationRepository(session)
        self.email_sender = email_sender or GmailEmailSender(self.settings)

    async def create_for_booking_request(self, booking: Booking, *, cycle: str = "created") -> int:
        """Create an immediately visible approval notification for every active staff user."""
        log_event(
            logger,
            logging.INFO,
            "notification.booking_request.start",
            description="Starting staff notifications for a booking request",
            booking_id=str(booking.id),
            cycle=cycle,
        )
        now = datetime.now(UTC)
        staff_ids = await self.notifications.list_active_staff_ids()
        for staff_id in staff_ids:
            await self._create_in_app_notification(
                user_id=staff_id,
                booking_id=booking.id,
                kind="booking_pending_approval",
                title="Có lịch khám mới cần duyệt",
                message="Một lịch khám mới đang chờ staff duyệt.",
                dedupe_key=f"booking:{booking.id}:approval:{cycle}:staff:{staff_id}",
                available_at=now,
            )
        log_event(
            logger,
            logging.INFO,
            "notification.booking_request.created",
            description="Staff approval notifications were created for a new booking request",
            booking_id=str(booking.id),
            recipient_count=len(staff_ids),
            cycle=cycle,
        )
        return len(staff_ids)

    async def create_for_booking_review(self, booking: Booking, status: str) -> None:
        """Create a patient decision notification after staff review."""
        log_event(
            logger,
            logging.INFO,
            "notification.booking_review.start",
            description="Starting patient notification for a staff booking decision",
            booking_id=str(booking.id),
            status=status,
        )
        if status == "confirmed":
            await self._create_patient_notification(
                booking,
                kind="booking_confirmed",
                title="Lịch khám đã được duyệt",
                message="Lịch khám của bạn đã được nhân viên xác nhận.",
                dedupe_suffix="decision:confirmed",
            )
        elif status == "rejected":
            await self._create_patient_notification(
                booking,
                kind="booking_rejected",
                title="Lịch khám chưa được duyệt",
                message=booking.staff_note or "Lịch khám chưa được nhân viên xác nhận.",
                dedupe_suffix="decision:rejected",
            )
        log_event(
            logger,
            logging.INFO,
            "notification.booking_review.created",
            description="Patient notification was created for the staff booking decision",
            booking_id=str(booking.id),
            status=status,
        )

    async def create_for_booking_expired(self, booking: Booking) -> None:
        """Create a patient notification when the approval deadline is missed."""
        log_event(
            logger,
            logging.INFO,
            "notification.booking_expired.start",
            description="Starting patient notification for an expired booking",
            booking_id=str(booking.id),
        )
        await self._create_patient_notification(
            booking,
            kind="booking_expired",
            title="Lịch khám đã hết hạn",
            message="Lịch khám chưa được duyệt trong thời hạn 24 giờ.",
            dedupe_suffix="expired",
        )
        log_event(
            logger,
            logging.INFO,
            "notification.booking_expired.created",
            description="Patient notification was created for an expired booking request",
            booking_id=str(booking.id),
        )

    async def create_due_reminders(self, limit: int = 100) -> int:
        """Create direct in-app reminders for confirmed appointments."""
        log_event(
            logger,
            logging.INFO,
            "notification.reminder.start",
            description="Starting due appointment reminder scan",
            limit=limit,
        )
        now = datetime.now(UTC)
        deadline = now + timedelta(days=get_settings().appointment_reminder_lead_days)
        async with self.session.begin():
            bookings = await self.bookings.list_confirmed_reminder_candidates(now, deadline, limit)
            for booking in bookings:
                await self._create_patient_notification(
                    booking,
                    kind="appointment_reminder",
                    title="Nhắc lịch khám",
                    message="Bạn có lịch khám sắp diễn ra. Vui lòng chuẩn bị trước giờ hẹn.",
                    dedupe_suffix="reminder:2d",
                    available_at=now,
                )
        log_event(
            logger,
            logging.INFO,
            "notification.reminder.created",
            description="Due appointment reminders were created for confirmed bookings",
            count=len(bookings),
        )
        return len(bookings)

    async def list_for_user(self, user_id: UUID, *, unread_only: bool, offset: int, limit: int) -> list[Notification]:
        """List visible in-app notifications owned by a user."""
        log_event(
            logger,
            logging.INFO,
            "notification.list.start",
            description="Starting user notification lookup",
            user_id=str(user_id),
            unread_only=unread_only,
            offset=offset,
            limit=limit,
        )
        values = await self.notifications.list_for_user(user_id, unread_only=unread_only, offset=offset, limit=limit)
        log_event(
            logger,
            logging.INFO,
            "notification.list.done",
            description="User notifications were listed with the requested read filter",
            user_id=str(user_id),
            count=len(values),
            unread_only=unread_only,
        )
        return values

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> Notification:
        """Mark one owned notification as read."""
        log_event(
            logger,
            logging.INFO,
            "notification.read.start",
            description="Starting one notification read-state update",
            user_id=str(user_id),
            notification_id=str(notification_id),
        )
        async with self.session.begin():
            notification = await self.notifications.get_for_user(notification_id, user_id, for_update=True)
            if notification is None:
                log_event(
                    logger,
                    logging.WARNING,
                    "notification.read.not_found",
                    description="Notification read request found no notification owned by the user",
                    user_id=str(user_id),
                    notification_id=str(notification_id),
                )
                raise NotFoundError("Notification not found")
            notification.read_at = datetime.now(UTC)
            await self.session.flush()
        log_event(
            logger,
            logging.INFO,
            "notification.read.done",
            description="A user notification was marked as read",
            user_id=str(user_id),
            notification_id=str(notification_id),
        )
        return notification

    async def mark_all_read(self, user_id: UUID) -> int:
        """Mark all owned visible notifications as read."""
        log_event(
            logger,
            logging.INFO,
            "notification.read_all.start",
            description="Starting all-notification read-state update",
            user_id=str(user_id),
        )
        async with self.session.begin():
            count = await self.notifications.mark_all_read(user_id, datetime.now(UTC))
        log_event(
            logger,
            logging.INFO,
            "notification.read_all.done",
            description="All visible user notifications were marked as read",
            user_id=str(user_id),
            count=count,
        )
        return count

    async def discard_reminders_for_booking(self, booking_id: UUID) -> int:
        """Invalidate reminders for a booking whose time is changing."""
        log_event(
            logger,
            logging.INFO,
            "notification.reminder.discard.start",
            description="Starting reminder invalidation for a booking change",
            booking_id=str(booking_id),
        )
        count = await self.notifications.discard_reminders_for_booking(booking_id, datetime.now(UTC))
        log_event(
            logger,
            logging.INFO,
            "notification.reminder.discarded",
            description="Appointment reminders were invalidated for a booking change",
            booking_id=str(booking_id),
            count=count,
        )
        return count

    async def deliver_pending_emails(self, limit: int = 100) -> int:
        """Deliver queued patient emails without coupling SMTP to booking commits."""
        log_event(
            logger,
            logging.INFO,
            "notification.email_delivery.start",
            description="Starting pending notification email delivery",
            limit=limit,
        )
        if not self.settings.gmail_smtp_username or not self.settings.gmail_smtp_app_password:
            log_event(
                logger,
                logging.DEBUG,
                "notification.email.skipped",
                description="Pending email delivery was skipped because SMTP is not configured",
                reason="smtp_not_configured",
            )
            return 0

        now = datetime.now(UTC)
        async with self.session.begin():
            await self.notifications.requeue_stale_email(now, self.settings.notification_processing_timeout_seconds)
            notifications = await self.notifications.claim_email_pending(now, limit)

        delivered = 0
        for notification in notifications:
            recipient = notification.user.email if notification.user else None
            if not recipient:
                async with self.session.begin():
                    await self.notifications.discard_email(
                        notification.id, datetime.now(UTC), "patient email address is missing"
                    )
                continue
            try:
                await self.email_sender.send(recipient, notification.title, notification.message)
            except Exception as exc:
                async with self.session.begin():
                    await self.notifications.mark_email_failed(
                        notification.id,
                        type(exc).__name__,
                        datetime.now(UTC),
                        max_attempts=self.settings.notification_max_attempts,
                        retry_backoff_seconds=self.settings.notification_retry_backoff_seconds,
                        retry_backoff_max_seconds=self.settings.notification_retry_backoff_max_seconds,
                    )
                log_event(
                    logger,
                    logging.WARNING,
                    "notification.email.retry_scheduled",
                    description="Email delivery failed and the notification was scheduled for retry",
                    notification_id=str(notification.id),
                    error_type=type(exc).__name__,
                )
                continue
            async with self.session.begin():
                await self.notifications.mark_email_delivered(notification.id, datetime.now(UTC))
            delivered += 1
        log_event(
            logger,
            logging.INFO,
            "notification.email_delivery.done",
            description="Pending notification emails were processed",
            delivered_count=delivered,
        )
        return delivered

    async def _create_patient_notification(
        self,
        booking: Booking,
        *,
        kind: str,
        title: str,
        message: str,
        dedupe_suffix: str,
        available_at: datetime | None = None,
    ) -> Notification:
        """Create one direct in-app notification for a business event."""
        notification = await self._create_in_app_notification(
            user_id=booking.user_id,
            booking_id=booking.id,
            kind=kind,
            title=title,
            message=message,
            dedupe_key=f"booking:{booking.id}:{dedupe_suffix}:in_app",
            available_at=available_at or datetime.now(UTC),
        )
        patient_email = await self._patient_email(booking)
        if patient_email:
            await self._create_email_notification(
                user_id=booking.user_id,
                booking_id=booking.id,
                kind=kind,
                title=title,
                message=message,
                dedupe_key=f"booking:{booking.id}:{dedupe_suffix}:email",
                available_at=available_at or datetime.now(UTC),
            )
        else:
            log_event(
                logger,
                logging.WARNING,
                "notification.email.skipped",
                description="Patient email notification was skipped because no address was available",
                booking_id=str(booking.id),
                reason="address_missing",
            )
        return notification

    async def _patient_email(self, booking: Booking) -> str | None:
        """Resolve the address without triggering an async lazy relationship load."""
        loaded_user = getattr(booking, "__dict__", {}).get("user")
        if loaded_user is not None:
            return loaded_user.email
        return await self.notifications.get_user_email(booking.user_id)

    async def _create_email_notification(
        self,
        *,
        user_id: UUID,
        booking_id: UUID,
        kind: str,
        title: str,
        message: str,
        dedupe_key: str,
        available_at: datetime,
    ) -> Notification:
        """Stage a Gmail delivery command in the same transaction as in-app state."""
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            booking_id=booking_id,
            kind=kind,
            channel="email",
            provider="gmail_smtp",
            status="pending",
            title=title,
            message=message,
            dedupe_key=dedupe_key,
            available_at=available_at,
        )
        await self.notifications.add(notification)
        return notification

    async def _create_in_app_notification(
        self,
        *,
        user_id: UUID,
        booking_id: UUID,
        kind: str,
        title: str,
        message: str,
        dedupe_key: str,
        available_at: datetime,
    ) -> Notification:
        """Persist an immediately delivered notification and fan it out live."""
        delivered_at = datetime.now(UTC)
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            booking_id=booking_id,
            kind=kind,
            channel="in_app",
            provider="database",
            status="delivered",
            title=title,
            message=message,
            dedupe_key=dedupe_key,
            available_at=available_at,
            delivered_at=delivered_at,
            created_at=delivered_at,
        )
        await self.notifications.add(notification)
        await notification_manager.publish(
            user_id,
            {
                "type": "notification.created",
                "data": notification_response(notification).model_dump(mode="json"),
            },
        )
        return notification


def notification_response(value: Notification):
    """Map a delivered in-app notification to the stable API response."""
    from src.schemas.notification import NotificationResponse

    return NotificationResponse(
        id=value.id,
        booking_id=value.booking_id,
        kind=value.kind,
        title=value.title,
        message=value.message,
        available_at=value.available_at,
        read_at=value.read_at,
        created_at=value.created_at,
    )
