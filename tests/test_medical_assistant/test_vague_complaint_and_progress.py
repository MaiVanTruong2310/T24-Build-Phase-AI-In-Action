"""Người thường kể chung chung → hỏi kiểu khó chịu kèm nút; thanh tiến trình 4 bước dựng từ dữ kiện có cấu trúc."""

from unittest.mock import patch

import pytest

from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
from src.medical_assistant.domain.clinical_fact_service import get_clinical_fact_service
from src.medical_assistant.domain.consultation_progress import build_progress
from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.hybrid_dialogue_service import HybridDialogueService
from src.medical_assistant.domain.hybrid_dialogue_v2_model import HybridDialogueResponse


def _state(query):
    return {
        "query": query,
        "probing_turn": 0,
        "collected_details": [],
        "language": "vi",
        "clinical_facts": {},
        "messages": [],
        "is_authenticated": False,
        "workflow_status": "IDLE",
    }


async def _llm_visit_menu(self, text, state, **kwargs):
    """LLM trả "hỏi mục đích khám" — tình huống từng làm hiện menu cho người đã kể bệnh."""
    return HybridDialogueResponse(primary_intent="visit_request", proposed_action="clarify_visit_purpose"), True


async def _turn(query, state=None):
    state = state or _state(query)
    state["query"] = query
    with patch.object(HybridDialogueService, "process_turn_async", _llm_visit_menu):
        state.update(await analyze_node(state))
        state.update(await respond_node(state))
    return state


@pytest.mark.parametrize(
    "query", ["trong người không khỏe", "tôi thấy không ổn lắm", "người mệt mệt", "thấy bất ổn quá", "I feel unwell"]
)
def test_vague_statements_are_recognised(query):
    assert get_guardrail_service().check_intent(query)["intent"] == "VAGUE_COMPLAINT"


@pytest.mark.parametrize("query", ["trong người không khỏe, đau ngực", "tôi muốn khám bệnh", "đau bụng"])
def test_specific_statements_are_not_vague(query):
    assert (get_guardrail_service().check_intent(query) or {}).get("intent") != "VAGUE_COMPLAINT"


@pytest.mark.asyncio
async def test_vague_statement_gets_one_question_with_layperson_buttons():
    state = await _turn("trong người không khỏe")
    assert state["workflow_status"] == "PROBING_IN_PROGRESS"
    assert state["response"].count("?") == 1
    assert "Khám sức khỏe tổng quát" not in state["response"]
    assert state["quick_replies"] == ["Đau ở một chỗ", "Sốt, ớn lạnh", "Mệt, chóng mặt", "Ho, đau họng"]


@pytest.mark.asyncio
async def test_pain_in_one_spot_button_asks_where():
    state = await _turn("Đau ở một chỗ")
    assert "vùng nào" in state["response"]
    assert state["quick_replies"] == ["Đau đầu", "Đau ngực", "Đau bụng", "Đau lưng"]


@pytest.mark.asyncio
async def test_vague_statement_with_red_flag_still_hits_emergency_gate():
    state = await _turn("trong người không khỏe, đau ngực dữ dội, vã mồ hôi")
    assert state["is_emergency"] is True


@pytest.mark.asyncio
async def test_dizziness_alone_is_not_asked_headache_location():
    state = await _turn("Mệt, chóng mặt")
    assert "đau đầu" not in state["response"].lower()
    assert "quay cuồng" in state["response"]


@pytest.mark.parametrize(
    ("query", "location"),
    [
        ("Tôi bị đau bụng hạ sườn phải", "hạ sườn phải"),
        ("Tôi bị đau bụng dưới bên trái", "bụng dưới bên trái"),
        ("Tôi bị nóng rát vùng thượng vị", "thượng vị"),
        ("Tôi bị đau bụng quanh rốn", "quanh rốn"),
        ("đau bụng bên trái", "bụng bên trái"),
    ],
)
def test_abdominal_location_is_extracted_with_accents(query, location):
    assert get_clinical_fact_service().extract(query, turn_index=1)["location"] == location


def test_stomach_mention_does_not_set_location_for_headache():
    facts = get_clinical_fact_service().extract("tôi bị đau đầu, hay ăn ngoài nên dạ dày cũng yếu", turn_index=1)
    assert facts["location"] is None


@pytest.mark.asyncio
async def test_known_epigastric_location_is_not_asked_again():
    state = await _turn("Dạ dày nóng rát")
    assert "vùng nào trên bụng" not in state["response"]


