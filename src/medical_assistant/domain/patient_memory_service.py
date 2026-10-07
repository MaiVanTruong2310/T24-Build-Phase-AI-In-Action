"""Patient Memory Service: Quản trị bộ nhớ bệnh nhân liên phiên (Cross-session Memory).

Tích hợp phòng thủ OWASP ASI06 (Anti-Memory Poisoning / Indirect Prompt Injection):
1. Strict Schema & Key Whitelist: Chỉ cho phép các trường lâm sàng hợp lệ, chặn đứng việc lưu quyền VIP/chiết khấu/role.
2. Taint Status & Security Inspection: Dùng SecurityService kiểm duyệt nội dung trước khi nạp vào bộ nhớ.
3. Provenance & Confidence: Phân loại nguồn gốc dữ liệu (patient_reported vs verified_by_coordinator).
4. Time-to-Live (TTL): Tự động gán hạn sử dụng cho triệu chứng cấp tính (14 ngày), giữ vĩnh viễn dị ứng/mãn tính.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert

from src.db.session import get_session_factory
from src.medical_assistant.domain.security.security_guardrail_service import get_security_guardrail_service
from src.models.patient_memory import PatientMemoryItem, PatientOpenLoop

logger = logging.getLogger(__name__)

# Danh mục Key được phép lưu trữ (Whitelist)
ALLOWED_MEMORY_CATEGORIES = {
    "symptom_history",     # Tiền sử triệu chứng các đợt trước
    "allergy",             # Dị ứng thuốc, thức ăn
    "chronic_condition",   # Bệnh lý nền (tiểu đường, huyết áp...)
    "facility_preference", # Cơ sở y tế quen thuộc / gần nhà
    "specialty_interest",  # Chuyên khoa hay thăm khám
}

# Các từ khóa tấn công đặc quyền bị cấm tuyệt đối (OWASP ASI06)
BANNED_POISON_KEYS = {
    "vip", "discount", "free", "admin", "role", "system_prompt",
    "override", "priority_bypass", "allow_all", "god_mode"
}


class PatientMemoryService:
    def __init__(self):
        self.sessionmaker = get_session_factory()
        self.security_service = get_security_guardrail_service()

    async def save_patient_fact(
        self,
        user_id: UUID | str,
        category: str,
        fact_key: str,
        fact_value: dict[str, Any],
        provenance: str = "patient_reported",
        source_session_id: str | None = None,
        ttl_days: int | None = None,
    ) -> bool:
        """Lưu một sự kiện y tế vào bộ nhớ dài hạn với kiểm duyệt an ninh OWASP ASI06."""
        if not user_id:
            return False

        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        cat_clean = category.lower().strip()
        key_clean = fact_key.lower().strip()

        # 1. Kiểm tra Whitelist & Banned Attack Keys
        if cat_clean not in ALLOWED_MEMORY_CATEGORIES:
            logger.warning("Rejected unwhitelisted memory category: %s", cat_clean)
            return False

        if any(banned in key_clean for banned in BANNED_POISON_KEYS):
            logger.error("OWASP ASI06 Alert: Blocked attempt to poison memory key '%s'", key_clean)
            return False

        # 2. Quét Taint qua Security Gateway (chống Indirect Injection)
        value_text = str(fact_value)
        sec_check = self.security_service.inspect_query(value_text)
        if not sec_check.is_safe:
            logger.error("OWASP ASI06 Alert: Payload detected in memory value for key '%s': %s", key_clean, sec_check.violation_type)
            return False

        # 3. Tính toán TTL
        valid_until = None
        if ttl_days:
            valid_until = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        elif cat_clean == "symptom_history":
            # Triệu chứng cấp tính mặc định hết hạn sau 14 ngày
            valid_until = datetime.now(timezone.utc) + timedelta(days=14)

        confidence = 1.0 if provenance == "verified_by_coordinator" else 0.7

        async with self.sessionmaker() as session:
            async with session.begin():
                stmt = insert(PatientMemoryItem).values(
                    user_id=u_id,
                    category=cat_clean,
                    fact_key=key_clean,
                    fact_value=fact_value,
                    provenance=provenance,
                    confidence=confidence,
                    taint_status="clean",
                    source_session_id=source_session_id,
                    valid_until=valid_until,
                ).on_conflict_do_update(
                    index_elements=["user_id", "fact_key"],
                    set_={
                        "fact_value": fact_value,
                        "provenance": provenance,
                        "confidence": confidence,
                        "valid_until": valid_until,
                        "updated_at": datetime.now(timezone.utc),
                    }
                )
                await session.execute(stmt)
                logger.info("Saved patient memory item: user=%s, key=%s, provenance=%s", u_id, key_clean, provenance)
                return True

    async def get_patient_profile(self, user_id: UUID | str) -> list[dict[str, Any]]:
        """Lấy danh sách các sự kiện y tế còn hiệu lực của bệnh nhân."""
        if not user_id:
            return []
        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        now = datetime.now(timezone.utc)

        async with self.sessionmaker() as session:
            stmt = select(PatientMemoryItem).where(
                PatientMemoryItem.user_id == u_id,
                PatientMemoryItem.taint_status == "clean",
                (PatientMemoryItem.valid_until.is_(None) | (PatientMemoryItem.valid_until > now))
            ).order_by(PatientMemoryItem.updated_at.desc())
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "category": r.category,
                    "fact_key": r.fact_key,
                    "fact_value": r.fact_value,
                    "provenance": r.provenance,
                    "confidence": r.confidence,
                }
                for r in rows
            ]

    async def create_open_loop(
        self,
        user_id: UUID | str,
        loop_type: str,
        payload: dict[str, Any],
        due_minutes: int | None = 15,
    ) -> UUID | None:
        """Tạo một việc dở dang (Open Loop) như giữ chỗ slot, chờ nạp thông tin..."""
        if not user_id:
            return None
        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        due_at = datetime.now(timezone.utc) + timedelta(minutes=due_minutes) if due_minutes else None

        async with self.sessionmaker() as session:
            async with session.begin():
                loop = PatientOpenLoop(
                    user_id=u_id,
                    loop_type=loop_type,
                    payload=payload,
                    status="open",
                    due_at=due_at,
                )
                session.add(loop)
                await session.flush()
                logger.info("Created open loop: user=%s, type=%s, id=%s", u_id, loop_type, loop.id)
                return loop.id

    async def get_active_open_loops(self, user_id: UUID | str) -> list[dict[str, Any]]:
        """Lấy các việc dở dang đang mở của bệnh nhân."""
        if not user_id:
            return []
        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        async with self.sessionmaker() as session:
            stmt = select(PatientOpenLoop).where(
                PatientOpenLoop.user_id == u_id,
                PatientOpenLoop.status == "open",
            ).order_by(PatientOpenLoop.created_at.desc())
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "id": str(r.id),
                    "loop_type": r.loop_type,
                    "payload": r.payload,
                    "due_at": r.due_at.isoformat() if r.due_at else None,
                }
                for r in rows
            ]

    async def resolve_open_loop(self, user_id: UUID | str, loop_type: str) -> int:
        """Đóng/giải quyết các open loop cùng loại (ví dụ người dùng đã đặt lịch thành công)."""
        if not user_id:
            return 0
        u_id = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        async with self.sessionmaker() as session:
            async with session.begin():
                stmt = update(PatientOpenLoop).where(
                    PatientOpenLoop.user_id == u_id,
                    PatientOpenLoop.loop_type == loop_type,
                    PatientOpenLoop.status == "open",
                ).values(status="resolved")
                res = await session.execute(stmt)
                return res.rowcount


_patient_memory_service: PatientMemoryService | None = None


def get_patient_memory_service() -> PatientMemoryService:
    global _patient_memory_service
    if _patient_memory_service is None:
        _patient_memory_service = PatientMemoryService()
    return _patient_memory_service
