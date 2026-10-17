"""Lưới lịch 7 ngày + giữ ngữ cảnh khi trả lời bằng tên bác sĩ vừa liệt kê + gợi ý cơ sở cùng khu vực."""

from unittest.mock import patch

import pytest

from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
from src.medical_assistant.agent.nodes.router_node import route_intent_node
from src.medical_assistant.api.routes import public_result
from src.medical_assistant.domain.booking_slot_service import (
    answers_listed_doctor,
    build_schedule_grid,
    nearby_facilities,
)
from src.medical_assistant.domain.hybrid_dialogue_service import HybridDialogueService

DA_NANG = "Bệnh viện ĐKQT Vinmec Đà Nẵng"
RIVERSIDE = "Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)"
TIMES_CITY = "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)"


def _doctor(doctor_id, name, slots, workplace="Bệnh viện Đa khoa Quốc tế Vinmec Đà Nẵng"):
    return {
        "id": doctor_id,
        "full_name": name,
        "title": "Bác sĩ chuyên khoa II",
        "specialties": ["Tai - Mũi - Họng"],
        "workplace": workplace,
        "available_slots": [
            {"schedule_id": f"{doctor_id}-{index}", "starts_at": starts_at, "verified": True}
            for index, starts_at in enumerate(slots)
        ],
    }


WEEK = [f"{hour} ngày {day}/10/2026" for day in range(17, 24) for hour in ("08:30 (Sáng)", "14:00 (Chiều)")]
THAI = _doctor("d1", "Nguyễn Văn Thái", WEEK)
HOA = _doctor("d2", "Lê Thị Hoa", WEEK[:2])
LISTED = [THAI, HOA]


def _listed_state(**extra):
    return {
        "workflow_status": "TRIAGED_READY_FOR_BOOKING",
        "last_listed_doctors": LISTED,
        "suggested_department_name": "Tai - Mũi - Họng",
        "facility_preference": DA_NANG,
        "language": "vi",
        **extra,
    }


# ---------- Router: tên bác sĩ trong danh sách vừa hiển thị không bị info agent bắt mất ----------


@pytest.mark.parametrize(
    "query",
    ["BS. Nguyễn Văn Thái", "Nguyễn Văn Thái", "bác sĩ thứ 2", "2", "14:00 chiều 17/10 · Nguyễn Văn Thái"],
)
def test_answers_listed_doctor(query):
    assert answers_listed_doctor(query, LISTED)


@pytest.mark.parametrize(
    "query",
    [
        "BS. Nguyễn Văn Thái có kinh nghiệm bao lâu?",
        "Nguyễn Văn Thái học ở đâu",
        "BS. Trần Văn Bình",  # không có trong danh sách → tra cứu bình thường
        "Bệnh viện có bãi đỗ xe không",
    ],
)
def test_questions_or_other_doctors_are_not_answers(query):
    assert not answers_listed_doctor(query, LISTED)


@pytest.mark.asyncio
async def test_router_keeps_listed_doctor_name_in_booking_flow():
    """Lỗi thật: 'BS. Nguyễn Văn Thái' sau danh sách Đà Nẵng → info agent liệt kê 2 bác sĩ trùng tên ở cơ sở khác."""

    class ExplodingLLM:  # router không được gọi LLM cho câu này
        def with_structured_output(self, *_a, **_k):
            raise AssertionError("LLM router không được gọi")

    result = await route_intent_node({**_listed_state(), "query": "BS. Nguyễn Văn Thái"}, llm=ExplodingLLM())
    assert result["route_destination"] == "analyze"
    assert result["metadata"]["route"] == "booking_followup_answer"


# ---------- Lưới lịch ----------


def test_grid_lists_week_by_day_and_period():
    grid = build_schedule_grid(_listed_state(preferred_date="2026-10-17", preferred_period="afternoon"))
    assert [day["label"] for day in grid["days"]] == [f"{d}/10" for d in range(17, 24)]
    assert grid["days"][0]["weekday"] == "T7"
    assert [c["doctor"] for c in grid["cells"]["2026-10-17|morning"]] == ["Nguyễn Văn Thái", "Lê Thị Hoa"]
    assert [c["doctor"] for c in grid["cells"]["2026-10-18|afternoon"]] == ["Nguyễn Văn Thái"]
    assert grid["cells"]["2026-10-17|afternoon"][0]["reply"] == "14:00 chiều 17/10 · Nguyễn Văn Thái"
    assert grid["highlight"] == "2026-10-17|afternoon"
    assert grid["facility"] == DA_NANG


