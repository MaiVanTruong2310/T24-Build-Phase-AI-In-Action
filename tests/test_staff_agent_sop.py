"""Tests for staff agent approved SOP procedures search."""

import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.agents.tools.staff_agent_tools import build_staff_tools
from src.models.user import User


@pytest.mark.asyncio
async def test_search_approved_staff_procedures_emergency_sop():
    staff = User(id=uuid4(), role="staff")
    tools = build_staff_tools(
        staff,
        session=AsyncMock(),
        patient_service=AsyncMock(),
        repository=AsyncMock(),
        query_service=AsyncMock(),
    )
    sop_tool = next(t for t in tools if t.name == "search_approved_staff_procedures")

    result = json.loads(await sop_tool.ainvoke({"query": "tiếp nhận cấp cứu"}))
    assert result["available"] is True
    assert result["total"] > 0
    assert any("SOP-CAPCUU-001" in item["citation"] or "Cấp cứu" in item["document"] for item in result["matches"])


@pytest.mark.asyncio
async def test_search_approved_staff_procedures_booking_review_sop():
    staff = User(id=uuid4(), role="staff")
    tools = build_staff_tools(
        staff,
        session=AsyncMock(),
        patient_service=AsyncMock(),
        repository=AsyncMock(),
        query_service=AsyncMock(),
    )
    sop_tool = next(t for t in tools if t.name == "search_approved_staff_procedures")

    result = json.loads(await sop_tool.ainvoke({"query": "phê duyệt lịch khám"}))
    assert result["available"] is True
    assert result["total"] > 0
    assert any("SOP-DATKHAM-003" in item["citation"] or "Lịch khám" in item["document"] for item in result["matches"])


@pytest.mark.asyncio
async def test_search_approved_staff_procedures_unmatched_query():
    staff = User(id=uuid4(), role="staff")
    tools = build_staff_tools(
        staff,
        session=AsyncMock(),
        patient_service=AsyncMock(),
        repository=AsyncMock(),
        query_service=AsyncMock(),
    )
    sop_tool = next(t for t in tools if t.name == "search_approved_staff_procedures")

    result = json.loads(await sop_tool.ainvoke({"query": "thủ tục mua sắm máy bay"}))
    assert result["available"] is True
    assert result["matches"] == []
    assert "Không tìm thấy" in result["message"]
