"""Production API Routes for VCare System.

Centralized entry point aggregating Agent endpoints and Domain API routers.
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Depends

from src.agents.graph import agent
from src.models.schemas import (
    AgentStatusResponse,
    ChatRequest,
    ChatResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Tương tác trực tiếp với LangGraph Medical Agent.

    Hỗ trợ xử lý thông minh qua các node:
    - Zero-Token Emergency Gate (ATS Level 1-2)
    - Fact-aware Probing & Triage
    - Gợi ý chuyên khoa & bác sĩ
    - Phản tư lâm sàng (Reflexion loop)
    """
    try:
        payload: dict[str, Any] = {
            "query": request.message,
            "user_input": request.message,
            "session_id": request.session_id or "default_session",
            "enable_citation": request.enable_citation,
        }
        if request.user_id:
            payload["user_id"] = request.user_id

        result = await agent.ainvoke(payload)

        return ChatResponse(
            response=result.get("response", ""),
            analysis=result.get("analysis", ""),
            session_id=result.get("session_id") or request.session_id,
            suggested_department=result.get("suggested_department_name") or result.get("suggested_department_code"),
            is_emergency=bool(result.get("is_emergency", False)),
            metadata={
                "ats_level": result.get("ats_level"),
                "urgency_tier": result.get("urgency_tier"),
                "workflow_status": result.get("workflow_status"),
            },
        )
    except Exception as exc:
        logger.exception("api.chat execution error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý hội thoại AI: {exc}") from exc


@router.get("/status", response_model=AgentStatusResponse)
async def agent_status() -> AgentStatusResponse:
    """Kiểm tra trạng thái hoạt động của LangGraph Agent runtime."""
    return AgentStatusResponse(
        status="ready",
        agent="VCare LangGraph Medical Agent v2.0",
        version="2.0.0",
        nodes=["analyze", "critic", "find_doctors", "respond"],
    )
