"""GĐ2 kế hoạch khớp có dấu: xử lý lần khớp cấp cứu MƠ HỒ (accent_matcher.AMBIGUOUS) và trả lời có/không.

Khi bộ luật chỉ khớp được nhờ chữ không dấu vốn là từ khác ("toi ho nhieu cung voi mat ngu": "voi" = với/vôi),
bác sĩ duyệt: dấu bị bỏ vẫn khớp VỚI ĐIỀU KIỆN LLM dịch ra được nghĩa hợp ngữ cảnh. Vì vậy:
  1. LLM khôi phục dấu cho tin nhắn. Kiểm tra bằng code: bỏ dấu bản LLM phải TRÙNG TỪNG CHỮ với tin gốc
     (LLM chỉ được thêm dấu, không thêm/bớt/đổi từ) — không đạt thì coi như LLM không giúp được.
  2. Bộ luật tất định đánh giá lại câu đã có dấu:
       cấp cứu chắc chắn → cấp cứu đầy đủ; không cấp cứu → tư vấn tiếp với câu đã có dấu; vẫn mơ hồ → hỏi xác nhận.
  3. Không có LLM / LLM không đạt → hỏi xác nhận: hướng dẫn 115 CÓ ĐIỀU KIỆN + nút Có/Không (không hạ mức im lặng).
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from src.medical_assistant.domain.accent_matcher import AMBIGUOUS, strip_marks

logger = logging.getLogger(__name__)

RESTORE_TIMEOUT_S = 8.0
RESTORE_SYSTEM = (
    "Bạn khôi phục dấu tiếng Việt cho tin nhắn bệnh nhân gửi chatbot y tế. CHỈ thêm dấu thanh và dấu chữ "
    "(ă â ê ô ơ ư đ) cho đúng nghĩa hợp ngữ cảnh; KHÔNG thêm, bớt, đổi, đảo từ; giữ nguyên chữ số và dấu câu. "
    "Từ viết tắt/teencode giữ nguyên. Chỉ trả về đúng câu đã thêm dấu, không giải thích."
)


def _letters(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", strip_marks(unicodedata.normalize("NFC", text or "").lower()))


def restoration_is_faithful(original: str, restored: str) -> bool:
    """Bản khôi phục chỉ được khác tin gốc ở dấu: bỏ dấu hai bên phải ra cùng một dãy chữ/số."""
    return bool(restored.strip()) and _letters(original) == _letters(restored)


async def restore_diacritics(text: str, llm: Any = None) -> str | None:
    """LLM thêm dấu; None khi không có LLM, quá thời gian, hoặc LLM sửa nội dung (không chỉ thêm dấu)."""
    try:
        if llm is None:
            from src.medical_assistant.infrastructure.llm import get_llm

            llm = get_llm()
        msg = await asyncio.wait_for(llm.ainvoke([("system", RESTORE_SYSTEM), ("user", text)]), RESTORE_TIMEOUT_S)
        restored = str(getattr(msg, "content", msg) or "").strip().strip('"').strip()
    except Exception as exc:  # LLM lỗi/timeout không được làm hỏng lượt chat: rơi về hỏi xác nhận
        logger.warning("diacritic restore unavailable: %s", type(exc).__name__)
        return None
    if not restoration_is_faithful(text, restored):
        logger.warning("diacritic restore rejected (content changed)")
        return None
    return restored


@dataclass
class AmbiguityDecision:
    kind: str  # "emergency" | "clear" | "confirm"
    result: Any  # TriageEvaluationResult dùng cho quyết định
    restored: str | None = None


RULE_OUT_SYSTEM = (
    "Bạn là điều dưỡng phân loại cấp cứu. Tin nhắn bệnh nhân gõ KHÔNG DẤU nên có thể đọc theo nhiều nghĩa. "
    "Câu hỏi: có CÁCH ĐỌC HỢP LÝ NÀO cho thấy người bệnh đang có dấu hiệu cấp cứu được nêu không? "
    "Trả lời đúng một từ: CO (có thể), KHONG (chắc chắn không), hoặc KHONG_CHAC."
)


async def llm_rules_out(original: str, flag: str, llm: Any = None) -> bool:
    """Bằng chứng thứ hai để gỡ cảnh báo: LLM phải khẳng định KHÔNG có cách đọc nào là cấp cứu (mọi lỗi = False).

    Lý do: một lần khôi phục dấu có thể chọn sai nghĩa ("ong dot sung moi kho tho" → "sưng mới" thay vì "sưng môi")."""
    try:
        if llm is None:
            from src.medical_assistant.infrastructure.llm import get_llm

            llm = get_llm()
        msg = await asyncio.wait_for(
            llm.ainvoke([("system", RULE_OUT_SYSTEM), ("user", f"Tin nhắn: {original}\nDấu hiệu cấp cứu: {flag}")]),
            RESTORE_TIMEOUT_S,
        )
        answer = strip_marks(str(getattr(msg, "content", msg) or "")).strip().upper()
    except Exception as exc:
        logger.warning("ambiguity rule-out unavailable: %s", type(exc).__name__)
        return False
    return re.match(r"^KHONG\b(?!_?\s*CHAC)", answer) is not None


async def resolve_ambiguous_emergency(
    triage_svc, query: str, messages: list[dict] | None, language: str = "vi", llm: Any = None
) -> AmbiguityDecision:
    """Gọi khi cổng cấp cứu khớp ở mức MƠ HỒ.

    Chỉ "clear" khi CẢ HAI: (1) câu khôi phục dấu không còn cấp cứu theo bộ luật, (2) LLM khẳng định không có cách
    đọc nào là cấp cứu. Thiếu một trong hai → hỏi người dùng xác nhận (không bao giờ gỡ cảnh báo trên một bằng chứng)."""
    current = triage_svc.evaluate_with_recent_context(query, messages, language=language)
    # Câu quá ngắn ("khó thở", "co giật": BS duyệt mục 9) mơ hồ vì THIẾU DỮ KIỆN, không vì thiếu dấu → khôi phục dấu
    # vô ích (~0,7s một lần gọi LLM): hỏi người dùng luôn.
    if any(str(r).startswith("SHORT_") for r in (current.triggered_rule_ids or [])):
        return AmbiguityDecision("confirm", current)
    restored = await restore_diacritics(query, llm)
    if restored is None:
        return AmbiguityDecision("confirm", current)
    again = triage_svc.evaluate_with_recent_context(restored, messages, language=language)
    if again.is_emergency and again.match_confidence != AMBIGUOUS:
        return AmbiguityDecision("emergency", again, restored)
    if not again.is_emergency:
        # ATS 1 (hồi sức) không bao giờ gỡ chỉ dựa vào LLM: eval từng có lần LLM đọc "vân tim" (tím) của trẻ 10 tuần
        # sốc thành không cấp cứu → luôn hỏi người dùng xác nhận (kèm hướng dẫn 115 có điều kiện).
        if int(current.ats_level or 5) == 1:
            return AmbiguityDecision("confirm", current, restored)
        flag = (current.triggered_red_flags or ["dấu hiệu nguy hiểm"])[0]
        if await llm_rules_out(query, flag, llm):
            return AmbiguityDecision("clear", again, restored)
        return AmbiguityDecision("confirm", current, restored)
    return AmbiguityDecision("confirm", again, restored)


# ---------------------------------------------------------------------------------------------------------------------
# Trả lời Có / Không cho câu hỏi xác nhận (cấp cứu mơ hồ, đề nghị gặp điều phối viên). So khớp NGUYÊN câu đã chuẩn hóa
# (không so chuỗi con: "khám" chứa "k" không được hiểu là "không").
_YES = re.compile(
    r"^(?:có|co|đúng|dung|phải|phai|đúng rồi|dung roi|phải rồi|phai roi|vâng|vang|dạ|da|ừ|u|ok|oke|okay|yes|yep|"
    r"đồng ý|dong y|có ạ|co a|dạ có|da co|đúng vậy|dung vay|đang bị|dang bi|có, đang bị như vậy|"
    r"co, dang bi nhu vay|yêu cầu hỗ trợ|yeu cau ho tro|chuyển đi|chuyen di|gặp nhân viên|gap nhan vien)$"
)
_NO = re.compile(
    r"^(?:không|khong|ko|k|không phải|khong phai|ko phải|ko phai|sai|không đúng|khong dung|chưa|chua|"
    r"no|nope|thôi|thoi|không cần|khong can|thôi không cần|thoi khong can|không ạ|khong a|dạ không|da khong)$"
)


def parse_yes_no(text: str) -> str | None:
    """'yes' | 'no' | None (không rõ) — cho câu trả lời ngắn của nút Có/Không hoặc gõ tay."""
    t = re.sub(r"[.!?…,]+$", "", re.sub(r"\s+", " ", unicodedata.normalize("NFC", text or "").strip().lower()))
    if _YES.match(t):
        return "yes"
    if _NO.match(t):
        return "no"
    return None


# ---------------------------------------------------------------------------------------------------------------------
# Phương án cuối: gợi ý gặp điều phối viên khi AI bế tắc nhiều lượt liên tiếp (mục tiêu chính vẫn là GIẢM tải cho
# điều phối viên, nên ngưỡng đủ cao và chỉ tính lượt AI thật sự không hiểu/không giúp được).
STUCK_THRESHOLD = 3
STUCK_STATUSES = {"VISIT_PURPOSE_CLARIFICATION", "INFO_UNAVAILABLE", "EMERGENCY_CONFIRM"}
NEVER_OFFER_STATUSES = {
    "EMERGENCY",
    "HUMAN_HELP_REQUESTED",
    "HITL_AWAITING_CONFIRMATION",
    "HITL_ESCALATED_COORDINATOR",
    "HITL_DECLINED_CONVERSATIONAL",
    "BOOKING_CONTACT_REQUIRED",
    "SAFETY_REVIEW",
    "EMERGENCY_CONFIRM",  # lượt hỏi xác nhận cấp cứu: không được thay hướng dẫn 115 bằng lời gợi ý khác
}


def is_stuck_turn(workflow_status: str, meta: dict, repeated_question: bool, misunderstood: bool) -> bool:
    """Lượt AI không giúp được: tin nhắn không đọc được, phải hỏi lại mục đích, không tra được thông tin,
    hỏi lại y nguyên câu cũ, hoặc tự nhận chưa hiểu. Lạc đề (nói chuyện khác) KHÔNG tính: đó không phải bế tắc."""
    return bool(
        meta.get("off_topic") == "gibberish" or workflow_status in STUCK_STATUSES or repeated_question or misunderstood
    )


def next_stuck_streak(previous: int, stuck: bool) -> int:
    return previous + 1 if stuck else 0


OFFER_TEXT = {
    "vi": "Dạ, em xin lỗi vì chưa hỗ trợ được bác qua tin nhắn. Bác có muốn em chuyển cuộc trò chuyện tới điều phối "
    "viên y tế để được hỗ trợ trực tiếp không ạ?",
    "en": "Sorry I couldn't help over chat. Would you like me to forward this conversation to a medical coordinator "
    "for direct support?",
}
OFFER_REPLIES = {"vi": ["Có", "Không"], "en": ["Yes", "No"]}


def coordinator_offer(
    previous_streak: int,
    workflow_status: str,
    meta: dict,
    *,
    repeated_question: bool = False,
    misunderstood: bool = False,
    is_emergency: bool = False,
    lang: str = "vi",
) -> tuple[int, dict | None]:
    """(số lượt bế tắc mới, phần ghi đè câu trả lời nếu đến lúc gợi ý gặp điều phối viên).

    Ghi đè dùng lại luồng HITL có sẵn: HITL_AWAITING_CONFIRMATION → "Có" = HITL_ESCALATED_COORDINATOR (bàn điều
    phối nhận ca), "Không" = HITL_DECLINED_CONVERSATIONAL ("còn câu hỏi nào khác không")."""
    stuck = not is_emergency and is_stuck_turn(workflow_status, meta, repeated_question, misunderstood)
    streak = next_stuck_streak(previous_streak, stuck)
    if streak < STUCK_THRESHOLD or is_emergency or workflow_status in NEVER_OFFER_STATUSES:
        return streak, None
    key = lang if lang in OFFER_TEXT else "vi"
    return 0, {
        "response": OFFER_TEXT[key],
        "quick_replies": list(OFFER_REPLIES[key]),
        "workflow_status": "HITL_AWAITING_CONFIRMATION",
    }
