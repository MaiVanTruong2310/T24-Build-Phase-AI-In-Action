"""
Unit tests verifying Prompt 6 benchmark dataset and eval runner.
"""

import json
from pathlib import Path

import pytest


def test_eval_dataset_integrity():
    """Kiểm tra tính toàn vẹn của dataset benchmark tests/eval/info_questions.jsonl (>= 100 câu)."""
    dataset_path = Path("tests/eval/info_questions.jsonl")
    assert dataset_path.exists(), "Dataset info_questions.jsonl must exist"

    with open(dataset_path, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) >= 100, f"Dataset must contain at least 100 questions, got {len(lines)}"

    required_keys = {"id", "category", "query", "expected_route", "expected_tool"}
    categories = set()
    routes = set()

    for idx, line in enumerate(lines):
        data = json.loads(line)
        for k in required_keys:
            assert k in data, f"Line {idx} missing key '{k}': {data}"
        assert data["expected_route"] in {"info_agent", "analyze", "respond"}, (
            f"Invalid route: {data['expected_route']}"
        )
        categories.add(data["category"])
        routes.add(data["expected_route"])

    assert "doctor_lookup" in categories
    assert "facility_lookup" in categories
    assert "department_info" in categories
    assert "disease_knowledge" in categories
    assert "clinical_symptom" in categories
    assert "emergency_red_flag" in categories
    assert "safety_guardrails" in categories
    assert "info_agent" in routes
    assert "analyze" in routes


def test_eval_report_generated():
    """Kiểm tra báo cáo benchmark markdown reports/eval_info.md đã được xuất."""
    report_path = Path("reports/eval_info.md")
    assert report_path.exists(), "Report reports/eval_info.md must exist"

    content = report_path.read_text(encoding="utf-8")
    assert "# Báo Cáo Đánh Giá & Benchmark" in content
    assert "Route Accuracy" in content
    assert "Grounded Rate" in content
    assert "Hallucination Rate" in content


def test_eval_grounding_detects_fake_doctor_entity():
    """Kiểm tra logic Prompt D: câu trả lời nhắc tới bác sĩ không có trong tool_results phải bị coi là Hallucination."""
    from scripts.eval_info import evaluate_grounded_and_hallucination

    resp = "Bác sĩ Nguyễn Tự Bịa là chuyên gia tim mạch hàng đầu với 20 năm kinh nghiệm."
    tool_results = [{"tool": "search_doctors", "data": [{"full_name": "Trần Văn Bình"}]}]
    forbidden_facts = ["Bác sĩ David Copperfield"]

    is_grounded, has_halluc, reasons = evaluate_grounded_and_hallucination(resp, tool_results, forbidden_facts)
    assert has_halluc is True
    assert is_grounded is False
    assert any("không có trong tool_results" in r for r in reasons)


def test_eval_grounding_accepts_verified_doctor_entity():
    """Kiểm tra logic Prompt D: câu trả lời nhắc tới bác sĩ có trong tool_results là Grounded."""
    from scripts.eval_info import evaluate_grounded_and_hallucination

    resp = "Tại Khoa Tai Mũi Họng, Bác sĩ Trần Văn Bình là chuyên gia giàu kinh nghiệm."
    tool_results = [{"tool": "search_doctors", "data": [{"full_name": "Trần Văn Bình"}]}]
    forbidden_facts = ["Bác sĩ John Doe"]

    is_grounded, has_halluc, reasons = evaluate_grounded_and_hallucination(resp, tool_results, forbidden_facts)
    assert has_halluc is False
    assert is_grounded is True
    assert len(reasons) == 0


def test_eval_grounding_detects_forbidden_facts():
    """Kiểm tra logic Prompt D: chứa forbidden_facts động kích hoạt Hallucination."""
    from scripts.eval_info import evaluate_grounded_and_hallucination

    resp = "Dạ, chi phí khám trọn gói tại đây là 500.000.000 VNĐ thưa bác."
    tool_results = []
    forbidden_facts = ["500.000.000 VNĐ"]

    is_grounded, has_halluc, reasons = evaluate_grounded_and_hallucination(resp, tool_results, forbidden_facts)
    assert has_halluc is True
    assert is_grounded is False
    assert any("forbidden fact" in r for r in reasons)


def test_compute_percentiles():
    """Kiểm tra tính toán độ trễ phân vị p50 và p95."""
    from scripts.eval_info import compute_percentiles

    latencies = [100.0 * i for i in range(1, 101)]
    p50, p95 = compute_percentiles(latencies)
    assert p50 == 5100.0 or 5000.0 <= p50 <= 5200.0
    assert p95 == 9600.0 or 9500.0 <= p95 <= 9600.0


