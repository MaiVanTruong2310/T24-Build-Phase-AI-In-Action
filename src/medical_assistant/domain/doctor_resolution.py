"""Xác định bác sĩ người dùng nêu tên ("bác si Nguyên Thị Nga") dựa trên dữ liệu thật.

Tên có thể đến từ regex hoặc LLM; chỉ dùng khi khớp bác sĩ trong DB, không bao giờ dùng tên LLM tự nghĩ ra.
Nhiều bác sĩ trùng đúng họ tên → trả về danh sách để người dùng chọn, không tự chọn thay
(chức danh như "nội trú" chỉ dùng để xếp người khớp lên đầu).
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.medical_assistant.domain.booking_slot_service import remove_accents

logger = logging.getLogger(__name__)


def _fold(text: str) -> str:
    return " ".join(remove_accents((text or "").lower()).split())


@dataclass
class DoctorResolution:
    query_name: str
    candidates: list[dict[str, Any]] = field(default_factory=list)
    exact: bool = False  # các ứng viên khớp đúng cả họ tên (không chỉ chứa chuỗi)
    data_unavailable: bool = False

    @property
    def unique(self) -> dict[str, Any] | None:
        return self.candidates[0] if len(self.candidates) == 1 else None


def name_supported_by_text(name: str, text: str) -> bool:
    """Tên bác sĩ do LLM trích phải xuất hiện trong câu người dùng (bỏ dấu), tránh LLM bịa tên."""
    folded_text = _fold(text)
    tokens = _fold(name).split()
    return bool(tokens) and all(re.search(rf"\b{re.escape(tok)}\b", folded_text) for tok in tokens)


def _to_candidate(doc: dict[str, Any]) -> dict[str, Any]:
    specialties = doc.get("specialties") or []
    return {
        "full_name": doc.get("full_name"),
        "title": doc.get("title"),
        "specialty": specialties[0] if specialties else None,
        "specialties": specialties,
        "workplace": str(doc.get("workplace") or "").split(",")[0] or None,
        "source_url": doc.get("source_url") or doc.get("source"),
    }


async def resolve_doctor(name: str, title_hint: str | None = None, limit: int = 5) -> DoctorResolution:
    from src.medical_assistant.agent.tools.doctor_tools import search_doctors

    result = DoctorResolution(query_name=name)
    try:
        data = await asyncio.to_thread(search_doctors.invoke, {"name": name, "limit": limit})
    except Exception as exc:  # tra cứu lỗi không được làm hỏng lượt chat
        logger.warning("doctor resolution failed: %s", exc)
        result.data_unavailable = True
        return result
    result.data_unavailable = bool((data or {}).get("data_unavailable")) and not (data or {}).get("doctors")
    doctors = [_to_candidate(d) for d in (data or {}).get("doctors") or [] if d.get("full_name")]

    wanted = _fold(name)
    exact = [d for d in doctors if _fold(d["full_name"]) == wanted]
    result.exact = bool(exact)
    candidates = exact or doctors
    if title_hint:
        hint = _fold(title_hint)
        candidates.sort(key=lambda d: hint not in _fold(str(d.get("title") or "")))
    result.candidates = candidates[:limit]
    return result