def test_grid_after_choosing_doctor_shows_only_that_doctor():
    grid = build_schedule_grid(_listed_state(workflow_status="SLOT_CHOICE_REQUIRED", chosen_doctor=HOA))
    assert grid["doctor"] == "Lê Thị Hoa"
    assert set(grid["cells"]) == {"2026-10-17|morning", "2026-10-17|afternoon"}


@pytest.mark.parametrize(
    "extra",
    [
        {"is_emergency": True},  # cấp cứu: không mời đặt lịch
        {"workflow_status": "PROBING_IN_PROGRESS"},
        {"workflow_status": "BOOKING_CONTACT_REQUIRED"},
        {"last_listed_doctors": [_doctor("d9", "Không Lịch", [])]},
    ],
)
def test_grid_hidden_outside_choice_steps(extra):
    assert build_schedule_grid(_listed_state(**extra)) is None


def test_public_result_carries_grid():
    payload = public_result({**_listed_state(), "response": "x", "metadata": {}}, "s1")
    assert payload["schedule_grid"]["cells"]["2026-10-17|morning"]


# ---------- Luồng analyze: bấm ô giữ chỗ ngay; tên bác sĩ → chọn giờ ----------


async def _fallback(self, text, state, **kwargs):
    return HybridDialogueService._fallback_response(text, state), False


async def _turn(state, query):
    with patch.object(HybridDialogueService, "process_turn_async", _fallback):
        state = {**state, "query": query}
        state.update(await analyze_node(state))
        state.update(await respond_node(state))
    return state


def _flow_state():
    return _listed_state(
        probing_turn=2,
        collected_details=["đau họng, ho", "hơn 1 tuần"],
        clinical_facts={"chief_complaint": "sore_throat", "duration_days": 7},
        messages=[],
        is_authenticated=False,
        suggested_department_code="TAI_MUI_HONG",
        ats_level=4,
        max_booking_days=7,
        metadata={},
    )


@pytest.mark.asyncio
async def test_grid_cell_click_holds_that_slot():
    state = await _turn(_flow_state(), "14:00 chiều 18/10 · Nguyễn Văn Thái")
    assert state["chosen_doctor"]["id"] == "d1"
    assert state["chosen_slot"]["schedule_id"] == "d1-3"
    assert state["workflow_status"] != "SLOT_CHOICE_REQUIRED"  # không hỏi lại giờ


@pytest.mark.asyncio
async def test_listed_doctor_name_goes_to_slot_choice():
    state = await _turn(_flow_state(), "BS. Nguyễn Văn Thái")
    assert state["workflow_status"] == "SLOT_CHOICE_REQUIRED"
    assert state["chosen_doctor"]["id"] == "d1"


# ---------- Cơ sở đã chọn không có bác sĩ chuyên khoa → cơ sở cùng khu vực ----------


def test_nearby_facilities():
    assert TIMES_CITY in nearby_facilities(RIVERSIDE)
    assert RIVERSIDE not in nearby_facilities(RIVERSIDE)
    assert nearby_facilities(DA_NANG) == []  # tỉnh khác: không gợi ý chéo tỉnh


@pytest.mark.asyncio
async def test_empty_facility_falls_back_to_same_region():
    times_doctor = _doctor("t1", "Cấn Thị Hằng", WEEK[:4], workplace="Khoa Nội - Bệnh viện Vinmec Times City")

    async def fake_slots(**kwargs):
        return ([dict(times_doctor)] if kwargs.get("facility_id") == TIMES_CITY else []), False, None

    state = {**_flow_state(), "workflow_status": "TRIAGED_AWAITING_SCHEDULE", "last_listed_doctors": []}
    state.pop("facility_preference")
    with patch("src.medical_assistant.domain.doctor_schedule_service.fetch_available_doctors_slots_cached", fake_slots):
        state = await _turn(state, "Xem lịch Tai - Mũi - Họng")
        state = await _turn(state, "Hà Nội")
        state = await _turn(state, "Riverside")
    fallback = state["metadata"]["facility_fallback"]
    assert fallback == {"requested": RIVERSIDE, "found": [TIMES_CITY]}  # tên cơ sở, không lấy chữ "Khoa ..."
    assert "Riverside" in state["response"] and "chưa có lịch trống" in state["response"]
    assert build_schedule_grid(state)["facility"] == TIMES_CITY
