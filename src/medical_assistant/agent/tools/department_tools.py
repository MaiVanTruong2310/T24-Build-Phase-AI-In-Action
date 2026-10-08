"""Read-only tool for retrieving medical specialty/department information."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.language_service import get_specialty_display_name

logger = logging.getLogger(__name__)


class GetDepartmentInfoInput(BaseModel):
    department_key: str = Field(
        ...,
        description="Tên hoặc mã chuyên khoa cần tra cứu (VD: 'TIM_MACH', 'Tiêu hóa', 'Thần kinh', 'Nhi', 'Xương khớp')",
    )


@tool("get_department_info", args_schema=GetDepartmentInfoInput)
def get_department_info(department_key: str) -> dict[str, Any]:
    """Tra cứu thông tin giới thiệu, phạm vi khám chữa bệnh, dịch vụ kỹ thuật và thế mạnh của chuyên khoa/khoa phòng y tế."""
    try:
        dept_raw = str(department_key or "").strip()
        if not dept_raw:
            return {
                "found": False,
                "department_key": "",
                "reason": "Tên hoặc mã chuyên khoa không được để trống.",
                "source": "specialties",
            }

        guardrail = get_guardrail_service()
        dept_display = get_specialty_display_name(dept_raw, "vi")

        # Sử dụng hàm chuẩn get_department_info_response đã tích hợp RAG Store
        resp_text, quick_replies = guardrail.get_department_info_response(
            dept_name_query=dept_raw,
            language="vi",
            enable_citation=True,
        )

        if not resp_text:
            return {
                "found": False,
                "department_key": dept_raw,
                "department_name": dept_display,
                "reason": f"Chưa có thông tin hồ sơ cho chuyên khoa '{dept_display}' trong cơ sở tri thức.",
                "source": "specialties",
            }

        return {
            "found": True,
            "department_key": dept_raw,
            "department_name": dept_display,
            "summary": resp_text,
            "quick_replies": quick_replies,
            "source": "datalake.specialties / rag",
        }
    except Exception as exc:
        logger.error("Error in get_department_info tool: %s", exc, exc_info=True)
        return {
            "found": False,
            "department_key": str(department_key or "").strip() if "department_key" in locals() else "",
            "data_unavailable": True,
            "reason": f"Lỗi kết nối hoặc không thể tra cứu thông tin chuyên khoa: {exc}",
            "source": "specialties",
        }
