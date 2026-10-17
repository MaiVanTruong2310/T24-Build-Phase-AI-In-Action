"""Hồi quy cho 10 lỗi tìm thấy khi review luồng chọn nơi khám → bác sĩ → giờ (trước khi tạo PR)."""

from unittest.mock import patch

import pytest

from src.medical_assistant.agent.nodes.example_node import analyze_node, respond_node
from src.medical_assistant.domain.booking_slot_service import (
    detect_facility_region,
    slot_choice_prompt,
    wants_any_facility,
    wants_coordinator_scheduling,
)
from src.medical_assistant.domain.clinical_fact_service import get_clinical_fact_service
from src.medical_assistant.domain.hybrid_dialogue_service import HybridDialogueService
from src.services.chat_history import STATE_FIELDS


def _doctor(doctor_id, name, slots):
    return {
        "id": doctor_id,
        "full_name": name,
        "workplace": "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
        "available_slots": [
            {"schedule_id": f"{doctor_id}-{index}", "starts_at": starts_at, "verified": True}
            for index, starts_at in enumerate(slots)
        ],
    }


DOCTORS = [
    _doctor("d1", "Phạm Đức Huấn", ["08:30 (Sáng) ngày 16/10/2026", "14:00 (Chiều) ngày 16/10/2026"]),
    _doctor("d2", "Tạ Quế Phương", ["09:00 (Sáng) ngày 17/10/2026"]),
    _doctor("d3", "Lê Văn Không Lịch", []),
]


async def _fallback(self, text, state, **kwargs):
    return HybridDialogueService._fallback_response(text, state), False


def _state(status, **extra):
    return {
        "probing_turn": 2,
        "collected_details": ["đau bụng thượng vị"],
        "language": "vi",
        "clinical_facts": {"chief_complaint": "abdominal_pain"},
        "messages": [],
        "is_authenticated": False,
        "workflow_status": status,
        "suggested_department_name": "Tiêu hóa - Gan mật",
        "suggested_department_code": "TIEU_HOA",
        "ats_level": 4,
        "max_booking_days": 7,
        "facility_preference": "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)",
        "last_listed_doctors": DOCTORS,
        **extra,
    }


async def _turn(state, query, slots=None):
    async def fake_slots(**kwargs):
        return (slots if slots is not None else DOCTORS), False, None

    state = {**state, "query": query}
    with (
        patch.object(HybridDialogueService, "process_turn_async", _fallback),
        patch("src.medical_assistant.domain.doctor_schedule_service.fetch_available_doctors_slots_cached", fake_slots),
    ):
        state.update(await analyze_node(state))
        state.update(await respond_node(state))
    return state


# 1. Chặn kê đơn (SAF-02) không được bị bước chọn nơi khám / bác sĩ / giờ nuốt mất.
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "query"),
    [
        ("FACILITY_CHOICE_REQUIRED", "Hà Nội, mà tôi nên uống thuốc gì cho đỡ đau?"),
        ("TRIAGED_READY_FOR_BOOKING", "Bác sĩ nào cũng được, mà tôi nên uống thuốc gì?"),
        ("SLOT_CHOICE_REQUIRED", "BS. Tạ Quế Phương, mà tôi nên uống thuốc gì?"),
    ],
)
async def test_medication_guardrail_survives_choice_steps(status, query):
    state = await _turn(_state(status), query)
    assert state["workflow_status"] == "GUARDRAIL_MEDICATION"
    assert "kê đơn" in state["response"]


# 2. Lựa chọn mới phải được lưu để khôi phục hội thoại (restart/deploy, worker khác, trả phiên).
def test_choice_fields_are_persisted():
    assert {"facility_region", "facility_choice_skipped", "chosen_doctor", "chosen_slot"} <= STATE_FIELDS


# 3. "đau vài hôm" (bỏ dấu = "dau vai hom") không phải đau vai.
@pytest.mark.parametrize(
    ("query", "chief"),
    [
        ("Tôi bị đau vài hôm nay ở bụng", "abdominal_pain"),
        ("đau vài ngày rồi, ở bụng dưới bên phải", "abdominal_pain"),
        ("Tôi bị đau vai", "neck_shoulder_pain"),
        ("đau mỏi vai khi giơ tay", "neck_shoulder_pain"),
    ],
)
def test_dau_vai_vs_dau_vai_hom(query, chief):
    assert get_clinical_fact_service().extract(query, turn_index=1)["chief_complaint"] == chief


# 4. Đổi bác sĩ / tra lịch mới phải bỏ giờ đã chọn (không ghép giờ của BS này với BS khác).
@pytest.mark.asyncio
async def test_switching_doctor_clears_chosen_slot():
    held = _state("BOOKING_CONTACT_REQUIRED", chosen_doctor=DOCTORS[0], chosen_slot=DOCTORS[0]["available_slots"][0])
    state = await _turn({**held, "workflow_status": "SLOT_CHOICE_REQUIRED"}, "BS. Tạ Quế Phương")
    intake = (state.get("metadata") or {}).get("booking_intake") or {}
    assert state["chosen_doctor"]["id"] == "d2"
    assert state["chosen_slot"] is None
    assert intake.get("selected_slot_id") is None
    assert intake.get("selected_doctor_id") == "d2"


