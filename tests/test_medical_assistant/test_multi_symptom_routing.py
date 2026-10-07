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
    result = await respond_node(
        {
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
        }
    )

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
        state["messages"].append(
            {
                "role": "assistant",
                "content": state.get("metadata", {}).get("clarification_question") or "",
            }
        )

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


def test_knee_pain_not_confused_with_headache_in_multi_symptom_pipeline() -> None:
    """Kiểm tra câu 'đau bụng trái kèm đau đầu gối' không bị nhận nhầm thành Thần kinh (đau đầu)."""
    from src.medical_assistant.domain.care_pipeline_service import get_care_pipeline_service
    from src.medical_assistant.domain.clinical_fact_service import ClinicalFactService

    query = "Tôi đang bị đau bụng trái kèm với việc đau đầu gối, tôi nghĩ có thể đây là 2 bệnh khác nhau đúng không? Vậy tôi phải làm gì?"

    # 1. Fact extraction: phải nhận 'abdominal_pain' và 'joint_pain', tuyệt đối KHÔNG có 'headache'
    facts = ClinicalFactService().extract(query)
    assert "abdominal_pain" in facts["positive_facts"]
    assert "joint_pain" in facts["positive_facts"]
    assert "headache" not in facts["positive_facts"]

    # 2. Care pipeline: Bước 1 Tiêu hóa (nội tạng sinh tồn), Bước 2 Chấn thương chỉnh hình / Xương khớp
    pipeline = get_care_pipeline_service().evaluate_multi_specialty_pipeline(query, language="vi")
    assert pipeline.is_multi_specialty is True
    assert pipeline.primary_department == "Khoa Tiêu hóa - Gan mật"
    assert "Khoa Chấn thương chỉnh hình & Cột sống" in pipeline.secondary_departments
    assert "Khoa Thần kinh" not in [s.department_name for s in pipeline.pipeline_steps]


@pytest.mark.asyncio
async def test_multi_task_compound_triage_and_booking_intent() -> None:
    """Kiểm tra xử lý multi-task trong cùng 1 turn: Đa triệu chứng + Đặt lịch hẹn cơ sở Long Biên sáng mai."""
    from src.medical_assistant.agent.nodes.respond_node import respond_node
    from src.medical_assistant.domain.booking_slot_service import generate_clinical_summary

    query = (
        "Tôi bị đau đầu và có nôn khan đấy cùng với việc đó là tôi có đau bụng ở mức nhẹ nhưng âm ỉ kéo dài. "
        "Và tôi đang muốn khám ở cơ sở nào đó nằm ở khu vực long biên vào sáng mai. Bạn lên lịch trình cho tôi và làm phiếu hẹn"
    )

    state = {
        "query": query,
        "language": "vi",
        "patient_name": "Mai Văn Trường",
        "patient_phone": "0912345678",
        "facility_preference": "Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)",
        "preferred_date": "2026-10-06",
        "preferred_period": "morning",
        "collected_details": [query],
        "metadata": {
            "is_booking_intent": True,
        },
    }

    # 1. Clinical summary phải có đủ Đau đầu, Đau bụng, Mức độ nhẹ, Nôn khan
    summary_res = generate_clinical_summary(state, current_text=query)
    summary_text = summary_res["summary"]
    details = summary_res["details"]

    assert "đau đầu" in summary_text.lower()
    assert "đau bụng" in summary_text.lower()
    assert "mức độ nhẹ" in summary_text.lower()
    assert "nôn khan" in summary_text.lower()
    assert "Nôn khan" in details["associated"]
    assert "Nôn ói" not in details["associated"]

    # 2. respond_node phải trả lời ĐỦ CẢ 2 PHẦN: Lộ trình phân tầng VÀ Thông tin lịch hẹn
    res = await respond_node(state)
    resp_text = res["response"]

    assert "Lộ trình Khám Ưu tiên Phân tầng" in resp_text
    assert "Khoa Thần kinh" in resp_text
    assert "Khoa Tiêu hóa - Gan mật" in resp_text
    assert "Thông tin lịch hẹn" in resp_text
    assert "Bệnh viện ĐKQT Vinmec Riverside" in resp_text
    assert "Phiếu Đăng Ký Khám" in resp_text
    assert "0912345678" in resp_text
    assert "[REDACTED_PHONE]" not in resp_text

    # 3. Booking intake snapshot
    intake = res["metadata"]["booking_intake"]
    assert intake is not None
    assert intake["is_multi_specialty"] is True
    assert len(intake["ranked_specialties"]) >= 2
    assert intake["facility_preference"] == "Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)"


