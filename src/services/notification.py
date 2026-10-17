"""Booking notification and reminder business rules."""

import asyncio
import logging
import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from src.config import get_settings
from src.core.exceptions import NotFoundError
from src.models.booking import Booking
from src.models.doctor import Doctor
from src.models.facility import Facility
from src.models.notification import Notification
from src.models.service import Service
from src.models.specialty import Specialty
from src.models.user import User
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
        context = await self.appointment_context(booking)
        if status == "confirmed":
            await self._create_in_app_notification(
                user_id=booking.user_id,
                booking_id=booking.id,
                kind="booking_confirmed",
                title="Lịch khám đã được xác nhận",
                message=f"Lịch khám của bạn đã được xác nhận.\n{context}",
                dedupe_key=f"booking:{booking.id}:decision:confirmed",
                available_at=now,
                status="delivered",
            )
            await self._create_in_app_notification(
                user_id=booking.user_id,
                booking_id=booking.id,
                kind="appointment_reminder",
                title="Nhắc lịch khám",
                message=f"Bạn sắp đến lịch khám.\n{context}\nVui lòng có mặt trước giờ hẹn.",
                dedupe_key=f"booking:{booking.id}:reminder:24h",
                available_at=booking.starts_at - timedelta(hours=24),
                status="pending",
            )
            patient = await self.session.get(User, booking.user_id)
            if patient and patient.email:
                await self._create_email_notification(
                    user_id=booking.user_id,
                    booking_id=booking.id,
                    recipient=patient.email,
                    title="Lịch khám đã được xác nhận",
                    message=f"Lịch khám của bạn đã được xác nhận.\n{context}",
                    dedupe_key=f"booking:{booking.id}:decision:confirmed:email",
                    available_at=now,
                )
        elif status == "rejected":
            await self._create_in_app_notification(
                user_id=booking.user_id,
                booking_id=booking.id,
                kind="booking_rejected",
                title="Lịch khám chưa được duyệt",
                message=f"Lịch khám chưa được xác nhận.\n{context}\nLý do: {booking.staff_note or 'Chưa có thông tin lý do.'}",
                dedupe_key=f"booking:{booking.id}:decision:rejected",
                available_at=now,
                status="delivered",
            )

    async def create_for_booking_expired(self, booking: Booking) -> None:
        """Notify a patient when a pending booking misses its review deadline."""
        now = datetime.now(UTC)
        context = await self.appointment_context(booking)
        await self._create_in_app_notification(
            user_id=booking.user_id,
            booking_id=booking.id,
            kind="booking_expired",
            title="Lịch khám đã hết hạn",
            message=f"Yêu cầu đặt lịch chưa được duyệt trong 24 giờ nên đã hết hạn.\n{context}",
            dedupe_key=f"booking:{booking.id}:expired",
            available_at=now,
            status="delivered",
        )

    async def create_for_booking_cancelled(self, booking: Booking, reason: str) -> None:
        """Notify the patient after staff cancels a confirmed appointment."""
        context = await self.appointment_context(booking)
        await self._create_in_app_notification(
            user_id=booking.requested_by_user_id or booking.user_id,
            booking_id=booking.id,
            kind="booking_cancelled",
            title="Lịch khám đã bị hủy",
            message=f"Lịch khám đã bị hủy.\n{context}\nLý do: {reason}",
            dedupe_key=f"booking:{booking.id}:decision:cancelled",
            available_at=datetime.now(UTC),
            status="delivered",
        )

    async def appointment_context(self, booking: Booking) -> str:
        """Build patient-facing appointment details without exposing intake notes."""
        start = booking.starts_at
        end = booking.ends_at
        start = (start if start.tzinfo else start.replace(tzinfo=UTC)).astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        end = (end if end.tzinfo else end.replace(tzinfo=UTC)).astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        doctor = await self.session.get(Doctor, booking.doctor_id)
        facility = await self.session.get(Facility, booking.facility_id)
        specialty = await self.session.get(Specialty, booking.specialty_id)
        service = await self.session.get(Service, booking.service_id) if booking.service_id else None
        encounter = "Trực tuyến" if booking.encounter_type == "telehealth" else "Trực tiếp"
        return "\n".join(
            (
                f"Thời gian: {start:%H:%M %d/%m/%Y} – {end:%H:%M} (giờ Việt Nam)",
                f"Bác sĩ: {doctor.full_name if doctor else 'Chưa cập nhật'}",
                f"Chuyên khoa: {specialty.name if specialty else 'Chưa cập nhật'}",
                f"Dịch vụ: {service.name if service else 'Khám riêng'}",
                f"Hình thức: {encounter}",
                f"Cơ sở: {facility.name if facility else 'Chưa cập nhật'}",
            )
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

    async def process_due_emails(self, limit: int = 20) -> int:
        settings = get_settings()
        if not (settings.gmail_smtp_username and settings.gmail_smtp_password and settings.gmail_from_email):
            return 0
        async with self.session.begin():
            now = datetime.now(UTC)
            notifications = await self.notifications.claim_due_emails(
                now,
                now - timedelta(seconds=settings.notification_processing_timeout_seconds),
                limit,
            )
            messages = [
                (item.id, item.recipient_email, item.title, item.message, item.attempt_count) for item in notifications
            ]
        delivered = 0
        for notification_id, recipient, title, body, attempt in messages:
            sent = False
            if recipient and attempt <= settings.notification_max_attempts:
                try:
                    await asyncio.to_thread(_send_gmail, settings, recipient, title, body)
                    sent = True
                except Exception:
                    logging.getLogger(__name__).warning("notification.email.delivery_failed")
            async with self.session.begin():
                item = await self.session.get(Notification, notification_id, with_for_update=True)
                if item is None or item.status != "processing":
                    continue
                if sent:
                    item.status = "delivered"
                    item.delivered_at = datetime.now(UTC)
                    item.last_error = None
                    item.processing_at = None
                    delivered += 1
                elif attempt >= settings.notification_max_attempts:
                    item.status = "dead_letter"
                    item.last_error = "delivery_failed" if recipient else "recipient_missing"
                    item.processing_at = None
                else:
                    delay = min(
                        settings.notification_retry_backoff_seconds * (2 ** (attempt - 1)),
                        settings.notification_retry_backoff_max_seconds,
                    )
                    item.status = "pending"
                    item.available_at = datetime.now(UTC) + timedelta(seconds=delay)
                    item.last_error = "delivery_failed" if recipient else "recipient_missing"
                    item.processing_at = None
        return delivered

    async def _create_email_notification(
        self,
        *,
        user_id: UUID,
        booking_id: UUID,
        recipient: str,
        title: str,
        message: str,
        dedupe_key: str,
        available_at: datetime,
    ) -> None:
        await self.notifications.add(
            Notification(
                id=uuid4(),
                user_id=user_id,
                booking_id=booking_id,
                kind="booking_confirmed",
                channel="email",
                recipient_email=recipient,
                status="pending",
                title=title,
                message=message,
                dedupe_key=dedupe_key,
                available_at=available_at,
            )
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


def _send_gmail(settings, recipient: str, title: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = f"{settings.gmail_from_name} <{settings.gmail_from_email}>"
    message["To"] = recipient
    message["Subject"] = title
    message.set_content(body)
    with smtplib.SMTP(settings.gmail_smtp_host, settings.gmail_smtp_port, timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(settings.gmail_smtp_username, settings.gmail_smtp_password)
        smtp.send_message(message)
