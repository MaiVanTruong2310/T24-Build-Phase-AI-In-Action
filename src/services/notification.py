"""Booking notification and reminder business rules."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from src.core.exceptions import NotFoundError
from src.models.booking import Booking
from src.models.notification import Notification
from src.realtime.notifications import notification_manager
from src.repositories.notification import NotificationRepository


class NotificationService:
    """Create transactional in-app booking notifications and reminders."""

    def __init__(self, session) -> None:
        self.session = session
        self.notifications = NotificationRepository(session)

    async def create_for_booking_request(self, booking: Booking, *, cycle: str = "created") -> int:
        """Notify active staff that a booking request needs review."""
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
                status="delivered",
            )
        return len(staff_ids)

    async def create_for_booking_review(self, booking: Booking, status: str) -> None:
        """Create the decision notification and a reminder when confirmed."""
        now = datetime.now(UTC)
        if status == "confirmed":
            await self._create_in_app_notification(
                user_id=booking.user_id,
                booking_id=booking.id,
                kind="booking_confirmed",
                title="Lịch khám đã được duyệt",
                message="Lịch khám của bạn đã được nhân viên xác nhận.",
                dedupe_key=f"booking:{booking.id}:decision:confirmed",
                available_at=now,
                status="delivered",
            )
            await self._create_in_app_notification(
                user_id=booking.user_id,
                booking_id=booking.id,
                kind="appointment_reminder",
                title="Nhắc lịch khám",
                message="Bạn có lịch khám sắp diễn ra. Vui lòng chuẩn bị trước giờ hẹn.",
                dedupe_key=f"booking:{booking.id}:reminder:24h",
                available_at=booking.starts_at - timedelta(hours=24),
                status="pending",
            )
        elif status == "rejected":
            await self._create_in_app_notification(
                user_id=booking.user_id,
                booking_id=booking.id,
                kind="booking_rejected",
                title="Lịch khám chưa được duyệt",
                message=booking.staff_note or "Lịch khám chưa được nhân viên xác nhận.",
                dedupe_key=f"booking:{booking.id}:decision:rejected",
                available_at=now,
                status="delivered",
            )

    async def create_for_booking_expired(self, booking: Booking) -> None:
        """Notify a patient when a pending booking misses its review deadline."""
        now = datetime.now(UTC)
        await self._create_in_app_notification(
            user_id=booking.user_id,
            booking_id=booking.id,
            kind="booking_expired",
            title="Lịch khám đã hết hạn",
            message="Lịch khám chưa được duyệt trong thời hạn 24 giờ.",
            dedupe_key=f"booking:{booking.id}:expired",
            available_at=now,
            status="delivered",
        )

    async def list_for_user(self, user_id: UUID, *, unread_only: bool, offset: int, limit: int) -> list[Notification]:
        return await self.notifications.list_for_user(user_id, unread_only=unread_only, offset=offset, limit=limit)

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> Notification:
        async with self.session.begin():
            notification = await self.notifications.get_for_user(notification_id, user_id, for_update=True)
            if notification is None:
                raise NotFoundError("Notification not found")
            notification.read_at = datetime.now(UTC)
            await self.session.flush()
        return notification

    async def mark_all_read(self, user_id: UUID) -> int:
        async with self.session.begin():
            return await self.notifications.mark_all_read(user_id, datetime.now(UTC))

    async def discard_reminders_for_booking(self, booking_id: UUID) -> int:
        return await self.notifications.discard_reminders_for_booking(booking_id, datetime.now(UTC))

    async def process_due_reminders(self, limit: int = 100) -> int:
        async with self.session.begin():
            notifications = await self.notifications.claim_due_reminders(datetime.now(UTC), limit)
        return sum(notification.status == "delivered" for notification in notifications)

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
        status: str,
    ) -> Notification:
        """Persist a notification and fan it out to connected clients."""
        created_at = datetime.now(UTC)
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            booking_id=booking_id,
            kind=kind,
            status=status,
            title=title,
            message=message,
            dedupe_key=dedupe_key,
            available_at=available_at,
            delivered_at=created_at if status == "delivered" else None,
            created_at=created_at,
        )
        await self.notifications.add(notification)
        if status == "delivered":
            await notification_manager.publish(
                user_id,
                {"type": "notification.created", "data": notification_response(notification).model_dump(mode="json")},
            )
        return notification


def notification_response(value: Notification):
    """Map a notification model to the stable API response."""
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
