import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.guardrail_service import ClinicalGuardrailService


def test_generic_hospital_visit_is_detected_without_swallowing_symptoms():
    service = ClinicalGuardrailService()

    assert service.check_intent("Tôi đang muốn khám bệnh ở bệnh viện") == {"intent": "VISIT_PURPOSE_CLARIFICATION"}
    assert service.check_intent("Tôi muốn khám vì đau ngực dữ dội") is None


@pytest.mark.asyncio
async def test_generic_hospital_visit_asks_purpose_before_triage_or_doctor_search():
    result = await agent.ainvoke(
        {"query": "Tôi đang muốn khám bệnh ở bệnh viện"},
        config={"configurable": {"thread_id": "test_visit_purpose_clarification_vi"}},
    )

    assert result["workflow_status"] == "VISIT_PURPOSE_CLARIFICATION"
    assert result["ats_level"] is None
    assert result.get("urgency_tier") is None
    assert result.get("max_booking_days") is None
    assert result.get("suggested_department_name") is None
    assert not result.get("available_slots")
    assert result.get("collected_details") == []

    expected_replies = [
        "Khám vì đang có triệu chứng",
        "Khám sức khỏe tổng quát/định kỳ",
        "Tìm một chuyên khoa cụ thể",
        "Tìm cơ sở bệnh viện gần hoặc phù hợp",
    ]
    assert "Dạ, em có thể hỗ trợ anh/chị. Anh/chị muốn:" in result["response"]  # khách vãng lai
    for reply in expected_replies:
        assert f"- {reply}" in result["response"]
    assert result["metadata"]["quick_replies"] == expected_replies
    assert result["token_usage"]["prompt_tokens"] == 0
    assert result["token_usage"]["completion_tokens"] == 0
