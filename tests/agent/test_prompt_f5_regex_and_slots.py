"""
Tests for Prompt F5:
1) Administrative regex demotion to hints (DEPARTMENT_INFO, FACILITY_*, VIEW_SCHEDULE)
   with final decision made by Router / LLM.
2) Hard veto preserved for SECURITY, EMERGENCY, MEDICATION, DIAGNOSIS, HOLD_BOOKING.
3) Single-fetch slot caching per turn across analyze_node, find_doctors_node, respond_node.
4) respond_node eliminates ungrounded statements ('luôn sẵn sàng tiếp nhận').
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.medical_assistant.agent.nodes.analyze_node import (
    resolve_action,
)
from src.medical_assistant.agent.nodes.doctor_node import find_doctors_node
from src.medical_assistant.agent.nodes.respond_node import respond_node
from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.doctor_schedule_service import (
    clear_turn_slot_cache,
)


def test_administrative_regex_does_not_override_llm_decision():
    """Khi regex gợi ý DEPARTMENT_INFO/FACILITY_INFO/VIEW_SCHEDULE, quyết định cuối thuộc về LLM."""
    mock_v2 = MagicMock()
    mock_v2.proposed_action = "clarify_visit_purpose"
    mock_v2.primary_intent = "symptom_report"
    mock_v2.needs_clarification = False

    mock_triage = MagicMock()
    mock_triage.triggered_rule_ids = []

    state: AgentState = {"session_id": "test_sess_1"}

    # 1. Regex gợi ý DEPARTMENT_INFO nhưng LLM đề xuất clarify_visit_purpose
    action, reason, extra = resolve_action(
        intent_check={"intent": "DEPARTMENT_INFO", "department_query": "Tim mạch"},
        booking_entities={},
        v2_response=mock_v2,
        triage_result=mock_triage,
        clinical_facts={},
        rule_facts={},
        current_turn=0,
        active_category=None,
        should_ask_multi=False,
        is_emergency=False,
        is_describe_more=False,
        has_explicit_booking_request=False,
        query="Khoa tim mạch điều trị những gì ạ?",
        state=state,
    )
    assert action == "clarify_visit_purpose"
    assert extra.get("intent_hint") == "DEPARTMENT_INFO"

    # 2. Regex gợi ý FACILITY_INFO nhưng LLM đề xuất suggest_specialty
    mock_v2.proposed_action = "suggest_specialty"
    action, reason, extra = resolve_action(
        intent_check={"intent": "FACILITY_INFO"},
        booking_entities={},
        v2_response=mock_v2,
        triage_result=mock_triage,
        clinical_facts={},
        rule_facts={},
        current_turn=0,
        active_category=None,
        should_ask_multi=False,
        is_emergency=False,
        is_describe_more=False,
        has_explicit_booking_request=False,
        query="Bệnh viện Vinmec ở đâu?",
        state=state,
    )
    assert action == "suggest_specialty"
    assert extra.get("intent_hint") == "FACILITY_INFO"

    # 3. Khi LLM không có đề xuất (hoặc fallback), mới kích hoạt regex hint
    mock_v2_empty = MagicMock()
    mock_v2_empty.proposed_action = None
    action_fb, reason_fb, extra_fb = resolve_action(
        intent_check={"intent": "DEPARTMENT_INFO", "department_query": "Nhi"},
        booking_entities={},
        v2_response=mock_v2_empty,
        triage_result=mock_triage,
        clinical_facts={},
        rule_facts={},
        current_turn=0,
        active_category=None,
        should_ask_multi=False,
        is_emergency=False,
        is_describe_more=False,
        has_explicit_booking_request=False,
        query="Giới thiệu khoa nhi",
        state=state,
    )
    assert action_fb == "show_department_info"
    assert "Fallback" in reason_fb


def test_hard_veto_intents_strictly_override_llm():
    """Quyền phủ quyết an toàn (SECURITY, EMERGENCY, MEDICATION, DIAGNOSIS, HOLD_BOOKING) luôn thắng LLM."""
    mock_v2 = MagicMock()
    mock_v2.proposed_action = "suggest_specialty"

    mock_triage = MagicMock()
    mock_triage.triggered_rule_ids = []
    state: AgentState = {"session_id": "test_sess_veto"}

    # MEDICATION_GUARDRAIL
    action, reason, _ = resolve_action(
        intent_check={"intent": "MEDICATION_GUARDRAIL"},
        booking_entities={},
        v2_response=mock_v2,
        triage_result=mock_triage,
        clinical_facts={},
        rule_facts={},
        current_turn=0,
        active_category=None,
        should_ask_multi=False,
        is_emergency=False,
        is_describe_more=False,
        has_explicit_booking_request=False,
        query="Uống thuốc panadol mấy viên?",
        state=state,
    )
    assert action == "decline_medication_request"
    assert "RULE-SAF-02" in reason

    # DIAGNOSIS_GUARDRAIL
    action, reason, _ = resolve_action(
        intent_check={"intent": "DIAGNOSIS_GUARDRAIL"},
        booking_entities={},
        v2_response=mock_v2,
        triage_result=mock_triage,
        clinical_facts={},
        rule_facts={},
        current_turn=0,
        active_category=None,
        should_ask_multi=False,
        is_emergency=False,
        is_describe_more=False,
        has_explicit_booking_request=False,
        query="Tôi có phải bị ung thư không?",
        state=state,
    )
    assert action == "respond_to_diagnosis_request"
    assert "RULE-SAF-01" in reason

    # HOLD_BOOKING
    action, _, extra = resolve_action(
        intent_check={"intent": "HOLD_BOOKING", "slot_id": "slot-999"},
        booking_entities={},
        v2_response=mock_v2,
        triage_result=mock_triage,
        clinical_facts={},
        rule_facts={},
        current_turn=0,
        active_category=None,
        should_ask_multi=False,
        is_emergency=False,
        is_describe_more=False,
        has_explicit_booking_request=False,
        query="Giữ slot 999",
        state=state,
    )
    assert action == "hold_slot"
    assert extra.get("slot_id") == "slot-999"


@pytest.mark.asyncio
async def test_slot_single_fetch_caching_across_nodes():
    """Kiểm tra cache lượt: chỉ truy vấn Supabase/service 1 lần duy nhất trong cả lượt."""
    clear_turn_slot_cache()

    dummy_doctors = [{"full_name": "Bác sĩ Nguyễn Văn A", "slots": ["08:00", "09:00"]}]

    state: AgentState = {
        "session_id": "thread_abc_123",
        "probing_turn": 1,
        "suggested_department_name": "Tim mạch",
        "max_booking_days": 7,
        "workflow_status": "TRIAGED_READY_FOR_BOOKING",
        "language": "vi",
        "metadata": {},
    }

    with patch(
        "src.medical_assistant.domain.doctor_schedule_service.fetch_available_doctors_slots",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = (dummy_doctors, False, None)

        # Lần 1: find_doctors_node gọi fetch_available_doctors_slots_cached
        res_doc = await find_doctors_node(state)
        assert len(res_doc["available_slots"]) == 1
        assert mock_fetch.call_count == 1

        # Cập nhật state mô phỏng LangGraph state passing
        state["available_slots"] = res_doc["available_slots"]
        state["metadata"] = res_doc["metadata"]

        # Lần 2: respond_node gọi lại trong cùng lượt
        res_resp = await respond_node(state)
        # mock_fetch KHÔNG được gọi thêm lần nào nữa (call_count vẫn là 1)
        assert mock_fetch.call_count == 1
        assert "Nguyễn Văn A" in res_resp["response"]


@pytest.mark.asyncio
async def test_respond_node_grounded_doctor_inquiry_no_fake_promises():
    """Kiểm tra respond_node loại bỏ câu 'luôn sẵn sàng tiếp nhận' khi không có căn cứ dữ liệu."""
    state_empty_docs: AgentState = {
        "query": "Có bác sĩ tim mạch nào không?",
        "suggested_department_name": "Tim mạch",
        "available_slots": [],
        "language": "vi",
        "workflow_status": "TRIAGED_READY_FOR_BOOKING",
        "metadata": {
            "is_doctor_inquiry": True,
            "slots_fetched_in_turn": True,
            "data_unavailable": False,
        },
    }

    res = await respond_node(state_empty_docs)
    response_text = res["response"]

    # Phải KHÔNG chứa khẳng định ảo giác "luôn sẵn sàng tiếp nhận"
    assert "luôn sẵn sàng tiếp nhận" not in response_text
    # Phải trung thực báo chưa tìm thấy lịch trống trực tiếp
    assert "chưa tìm thấy thông tin bác sĩ còn lịch trống" in response_text
    assert "Phiếu Đăng Ký Khám" in response_text
