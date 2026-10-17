"""LLM được NÂNG lên cấp cứu (không bao giờ hạ) khi bộ luật tất định bỏ sót.

Bộ luật chạy trước (zero-token, không phụ thuộc LLM) nhưng thiếu từ vựng (phương ngữ, cách kể lạ). LLM đọc hiểu
được, nên safety_concern có severity="emergency" được dùng như lưới an toàn thứ hai, với 3 điều kiện chống ảo giác:
  1. severity == "emergency" (tiêu chí ATS 1-2 ghi trong prompt hybrid_dialogue_service, mục 6)
  2. evidence là trích dẫn có thật trong lời người dùng (so khớp sau khi bỏ dấu + quy đổi phương ngữ)
  3. câu không phải câu hỏi kiến thức / giả định ("nếu…", "dấu hiệu … là gì", "cách sơ cứu")
"""

from __future__ import annotations

import re
from typing import Any

from src.medical_assistant.domain.ats_descriptor_service import strip_accents
from src.medical_assistant.domain.disease_triage import ATSLevel, UrgencyTier
from src.medical_assistant.domain.language_service import get_emergency_guidance
from src.medical_assistant.domain.text_normalization import canonicalize_for_matching

# category → (tên cờ hiển thị, chuyên khoa); tên bám nhãn của luật tất định tương ứng
CATEGORY_FLAGS: dict[str, tuple[str, str]] = {
    "self_harm": ("Nguy cơ tự hại / khủng hoảng tâm lý", "Cấp cứu"),
    "bleeding": ("Chảy máu nặng không cầm", "Cấp cứu"),
    "breathing": ("Suy hô hấp", "Nội hô hấp"),
    "neuro": ("Dấu hiệu thần kinh khu trú cấp (nghi đột quỵ / TIA)", "Thần kinh"),
    "chest": ("Đau ngực nghi do tim", "Trung tâm Tim mạch"),
    "consciousness": ("Rối loạn ý thức", "Cấp cứu"),
    "seizure": ("Co giật", "Thần kinh"),
    "allergy": ("Phản vệ", "Cấp cứu"),
    "trauma": ("Chấn thương nặng", "Cấp cứu"),
    "poisoning": ("Ngộ độc / quá liều", "Cấp cứu"),
    "pregnancy": ("Cấp cứu sản khoa", "Sản phụ khoa"),
    "other": ("Dấu hiệu nguy hiểm cần cấp cứu", "Cấp cứu"),
}
_HYPOTHETICAL = re.compile(
    r"\b(?:neu|gia su|lo nhu|phong khi)\b|\bla gi\b|\bthe nao (?:la|thi)\b|\bcach so cuu\b|\bhoi truoc\b"
    r"|\btap huan\b|\bphong ngua\b|\bnhan biet\b"
)


def _tokens(text: str) -> list[str]:
    """Từ đã quy đổi phương ngữ, bỏ dấu, bỏ dấu câu."""
    return re.sub(r"[^\w\s]", " ", strip_accents(canonicalize_for_matching(text or "").lower())).split()


def evidence_in_text(evidence: str | None, user_texts: list[str]) -> bool:
    """Trích dẫn có thật: cụm liên tiếp có trong lời người dùng, hoặc ≥ 80% từ (LLM đôi khi bỏ hư từ)."""
    ev = _tokens(evidence or "")
    if len(ev) < 2:
        return False
    hay = _tokens(" ".join(user_texts))
    joined_hay, joined_ev = f" {' '.join(hay)} ", f" {' '.join(ev)} "
    if joined_ev in joined_hay:
        return True
    vocab = set(hay)
    return sum(t in vocab for t in ev) / len(ev) >= 0.8


def llm_emergency_escalation(v2_response: Any, query: str, user_texts: list[str], language: str = "vi") -> dict | None:
    """Trả về các trường cập nhật TriageEvaluationResult để nâng lên cấp cứu, hoặc None."""
    if v2_response is None:
        return None
    if _HYPOTHETICAL.search(" ".join(_tokens(query))):
        return None
    for concern in getattr(v2_response, "safety_concerns", None) or []:
        if getattr(concern, "severity", "urgent") != "emergency":
            continue
        if not evidence_in_text(concern.evidence, [*user_texts, query]):
            continue
        category = getattr(concern, "category", "other")
        flag, specialty = CATEGORY_FLAGS.get(category, CATEGORY_FLAGS["other"])
        return {
            "is_emergency": True,
            "ats_level": ATSLevel.LEVEL_2_EMERGENT,
            "urgency_tier": UrgencyTier.EMERGENCY_BLOCK,
            "max_booking_days": 0,
            "care_setting": "EMERGENCY_DEPT",
            "triggered_red_flags": [flag],
            "triggered_rule_ids": [f"LLM_SAFETY_ESCALATION:{category}"],
            "suggested_specialty": specialty,
            "patient_guidance": get_emergency_guidance(
                flag_name=flag, specialty=specialty, ats_level=2, language=language
            ),
        }
    return None
