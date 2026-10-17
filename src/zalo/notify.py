"""Đẩy hoạt động của Bàn điều phối về Zalo (best-effort, không bao giờ chặn hay làm hỏng thao tác của điều phối viên).

- Ca có phiên `zalo_<chat_id>` (bệnh nhân đang nhắn qua Zalo): tin nhắn điều phối viên gửi trong Workbench được chuyển
  thẳng tới Zalo — trên web khung chat tự tải lại, còn Zalo thì phải đẩy.
- Ca chuyển sang `confirmed` / `cancelled`: báo cho bệnh nhân qua Zalo (phiên Zalo, hoặc tài khoản web đã `/link`).
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select

from src.core.logging import get_logger
from src.zalo.client import ZaloBotClient

logger = get_logger(__name__)

ZALO_SESSION_PREFIX = "zalo_"
STATUS_MESSAGES = {
    "confirmed": "✅ **Lịch khám của bạn đã được xác nhận**",
    "cancelled": "❌ **Yêu cầu đặt lịch của bạn đã được hủy**",
}
VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
_PENDING: set[asyncio.Task] = set()  # giữ tham chiếu để task nền không bị thu gom giữa chừng


def schedule_case_notification(case: Any, previous_status: str | None, message: Any | None = None) -> None:
    """Gọi SAU khi thao tác Workbench đã commit. Chụp giá trị cần dùng rồi giao việc gửi cho task nền.
    Không bao giờ ném lỗi ra ngoài: Zalo hỏng không được làm hỏng thao tác của điều phối viên."""
    try:
        _schedule(case, previous_status, message)
    except Exception:
        logger.exception("Không lên lịch được thông báo Zalo cho ca %s", getattr(case, "id", None))


def _schedule(case: Any, previous_status: str | None, message: Any | None) -> None:
    if not ZaloBotClient().is_configured:
        return
    coordinator_text = None
    if message is not None and getattr(message, "sender", None) == "coordinator":
        if getattr(message, "_created_by_request", True):  # gửi lại cùng client_id → không đẩy lần hai
            coordinator_text = str(getattr(message, "body", "") or "").strip() or None
    status_changed = case.status != previous_status and case.status in STATUS_MESSAGES
    if not coordinator_text and not status_changed:
        return
    task = asyncio.create_task(
        _deliver(
            case_id=case.id,
            session_id=case.session_id,
            patient_id=case.patient_id,
            booking_id=case.booking_id,
            status=case.status if status_changed else None,
            coordinator_text=coordinator_text,
        )
    )
    _PENDING.add(task)
    task.add_done_callback(_PENDING.discard)


async def _deliver(
    *,
    case_id: UUID,
    session_id: str | None,
    patient_id: UUID | None,
    booking_id: UUID | None,
    status: str | None,
    coordinator_text: str | None,
) -> None:
    from src.db.session import get_session_factory
    from src.models.zalo import ZaloUserMapping

    try:
        async with get_session_factory()() as db:
            chat_id = None
            from_zalo_session = bool(session_id and session_id.startswith(ZALO_SESSION_PREFIX))
            if from_zalo_session:
                raw = session_id[len(ZALO_SESSION_PREFIX) :]
                # Chỉ gửi tới chat_id đã thực sự nhắn bot (chống giả mạo session_id)
                chat_id = (
                    await db.execute(select(ZaloUserMapping.zalo_chat_id).where(ZaloUserMapping.zalo_chat_id == raw))
                ).scalar_one_or_none()
            if chat_id is None and patient_id is not None:
                chat_id = (
                    await db.execute(
                        select(ZaloUserMapping.zalo_chat_id).where(ZaloUserMapping.user_id == patient_id).limit(1)
                    )
                ).scalar_one_or_none()
            if chat_id is None:
                return

            client = ZaloBotClient()
            # Tin nhắn trò chuyện chỉ chuyển khi bệnh nhân đang nhắn qua Zalo (người dùng web xem trên web)
            if coordinator_text and from_zalo_session:
                await client.send_message(chat_id=chat_id, text=f"💬 **Điều phối viên Vinmec:**\n{coordinator_text}")
            if status:
                text = STATUS_MESSAGES[status] + f"\nMã phiếu: #{str(case_id)[:8]}"
                if status == "confirmed" and booking_id:
                    text += await _booking_details(db, booking_id)
                if status == "cancelled":
                    text += "\nNếu cần, bạn có thể nhắn tin để đặt lại lịch khám mới."
                await client.send_message(chat_id=chat_id, text=text)
    except Exception:
        logger.exception("Không gửi được thông báo Zalo cho ca %s", case_id)


async def _booking_details(db: Any, booking_id: UUID) -> str:
    from src.models.booking import Booking
    from src.models.doctor import Doctor
    from src.models.facility import Facility

    booking = await db.get(Booking, booking_id)
    if booking is None:
        return ""
    doctor = await db.get(Doctor, booking.doctor_id) if booking.doctor_id else None
    facility = await db.get(Facility, booking.facility_id) if booking.facility_id else None
    lines = []
    if booking.starts_at:
        lines.append(f"• Thời gian: {booking.starts_at.astimezone(VN_TZ).strftime('%H:%M ngày %d/%m/%Y')}")
    if doctor is not None:
        lines.append(f"• Bác sĩ: {doctor.full_name}")
    if facility is not None:
        lines.append(f"• Cơ sở: {facility.name}")
    return ("\n" + "\n".join(lines)) if lines else ""
