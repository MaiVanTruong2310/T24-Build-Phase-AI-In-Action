"""
Unit tests for Step 4: Failure Transparency & Telemetry
Tests transparent error responses when Supabase DB or LLM fails.
"""

from unittest.mock import MagicMock, patch

import pytest

from scripts.stats_telemetry import compute_statistics, parse_telemetry_lines
from src.medical_assistant.agent.nodes.doctor_node import find_doctors_node
from src.medical_assistant.agent.nodes.respond_node import respond_node
from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.hybrid_dialogue_service import (
    HybridDialogueService,
)


@pytest.mark.asyncio
async def test_doctor_node_unconfigured_db():
    """Khi Supabase chưa cấu hình (ValueError), doctor_node phải set cờ data_unavailable=True."""
    state: AgentState = {
        "is_emergency": False,
        "suggested_department_name": "Khoa Tiêu hóa",
        "max_booking_days": 7,
        "metadata": {
            "needs_more_probing": False,
        },
    }

    with patch(
        "src.medical_assistant.agent.nodes.doctor_node.get_doctor_schedule_service",
        side_effect=ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured"),
    ):
        res = await find_doctors_node(state)

        assert res["available_slots"] == []
        meta = res.get("metadata", {})
        assert meta.get("data_unavailable") is True
        assert meta.get("data_unavailable_reason") == "DATABASE_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_doctor_node_db_error():
    """Khi truy vấn Supabase gặp sự cố mạng (Exception), doctor_node phải ghi nhận QUERY_ERROR."""
    state: AgentState = {
        "is_emergency": False,
        "suggested_department_name": "Khoa Tim mạch",
        "max_booking_days": 7,
        "metadata": {
            "needs_more_probing": False,
        },
    }

    mock_service = MagicMock()
    mock_service.get_available_doctors_and_slots.side_effect = ConnectionError("Supabase DB connection timed out")

    with patch(
        "src.medical_assistant.agent.nodes.doctor_node.get_doctor_schedule_service",
        return_value=mock_service,
    ):
        res = await find_doctors_node(state)

        assert res["available_slots"] == []
        meta = res.get("metadata", {})
        assert meta.get("data_unavailable") is True
        assert "QUERY_ERROR: ConnectionError" in meta.get("data_unavailable_reason", "")


@pytest.mark.asyncio
async def test_doctor_node_success():
    """Khi DB hoạt động bình thường, data_unavailable phải là False."""
    state: AgentState = {
        "is_emergency": False,
        "suggested_department_name": "Khoa Nhi",
        "max_booking_days": 7,
        "metadata": {
            "needs_more_probing": False,
        },
    }

    mock_service = MagicMock()
    mock_service.get_available_doctors_and_slots.return_value = [
        {
            "doctor_id": "doc-01",
            "full_name": "BS CKII Nguyễn Văn A",
            "title": "Bác sĩ",
            "available_slots": [{"starts_at": "08:30", "schedule_id": "slot-1", "verified": True}],
        }
    ]

    with patch(
        "src.medical_assistant.agent.nodes.doctor_node.get_doctor_schedule_service",
        return_value=mock_service,
    ):
        res = await find_doctors_node(state)

        assert len(res["available_slots"]) == 1
        meta = res.get("metadata", {})
        assert meta.get("data_unavailable") is False
        assert meta.get("data_unavailable_reason") is None


