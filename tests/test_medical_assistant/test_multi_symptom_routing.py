import pytest

from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
from src.medical_assistant.domain.clinical_fact_service import ClinicalFactService
from src.medical_assistant.domain.hybrid_dialogue_service import get_hybrid_dialogue_service
from src.medical_assistant.domain.probing_service import DynamicProbingService
from src.medical_assistant.domain.triage_service import ClinicalTriageService


def _conversation_facts() -> dict:
    service = ClinicalFactService()
    facts: dict = {}
    turns = [
        "Tôi đau đầu với đau họng đấy",
        "Tôi đau thêm cả bụng nữa",
        "Tôi có buồn nôn nhẹ",
    ]
    for index, text in enumerate(turns, start=1):
        facts = service.merge(facts, service.extract(text, turn_index=index))
    return facts


def test_complaints_accumulate_without_overwriting_primary() -> None:
    facts = _conversation_facts()

    assert facts["primary_complaint"] == "headache"
    assert facts["active_complaint_codes"] == ["headache", "sore_throat", "abdominal_pain"]
    assert "nausea" in facts["positive_facts"]
    assert [item["first_seen_turn"] for item in facts["complaints"]] == [1, 1, 2]


def test_complaint_can_be_resolved_and_explicit_priority_can_change() -> None:
    service = ClinicalFactService()
    facts = service.merge({}, service.extract("Tôi đau đầu và đau bụng", turn_index=1))
    facts = service.merge(facts, service.extract("Đau bụng là chính", turn_index=2))
    assert facts["primary_complaint"] == "abdominal_pain"

    facts = service.merge(facts, service.extract("Tôi hết đau đầu rồi", turn_index=3))
    complaint_by_code = {item["code"]: item for item in facts["complaints"]}
    assert complaint_by_code["headache"]["status"] == "resolved"
    assert facts["active_complaint_codes"] == ["abdominal_pain"]


def test_multi_system_triage_returns_ranked_candidates_and_one_clarification() -> None:
    facts = _conversation_facts()
    service = ClinicalTriageService()
    base = service.evaluate_symptoms(
        "Tôi đau đầu, đau họng, đau bụng và buồn nôn nhẹ",
        language="vi",
    )
    result = service.resolve_multi_symptom(base, facts, language="vi")

    assert result.is_emergency is False
    assert result.needs_multi_symptom_clarification is True
    assert result.conflict_reason
    assert [item.code for item in result.candidate_specialties] == [
        "THAN_KINH",
        "TAI_MUI_HONG",
        "TIEU_HOA",
    ]
    assert "triệu chứng nào xuất hiện trước" in (result.clarification_question or "")


def test_probing_budget_is_tracked_per_complaint() -> None:
    probing = DynamicProbingService()
    facts = _conversation_facts()
    state = probing.sync_probing_state(facts)

    assert set(state) == {"headache", "sore_throat", "abdominal_pain"}
    assert probing.active_categories(state) == ["DAU_DAU", "DAU_BUNG"]
    assert probing.should_ask_multi_question(state) is True

    state = probing.mark_multi_question_asked(state, facts["active_complaint_codes"])
    assert all(item["questions_asked"] == 1 for item in state.values())
    assert probing.should_ask_multi_question(state) is False


def test_emergency_result_remains_authoritative_with_multiple_complaints() -> None:
    fact_service = ClinicalFactService()
    facts = fact_service.merge({}, fact_service.extract("Tôi đau đầu và đau ngực dữ dội", turn_index=1))
    triage = ClinicalTriageService()
    base = triage.evaluate_symptoms("Tôi đau đầu và đau ngực dữ dội, khó thở", language="vi")
    result = triage.resolve_multi_symptom(base, facts, language="vi")

    assert result.is_emergency is True
    assert result.ats_level.value <= 2
    assert result.needs_multi_symptom_clarification is False


def test_same_day_candidate_is_ranked_before_earlier_standard_complaint() -> None:
    fact_service = ClinicalFactService()
    text = "Tôi đau đầu và đau bụng bên phải phía dưới, đi lại đau hơn"
    facts = fact_service.merge({}, fact_service.extract(text, turn_index=1))
    triage = ClinicalTriageService()
    base = triage.evaluate_symptoms(text, language="vi")
    result = triage.resolve_multi_symptom(base, facts, language="vi")

    assert base.ats_level.value == 3
    assert result.candidate_specialties[0].code == "TIEU_HOA"
    assert result.candidate_specialties[0].ats_level.value == 3
    assert result.candidate_specialties[1].code == "THAN_KINH"
    assert result.candidate_specialties[1].ats_level.value == 4


