"""Zalo Bot service for processing events, orchestrating LangGraph Medical Agent turns,
managing user account linking, and querying patient bookings.
"""

from __future__ import annotations

import hashlib
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.db.session import get_session_factory
from src.medical_assistant.api.routes import prepare_turn, run_turn
from src.medical_assistant.domain.schemas import ChatPatientProfile, ChatRequest
from src.models.user import User
from src.models.workbench import CoordinationCase
from src.models.zalo import ZaloUserMapping
from src.services.booking import BookingService
from src.zalo.client import ZaloBotClient
from src.zalo.schemas import ZaloWebhookPayload

logger = get_logger(__name__)


def normalize_vietnamese_phone(phone: str) -> str:
    """Normalize phone string into standard format."""
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("84") and len(digits) == 11:
        return "0" + digits[2:]
    return digits


class ZaloBotService:
    """Service to handle incoming Zalo events and format messages."""

    def __init__(self, client: ZaloBotClient | None = None) -> None:
        self.client = client or ZaloBotClient()

    async def handle_webhook_event(self, payload: ZaloWebhookPayload) -> dict:
        """Process webhook payload asynchronously from Zalo Bot Platform."""
        # Support both wrapped {"ok": true, "result": {...}} and flat {"event_name": "...", "message": {...}}
        result = payload.result
        if not result and payload.event_name:
            from src.zalo.schemas import ZaloWebhookResult

            result = ZaloWebhookResult(event_name=payload.event_name, message=payload.message)

        if not result:
            logger.info("Received verification ping or empty event in Zalo webhook: %s", payload.model_dump())
            return {"ok": True, "status": "ignored_no_result"}

        event_name = result.event_name
        msg = result.message

        if not msg:
            logger.info("Received event without message: %s", event_name)
            return {"ok": True, "event": event_name}

        chat_id = msg.chat.id
        sender_name = (msg.from_user.display_name or "bạn").strip()
        text = (msg.text or "").strip()

        logger.info(
            "Zalo event=%s chat_id=%s sender=%s text_length=%d",
            event_name,
            chat_id,
            sender_name,
            len(text),
        )

        if event_name == "message.text.received":
            await self._process_text_message(chat_id, sender_name, text)
        elif event_name == "message.unsupported.received":
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    f"Xin chào **{sender_name}**, hệ thống đã ghi nhận yêu cầu của bạn. "
                    "Để được hỗ trợ tốt nhất, bạn vui lòng liên hệ tổng đài CSKH hoặc đến trực tiếp phòng khám."
                ),
            )
        else:
            logger.debug("Unhandled Zalo event: %s", event_name)

        return {"ok": True}

    async def _get_or_create_mapping(
        self, session: AsyncSession, chat_id: str, sender_name: str
    ) -> tuple[ZaloUserMapping, User | None]:
        """Find or create Zalo user mapping and fetch linked User if present."""
        stmt = select(ZaloUserMapping).where(ZaloUserMapping.zalo_chat_id == chat_id)
        mapping = (await session.execute(stmt)).scalar_one_or_none()

        if mapping is None:
            mapping = ZaloUserMapping(
                zalo_chat_id=chat_id,
                zalo_display_name=sender_name,
            )
            session.add(mapping)
            await session.flush()
        elif mapping.zalo_display_name != sender_name and sender_name:
            mapping.zalo_display_name = sender_name
            await session.flush()

        user = None
        if mapping.user_id:
            user = await session.get(User, mapping.user_id)

        return mapping, user

    async def _process_text_message(self, chat_id: str, sender_name: str, text: str) -> None:
        """Handle incoming text message with commands, account linking, or AI Agent."""
        if not text:
            return

        async with get_session_factory()() as session:
            mapping, user = await self._get_or_create_mapping(session, chat_id, sender_name)

            # Command: /start
            if text.startswith("/start"):
                welcome_text = (
                    f"Xin chào **{sender_name}**! 👋\n\n"
                    "Tôi là **Trợ lý Y tế Thông minh AI20K (VCarePlus)**.\n\n"
                    "Tôi có thể hỗ trợ bạn:\n"
                    "• 🩺 Tư vấn sơ bộ triệu chứng sức khỏe (Triage ATS)\n"
                    "• 👨‍⚕️ Tìm kiếm chuyên khoa và bác sĩ phù hợp\n"
                    "• 📅 Đặt lịch khám và theo dõi lịch hẹn đã đặt\n\n"
                    "**Các lệnh hữu ích:**\n"
                    "• `/my_bookings` - Tra cứu các lịch khám đã đặt\n"
                    "• `/link <số_điện_thoại>` - Liên kết tài khoản bệnh nhân\n"
                    "• `/help` - Xem hướng dẫn sử dụng\n\n"
                    "Bạn có thể nhắn tin miêu tả triệu chứng ngay bây giờ để bắt đầu tư vấn!"
                )
                await self.client.send_message(chat_id=chat_id, text=welcome_text)
                return

            # Command: /help
            if text.startswith("/help"):
                help_text = (
                    "📖 **HƯỚNG DẪN SỬ DỤNG BOT Y TẾ**\n\n"
                    "1. **Tư vấn sức khỏe:** Bạn chỉ cần nhắn tin miêu tả triệu chứng (ví dụ: *Tôi bị đau đầu, sốt 38.5 độ từ tối qua*).\n"
                    "2. **Xem lịch hẹn:** Nhắn `/my_bookings` để xem lịch khám đã đặt trên web hoặc qua bot.\n"
                    "3. **Đồng bộ tài khoản:** Nhắn `/link <SĐT>` (ví dụ: `/link 0912345678`) để liên kết với hồ sơ đã có trên website.\n"
                    "4. **Cấp cứu khẩn cấp:** Trong trường hợp nguy kịch, vui lòng gọi ngay **115** hoặc đến bệnh viện gần nhất!"
                )
                await self.client.send_message(chat_id=chat_id, text=help_text)
                return

            # Command: /link <phone>
            if text.startswith("/link"):
                parts = text.split(maxsplit=1)
                if len(parts) < 2 or not parts[1].strip():
                    await self.client.send_message(
                        chat_id=chat_id,
                        text="⚠️ Vui lòng cung cấp số điện thoại theo cú pháp: `/link <số_điện_thoại>` (Ví dụ: `/link 0912345678`).",
                    )
                    return

                phone_raw = parts[1].strip()
                normalized_phone = normalize_vietnamese_phone(phone_raw)
                phone_patterns = [normalized_phone]
                if normalized_phone.startswith("0"):
                    phone_patterns.append("+84" + normalized_phone[1:])
                elif normalized_phone.startswith("84"):
                    phone_patterns.append("+" + normalized_phone)

                user_stmt = select(User).where(User.phone.in_(phone_patterns))
                found_user = (await session.execute(user_stmt)).scalars().first()

                if found_user:
                    mapping.user_id = found_user.id
                    mapping.phone = found_user.phone
                    await session.commit()
                    success_msg = (
                        f"✅ **Liên kết tài khoản thành công!**\n\n"
                        f"• Bệnh nhân: **{found_user.full_name or 'Bệnh nhân'}**\n"
                        f"• Số điện thoại: **{found_user.phone}**\n\n"
                        "Hồ sơ bệnh án và các lịch khám đã đặt trên website của bạn giờ đây đã được đồng bộ với Zalo! "
                        "Bạn có thể gõ `/my_bookings` để kiểm tra lịch khám."
                    )
                    await self.client.send_message(chat_id=chat_id, text=success_msg)
                else:
                    mapping.phone = normalized_phone
                    await session.commit()
                    msg = (
                        f"ℹ️ Đã ghi nhận số điện thoại: **{normalized_phone}**.\n\n"
                        "Chưa tìm thấy tài khoản đã đăng ký trên hệ thống với số này, nhưng hệ thống sẽ dùng số này để đặt lịch hẹn và lưu hồ sơ cho bạn trong các cuộc trò chuyện tiếp theo."
                    )
                    await self.client.send_message(chat_id=chat_id, text=msg)
                return

            # Command: /my_bookings or "xem lịch khám"
            if text.lower() in ("/my_bookings", "xem lịch khám", "lich kham", "lịch khám", "xem lich"):
                await self._handle_my_bookings(session, chat_id, mapping, user)
                return

            # Default: Dispatch to LangGraph AI Medical Assistant
            await self._handle_agent_chat_turn(session, chat_id, sender_name, mapping, user, text)

    async def _handle_my_bookings(
        self, session: AsyncSession, chat_id: str, mapping: ZaloUserMapping, user: User | None
    ) -> None:
        """Fetch and format appointments for the user."""
        user_id = user.id if user else mapping.user_id
        if not user_id and not mapping.phone:
            await self.client.send_message(
                chat_id=chat_id,
                text=(
                    "ℹ️ Bạn chưa liên kết tài khoản.\n\n"
                    "Vui lòng gửi lệnh: `/link <số_điện_thoại>` (ví dụ: `/link 0912345678`) "
                    "để tra cứu các lịch khám đã đặt trên website hoặc app!"
                ),
            )
            return

        status_text_map = {
            "pending_approval": "⏳ Chờ xác nhận",
            "confirmed": "✅ Đã xác nhận",
            "cancelled": "❌ Đã hủy",
            "rejected": "⛔ Đã từ chối",
            "completed": "🏁 Đã hoàn thành",
            "new": "⏳ Đang tiếp nhận",
            "contacting": "📞 Nhân viên đang liên hệ",
        }

        bookings_list: list[str] = []

        # 1. Query standard bookings if user_id exists
        if user_id:
            try:
                booking_service = BookingService(session)
                user_bookings = await booking_service.bookings.list_for_user(
                    user_id, status=None, offset=0, limit=5
                )
                for b in user_bookings:
                    time_str = b.starts_at.strftime("%H:%M ngày %d/%m/%Y") if b.starts_at else "Chưa xếp giờ"
                    st = status_text_map.get(b.status, b.status)
                    reason_str = b.reason or "Khám bệnh"
                    bookings_list.append(
                        f"📅 **Lịch hẹn #{str(b.id)[:8]}**\n"
                        f"• Thời gian: {time_str}\n"
                        f"• Trạng thái: {st}\n"
                        f"• Lý do/Nhu cầu: {reason_str}"
                    )
            except Exception as e:
                logger.warning("Error fetching bookings for user %s: %s", user_id, e)

        # 2. Query AI coordination cases if any
        try:
            case_conditions = []
            if user_id:
                case_conditions.append(CoordinationCase.patient_id == user_id)
            if mapping.phone:
                case_conditions.append(CoordinationCase.patient["phone"].astext == mapping.phone)

            if case_conditions:
                stmt = (
                    select(CoordinationCase)
                    .where(*case_conditions)
                    .order_by(CoordinationCase.created_at.desc())
                    .limit(5)
                )
                cases = (await session.execute(stmt)).scalars().all()
                for c in cases:
                    pref_date = (c.patient or {}).get("preferred_date") or c.created_at.strftime("%d/%m/%Y")
                    st = status_text_map.get(c.status, c.status)
                    symp = (c.ai_snapshot or {}).get("symptoms") or (c.patient or {}).get("notes") or "Yêu cầu đặt khám AI"
                    bookings_list.append(
                        f"📋 **Phiếu điều phối #{str(c.id)[:8]}**\n"
                        f"• Ngày dự kiến: {pref_date}\n"
                        f"• Trạng thái: {st}\n"
                        f"• Triệu chứng: {symp}"
                    )
        except Exception as e:
            logger.warning("Error fetching coordination cases: %s", e)

        if not bookings_list:
            await self.client.send_message(
                chat_id=chat_id,
                text="Hiện tại bạn chưa có lịch khám nào. Bạn có thể nhắn tin miêu tả triệu chứng để tôi tư vấn và hỗ trợ đặt lịch ngay!",
            )
            return

        summary_msg = "📋 **DANH SÁCH LỊCH KHÁM CỦA BẠN:**\n\n" + "\n\n---\n\n".join(bookings_list)
        await self.client.send_message(chat_id=chat_id, text=summary_msg)

    async def _handle_agent_chat_turn(
        self,
        session: AsyncSession,
        chat_id: str,
        sender_name: str,
        mapping: ZaloUserMapping,
        user: User | None,
        text: str,
    ) -> None:
        """Dispatch message to LangGraph Medical Assistant and format reply."""
        clean_chat_id = re.sub(r"[^A-Za-z0-9_-]", "_", chat_id)
        session_id = f"zalo_{clean_chat_id}"
        guest_token = hashlib.sha256(f"zalo:{chat_id}".encode()).hexdigest()

        # Build patient profile
        profile_name = user.full_name if user and user.full_name else (mapping.zalo_display_name or sender_name)
        profile_phone = user.phone if user and user.phone else (mapping.phone or "")

        chat_request = ChatRequest(
            message=text,
            session_id=session_id,
            patient_profile=ChatPatientProfile(name=profile_name, phone=profile_phone) if profile_phone else None,
            enable_citation=False,
        )

        try:
            payload, turn, chat_service = await prepare_turn(chat_request, user, session)
            result = await run_turn(chat_request, user, payload, turn, chat_service, guest_token)
        except Exception:
            logger.exception("Failed to execute LangGraph agent turn for Zalo chat_id=%s", chat_id)
            await self.client.send_message(
                chat_id=chat_id,
                text="Xin lỗi bạn, hệ thống AI đang bận xử lý dữ liệu y khoa hoặc gặp sự cố tạm thời. Vui lòng thử lại sau ít giây.",
            )
            return

        # Format Agent response for Zalo
        reply_text = self._format_agent_response(result)
        await self.client.send_message(chat_id=chat_id, text=reply_text)

    def _format_agent_response(self, result: dict) -> str:
        """Convert LangGraph agent output dictionary into formatted Zalo text."""
        raw_response = (result.get("response") or "").strip()
        is_emergency = result.get("is_emergency", False)
        ats_level = result.get("ats_level")
        quick_replies = result.get("quick_replies") or []
        suggested_dept = result.get("suggested_department") or result.get("suggested_department_name")
        candidate_specialties = result.get("candidate_specialties") or []

        parts: list[str] = []

        if is_emergency:
            parts.append(f"🚨 **CẢNH BÁO TÌNH HUỐNG KHẨN CẤP / CẤP CỨU (ATS CẤP {ats_level or 1})**")
            parts.append(raw_response)
            parts.append("\n👉 **Khuyến cáo:** Vui lòng gọi cấp cứu **115** hoặc tới cơ sở y tế gần nhất ngay lập tức!")
            return "\n\n".join(parts)

        parts.append(raw_response)

        # Department / Specialty recommendation highlight
        if suggested_dept:
            parts.append(f"🏥 **Chuyên khoa đề xuất:** {suggested_dept}")
        elif candidate_specialties and isinstance(candidate_specialties, list):
            names = [s.get("name") if isinstance(s, dict) else str(s) for s in candidate_specialties[:2]]
            if names:
                parts.append(f"🏥 **Chuyên khoa tham khảo:** {', '.join(names)}")

        # Quick replies formatting
        if quick_replies and isinstance(quick_replies, list):
            options = [f"• {opt}" for opt in quick_replies[:4] if opt]
            if options:
                parts.append("💡 *Gợi ý trả lời nhanh:*\n" + "\n".join(options))

        return "\n\n".join(parts)


async def send_zalo_notification_to_user(
    session: AsyncSession, user_id: UUID, title: str, message: str
) -> bool:
    """Send transactional notification message to user via Zalo if linked."""
    stmt = select(ZaloUserMapping).where(ZaloUserMapping.user_id == user_id)
    mapping = (await session.execute(stmt)).scalars().first()
    if not mapping or not mapping.zalo_chat_id:
        return False

    client = ZaloBotClient()
    if not client.is_configured:
        return False

    text = f"🔔 **{title}**\n\n{message}"
    resp = await client.send_message(chat_id=mapping.zalo_chat_id, text=text)
    return bool(resp.get("ok"))
