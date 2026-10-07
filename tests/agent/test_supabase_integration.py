"""Integration tests against live Supabase and LLM endpoints.

Được đánh dấu @pytest.mark.integration để chứng minh:
1. Supabase không còn bị lỗi HTTP 400 Bad Request trên bảng `doctors`.
2. Truy vấn bác sĩ trả về 200 OK với đầy đủ quan hệ phòng ban và cơ sở (doctor_facilities).
3. LLM Failover hỗ trợ tốt cả tool-calling và structured output (không dính 400 DeepSeek hay 402 OpenRouter).
"""

from __future__ import annotations

import pytest

from src.medical_assistant.agent.nodes.router_node import IntentRouteResult
from src.medical_assistant.agent.tools import ALL_TOOLS
from src.medical_assistant.agent.tools.doctor_tools import (
    get_doctor_detail,
    search_doctors,
)
from src.medical_assistant.domain.doctor_schedule_service import get_doctor_schedule_service
from src.medical_assistant.infrastructure.llm import get_llm


@pytest.mark.integration
def test_supabase_search_doctors_live_query_returns_200():
    """Xác minh truy vấn Supabase doctors trả về dữ liệu thực (không bị lỗi 400, không bị data_unavailable)."""
    result = search_doctors.invoke({"name": "Nguyễn Đình Dũng"})
    assert result["found"] is True
    assert result["data_unavailable"] is False
    assert result["source"] == "supabase.doctors"
    assert len(result["doctors"]) >= 1

    doc = result["doctors"][0]
    assert doc["id"] == "78733882-b3fc-5d35-964e-1376d140ea50"
    assert "Dũng" in doc["full_name"]
    assert doc["data_source"] == "supabase"
    assert doc["schedule_verified"] is True
    assert "Vinmec" in doc["workplace"]


@pytest.mark.integration
def test_supabase_get_doctor_detail_live():
    """Xác minh xem chi tiết bác sĩ theo UUID Supabase lấy đúng cơ sở từ doctor_facilities."""
    doc_id = "78733882-b3fc-5d35-964e-1376d140ea50"
    detail = get_doctor_detail.invoke({"doctor_id": doc_id})
    assert detail["found"] is True
    assert detail["doctor_id"] == doc_id
    assert detail["data_source"] == "supabase"
    assert detail["schedule_verified"] is True
    assert "Vinmec" in detail["workplace"]


@pytest.mark.integration
def test_doctor_schedule_service_database_doctors():
    """Xác minh DoctorScheduleService lấy danh sách bác sĩ từ Supabase thành công."""
    svc = get_doctor_schedule_service()
    results = svc.get_available_doctors_and_slots(specialty_name="tiêu hóa", limit_doctors=2)
    assert len(results) >= 1
    assert any(doc.get("data_source") == "supabase" for doc in results)


@pytest.mark.integration
def test_failover_llm_structured_output():
    """Xác minh with_structured_output hoạt động trơn tru qua chuỗi FailoverChatModel."""
    llm = get_llm()
    structured = llm.with_structured_output(IntentRouteResult)
    try:
        resp = structured.invoke("Tôi muốn tìm bác sĩ tiêu hóa giỏi ở Times City")
    except RuntimeError as exc:
        if "All LLM providers are temporarily unavailable" in str(exc):
            pytest.skip("External LLM provider out of credits / unavailable in current environment")
        raise
    assert isinstance(resp, IntentRouteResult)
    assert resp.route == "info_lookup"
    assert resp.confidence >= 0.7


@pytest.mark.integration
def test_failover_llm_bind_tools():
    """Xác minh bind_tools(ALL_TOOLS) kích hoạt chính xác tool call."""
    llm = get_llm()
    bound = llm.bind_tools(ALL_TOOLS)
    try:
        resp = bound.invoke("Tìm giúp tôi bác sĩ Nguyễn Đình Dũng")
    except RuntimeError as exc:
        if "All LLM providers are temporarily unavailable" in str(exc):
            pytest.skip("External LLM provider out of credits / unavailable in current environment")
        raise
    assert hasattr(resp, "tool_calls")
    assert len(resp.tool_calls) >= 1
    assert resp.tool_calls[0]["name"] in ["search_doctors", "get_doctor_detail"]


