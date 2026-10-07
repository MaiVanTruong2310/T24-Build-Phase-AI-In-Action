import os
from unittest.mock import patch
import pytest

from src.medical_assistant.agent.graph import agent


@pytest.fixture(autouse=True)
def mock_offline_llm():
    """Bảo đảm test suite offline chạy hoàn toàn độc lập, không phụ thuộc API mạng hay LLM provider.
    Nếu RUN_LIVE_LLM=true thì cho phép kiểm thử e2e với LLM thật.
    """
    if os.getenv("RUN_LIVE_LLM", "").lower() in ("true", "1", "yes"):
        yield
    else:
        with patch(
            "src.medical_assistant.infrastructure.llm.FailoverChatModel._ainvoke_candidates",
            side_effect=RuntimeError("Offline test mode - LLM network disabled"),
        ), patch(
            "src.medical_assistant.domain.hybrid_dialogue_service.get_llm",
            side_effect=RuntimeError("Offline test mode - LLM network disabled"),
        ):
            yield


@pytest.mark.asyncio
async def test_constipation_diagnosis_question_routes_to_gastro_without_disease_suggestions():
    result = await agent.ainvoke(
        {"query": "Tôi bị táo bón và nóng trong người đấy, tôi có bị bệnh gì nghiêm trọng không?"},
        config={"configurable": {"thread_id": "test_constipation_diagnosis_routing"}},
    )

    assert result["workflow_status"] == "GUARDRAIL_DIAGNOSIS"
    assert result["suggested_department_name"] == "Tiêu hóa - Gan mật"
    assert result["ats_level"] == 4
    assert "Triệu chứng bắt đầu từ khi nào" in result["response"]
    assert "0–10" in result["response"]
    assert "Khoa Thần kinh" not in result["response"]
    assert "Migraine" not in result["response"]
    assert "Đau đầu căng thẳng" not in result["response"]
    assert "không nên tự liệt kê các bệnh" in result["response"]


@pytest.mark.asyncio
async def test_red_flag_inside_diagnosis_question_is_still_emergency():
    result = await agent.ainvoke(
        {"query": "Tôi đau ngực dữ dội, vã mồ hôi lạnh, tôi bị bệnh gì?"},
        config={"configurable": {"thread_id": "test_diagnosis_question_with_red_flag"}},
    )

    assert result["workflow_status"] == "EMERGENCY"
    assert result["is_emergency"] is True
    assert result["ats_level"] in {1, 2}


@pytest.mark.asyncio
async def test_new_explicit_symptom_adds_secondary_without_overriding_higher_acuity():
    config = {"configurable": {"thread_id": "test_new_symptom_overrides_stale_specialty"}}
    await agent.ainvoke({"query": "Tôi bị ho nhiều và khó thở nhẹ"}, config=config)

    result = await agent.ainvoke(
        {"query": "Tôi bị táo bón, tôi có bị bệnh gì nghiêm trọng không?"},
        config=config,
    )

    assert result["suggested_department_name"] == "Nội hô hấp"
    assert result["ats_level"] == 3
    assert [item["code"] for item in result["candidate_specialties"]] == ["HO_HAP", "TIEU_HOA"]
    assert "Khoa Nội hô hấp" in result["response"]
    assert "Tiêu hóa - Gan mật" in result["response"]