@pytest.mark.asyncio
async def test_respond_node_transparent_when_data_unavailable_vi():
    """Khi data_unavailable=True, respond_node phải thông báo trung thực bằng tiếng Việt."""
    state: AgentState = {
        "query": "Tôi muốn đặt lịch khám khoa Tiêu hóa",
        "workflow_status": "TRIAGED_READY_FOR_BOOKING",
        "suggested_department_name": "Gastroenterology",
        "language": "vi",
        "available_slots": [],
        "metadata": {
            "data_unavailable": True,
            "data_unavailable_reason": "DATABASE_NOT_CONFIGURED",
        },
    }

    res = await respond_node(state)
    resp_text = res["response"]

    # Tuyệt đối không được trả lời câu giả vờ như không có lịch khám
    assert "Xin lỗi bác, hiện tại em chưa tìm thấy lịch khám phù hợp" not in resp_text
    # Phải nói rõ hệ thống tra cứu online tạm thời gián đoạn
    assert "hệ thống tra cứu lịch trực tuyến của bệnh viện hiện đang tạm thời gián đoạn" in resp_text
    # Hướng dẫn hotline đặt lịch
    assert "1900 232 389" in resp_text

    # Kiểm tra telemetry được lưu lại
    meta = res.get("metadata", {})
    assert "structured_telemetry" in meta
    telem = meta["structured_telemetry"]
    assert telem["data_unavailable"] is True
    assert telem["data_unavailable_reason"] == "DATABASE_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_respond_node_transparent_when_data_unavailable_en():
    """Khi data_unavailable=True, respond_node phải thông báo trung thực bằng tiếng Anh."""
    state: AgentState = {
        "query": "I want to see a cardiologist",
        "workflow_status": "TRIAGED_READY_FOR_BOOKING",
        "suggested_department_name": "Cardiology",
        "language": "en",
        "available_slots": [],
        "metadata": {
            "data_unavailable": True,
            "data_unavailable_reason": "DATABASE_ERROR: ConnectionError",
        },
    }

    res = await respond_node(state)
    resp_text = res["response"]

    assert "couldn't find any available slots" not in resp_text
    assert "online schedule system is temporarily unavailable" in resp_text
    assert "1900 232 389" in resp_text

    meta = res.get("metadata", {})
    telem = meta["structured_telemetry"]
    assert telem["data_unavailable"] is True


@pytest.mark.asyncio
async def test_hybrid_dialogue_fallback_transparency():
    """Khi LLM gặp sự cố, process_turn_async kích hoạt fallback và adapt_v2_to_v1 đánh dấu rõ ràng."""
    service = HybridDialogueService()

    state = {
        "language": "vi",
        "clinical_facts": {},
    }

    with patch(
        "src.medical_assistant.domain.hybrid_dialogue_service.get_llm", side_effect=RuntimeError("LLM quota exceeded")
    ):
        v2_res, llm_succeeded = await service.process_turn_async("Tôi bị đau bụng 2 ngày nay", state)

        assert llm_succeeded is False
        assert v2_res is not None

        v1_adapted = service.adapt_v2_to_v1(v2_res, llm_succeeded=False)
        assert v1_adapted["llm_succeeded"] is False
        assert v1_adapted["fallback_used"] is True
        assert v1_adapted["extraction_method"] == "RULE_FALLBACK"
        for comp in v1_adapted["complaints"]:
            assert comp["source"] == "rule_fallback"


def test_stats_telemetry_script_logic():
    """Kiểm tra logic phân tích log telemetry của stats_telemetry.py."""
    sample_logs = [
        '2026-10-07 10:00:00 [INFO] TURN_TELEMETRY: {"route": "clinical", "workflow_status": "TRIAGED_READY_FOR_BOOKING", "action": "search_available_slot", "tools_called": [], "llm_succeeded": true, "fallback_used": false, "data_unavailable": true, "data_unavailable_reason": "DATABASE_NOT_CONFIGURED", "latency_ms": 120.5}',
        '2026-10-07 10:01:00 [INFO] TURN_TELEMETRY: {"route": "clinical", "workflow_status": "VISIT_PURPOSE_CLARIFICATION", "action": "clarify_visit_purpose", "tools_called": [], "llm_succeeded": false, "fallback_used": true, "data_unavailable": false, "latency_ms": 85.0}',
        '2026-10-07 10:02:00 [INFO] TURN_TELEMETRY: {"route": "info_agent", "workflow_status": "INFO_ANSWERED", "action": null, "tools_called": ["search_doctors"], "llm_succeeded": true, "fallback_used": false, "data_unavailable": false, "latency_ms": 450.0}',
    ]

    records = parse_telemetry_lines(sample_logs)
    assert len(records) == 3

    stats = compute_statistics(records)
    assert "2026-10-07" in stats
    day_stats = stats["2026-10-07"]

    assert day_stats["total_turns"] == 3
    assert day_stats["fallback_count"] == 1
    assert day_stats["fallback_rate_pct"] == 33.33
    assert day_stats["clarify_visit_purpose_count"] == 1
    assert day_stats["clarify_visit_purpose_rate_pct"] == 33.33
    assert day_stats["data_unavailable_count"] == 1
    assert day_stats["data_unavailable_rate_pct"] == 33.33
    assert day_stats["route_distribution"]["info_agent"] == 1
    assert day_stats["route_distribution"]["clinical"] == 2
