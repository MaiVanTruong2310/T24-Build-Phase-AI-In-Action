"""Read-only tool for listing and searching hospital and clinic facilities."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.medical_assistant.agent.tools.base import ToolExecutionError, normalize_fold
from src.medical_assistant.domain.facility_service import FacilityService

logger = logging.getLogger(__name__)

REGION_ALIASES: dict[str, list[str]] = {
    "hà nội": ["ha noi", "hanoi", "mien bac", "miền bắc"],
    "hồ chí minh": ["ho chi minh", "tp hcm", "tphcm", "sai gon", "sài gòn", "mien nam", "miền nam"],
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
        description="Quận/Huyện (VD: 'Hai Bà Trưng', 'Bình Thạnh', 'Cầu Giấy')",
    )
    name: str | None = Field(
        default=None,
        description="Tên hoặc từ khóa cơ sở bệnh viện/phòng khám (VD: 'Times City', 'Central Park', 'Nguyễn Chí Thanh')",
    )


@tool("list_facilities", args_schema=ListFacilitiesInput)
def list_facilities(
    region: str | None = None,
    district: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Tra cứu danh sách các bệnh viện và phòng khám đa khoa quốc tế Vinmec theo khu vực, quận huyện hoặc tên cơ sở."""
    try:
        service = FacilityService()
        all_facilities = service.fetch_active_facilities()

        if not all_facilities:
            return {
                "found": False,
                "count": 0,
                "facilities": [],
                "reason": "Hiện không có dữ liệu cơ sở y tế nào trong hệ thống.",
            }

        norm_name = normalize_fold(name) if name else None
        norm_district = normalize_fold(district) if district else None
        norm_region = normalize_fold(region) if region else None

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
            filter_str = ", ".join(filter_parts) or "bộ lọc đã chọn"

            return {
                "found": False,
                "count": 0,
                "facilities": [],
                "reason": f"Không tìm thấy cơ sở y tế nào phù hợp với {filter_str}.",
            }

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
