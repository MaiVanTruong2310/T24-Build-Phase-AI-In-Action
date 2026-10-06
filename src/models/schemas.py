"""Central Pydantic Schemas for VCare Production Application.

Combines agent chat contracts with application domain schemas.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

# 1. Base Agent & Chat Schemas
class ChatRequest(BaseModel):
    """Yêu cầu chat gửi tới AI Agent."""

    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ người dùng")
    session_id: str | None = Field(default=None, description="Mã định danh phiên hội thoại")
    user_id: str | None = Field(default=None, description="Mã người dùng (nếu đã đăng nhập)")
    enable_citation: bool = Field(default=True, description="Bật trích dẫn nguồn y khoa RAG")


class ChatResponse(BaseModel):
    """Phản hồi trả về từ AI Agent."""

    response: str = Field(..., description="Nội dung phản hồi từ AI Agent")
    analysis: str = Field(default="", description="Phân tích nội bộ / Triage tóm tắt")
    session_id: str | None = Field(default=None, description="Mã phiên hội thoại")
    suggested_department: str | None = Field(default=None, description="Chuyên khoa được gợi ý")
    is_emergency: bool = Field(default=False, description="Cờ cảnh báo cấp cứu khẩn cấp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata bổ sung")


class ChatStreamRequest(BaseModel):
    """Yêu cầu streaming SSE phản hồi thời gian thực."""

    message: str = Field(..., min_length=1, max_length=5000)
    session_id: str | None = None
    user_id: str | None = None


class AgentStatusResponse(BaseModel):
    """Trạng thái hoạt động của hệ thống Agent."""

    status: str = Field(default="ready", description="Trạng thái dịch vụ")
    agent: str = Field(default="VCare LangGraph Medical Agent v2.0")
    version: str = Field(default="2.0.0")
    nodes: list[str] = Field(
        default_factory=lambda: ["analyze", "critic", "find_doctors", "respond"]
    )


# 2. Re-export Application Domain Schemas
try:
    from src.schemas.auth import *  # noqa: F403
except ImportError:
    pass

try:
    from src.schemas.booking import *  # noqa: F403
except ImportError:
    pass

try:
    from src.schemas.coordination import *  # noqa: F403
except ImportError:
    pass

try:
    from src.schemas.patient_profile import *  # noqa: F403
except ImportError:
    pass

try:
    from src.schemas.workbench import *  # noqa: F403
except ImportError:
    pass
