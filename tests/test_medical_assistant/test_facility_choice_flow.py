"""Sau gợi ý chuyên khoa, trước khi tra lịch: hỏi khu vực → cơ sở (mỗi lượt một câu), rồi tra lịch theo nơi đã chọn."""

from unittest.mock import patch

import pytest

from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
from src.medical_assistant.domain.booking_slot_service import (
    detect_facility_region,
    facility_choice_prompt,
    is_facility_answer,
    wants_any_facility,
)
from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.hybrid_dialogue_service import HybridDialogueService

FACILITY_CALLS: list[str | None] = []


async def _fallback(self, text, state, **kwargs):
    return HybridDialogueService._fallback_response(text, state), False


async def _fake_slots(**kwargs):
    facility = kwargs.get("facility_id")
    FACILITY_CALLS.append(facility)
    # Chỉ Smart City còn lịch → kiểm tra việc tra lần lượt các cơ sở trong khu vực.
    if facility and "Smart City" in facility:
        return (
            [
                {
                    "full_name": "BS A",
                    "doctor_name": "BS A",
                    "title": "Bác sĩ",
                    "specialty": "Tiêu hóa - Gan mật",
                    "workplace": facility,
                    "slots": [],
                }
            ],
            False,
            None,
        )
    return [], False, None


def _triaged_state():
    return {
        "probing_turn": 2,
        "collected_details": ["đau bụng thượng vị", "khoảng 3 ngày nay"],
        "language": "vi",
        "clinical_facts": {"chief_complaint": "abdominal_pain", "duration_days": 3},
        "messages": [],
        "is_authenticated": False,
        "workflow_status": "TRIAGED_AWAITING_SCHEDULE",
        "suggested_department_name": "Tiêu hóa - Gan mật",
        "suggested_department_code": "TIEU_HOA",
        "ats_level": 4,
        "max_booking_days": 7,
    }


async def _turns(*queries):
    state = _triaged_state()
    FACILITY_CALLS.clear()
    with (
        patch.object(HybridDialogueService, "process_turn_async", _fallback),
        patch(
            "src.medical_assistant.domain.doctor_schedule_service.fetch_available_doctors_slots_cached",
            _fake_slots,
        ),
    ):
        for query in queries:
            state["query"] = query
            state.update(await analyze_node(state))
            state.update(await respond_node(state))
    return state


@pytest.mark.parametrize(
    ("text", "region"),
    [
        ("Hà Nội", "Hà Nội"),
        ("ha noi", "Hà Nội"),
        ("TP.HCM", "TP.HCM"),
        ("Sài Gòn", "TP.HCM"),
        ("Tỉnh/thành khác", "Tỉnh/thành khác"),
    ],
)
def test_detect_region(text, region):
    assert detect_facility_region(text) == region


@pytest.mark.parametrize("text", ["Cơ sở nào cũng được", "Cơ sở nào ở Hà Nội cũng được", "bất kỳ"])
def test_any_facility(text):
    assert wants_any_facility(text)


def test_facility_answer_recognises_branch_names_but_not_symptoms():
    assert is_facility_answer("Times City")
    assert not is_facility_answer("tôi bị đau đầu")


def test_prompts_ask_one_question_with_at_most_four_buttons():
    for region in (None, "Hà Nội", "Tỉnh/thành khác"):
        text, buttons = facility_choice_prompt(region)
        assert text.count("?") == 1
        assert 1 <= len(buttons) <= 4


@pytest.mark.asyncio
async def test_view_schedule_without_facility_asks_region_first():
    state = await _turns("Xem lịch Tiêu hóa - Gan mật")
    assert state["workflow_status"] == "FACILITY_CHOICE_REQUIRED"
    assert "khu vực" in state["response"]
    assert state["quick_replies"] == ["Hà Nội", "TP.HCM", "Tỉnh/thành khác", "Cơ sở nào cũng được"]
    assert FACILITY_CALLS == []  # chưa tra lịch khi chưa biết nơi khám


@pytest.mark.asyncio
async def test_region_then_facility_searches_that_facility():
    state = await _turns("Xem lịch Tiêu hóa - Gan mật", "Hà Nội")
    assert state["workflow_status"] == "FACILITY_CHOICE_REQUIRED"
    assert "Times City" in state["response"] and "Royal City" in state["response"]
    state = await _turns("Xem lịch Tiêu hóa - Gan mật", "Hà Nội", "Times City")
    assert state["workflow_status"] == "TRIAGED_READY_FOR_BOOKING"
    # Tra đúng cơ sở đã chọn trước; dữ liệu giả không có bác sĩ → mới tra thêm các cơ sở cùng khu vực để gợi ý.
    assert FACILITY_CALLS[0] == "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)"
    assert all("Hà Nội" in call for call in FACILITY_CALLS)


@pytest.mark.asyncio
async def test_single_facility_region_is_chosen_directly():
    state = await _turns("Xem lịch Tiêu hóa - Gan mật", "TP.HCM")
    assert state["facility_preference"] == "Bệnh viện ĐKQT Vinmec Central Park (TP.HCM)"
    assert state["workflow_status"] == "TRIAGED_READY_FOR_BOOKING"


@pytest.mark.asyncio
async def test_any_facility_in_region_searches_facilities_in_turn():
    state = await _turns("Xem lịch Tiêu hóa - Gan mật", "Hà Nội", "Cơ sở nào ở Hà Nội cũng được")
    assert state["workflow_status"] == "TRIAGED_READY_FOR_BOOKING"
    assert FACILITY_CALLS[:2] == [
        "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)",
        "Phòng khám ĐKQT Vinmec Smart City (Hà Nội)",
    ]
    assert all("Hà Nội" in call for call in FACILITY_CALLS)


@pytest.mark.asyncio
async def test_any_facility_skips_question_and_is_not_asked_again():
    state = await _turns("Xem lịch Tiêu hóa - Gan mật", "Cơ sở nào cũng được")
    assert state["workflow_status"] == "TRIAGED_READY_FOR_BOOKING"
    assert state["facility_choice_skipped"] is True
    assert len(FACILITY_CALLS) == 1 and not FACILITY_CALLS[0]  # tra lịch không lọc cơ sở


@pytest.mark.asyncio
async def test_facility_named_up_front_is_not_asked():
    state = await _turns("Xem lịch Tiêu hóa ở Vinmec Times City")
    assert state["workflow_status"] != "FACILITY_CHOICE_REQUIRED"
    assert state["facility_preference"] == "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)"


@pytest.mark.asyncio
async def test_new_symptom_while_choosing_facility_goes_back_to_triage():
    state = await _turns("Xem lịch Tiêu hóa - Gan mật", "à mà tôi còn bị đau đầu nữa")
    assert state["workflow_status"] not in {"FACILITY_CHOICE_REQUIRED", "THIRD_PARTY_HEALTH_GUIDANCE"}


@pytest.mark.parametrize(
    ("query", "third_party"),
    [
        ("à mà tôi còn bị đau đầu nữa", False),
        ("tôi cũng bị ho", False),
        ("mẹ tôi bị đau đầu", True),
        ("má tôi còn bị sốt", True),
        ("chồng tôi bị ho", True),
    ],
)
def test_first_person_with_adverb_is_not_third_party(query, third_party):
    intent = (get_guardrail_service().check_intent(query) or {}).get("intent")
    assert (intent == "THIRD_PARTY_HEALTH_QUERY") is third_party
