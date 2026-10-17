"""Unit tests for staff agent multi-intent planner and feasibility evaluation."""

from src.agents.staff_agent_planner import decompose_and_evaluate_tasks
from src.agents.staff_agent_router import route_staff_request


def test_decompose_single_intent_is_not_multi_intent():
    result = decompose_and_evaluate_tasks("Tra cứu lịch khám của bác sĩ Nguyễn Văn A")
    assert not result.is_multi_intent
    assert result.tasks == []


def test_decompose_executable_patient_and_today_case():
    query = "Tra cứu hồ sơ bệnh nhân Nguyễn Văn A và các ca cấp cứu hôm nay"
    result = decompose_and_evaluate_tasks(query)

    assert result.is_multi_intent
    assert result.all_executable
    domains = [t.domain for t in result.tasks]
    assert "patient_profile" in domains
    assert "today_coordination_cases" in domains

    patient_task = next(t for t in result.tasks if t.domain == "patient_profile")
    assert patient_task.is_executable
    assert "nguyen van a" in patient_task.extracted_entities.get("patient_name", "").lower()

    case_task = next(t for t in result.tasks if t.domain == "today_coordination_cases")
    assert case_task.is_executable
    assert case_task.filters.get("received_today") is True
    assert case_task.filters.get("emergency_only") is True


def test_decompose_missing_patient_identifier_requires_clarification():
    query = "Tra cứu hồ sơ bệnh nhân đi, hôm nay tiếp nhận các ca nào"
    result = decompose_and_evaluate_tasks(query)

    assert result.is_multi_intent
    assert not result.all_executable
    patient_task = next(t for t in result.tasks if t.domain == "patient_profile")
    assert not patient_task.is_executable
    assert "tên hoặc mã" in patient_task.missing_reason


def test_router_auto_executes_when_all_subtasks_are_executable():
    query = "Tra cứu hồ sơ bệnh nhân Nguyễn Văn A và các ca cấp cứu hôm nay"
    route = route_staff_request(query)

    assert route.category == "complex"
    assert route.reason_code == "multi_intent_auto_execute"
    assert route.reply is None
    assert "search_staff_patients" in route.tool_names
    assert "search_staff_cases" in route.tool_names
    assert len(route.tasks) >= 2


def test_router_requests_confirmation_when_patient_name_is_missing():
    query = "Tra cứu hồ sơ bệnh nhân đi, hôm nay tiếp nhận các ca nào"
    route = route_staff_request(query)

    assert route.category == "confirmation"
    assert route.reply is not None
    assert "xác nhận" in route.reply.lower() or "tên hoặc mã" in route.reply.lower()