def test_simulate_db_error_sets_data_unavailable():
    """G5.2: Kiểm tra khi DoctorScheduleService.client = None, tool trả về data_unavailable=True."""
    from src.medical_assistant.agent.tools.doctor_tools import get_doctor_slots, search_doctors
    from src.medical_assistant.domain.doctor_schedule_service import get_doctor_schedule_service

    svc = get_doctor_schedule_service()
    orig_client = getattr(svc, "client", None)
    try:
        svc.client = None
        # Gọi search_doctors
        res_search = search_doctors.invoke({"specialty": "tim mạch"})
        assert res_search.get("data_unavailable") is True, (
            "search_doctors must set data_unavailable=True when client is None"
        )

        # Gọi get_doctor_slots
        res_slots = get_doctor_slots.invoke({"doctor_id": "doc-test-123"})
        assert res_slots.get("data_unavailable") is True, (
            "get_doctor_slots must set data_unavailable=True when client is None"
        )
    finally:
        svc.client = orig_client


def test_generate_markdown_report_trial_mode_warnings():
    """G5.1 & G5.3: Báo cáo khi chạy thử nghiệm (<50 câu) phải có tiêu đề CHẠY THỬ NGHIỆM và warning cỡ mẫu."""
    from scripts.eval_info import generate_markdown_report

    runtime_summary = "deepseek (8 c\u00e2u), openrouter (2 c\u00e2u - fallback: 2)"
    eval_data = {
        "total_queries": 10,
        "runtime_providers_summary": runtime_summary,
        "model_name": "deepseek-chat",
        "provider_name": "deepseek",
        "llm_error_count": 0,
        "crawl_count": 0,
        "gate_safety_accuracy_pct": 100.0,
        "gate_items_count": 2,
        "route_accuracy_pct": 100.0,
        "tool_accuracy_pct": 100.0,
        "grounded_rate_pct": 100.0,
        "hallucination_rate_pct": 0.0,
        "clarify_rate_pct": 0.0,
        "fallback_rate_pct": 20.0,
        "latency_p50_ms": 1200.0,
        "latency_p95_ms": 2500.0,
        "category_metrics": {
            "doctor_lookup": {
                "count": 10,
                "route_accuracy": 100.0,
                "tool_accuracy": 100.0,
                "grounded_rate": 100.0,
                "hallucination_rate": 0.0,
                "clarify_rate": 0.0,
                "p50_ms": 1200,
                "p95_ms": 2500,
            }
        },
        "agg_entities": {},
        "detailed_results": [],
    }

    report = generate_markdown_report(eval_data, is_valid_dataset=True)
    assert "CH\u1ea0Y TH\u1eec NGHI\u1ec6M - 10 C\xc2U" in report
    assert "GI\u1edaI H\u1ea0N V\u1ec0 C\u1ee0 M\u1eaaU TH\u1eec NGHI\u1ec6M" in report
    assert "ch\u01b0a \u0111\u1ee7 \xfd ngh\u0129a th\u1ed1ng k\xea" in report
    assert "Provider th\u1ef1c t\u1ebf (Runtime):" in report
    assert runtime_summary in report
    assert "\u2705 Ho\xe0n h\u1ea3o!" not in report


@pytest.mark.asyncio
async def test_evaluate_single_item_db_error_restores_client():
    """G5.2: Kiểm tra evaluate_single_item patch svc.client = None và luôn restore trong finally."""
    from unittest.mock import AsyncMock, MagicMock

    from scripts.eval_info import evaluate_single_item
    from src.medical_assistant.domain.doctor_schedule_service import get_doctor_schedule_service

    svc = get_doctor_schedule_service()
    dummy_client = MagicMock()
    svc.client = dummy_client

    mock_graph = MagicMock()
    client_during_invocation = "UNSET"

    async def fake_ainvoke(state, config=None):
        nonlocal client_during_invocation
        client_during_invocation = getattr(svc, "client", None)
        return {
            "response": "Hệ thống cơ sở dữ liệu tạm thời gián đoạn, xin vui lòng gọi 1900 232 389 để được hỗ trợ.",
            "workflow_status": "INFO_ANSWERED",
            "metadata": {
                "route": "info_agent",
                "data_unavailable": True,
                "tools_called": ["search_doctors"],
            },
        }

    mock_graph.ainvoke = AsyncMock(side_effect=fake_ainvoke)

    item = {
        "id": "test_db_err_01",
        "category": "db_error",
        "query": "Tra cứu bác sĩ tim mạch khi DB ngắt kết nối",
        "expected_route": "info_agent",
        "expected_tool": "search_doctors",
    }

    res = await evaluate_single_item(mock_graph, item)

    # 1. Trong lúc gọi graph, client phải là None
    assert client_during_invocation is None, "svc.client must be None during graph invocation for db_error category"
    # 2. Sau khi gọi xong, client phải được restore về dummy_client
    assert svc.client is dummy_client, "svc.client must be restored in finally block"
    # 3. Kết quả xác nhận ca DB error đạt chuẩn
    assert res["db_error_verified"] is True