@pytest.mark.asyncio
async def test_agent_asks_one_combined_question_instead_of_collapsing_to_gastro(monkeypatch) -> None:
    hybrid = get_hybrid_dialogue_service()

    async def fallback_only(text, state, recent_turns, last_assistant_question, allowed_actions):
        return hybrid._fallback_response(text, state), False

    monkeypatch.setattr(hybrid, "process_turn_async", fallback_only)
    state = {
        "query": "Tôi đau đầu với đau họng đấy",
        "messages": [],
        "metadata": {},
        "collected_details": [],
    }
    state.update(await analyze_node(state))
    assert set(state["clinical_facts"]["active_complaint_codes"]) == {"headache", "sore_throat"}
    assert state["workflow_status"] == "PROBING_IN_PROGRESS"
    assert len(state["candidate_specialties"]) == 2

    state["messages"] = [
        {"role": "user", "content": "Tôi đau đầu với đau họng đấy"},
        {"role": "assistant", "content": state["metadata"]["clarification_question"]},
    ]
    state["query"] = "Tôi đau thêm cả bụng nữa"
    state.update(await analyze_node(state))

    assert state["clinical_facts"]["active_complaint_codes"] == [
        "headache",
        "sore_throat",
        "abdominal_pain",
    ]
    assert state["workflow_status"] == "PROBING_IN_PROGRESS"
    assert state["suggested_department_code"] == "THAN_KINH"
    assert {item["code"] for item in state["candidate_specialties"]} == {
        "THAN_KINH",
        "TAI_MUI_HONG",
    }
    assert {item["code"] for item in state["routing_candidates"]} == {
        "THAN_KINH",
        "TAI_MUI_HONG",
        "TIEU_HOA",
    }
    suppressed = next(item for item in state["routing_candidates"] if item["code"] == "TIEU_HOA")
    assert suppressed["publicly_recommended"] is False
    assert suppressed["suppression_reason"] == "public_limit_reached"
    assert "triệu chứng nào xuất hiện trước" in state["metadata"]["clarification_question"]