@pytest.mark.asyncio
async def test_new_search_clears_previous_choice():
    held = _state(
        "FACILITY_CHOICE_REQUIRED",
        facility_preference=None,
        chosen_doctor=DOCTORS[0],
        chosen_slot=DOCTORS[0]["available_slots"][0],
    )
    state = await _turn(held, "Times City")  # chọn cơ sở → tra lịch mới
    assert state["chosen_doctor"] is None and state["chosen_slot"] is None


# 5. "ngoài Hà Nội" là tỉnh/thành khác; nút tiếng Anh cũng được nhận.
@pytest.mark.parametrize(
    ("text", "region"),
    [
        ("Tôi ở ngoài Hà Nội", "Tỉnh/thành khác"),
        ("ngoai ha noi", "Tỉnh/thành khác"),
        ("Other provinces", "Tỉnh/thành khác"),
        ("Hà Nội", "Hà Nội"),
        ("Hanoi", "Hà Nội"),
        ("Ho Chi Minh City", "TP.HCM"),
    ],
)
def test_region_detection(text, region):
    assert detect_facility_region(text) == region


# 6. Chọn bác sĩ không có giờ trống → điều phối viên xếp giờ, không nói "còn giờ trống".
@pytest.mark.asyncio
async def test_doctor_without_slots_goes_to_coordinator():
    state = await _turn(_state("TRIAGED_READY_FOR_BOOKING"), "BS. Lê Văn Không Lịch")
    assert state["workflow_status"] == "CONFIRM_BOOKING_CONVERSATIONALLY"
    assert state["chosen_doctor"]["id"] == "d3"
    assert "còn các khung giờ trống" not in state["response"]


def test_slot_prompt_without_slots_does_not_claim_open_times():
    text, buttons = slot_choice_prompt(DOCTORS, DOCTORS[2], "Times City")
    assert "còn các khung giờ trống" not in text
    assert buttons == ["Để điều phối viên xếp giờ"]


# 7. Nút tiếng Anh do chính bot sinh ra phải bấm được.
def test_english_buttons_are_recognised():
    assert wants_any_facility("Any doctor")
    assert wants_any_facility("Any facility")
    assert wants_coordinator_scheduling("Let a coordinator schedule")
    assert wants_coordinator_scheduling("Để điều phối viên xếp giờ")


# 8. Lần tra mới không ra ai → không dùng lại danh sách bác sĩ cũ.
@pytest.mark.asyncio
async def test_empty_search_replaces_stale_doctor_list():
    state = await _turn(_state("FACILITY_CHOICE_REQUIRED", facility_preference=None), "Times City", slots=[])
    assert state["last_listed_doctors"] == []


# 9. Tra nhiều cơ sở song song: một cơ sở lỗi không làm cả kết quả thành "không có dữ liệu".
@pytest.mark.asyncio
@pytest.mark.parametrize(("failing", "expect_unavailable"), [({"Times City"}, False), ({"*"}, True)])
async def test_multi_facility_unavailable_only_when_all_fail(failing, expect_unavailable):
    async def fake_slots(**kwargs):
        facility = kwargs.get("facility_id") or ""
        if "*" in failing or any(name in facility for name in failing):
            return [], True, "db_down"
        return ([DOCTORS[0]] if "Smart City" in facility else []), False, None

    state = {
        **_state("FACILITY_CHOICE_REQUIRED", facility_preference=None, facility_region="Hà Nội"),
        "query": "Cơ sở nào ở Hà Nội cũng được",
    }
    with (
        patch.object(HybridDialogueService, "process_turn_async", _fallback),
        patch("src.medical_assistant.domain.doctor_schedule_service.fetch_available_doctors_slots_cached", fake_slots),
    ):
        result = await analyze_node(state)
    assert bool(result["metadata"]["data_unavailable"]) is expect_unavailable
    assert bool(result["available_slots"]) is not expect_unavailable


# 10. Câu "mơ hồ" nhưng đã có triệu chứng cụ thể (mệt mỏi) → hỏi tiếp triệu chứng, không hiện menu chung.
@pytest.mark.asyncio
async def test_vague_with_symptom_fact_is_not_generic_menu():
    state = {
        "query": "tôi thấy mệt mỏi quá",
        "probing_turn": 0,
        "collected_details": [],
        "language": "vi",
        "clinical_facts": {},
        "messages": [],
        "is_authenticated": False,
        "workflow_status": "IDLE",
    }
    with patch.object(HybridDialogueService, "process_turn_async", _fallback):
        state.update(await analyze_node(state))
        state.update(await respond_node(state))
    assert "khó chịu kiểu nào" not in state["response"]
