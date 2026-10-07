"""Base classes and utility helpers for read-only medical assistant tools."""

from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc


class ToolExecutionError(Exception):
    """Ngoại lệ khi thực thi tool gặp lỗi hệ thống, cấu hình hoặc kết nối cơ sở dữ liệu."""

    pass


def normalize_fold(text: Any) -> str:
    """Loại bỏ dấu tiếng Việt và chuẩn hóa về chữ thường không dấu để so khớp linh hoạt."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", str(text).lower())
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    cleaned = without_marks.replace("đ", "d").replace("-", " ")
    return " ".join(cleaned.split())


def format_utc_to_vn_time(utc_iso_str: str) -> str:
    """Định dạng thời gian ISO/UTC sang múi giờ Việt Nam GMT+7 theo định dạng thân thiện.

    Ví dụ: '08:30 (Sáng) ngày 25/09/2026' (tuân thủ RULE-DATA-02).
    """
    try:
        parsed = datetime.fromisoformat(str(utc_iso_str).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        local = parsed.astimezone(VN_TZ)
        period = "Sáng" if local.hour < 12 else "Chiều"
        return f"{local.strftime('%H:%M')} ({period}) ngày {local.strftime('%d/%m/%Y')}"
    except Exception:
        return str(utc_iso_str).replace("T", " ")[:16]
