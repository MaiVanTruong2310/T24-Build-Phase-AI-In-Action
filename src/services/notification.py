"""Booking notification and reminder business rules."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from src.core.exceptions import NotFoundError
from src.models.booking import Booking
from src.models.notification import Notification
from src.repositories.notification import NotificationRepository


class NotificationService:
    """Create transactional booking notifications and process reminders."""

    def __init__(self, session) -> None:
        self.session = session
        self.notifications = NotificationRepository(session)

    async def create_for_booking_review(self, booking: Booking, status: str) -> None:
        """Create the decision notification and a reminder when confirmed."""
        now = datetime.now(UTC)
        if status == "confirmed":
            await self.notifications.add(
                Notification(
                    user_id=booking.user_id,
                    booking_id=booking.id,
                    kind="booking_confirmed",
                    status="delivered",
                    title="Lịch khám đã được duyệt",
                    message="Lịch khám của bạn đã được nhân viên xác nhận.",
                    dedupe_key=f"booking:{booking.id}:decision:confirmed",
                    available_at=now,
                    delivered_at=now,
                )
            )
            await self.notifications.add(
                Notification(
                    user_id=booking.user_id,
                    booking_id=booking.id,
                    kind="appointment_reminder",
                    status="pending",
                    title="Nhắc lịch khám",
                    message="Bạn có lịch khám sắp diễn ra. Vui lòng chuẩn bị trước giờ hẹn.",
                    dedupe_key=f"booking:{booking.id}:reminder:24h",
                    available_at=booking.starts_at - timedelta(hours=24),
                )
            )
        elif status == "rejected":
            await self.notifications.add(
                Notification(
                    user_id=booking.user_id,
                    booking_id=booking.id,
                    kind="booking_rejected",
                    status="delivered",
                    title="Lịch khám chưa được duyệt",
                    message=booking.staff_note or "Lịch khám chưa được nhân viên xác nhận.",
                    dedupe_key=f"booking:{booking.id}:decision:rejected",
                    available_at=now,
                    delivered_at=now,
                )
            )

        # Trigger Zalo notification if patient linked Zalo Bot
        try:
            from src.zalo.service import send_zalo_notification_to_user

            if status == "confirmed":
                time_str = (
                    booking.starts_at.strftime("%H:%M ngày %d/%m/%Y")
                    if booking.starts_at
                    else "Theo thông báo"
                )
                await send_zalo_notification_to_user(
                    self.session,
                    booking.user_id,
                    "Lịch khám đã được duyệt ✅",
                    f"Lịch khám của bạn (Mã: #{str(booking.id)[:8]}) đã được nhân viên y tế xác nhận thành công!\nThời gian: {time_str}.",
                )
            elif status == "rejected":
                await send_zalo_notification_to_user(
                    self.session,
                    booking.user_id,
                    "Thông báo về lịch khám ⚠️",
                    booking.staff_note or "Lịch khám của bạn chưa được nhân viên xác nhận.",
                )
        except Exception:
            pass

    async def list_for_user(self, user_id: UUID, *, unread_only: bool, offset: int, limit: int) -> list[Notification]:
        """List notifications owned by a user."""
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
        """Mark all owned delivered notifications as read."""
        async with self.session.begin():
            return await self.notifications.mark_all_read(user_id, datetime.now(UTC))

    async def discard_reminders_for_booking(self, booking_id: UUID) -> int:
        """Invalidate reminders for a booking whose time is changing."""
        return await self.notifications.discard_reminders_for_booking(booking_id, datetime.now(UTC))

    async def process_due_reminders(self, limit: int = 100) -> int:
        """Deliver or discard due reminder rows in one transaction."""
        async with self.session.begin():
            notifications = await self.notifications.claim_due_reminders(datetime.now(UTC), limit)
        return sum(notification.status == "delivered" for notification in notifications)


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
