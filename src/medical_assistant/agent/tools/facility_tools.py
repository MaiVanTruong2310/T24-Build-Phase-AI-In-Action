"""Read-only tool for listing and searching hospital and clinic facilities."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.medical_assistant.agent.tools.base import normalize_fold
from src.medical_assistant.domain.facility_linking import facility_key
from src.medical_assistant.domain.facility_service import FacilityService

logger = logging.getLogger(__name__)

REGION_ALIASES: dict[str, list[str]] = {
    "hà nội": ["ha noi", "hanoi", "mien bac", "miền bắc"],
    "hồ chí minh": ["ho chi minh", "tp hcm", "tphcm", "hcm", "sai gon", "sài gòn", "saigon", "mien nam", "miền nam"],
    "đà nẵng": ["da nang", "mien trung", "miền trung"],
    "quảng ninh": ["quang ninh", "ha long", "hạ long"],
    "hải phòng": ["hai phong"],
    "nha trang": ["nha trang", "khanh hoa"],
    "phú quốc": ["phu quoc", "kien giang"],
    "cần thơ": ["can tho", "tay nam bo"],
}


class ListFacilitiesInput(BaseModel):
    region: str | None = Field(
        default=None,
        description="Tỉnh/Thành phố hoặc miền (VD: 'Hà Nội', 'TP.HCM', 'Đà Nẵng', 'Hạ Long', 'Phú Quốc', 'Miền Bắc', 'Miền Nam')",
    )
    district: str | None = Field(
        default=None,
        description=(
            "Phường/Xã/Quận/đường mà người dùng nhắc (VD: 'Vĩnh Tuy', 'Tây Mỗ', 'Minh Khai', 'Bình Thạnh'). "
            "Địa chỉ cơ sở dùng phường MỚI (sau 07/2025), nên truyền đúng tên người dùng nói, không đổi sang quận cũ."
        ),
    )
    name: str | None = Field(
        default=None,
        description="Tên hoặc từ khóa cơ sở bệnh viện/phòng khám (VD: 'Times City', 'Central Park', 'Nguyễn Chí Thanh')",
    )
    specialty: str | None = Field(
        default=None,
        description=(
            "Chuyên khoa/khoa mà cơ sở phải có (VD: 'Sức khỏe tinh thần', 'Tim mạch', 'Nhi', 'Răng hàm mặt'). "
            "BẮT BUỘC truyền khi người dùng hỏi cơ sở nào có khoa/trung tâm X; chỉ trả về cơ sở thực sự có khoa đó."
        ),
    )


# Khoa → cơ sở suy từ nơi làm việc của bác sĩ (doctor_facilities.department). Lưu đệm để không đọc lại mỗi lượt.
_DEPT_CACHE: dict[str, Any] = {"at": 0.0, "rows": []}
_DEPT_TTL_SECONDS = 600
_DEPT_PREFIX = re.compile(r"^(?:trung tam|khoa|chuyen khoa|don vi|cham soc|phong kham)\s+")
_DEPT_SYNONYMS = (("tinh than", "tam than"), ("tam ly", "tinh than"), ("tam ly", "tam than"))
_UNIT_BEFORE = r"(?:khoa|trung tam|chuyen khoa|don vi|ngoai|noi)"


def _department_rows(client: Any) -> list[dict[str, Any]]:
    if time.monotonic() - _DEPT_CACHE["at"] < _DEPT_TTL_SECONDS and _DEPT_CACHE["rows"]:
        return _DEPT_CACHE["rows"]
    rows: list[dict[str, Any]] = []
    for offset in range(0, 20000, 1000):  # PostgREST trả tối đa 1.000 dòng mỗi lần
        page = (
            client.select(
                "doctor_facilities",
                params={"select": "department,facilities(name)", "limit": 1000, "offset": offset},
            )
            or []
        )
        rows += [r for r in page if r.get("department")]
        if len(page) < 1000:
            break
    _DEPT_CACHE.update(at=time.monotonic(), rows=rows)
    return rows


def _specialty_patterns(specialty: str) -> list[re.Pattern]:
    """Cụm lõi của tên khoa người dùng gõ ("trung tâm chăm sóc sức khỏe tinh thần" → "suc khoe tinh than") kèm đồng
    nghĩa (tinh thần ↔ tâm thần ↔ tâm lý). Lõi một âm tiết ("nhi", "mat") phải đứng sau "khoa/trung tâm…" để
    không khớp "truyền nhiễm", "răng hàm mặt"."""
    core = " ".join(normalize_fold(specialty).replace("-", " ").split())
    while (stripped := _DEPT_PREFIX.sub("", core)) != core:
        core = stripped
    variants = {core}
    for a, b in _DEPT_SYNONYMS:
        variants |= {v.replace(a, b) for v in variants} | {v.replace(b, a) for v in variants}
    # "(?! kinh)": "trung tâm thần kinh" bỏ dấu chứa đúng cụm "tam than" (tâm thần)
    return [
        re.compile(
            (rf"\b{_UNIT_BEFORE} {re.escape(v)}\b" if len(v.split()) == 1 else rf"\b{re.escape(v)}\b") + r"(?! kinh)"
        )
        for v in variants
        if v
    ]


def _facility_keys_with_specialty(client: Any, specialty: str) -> dict[tuple[str, str], set[str]]:
    """{facility_key: {tên khoa khớp}} cho mọi cơ sở có bác sĩ làm việc tại khoa khớp với `specialty`."""
    patterns = _specialty_patterns(specialty)
    out: dict[tuple[str, str], set[str]] = {}
    for row in _department_rows(client):
        dept = str(row["department"])
        dept_fold = " ".join(normalize_fold(dept).replace("-", " ").split())
        if not any(p.search(dept_fold) for p in patterns):
            continue
        key = facility_key((row.get("facilities") or {}).get("name"))
        if key:
            out.setdefault(key, set()).add(dept)
    return out


@tool("list_facilities", args_schema=ListFacilitiesInput)
def list_facilities(
    region: str | None = None,
    district: str | None = None,
    name: str | None = None,
    specialty: str | None = None,
) -> dict[str, Any]:
    """Tra cứu danh sách các bệnh viện và phòng khám đa khoa quốc tế Vinmec theo khu vực, quận huyện, tên cơ sở hoặc
    chuyên khoa mà cơ sở có."""
    try:
        service = FacilityService()
        all_facilities = service.fetch_active_facilities()
        dept_by_key: dict[tuple[str, str], set[str]] | None = None
        if specialty:
            dept_by_key = _facility_keys_with_specialty(service._get_client(), specialty)
            active_keys = {facility_key(str(f.get("name") or "")) for f in all_facilities}
            exact_sites = {k[0] for k in dept_by_key if k in active_keys}
            if not dept_by_key:
                return {
                    "found": False,
                    "count": 0,
                    "facilities": [],
                    "reason": f"Chưa có dữ liệu cơ sở nào có khoa '{specialty}'. Không liệt kê cơ sở khác thay thế.",
                }

        if not all_facilities:
            return {
                "found": False,
                "count": 0,
                "facilities": [],
                "reason": "Hiện không có dữ liệu cơ sở y tế nào trong hệ thống.",
            }

        norm_name = normalize_fold(name) if name else None
        norm_district = normalize_fold(district) if district else None
        # "TP.HCM" → "tp hcm": bỏ dấu chấm để khớp alias.
        norm_region = " ".join(normalize_fold(region).replace(".", " ").split()) if region else None

        # Mở rộng alias vùng miền nếu có
        region_keywords = [norm_region] if norm_region else []
        if norm_region:
            for canon, aliases in REGION_ALIASES.items():
                canon_fold = normalize_fold(canon)
                all_alias_folds = [canon_fold, *(normalize_fold(a) for a in aliases)]
                if any(kw in norm_region or norm_region in kw for kw in all_alias_folds):
                    region_keywords.extend(all_alias_folds)

        matched: list[dict[str, Any]] = []

        for fac in all_facilities:
            fac_name = str(fac.get("name") or "")
            fac_address = str(fac.get("address") or "")
            searchable_text = normalize_fold(f"{fac_name} {fac_address}")

            # Lọc theo tên cơ sở
            if norm_name and norm_name not in searchable_text:
                continue

            # Lọc theo quận/huyện
            if norm_district and norm_district not in searchable_text:
                continue

            # Lọc theo khu vực/tỉnh thành
            if region_keywords:
                if not any(kw in searchable_text for kw in region_keywords):
                    continue

            # Lọc theo chuyên khoa: chỉ cơ sở có bác sĩ làm việc tại khoa đó (cùng loại hình trước, cùng địa điểm sau)
            departments: list[str] = []
            if dept_by_key is not None:
                key = facility_key(fac_name)
                if not key:
                    continue
                hits = dept_by_key.get(key)
                if not hits and key[0] not in exact_sites:  # địa điểm không có cơ sở khớp đúng loại hình
                    hits = set().union(*(v for k, v in dept_by_key.items() if k[0] == key[0]))
                if not hits:
                    continue
                departments = sorted(hits)

            is_clinic = "phòng khám" in fac_name.lower() or "clinic" in fac_name.lower()
            fac_type = "Phòng khám Đa khoa Quốc tế" if is_clinic else "Bệnh viện Đa khoa Quốc tế"

            # Tìm metadata chi tiết (URL, chuyên khoa nổi bật)
            meta = service._find_detail_metadata(fac_name)
            detail_url = meta.get("detail_url") or "https://www.vinmec.com/vie/co-so-y-te/"
            specialties = meta.get("specialties") or []

            matched.append(
                {
                    "id": str(fac.get("id") or fac.get("code")),
                    "name": fac_name,
                    "facility_type": fac_type,
                    "address": fac_address,
                    "phone": fac.get("phone") or "1900 232 389",
                    "key_specialties": specialties[:5],
                    **({"matched_departments": departments} if departments else {}),
                    "detail_url": detail_url,
                    "verified": True,
                }
            )

        if not matched:
            filter_parts = []
            if name:
                filter_parts.append(f"tên '{name}'")
            if district:
                filter_parts.append(f"quận/huyện '{district}'")
            if region:
                filter_parts.append(f"khu vực '{region}'")
            if specialty:
                filter_parts.append(f"có khoa '{specialty}'")
            filter_str = ", ".join(filter_parts) or "bộ lọc đã chọn"

            out: dict[str, Any] = {
                "found": False,
                "count": 0,
                "facilities": [],
                "reason": f"Không tìm thấy cơ sở y tế nào phù hợp với {filter_str}.",
            }
            if dept_by_key:  # khoa có, chỉ không có ở khu vực được hỏi → cho biết nơi đang có
                out["specialty_available_at"] = sorted(
                    str(f.get("name")) for f in all_facilities if facility_key(str(f.get("name") or "")) in dept_by_key
                )
            return out

        return {
            "found": True,
            "count": len(matched),
            "facilities": matched,
        }
    except Exception as exc:
        logger.error("Error in list_facilities tool: %s", exc, exc_info=True)
        return {
            "found": False,
            "count": 0,
            "facilities": [],
            "data_unavailable": True,
            "reason": f"Hệ thống cơ sở dữ liệu y tế gặp sự cố hoặc gián đoạn kết nối: {exc}",
        }
