"""Booking notification lifecycle with direct database and WebSocket delivery."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.config import get_settings
from src.core.exceptions import NotFoundError
from src.models.booking import Booking
from src.models.notification import Notification
from src.repositories.booking import BookingRepository
from src.repositories.notification import NotificationRepository
from src.realtime.notifications import notification_manager


class NotificationService:
    """Create durable in-app notifications and publish them over WebSocket."""

    def __init__(self, session) -> None:
        self.session = session
        self.bookings = BookingRepository(session)
        self.notifications = NotificationRepository(session)

    async def create_for_booking_request(self, booking: Booking, *, cycle: str = "created") -> int:
        """Create an immediately visible approval notification for every active staff user."""
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
        return len(staff_ids)

    async def create_for_booking_review(self, booking: Booking, status: str) -> None:
        """Create a patient decision notification after staff review."""
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

    async def create_for_booking_expired(self, booking: Booking) -> None:
        """Create a patient notification when the approval deadline is missed."""
        await self._create_patient_notification(
            booking,
            kind="booking_expired",
            title="Lịch khám đã hết hạn",
            message="Lịch khám chưa được duyệt trong thời hạn 24 giờ.",
            dedupe_suffix="expired",
        )

    async def create_due_reminders(self, limit: int = 100) -> int:
        """Create direct in-app reminders for confirmed appointments."""
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
        return len(bookings)

    async def list_for_user(self, user_id: UUID, *, unread_only: bool, offset: int, limit: int) -> list[Notification]:
        """List visible in-app notifications owned by a user."""
        return await self.notifications.list_for_user(user_id, unread_only=unread_only, offset=offset, limit=limit)

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> Notification:
        """Mark one owned notification as read."""
        async with self.session.begin():
            notification = await self.notifications.get_for_user(notification_id, user_id, for_update=True)
            if notification is None:
                raise NotFoundError("Notification not found")
            notification.read_at = datetime.now(UTC)
            await self.session.flush()
        return notification

    async def mark_all_read(self, user_id: UUID) -> int:
        """Mark all owned visible notifications as read."""
        async with self.session.begin():
            return await self.notifications.mark_all_read(user_id, datetime.now(UTC))

    async def discard_reminders_for_booking(self, booking_id: UUID) -> int:
        """Invalidate reminders for a booking whose time is changing."""
        return await self.notifications.discard_reminders_for_booking(booking_id, datetime.now(UTC))

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
        return await self._create_in_app_notification(
            user_id=booking.user_id,
            booking_id=booking.id,
            kind=kind,
            title=title,
            message=message,
            dedupe_key=f"booking:{booking.id}:{dedupe_suffix}:in_app",
            available_at=available_at or datetime.now(UTC),
        )

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
