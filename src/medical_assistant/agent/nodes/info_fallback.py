"""Trả lời tra cứu cơ sở / bác sĩ KHÔNG cần LLM khi info agent lỗi hoặc hết thời gian.

Gọi thẳng các tool đọc DB (list_facilities, search_doctors) và định dạng câu trả lời cố định,
để người dùng vẫn nhận được địa chỉ, số điện thoại, danh sách bác sĩ thay vì "hệ thống trục trặc".
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.medical_assistant.agent.tools.base import normalize_fold
from src.medical_assistant.agent.tools.doctor_tools import search_doctors
from src.medical_assistant.agent.tools.facility_tools import REGION_ALIASES, list_facilities
from src.medical_assistant.domain.booking_slot_service import extract_booking_entities
from src.medical_assistant.domain.language_service import canonicalize_specialty_code, get_specialty_display_name

logger = logging.getLogger(__name__)

_DOCTOR_INTENT = re.compile(r"\b(?:bac si|bs|doctor|chuyen gia|truong khoa)\b")
_FACILITY_INTENT = re.compile(
    r"\b(?:co so|benh vien|phong kham|dia chi|o dau|chi nhanh|so dien thoai|hotline|lien he|vinmec)\b"
)
# Mã trả về khi không nhận ra chuyên khoa nào trong câu (canonicalize mặc định TONG_QUAT).
_NO_SPECIALTY = "TONG_QUAT"
# Từ khóa ngắn người dùng hay gõ ("bác sĩ nhi", "khám mắt") mà canonicalize_specialty_code không bắt được.
_SHORT_SPECIALTY = [
    (r"\bnhi\b|\bso sinh\b|\btre em\b", "NHI_KHOA"),
    (r"\bmat\b|\bnhan khoa\b", "MAT"),
    (r"\brang\b|\bnha khoa\b|\bnha si\b", "RANG_HAM_MAT"),
    (r"\bsan\b|\bphu khoa\b|\bthai san\b", "SAN_PHU_KHOA"),
    (r"\btim\b", "TIM_MACH"),
    (r"\bda\b", "DA_LIEU"),
    (r"\bxuong\b|\bkhop\b", "XUONG_KHOP"),
    (r"\btieu duong\b|\btuyen giap\b", "NOI_TIET"),
]


def detect_specialty(query: str) -> str | None:
    code = canonicalize_specialty_code(query)
    if code == _NO_SPECIALTY:
        folded = _fold(query)
        code = next((c for pattern, c in _SHORT_SPECIALTY if re.search(pattern, folded)), _NO_SPECIALTY)
    return get_specialty_display_name(code, "vi") if code != _NO_SPECIALTY else None


def _fold(text: str) -> str:
    return " ".join(normalize_fold(text).replace(".", " ").split())


def detect_region(folded_query: str) -> str | None:
    for canon, aliases in REGION_ALIASES.items():
        if any(re.search(rf"\b{re.escape(_fold(a))}\b", folded_query) for a in [canon, *aliases]):
            return canon
    return None


def detect_facility_name(folded_query: str) -> str | None:
    """Tên ngắn của cơ sở được nhắc trong câu (vd "times city"), so với danh sách cơ sở đang hoạt động."""
    try:
        facilities = list_facilities.invoke({}).get("facilities") or []
    except Exception as exc:  # noqa: BLE001 - fallback không được làm hỏng luồng chính
        logger.warning("info_fallback: list_facilities failed: %s", type(exc).__name__)
        return None
    keys: dict[str, str] = {}  # khóa không dấu → tên gốc có dấu (vd "da nang" → "Đà Nẵng")
    for fac in facilities:
        raw = str(fac.get("name") or "")
        idx = raw.lower().find("vinmec ")
        if idx >= 0:
            short = raw[idx + len("vinmec ") :].strip()
            keys.setdefault(_fold(short), short)
    for key in sorted(keys, key=len, reverse=True):
        if key and re.search(rf"\b{re.escape(key)}\b", folded_query):
            return keys[key]
    return None


def _format_facilities(data: dict[str, Any]) -> str:
    facilities = data.get("facilities") or []
    lines = [f"Dạ, Hệ thống Y tế Vinmec có **{len(facilities)} cơ sở** phù hợp:"]
    for fac in facilities[:8]:
        lines.append(f"\n🏥 **{fac.get('name')}**")
        if fac.get("address"):
            lines.append(f"   • Địa chỉ: {fac['address']}")
        if fac.get("phone"):
            lines.append(f"   • Điện thoại: {fac['phone']}")
        if fac.get("detail_url"):
            lines.append(f"   • 👉 [Xem chi tiết cơ sở]({fac['detail_url']})")
    lines.append("\nBác muốn em kiểm tra lịch khám tại cơ sở nào ạ?")
    return "\n".join(lines)


def _format_doctors(data: dict[str, Any], specialty: str | None, facility: str | None) -> str:
    doctors = data.get("doctors") or []
    scope = " ".join(
        x for x in [f"chuyên khoa **{specialty}**" if specialty else "", f"tại **{facility}**" if facility else ""] if x
    )
    lines = [f"Dạ, em tìm thấy {len(doctors)} bác sĩ{' ' + scope if scope else ''}:"]
    for i, doc in enumerate(doctors[:5], start=1):
        title = f" ({doc['title']})" if doc.get("title") else ""
        lines.append(f"\n**{i}. {doc.get('full_name')}**{title}")
        if doc.get("specialties"):
            lines.append(f"   • Chuyên môn: {', '.join(doc['specialties'])}")
        if doc.get("experience_display"):
            lines.append(f"   • {doc['experience_display']}")
        if doc.get("workplace"):
            lines.append(f"   • Nơi làm việc: {doc['workplace'].split(',')[0]}")
        if doc.get("source"):
            lines.append(f"   • [Hồ sơ nguồn Vinmec]({doc['source']})")
    lines.append("\nBác có muốn em kiểm tra lịch khám còn trống của bác sĩ nào không ạ?")
    return "\n".join(lines)


def answer_info_without_llm(query: str) -> tuple[str, str, dict[str, Any]] | None:
    """Trả về (câu trả lời, tên tool, dữ liệu) hoặc None nếu không phải câu hỏi cơ sở / bác sĩ."""
    folded = _fold(query)
    try:
        # Hỏi đích danh một bác sĩ ("Bác sĩ Nguyễn Vĩnh Toàn làm ở đâu?") → tra theo tên.
        doctor_name = extract_booking_entities(query, {}).get("doctor_preference")
        if doctor_name and doctor_name != "coordinator" and _DOCTOR_INTENT.search(folded):
            data = search_doctors.invoke({"name": doctor_name, "limit": 3})
            if data.get("found") and data.get("doctors"):
                return _format_doctors(data, None, None), "search_doctors", data
            return (
                f"Dạ, em chưa tìm thấy bác sĩ **{doctor_name}** trong danh sách bác sĩ Vinmec. "
                "Bác kiểm tra lại họ tên giúp em, hoặc cho em biết chuyên khoa để em gợi ý bác sĩ phù hợp nhé ạ.",
                "search_doctors",
                data,
            )
        # "Vinmec có khoa nội tiết không?" → xác nhận chuyên khoa kèm vài bác sĩ.
        specialty = detect_specialty(query)
        if specialty and re.search(r"\bco (?:chuyen )?khoa\b.*\bkhong\b", folded) and not _DOCTOR_INTENT.search(folded):
            data = search_doctors.invoke({"specialty": specialty, "limit": 3})
            if data.get("found") and data.get("doctors"):
                text = _format_doctors(data, specialty, None).replace(
                    "Dạ, em tìm thấy", f"Dạ, Vinmec **có chuyên khoa {specialty}** ạ. Một số bác sĩ:\n\nEm tìm thấy", 1
                )
                return text, "search_doctors", data
        if _DOCTOR_INTENT.search(folded):
            specialty = detect_specialty(query)
            facility = detect_facility_name(folded)
            if not specialty and not facility:
                return None
            data = search_doctors.invoke({"specialty": specialty, "facility": facility, "limit": 5})
            if data.get("found") and data.get("doctors"):
                return _format_doctors(data, specialty, facility), "search_doctors", data
            return None
        if _FACILITY_INTENT.search(folded):
            facility = detect_facility_name(folded)
            region = None if facility else detect_region(folded)
            data = list_facilities.invoke({"name": facility, "region": region})
            if data.get("found") and data.get("facilities"):
                return _format_facilities(data), "list_facilities", data
    except Exception as exc:  # noqa: BLE001
        logger.warning("info_fallback failed: %s", type(exc).__name__)
    return None