def _steps(progress):
    return {step["key"]: (step["status"], step["summary"]) for step in progress["steps"]}


def test_progress_while_probing_is_on_details_step():
    progress = build_progress(
        {
            "workflow_status": "PROBING_IN_PROGRESS",
            "clinical_facts": {"chief_complaint": "abdominal_pain", "location": "thượng vị"},
            "collected_details": ["Dạ dày nóng rát"],
            "suggested_department_name": "Tiêu hóa - Gan mật",
            # Phiếu điền sẵn luôn có trong metadata: không được coi là đã định khoa/đặt lịch.
            "metadata": {"booking_intake": {"specialty_name": "Tiêu hóa - Gan mật"}},
        }
    )
    steps = _steps(progress)
    assert progress["current_step"] == 2
    assert steps["symptom"] == ("done", "Đau bụng (thượng vị)")
    assert steps["details"][0] == "current"
    assert steps["specialty"] == ("todo", None)


def test_progress_after_triage_shows_specialty_and_plain_urgency():
    steps = _steps(
        build_progress(
            {
                "workflow_status": "TRIAGED_AWAITING_SCHEDULE",
                "clinical_facts": {"chief_complaint": "abdominal_pain", "duration_days": 3},
                "collected_details": ["đau bụng"],
                "suggested_department_name": "Tiêu hóa - Gan mật",
                "max_booking_days": 7,
                "ats_level": 4,
            }
        )
    )
    assert steps["details"] == ("done", "khoảng 3 ngày nay")
    assert steps["specialty"] == ("done", "Tiêu hóa - Gan mật · nên khám trong tuần")
    assert "ATS" not in str(steps)
    assert steps["booking"][0] == "current"


def test_progress_direct_booking_skips_symptom_steps():
    progress = build_progress(
        {"workflow_status": "CONFIRM_BOOKING_CONVERSATIONALLY", "suggested_department_name": "Trung tâm Tim mạch"}
    )
    steps = _steps(progress)
    assert steps["symptom"][0] == steps["details"][0] == "skipped"
    assert progress["current_step"] == 4


def test_progress_submitted_booking_is_done():
    steps = _steps(
        build_progress(
            {
                "workflow_status": "TRIAGED_READY_FOR_BOOKING",
                "suggested_department_name": "Da liễu",
                "collected_details": ["ngứa"],
                "metadata": {"booking_intake": {"request_code": "YC-1", "facility_preference": "Vinmec Times City"}},
            }
        )
    )
    assert steps["booking"] == ("done", "Vinmec Times City · chờ điều phối viên xác nhận")


def test_progress_emergency_flag_and_unrecognised_symptom_quotes_patient():
    progress = build_progress({"is_emergency": True, "collected_details": ["người cứ lả đi, khó tả lắm"]})
    assert progress["emergency"] is True
    assert _steps(progress)["symptom"] == ("done", "“người cứ lả đi, khó tả lắm”")


@pytest.mark.parametrize(
    ("query", "chief"),
    [
        # Đau lưng + tiểu buốt: nghi đường tiết niệu dù kể đau lưng trước.
        ("Tôi bị đau thắt lưng, tiểu buốt", "urinary_symptoms"),
        ("tiểu buốt kèm đau hông lưng", "urinary_symptoms"),
        ("Tôi bị đau lưng", "back_pain"),
        ("Tôi bị hồi hộp, tim đập nhanh", "palpitations"),
        ("Tôi bị khàn tiếng", "hoarseness"),
        ("Tôi bị nhiệt miệng", "mouth_ulcer"),
    ],
)
def test_new_and_reprioritised_complaints(query, chief):
    assert get_clinical_fact_service().extract(query, turn_index=1)["chief_complaint"] == chief


def test_flank_pain_is_not_read_as_sore_throat():
    """Bỏ dấu "đau hông lưng" thành "dau hong lung" từng khớp nhầm đau họng."""
    facts = get_clinical_fact_service().extract("đau hông lưng", turn_index=1)
    assert "sore_throat" not in facts["positive_facts"]
    assert facts["chief_complaint"] == "back_pain"


def test_denied_palpitations_is_not_a_complaint():
    facts = get_clinical_fact_service().extract("không hồi hộp, chỉ đau đầu", turn_index=1)
    assert facts["chief_complaint"] == "headache"
    assert "palpitations" not in facts["positive_facts"]