@pytest.mark.asyncio
async def test_response_names_primary_and_secondary_specialties() -> None:
    result = await respond_node({
        "query": "Tôi đau đầu và đau bụng",
        "language": "vi",
        "workflow_status": "TRIAGED_AWAITING_SCHEDULE",
        "suggested_department_name": "Thần kinh",
        "candidate_specialties": [
            {"code": "THAN_KINH", "name": "Thần kinh", "score": 1.25},
            {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật", "score": 1.0},
        ],
        "metadata": {},
        "collected_details": ["Tôi đau đầu và đau bụng"],
        "messages": [],
    })

    assert "Khoa Thần kinh" in result["response"]
    assert "Tiêu hóa - Gan mật" in result["response"]


def test_chest_tightness_phrase_and_fatigue_are_extracted() -> None:
    service = ClinicalFactService()
    facts = service.extract("Tôi đau tức lồng ngực và cơ thể cảm giác rất mệt", turn_index=1)

    assert facts["chief_complaint"] == "chest_pain"
    assert [item["code"] for item in facts["complaints"]] == ["chest_pain"]
    assert "chest_pain" in facts["positive_facts"]
    assert "fatigue" in facts["positive_facts"]


def test_undifferentiated_chest_discomfort_is_same_day_not_routine() -> None:
    result = ClinicalTriageService().evaluate_symptoms(
        "Tôi đang đau tức lồng ngực nên làm sao",
        language="vi",
    )

    assert result.is_emergency is False
    assert result.ats_level.value == 3
    assert result.disposition == "URGENT_SAME_DAY"
    assert "UNDIFFERENTIATED_CHEST_DISCOMFORT" in result.triggered_rule_ids


def test_likely_cardiac_chest_pain_is_ats2_not_ats1() -> None:
    result = ClinicalTriageService().evaluate_symptoms(
        "Tôi đau tức lồng ngực kèm khó thở và vã mồ hôi",
        language="vi",
    )

    assert result.is_emergency is True
    assert result.ats_level.value == 2
    assert result.disposition == "EMERGENCY_NOW"
    assert "ACS_COMBINED_CARDIAC_RULE" in result.triggered_rule_ids


def test_headache_with_blurred_vision_is_same_day_warning() -> None:
    result = ClinicalTriageService().evaluate_symptoms(
        "Tôi đau đầu và có nhìn mờ",
        language="vi",
    )

    assert result.is_emergency is False
    assert result.ats_level.value == 3
    assert "HEADACHE_WITH_VISUAL_CHANGE" in result.triggered_rule_ids


@pytest.mark.asyncio
async def test_chest_headache_blurred_vision_sequence_blocks_routine_booking(monkeypatch) -> None:
    hybrid = get_hybrid_dialogue_service()

    async def fallback_only(text, state, recent_turns, last_assistant_question, allowed_actions):
        return hybrid._fallback_response(text, state), False

    monkeypatch.setattr(hybrid, "process_turn_async", fallback_only)
    state = {"messages": [], "metadata": {}, "collected_details": []}
    turns = [
        "Tôi đang đau tức lồng ngực nên làm sao",
        "Tôi đau đầu nữa, cơ thể có cảm giác rất mệt",
        "Tôi có nhìn mờ",
    ]
    first_question = ""
    for index, query in enumerate(turns):
        state["query"] = query
        state.update(await analyze_node(state))
        if index == 0:
            first_question = state["metadata"]["clarification_question"]
        state.setdefault("messages", []).append({"role": "user", "content": query})
        state["messages"].append({
            "role": "assistant",
            "content": state.get("metadata", {}).get("clarification_question") or "",
        })

    assert "lan ra cánh tay trái" in first_question
    assert state["workflow_status"] == "SAFETY_REVIEW"
    assert state["ats_level"] == 3
    assert state["max_booking_days"] == 0
    assert state["disposition"] == "SAFETY_REVIEW"
    assert {item["code"] for item in state["candidate_specialties"]} >= {"TIM_MACH", "THAN_KINH"}
    candidate_ats = {item["code"]: item["ats_level"].value for item in state["candidate_specialties"]}
    assert candidate_ats["TIM_MACH"] == 3
    assert candidate_ats["THAN_KINH"] == 3

    response = await respond_node(state)
    assert "đau hoặc tức ngực, đau đầu và nhìn mờ" in response["response"]
    assert "đặt lịch khám thường" in response["response"]


def test_llm_only_secondary_candidate_stays_internal_below_threshold() -> None:
    triage = ClinicalTriageService()
    facts = {
        "primary_complaint": "headache",
        "chief_complaint": "headache",
        "positive_facts": ["headache", "abdominal_pain"],
        "negative_facts": [],
        "complaints": [
            {
                "code": "headache",
                "status": "active",
                "source": "deterministic",
                "evidence": ["đau đầu"],
            },
            {
                "code": "abdominal_pain",
                "status": "active",
                "source": "llm",
                "evidence": ["khó chịu trong người"],
                "confidence": 0.55,
            },
        ],
    }
    base = triage.evaluate_symptoms("Tôi đau đầu", language="vi")
    result = triage.resolve_multi_symptom(base, facts, language="vi")

    assert [item.code for item in result.recommended_specialties] == ["THAN_KINH"]
    gi = next(item for item in result.candidate_specialties if item.code == "TIEU_HOA")
    assert gi.routing_confidence < triage.SECONDARY_ROUTING_THRESHOLD
    assert gi.publicly_recommended is False
    assert gi.suppression_reason == "below_secondary_threshold"


def test_public_specialty_recommendations_are_capped_at_two() -> None:
    result = ClinicalTriageService().resolve_multi_symptom(
        ClinicalTriageService().evaluate_symptoms(
            "Tôi đau đầu, đau họng và đau bụng",
            language="vi",
        ),
        _conversation_facts(),
        language="vi",
    )

    assert len(result.candidate_specialties) == 3
    assert len(result.recommended_specialties) == 2
    assert all(item.publicly_recommended for item in result.recommended_specialties)
