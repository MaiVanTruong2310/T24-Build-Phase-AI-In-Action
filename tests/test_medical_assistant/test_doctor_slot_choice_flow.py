"""Sau khi chọn cơ sở: danh sách bác sĩ có lịch trống → chọn bác sĩ → chọn giờ → giữ chỗ, xin liên hệ (mỗi lượt 1 câu)."""

from unittest.mock import patch

import pytest

from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
from src.medical_assistant.domain.booking_slot_service import match_slot, slot_date_period, slot_label
from src.medical_assistant.domain.consultation_progress import build_progress
from src.medical_assistant.domain.hybrid_dialogue_service import HybridDialogueService

TIMES_CITY = "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)"


def _doctor(doctor_id, name, slots):
    return {
        "id": doctor_id,
        "full_name": name,
        "title": "Bác sĩ",
        "specialties": ["Tiêu hóa - Gan mật"],
        "workplace": "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
        "source_url": "https://www.vinmec.com/x",
        "available_slots": [
            {"schedule_id": f"{doctor_id}-{index}", "starts_at": starts_at, "verified": True}
            for index, starts_at in enumerate(slots)
        ],
    }


DOCTORS = [
    _doctor("d1", "Phạm Đức Huấn", ["08:30 (Sáng) ngày 16/10/2026", "14:00 (Chiều) ngày 16/10/2026"]),
    _doctor("d2", "Tạ Quế Phương", ["08:30 (Sáng) ngày 16/10/2026", "14:00 (Chiều) ngày 17/10/2026"]),
]


async def _fallback(self, text, state, **kwargs):
    return HybridDialogueService._fallback_response(text, state), False


async def _fake_slots(**kwargs):
    return [dict(doctor) for doctor in DOCTORS], False, None


async def _turns(*queries):
    state = {
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
    with (
        patch.object(HybridDialogueService, "process_turn_async", _fallback),
        patch("src.medical_assistant.domain.doctor_schedule_service.fetch_available_doctors_slots_cached", _fake_slots),
    ):
        for query in ("Xem lịch Tiêu hóa - Gan mật", "Times City", *queries):
            state["query"] = query
            state.update(await analyze_node(state))
            state.update(await respond_node(state))
    return state


def _intake(state):
    return (state.get("metadata") or {}).get("booking_intake") or {}


def test_slot_helpers():
    slot = DOCTORS[0]["available_slots"][1]
    assert slot_label(slot) == "14:00 chiều 16/10"
    assert slot_label(slot, "Phạm Đức Huấn") == "14:00 chiều 16/10 · Phạm Đức Huấn"
    assert slot_date_period(slot) == ("2026-10-16", "afternoon")
    assert match_slot("14:00 chiều 16/10", DOCTORS, DOCTORS[0])[1] is slot
    # Cùng giờ ở hai bác sĩ: lấy theo tên trong câu.
    assert match_slot("08:30 sáng 16/10 · Tạ Quế Phương", DOCTORS)[0]["id"] == "d2"
    assert match_slot("9:00 sáng 16/10", DOCTORS) is None


@pytest.mark.asyncio
async def test_doctor_list_asks_which_doctor_with_buttons():
    state = await _turns()
    assert state["workflow_status"] == "TRIAGED_READY_FOR_BOOKING"
    assert state["response"].split("\n---")[0].strip().endswith("Anh/chị muốn khám với bác sĩ nào ạ?")
    assert state["quick_replies"] == ["BS. Phạm Đức Huấn", "BS. Tạ Quế Phương", "Bác sĩ nào cũng được"]


@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["BS. Tạ Quế Phương", "bác sĩ thứ 2", "2", "Tôi muốn khám bác sĩ Tạ Quế Phương"])
async def test_choosing_doctor_shows_that_doctors_times(answer):
    state = await _turns(answer)
    assert state["workflow_status"] == "SLOT_CHOICE_REQUIRED"
    assert state["chosen_doctor"]["id"] == "d2"
    assert state["quick_replies"] == ["08:30 sáng 16/10", "14:00 chiều 17/10", "Để điều phối viên xếp giờ"]
    assert state["facility_preference"] == TIMES_CITY
    assert not state.get("preferred_date")  # "thứ 2" là thứ tự bác sĩ, không phải ngày thứ Hai


@pytest.mark.asyncio
async def test_choosing_time_holds_slot_and_fills_form():
    state = await _turns("BS. Tạ Quế Phương", "14:00 chiều 17/10")
    intake = _intake(state)
    assert state["workflow_status"] == "BOOKING_CONTACT_REQUIRED"
    assert "chọn giờ **14:00 chiều 17/10** với **BS. Tạ Quế Phương**" in state["response"]
    assert intake["selected_doctor_id"] == "d2"
    assert intake["selected_slot_id"] == "d2-1"
    assert (intake["preferred_date"], intake["preferred_period"]) == ("2026-10-17", "afternoon")
    booking = {step["key"]: step for step in build_progress(state)["steps"]}["booking"]
    assert "BS. Tạ Quế Phương · 14:00 chiều 17/10" in booking["summary"]


@pytest.mark.asyncio
async def test_any_doctor_lists_times_with_names_then_picks_that_doctor():
    state = await _turns("Bác sĩ nào cũng được")
    assert state["workflow_status"] == "SLOT_CHOICE_REQUIRED"
    assert state["quick_replies"][0] == "08:30 sáng 16/10 · Phạm Đức Huấn"
    state = await _turns("Bác sĩ nào cũng được", "08:30 sáng 16/10 · Tạ Quế Phương")
    assert state["chosen_doctor"]["id"] == "d2"
    assert _intake(state)["selected_slot_id"] == "d2-0"


@pytest.mark.asyncio
async def test_coordinator_scheduling_skips_time_choice():
    state = await _turns("BS. Tạ Quế Phương", "Để điều phối viên xếp giờ")
    assert state["workflow_status"] == "CONFIRM_BOOKING_CONVERSATIONALLY"
    assert _intake(state)["selected_doctor_id"] == "d2"
    assert not _intake(state).get("selected_slot_id")


@pytest.mark.asyncio
async def test_switching_doctor_while_choosing_time():
    state = await _turns("BS. Tạ Quế Phương", "BS. Phạm Đức Huấn")
    assert state["workflow_status"] == "SLOT_CHOICE_REQUIRED"
    assert state["chosen_doctor"]["id"] == "d1"
