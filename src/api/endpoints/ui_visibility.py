"""Cấu hình ẩn/hiện thành phần giao diện người dùng.

GET công khai (trang người dùng đọc để ẩn thành phần); PUT chỉ admin hệ thống (coordinator admin, không giới hạn cơ sở).
Thành phần an toàn (cấp cứu 115, cảnh báo cấp cứu, khuyến cáo không chẩn đoán/kê đơn, trạng thái bác sĩ điều phối)
bị khoá: không ẩn được kể cả gọi API trực tiếp.
"""

import logging
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_coordination_admin
from src.api.response import success_response
from src.core.error_codes import ErrorCode
from src.core.exceptions import AppException
from src.core.logging import log_event
from src.db.dependencies import get_db_session
from src.models.ui_visibility import UiVisibility
from src.models.user import User
from src.schemas.common import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ui-visibility", tags=["ui-visibility"])

# Phải khớp các mục `locked: true` trong frontend/src/features/uiVisibility/registry.ts (test kiểm tra đồng bộ).
LOCKED_UI_KEYS = frozenset(
    {
        "header.sos",  # nút Cấp cứu 115 (dùng chung desktop + điện thoại)
        "landing.hero_emergency",  # "Đau ngực, khó thở…? Gọi ngay 115" ở trang chủ
        "chat.disclaimer",  # "VCare+ hỗ trợ tư vấn sơ bộ, không chẩn đoán hay kê đơn…"
        "chat.emergency_banner",  # huy hiệu ATS / Cấp cứu khẩn cấp trên tin nhắn bot
        "chat.coordinator_status",  # trạng thái bác sĩ điều phối đang hỗ trợ / đã gửi yêu cầu
        "booking.consent",  # đồng ý chia sẻ thông tin khi đặt lịch (yêu cầu pháp lý)
    }
)
KEY_PATTERN = re.compile(r"^[a-z0-9_]+(?:\.[a-z0-9_]+)+$")


class VisibilityUpdate(BaseModel):
    visible: bool


class VisibilityState(BaseModel):
    hidden: list[str]


async def _hidden_keys(db: AsyncSession) -> list[str]:
    rows = await db.execute(select(UiVisibility.key).where(UiVisibility.visible.is_(False)))
    return sorted(key for key in rows.scalars() if key not in LOCKED_UI_KEYS)


@router.get("", response_model=ApiResponse[VisibilityState])
async def get_ui_visibility(db: AsyncSession = Depends(get_db_session)) -> ApiResponse[VisibilityState]:
    """Danh sách thành phần đang bị ẩn (mọi thành phần khác hiển thị)."""
    return success_response(VisibilityState(hidden=await _hidden_keys(db)), "UI visibility retrieved")


@router.put("/{key}", response_model=ApiResponse[VisibilityState])
async def set_ui_visibility(
    key: str,
    payload: VisibilityUpdate,
    admin: User = Depends(require_coordination_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[VisibilityState]:
    """Bật/tắt một thành phần. Thành phần an toàn bị khoá luôn hiển thị."""
    if not KEY_PATTERN.fullmatch(key) or len(key) > 120:
        raise AppException("Mã thành phần không hợp lệ.", error_code=ErrorCode.VALIDATION_ERROR, status_code=400)
    if key in LOCKED_UI_KEYS:
        raise AppException(
            "Thành phần an toàn (cấp cứu, khuyến cáo y tế) luôn hiển thị, không thể ẩn.",
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
        )
    row = await db.get(UiVisibility, key)
    if row is None:
        db.add(UiVisibility(key=key, visible=payload.visible, updated_by=admin.id))
    else:
        row.visible = payload.visible
        row.updated_by = admin.id
    await db.commit()
    log_event(
        logger,
        logging.INFO,
        "ui_visibility.updated",
        description="Admin bật/tắt hiển thị thành phần giao diện",
        key=key,
        visible=payload.visible,
        admin_id=str(admin.id),
    )
    return success_response(VisibilityState(hidden=await _hidden_keys(db)), "UI visibility updated")