@pytest.mark.asyncio
async def test_conversational_booking_confirmation_after_multi_symptom_triage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that after multi-symptom triage, when patient confirms with 'Xác nhận đặt lịch'
    or 'Xác nhận bạn hãy đặt lịch cho tôi', the agent automatically commits the booking,
    issues a booking request code, and returns the reassuring confirmation message."""
    from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
    from src.medical_assistant.domain.booking_slot_service import detect_booking_confirmation

    # Test phrase detection
    assert detect_booking_confirmation("Xác nhận đặt lịch") is True
    assert detect_booking_confirmation("Xác nhận bạn hãy đặt lịch cho tôi") is True
    assert detect_booking_confirmation("Bạn hãy đặt lịch cho tôi") is True
    assert detect_booking_confirmation("Chốt lịch giúp tôi") is True

    # State carried over from turn 1
    state = {
        "query": "Xác nhận bạn hãy đặt lịch cho tôi",
        "language": "vi",
        "patient_name": "Mai Văn Trường",
        "patient_phone": "0364335411",
        "facility_preference": "Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)",
        "preferred_date": "2026-10-06",
        "preferred_period": "morning",
        "suggested_department_name": "Khoa Thần kinh",
        "suggested_department_code": "THAN_KINH",
        "collected_details": ["đau đầu", "nôn khan", "đau bụng"],
        "booking_intake": {
            "required": True,
            "patient_name": "Mai Văn Trường",
            "patient_phone": "0364335411",
            "facility_preference": "Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)",
            "preferred_date": "2026-10-06",
            "preferred_period": "morning",
            "patient_notes": "Bệnh nhân có triệu chứng đau đầu, đau bụng, Mức độ nhẹ. Triệu chứng đi kèm: Nôn khan.",
        },
        "messages": [
            {"role": "user", "content": "Tôi bị đau đầu và có nôn khan..."},
            {"role": "assistant", "content": "Lộ trình Khám Ưu tiên Phân tầng..."},
        ],
    }

    # Mock the DB auto_commit to return a mock request code without live DB connection
    from src.medical_assistant.domain.booking_lookup_service import BookingLookupService
    async def mock_auto_commit(*args, **kwargs):
        return {
            "status": "success",
            "request_id": 9999,
            "request_code": "VNMC-20261006-MV01",
        }
    monkeypatch.setattr(BookingLookupService, "auto_commit_conversational_booking", mock_auto_commit)

    # 1. Analyze node must resolve to CONFIRM_BOOKING_CONVERSATIONALLY
    analyzed_state = await analyze_node(state)
    assert analyzed_state["workflow_status"] == "CONFIRM_BOOKING_CONVERSATIONALLY"

    # Merge analyzed state into current state
    merged_state = {**state, **analyzed_state}

    # 2. Respond node must return the booking confirmation and code, NOT the triage pipeline
    res = await respond_node(merged_state)
    resp_text = res["response"]

    assert "ĐÃ GIỮ CHỖ THÀNH CÔNG" in resp_text
    assert "VNMC-20261006-MV01" in resp_text
    assert "0364335411" in resp_text
    assert "Mai Văn Trường" in resp_text
    assert "nhân viên điều phối" in resp_text
    assert "để ý số điện thoại của mình" in resp_text
    # Must NOT re-render the triage navigation pipeline prompt asking to click the form button
    assert "bấm nút 'Xác nhận gửi thông tin đặt khám'" not in resp_text