@pytest.mark.integration
def test_tools_graceful_data_unavailable_on_db_outage(monkeypatch):
    """Xác minh rằng khi DB gián đoạn, các tool trả cờ data_unavailable=True chứ không crash hoặc nuốt lỗi."""
    from unittest.mock import MagicMock
    from src.medical_assistant.agent.tools.doctor_tools import get_doctor_slots
    from src.medical_assistant.agent.tools.facility_tools import list_facilities
    from src.medical_assistant.agent.tools.department_tools import get_department_info
    from src.medical_assistant.agent.tools.disease_tools import search_disease_knowledge

    # 1. Giả lập get_doctor_schedule_service client bị ngắt kết nối
    mock_svc = MagicMock()
    mock_svc.client.select.side_effect = RuntimeError("Database connection refused")
    monkeypatch.setattr("src.medical_assistant.agent.tools.doctor_tools.get_doctor_schedule_service", lambda: mock_svc)

    slot_res = get_doctor_slots.invoke({"doctor_id": "78733882-b3fc-5d35-964e-1376d140ea50"})
    assert slot_res["found"] is False
    assert slot_res["data_unavailable"] is True
    assert "Database connection refused" in slot_res["reason"]

    # 2. Giả lập FacilityService crash
    mock_fac = MagicMock()
    mock_fac.fetch_active_facilities.side_effect = ConnectionError("Supabase connection reset")
    monkeypatch.setattr("src.medical_assistant.agent.tools.facility_tools.FacilityService", lambda: mock_fac)

    fac_res = list_facilities.invoke({"name": "Times City"})
    assert fac_res["found"] is False
    assert fac_res["data_unavailable"] is True
    assert "Supabase connection reset" in fac_res["reason"]

    # 3. Giả lập GuardrailService crash trong get_department_info
    mock_guard = MagicMock()
    mock_guard.get_department_info_response.side_effect = RuntimeError("Knowledge store unreachable")
    monkeypatch.setattr("src.medical_assistant.agent.tools.department_tools.get_guardrail_service", lambda: mock_guard)

    dept_res = get_department_info.invoke({"department_key": "TIM_MACH"})
    assert dept_res["found"] is False
    assert dept_res["data_unavailable"] is True
    assert "Knowledge store unreachable" in dept_res["reason"]

    # 4. Giả lập TriageService crash trong search_disease_knowledge
    mock_triage = MagicMock()
    monkeypatch.setattr("src.medical_assistant.agent.tools.disease_tools.get_triage_service", lambda: (_ for _ in ()).throw(RuntimeError("Triage DB error")))

    dis_res = search_disease_knowledge.invoke({"query": "sốt xuất huyết"})
    assert dis_res["found"] is False
    assert dis_res["data_unavailable"] is True
    assert "Triage DB error" in dis_res["reason"]


@pytest.mark.integration
def test_failover_llm_circuit_breaker():
    """Xác minh circuit breaker chặn vĩnh viễn provider hết quota (402) mà không chờ đợt sau."""
    from unittest.mock import MagicMock
    from src.medical_assistant.infrastructure.llm import FailoverChatModel

    p1 = MagicMock()
    err_402 = Exception("Insufficient credits (quota exceeded)")
    setattr(err_402, "status_code", 402)
    p1.invoke.side_effect = err_402

    p2 = MagicMock()
    p2.invoke.return_value = "Hello from backup model"

    failover = FailoverChatModel(primary=p1, fallbacks=[p2])
    res = failover.invoke("Xin chào")

    assert res == "Hello from backup model"
    # p1 phải được đánh dấu vĩnh viễn bị loại
    assert 0 in failover._permanently_failed
    assert p1.invoke.call_count == 1

    # Lượt tiếp theo: p1 hoàn toàn không được gọi nữa!
    res2 = failover.invoke("Xin chào lần 2")
    assert res2 == "Hello from backup model"
    assert p1.invoke.call_count == 1

