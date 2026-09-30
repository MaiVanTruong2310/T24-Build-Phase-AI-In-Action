import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.guardrail_service import get_guardrail_service


def test_conversation_boundary_intents_are_general_not_exact_sentence_rules():
    guard = get_guardrail_service()

    assert guard.check_intent("Tui rất ghét người kia", current_department="Tiêu hóa - Gan mật")["intent"] == "SOCIAL_STATEMENT"
    third_party = guard.check_intent(
        "Chồng chị tôi bị hiếm muộn thì nên làm gì?",
        current_department="Tiêu hóa - Gan mật",
    )
    assert third_party == {"intent": "THIRD_PARTY_HEALTH_QUERY", "topic": "infertility"}
    assert guard.check_intent("Vậy tôi nên khám khoa nào?", current_department="Tiêu hóa - Gan mật")["intent"] == "SELF_CARE_FOLLOWUP"


@pytest.mark.asyncio
async def test_social_and_third_party_detours_do_not_corrupt_active_clinical_episode():
    config = {"configurable": {"thread_id": "episode-isolation-social-third-party"}}
    initial_details = [
        "Bụng bên trái đau âm ỉ khoảng 4 trên 10, không sốt, không nôn.",
        "Đã ba ngày rồi, không tiêu chảy và không đi ngoài ra máu.",
    ]
    seeded_state = {
        "query": "Tôi ghét anh Thành",
        "ats_level": 4,
        "urgency_tier": "WITHIN_WEEK",
        "max_booking_days": 7,
        "suggested_department_code": "TIEU_HOA",
        "suggested_department_name": "Tiêu hóa - Gan mật",
        "workflow_status": "TRIAGED_AWAITING_SCHEDULE",
        "probing_turn": 2,
        "active_probing_category": "DAU_BUNG",
        "collected_details": initial_details,
        "clinical_facts": {
            "chief_complaint": "abdominal_pain",
            "positive_facts": ["mild_abdominal_pain"],
            "negative_facts": ["fever", "vomiting", "diarrhea", "blood_in_stool"],
            "duration_days": 3,
            "location": "bụng bên trái",
        },
    }

    social = await agent.ainvoke(seeded_state, config=config)
    assert social["workflow_status"] == "SOCIAL_REDIRECT"
    assert social["ats_level"] == 4
    assert social["collected_details"] == initial_details
    assert "không đánh giá" in social["response"]

    third_party = await agent.ainvoke(
        {"query": "Bạn Thành bị vô sinh thì làm thế nào?"},
        config=config,
    )
    assert third_party["workflow_status"] == "THIRD_PARTY_HEALTH_GUIDANCE"
    assert third_party["ats_level"] == 4
    assert third_party["suggested_department_name"] == "Tiêu hóa - Gan mật"
    assert third_party["collected_details"] == initial_details
    assert "Trung tâm Hỗ trợ sinh sản" in third_party["response"]

    self_followup = await agent.ainvoke(
        {"query": "Vậy tôi nên khám ở đâu?"},
        config=config,
    )
    assert self_followup["workflow_status"] == "TRIAGED_AWAITING_SCHEDULE"
    assert self_followup["ats_level"] == 4
    assert self_followup["suggested_department_name"] == "Tiêu hóa - Gan mật"
    assert self_followup["collected_details"] == initial_details


@pytest.mark.asyncio
async def test_doctor_lookup_during_probing_is_not_saved_as_a_symptom():
    config = {"configurable": {"thread_id": "episode-isolation-doctor-lookup"}}
    symptom = "Bụng bên trái của tôi đau âm ỉ khoảng 4 trên 10."
    result = await agent.ainvoke(
        {
            "query": "Cho tôi xin thông tin của các bác sĩ trong khoa này.",
            "ats_level": 4,
            "urgency_tier": "WITHIN_WEEK",
            "max_booking_days": 7,
            "suggested_department_code": "TIEU_HOA",
            "suggested_department_name": "Tiêu hóa - Gan mật",
            "workflow_status": "PROBING_IN_PROGRESS",
            "probing_turn": 1,
            "active_probing_category": "DAU_BUNG",
            "collected_details": [symptom],
            "clinical_facts": {
                "chief_complaint": "abdominal_pain",
                "positive_facts": ["mild_abdominal_pain"],
                "negative_facts": [],
                "location": "bụng bên trái",
            },
        },
        config=config,
    )

    assert result["workflow_status"] == "TRIAGED_READY_FOR_BOOKING"
    assert result["collected_details"] == [symptom]
