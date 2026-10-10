"""Luồng đặt lịch / gợi ý chuyên khoa thực tế (agent chạy offline, LLM tắt) — hồi quy 2026-10-10."""

import uuid
from unittest.mock import patch

import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.booking_slot_service import detect_package_inquiry
from src.medical_assistant.domain.guardrail_service import get_guardrail_service
from src.medical_assistant.domain.triage_service import get_triage_service

OFFLINE = RuntimeError("Offline test mode - LLM network disabled")


async def _ask(query: str) -> dict:
    with (
        patch("src.medical_assistant.infrastructure.llm.FailoverChatModel._ainvoke_candidates", side_effect=OFFLINE),
        patch("src.medical_assistant.domain.hybrid_dialogue_service.get_llm", side_effect=OFFLINE),
    ):
        return await agent.ainvoke({"query": query}, config={"configurable": {"thread_id": f"flow-{uuid.uuid4().hex}"}})


def test_parent_booking_for_child_is_not_blocked_as_third_party():
    intent = get_guardrail_service().check_intent("Đặt lịch khám cho con tôi 3 tuổi bị sốt ho 2 ngày")
    assert intent is None or intent.get("intent") != "THIRD_PARTY_HEALTH_QUERY"


def test_question_about_friend_is_still_third_party():
    intent = get_guardrail_service().check_intent("Bạn tôi bị vô sinh thì làm thế nào?")
    assert intent["intent"] == "THIRD_PARTY_HEALTH_QUERY"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Tôi muốn khám định kỳ", True),
        ("Cho tôi xem các gói khám", True),
        ("Tôi bị tiểu đường muốn đi khám định kỳ", False),
        ("Tôi bị tăng huyết áp, muốn tái khám", False),
    ],
)
def test_periodic_checkup_vs_chronic_follow_up(text, expected):
    assert detect_package_inquiry(text) is expected


@pytest.mark.parametrize(
    ("query", "specialty"),
    [
        ("Tôi bị tiểu đường muốn đi khám định kỳ", "Nội tiết"),
        ("tôi bị bệnh basedow muốn tái khám", "Nội tiết"),
        ("Tôi bị tăng huyết áp, muốn tái khám", "Trung tâm Tim mạch"),
        ("mình bị trào ngược dạ dày lâu rồi", "Tiêu hóa - Gan mật"),
    ],
)
def test_named_known_disease_routes_to_its_specialty(query, specialty):
    assert get_triage_service().evaluate_symptoms(query).suggested_specialty == specialty


@pytest.mark.parametrize("word", ["than", "dại", "down"])
def test_single_word_disease_names_do_not_get_name_bonus(word):
    assert get_triage_service()._disease_name_mention_bonus(word, f"tôi {word} quá") == 0


@pytest.mark.asyncio
async def test_child_booking_goes_to_pediatrics():
    state = await _ask("Đặt lịch khám cho con tôi 3 tuổi bị sốt ho 2 ngày")
    assert state["workflow_status"] != "THIRD_PARTY_HEALTH_GUIDANCE"
    assert state["suggested_department_name"] == "Nhi khoa"


@pytest.mark.asyncio
async def test_chronic_follow_up_offers_specialty_slots():
    state = await _ask("Tôi bị tăng huyết áp, muốn tái khám")
    assert state["workflow_status"] == "TRIAGED_READY_FOR_BOOKING"
    assert state["suggested_department_name"] == "Trung tâm Tim mạch"


@pytest.mark.parametrize(
    ("query", "specialty"),
    [
        ("Đặt lịch khám cho con tôi 3 tuổi bị sốt ho 2 ngày", "Nhi khoa"),
        ("con tôi bị sốt 38 độ, vẫn chơi", "Nhi khoa"),
        ("mẹ tôi mắc basedow", "Nội tiết"),
        ("bố tôi bị parkinson", "Thần kinh"),
        # Trẻ nhũ nhi: chuyên khoa cơ quan (tiêu hóa, mắt) vẫn khám Nhi trước.
        ("Con tôi 9 tháng, sốt ba hôm nay, bú kém, nôn 1 lần, đi lỏng 2 lần", "Nhi khoa"),
        ("Bé 6 tháng tuổi bị đỏ mắt có ghèn", "Nhi khoa"),
    ],
)
def test_child_and_proper_name_disease_routing(query, specialty):
    assert get_triage_service().evaluate_symptoms(query).suggested_specialty == specialty


def test_adult_child_is_not_pediatrics():
    assert get_triage_service().evaluate_symptoms("con tôi 30 tuổi bị sốt ho").suggested_specialty != "Nhi khoa"


def test_illness_duration_in_months_is_not_infant_age():
    from src.medical_assistant.domain.clinical_fact_service import get_clinical_fact_service

    facts = get_clinical_fact_service().extract("Tôi ho 2 tháng nay")
    assert not facts.get("patient_is_infant")


async def _conversation(turns: list[str]) -> tuple[dict, list[dict]]:
    """Hội thoại nhiều lượt; chặn ghi DB, trả về trạng thái cuối + payload định gửi."""
    from src.medical_assistant.domain.booking_lookup_service import BookingLookupService

    captured: list[dict] = []

    async def fake_commit(self, intake_data, user=None, session_id="", guest_token="", state=None):
        captured.append(intake_data)
        return {"saved": True, "request_id": "00000000-test", "request_code": "YC-TEST", "status": "PENDING_CONTACT"}

    config = {"configurable": {"thread_id": f"book-{uuid.uuid4().hex}"}}
    with (
        patch("src.medical_assistant.infrastructure.llm.FailoverChatModel._ainvoke_candidates", side_effect=OFFLINE),
        patch("src.medical_assistant.domain.hybrid_dialogue_service.get_llm", side_effect=OFFLINE),
        patch.object(BookingLookupService, "auto_commit_conversational_booking", fake_commit),
    ):
        state: dict = {}
        for turn in turns:
            state = await agent.ainvoke({"query": turn}, config=config)
    return state, captured


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("turns", "expected"),
    [
        (
            ["Tôi muốn đặt lịch khám Tai mũi họng ở Vinmec Times City sáng mai", "Nguyễn Văn An, 0912345678"],
            {"patient_name": "Nguyễn Văn An", "specialty_code": "TAI_MUI_HONG", "preferred_period": "morning"},
        ),
        (
            ["Đặt lịch khám cho con tôi 3 tuổi bị sốt ho 2 ngày", "Bé tên Lê Minh Khôi, số của mẹ là 0901234567"],
            {"patient_name": "Lê Minh Khôi", "specialty_code": "NHI_KHOA"},
        ),
        (
            ["Tôi bị tăng huyết áp, muốn tái khám", "Phạm Văn Cường 0933222111"],
            {"patient_name": "Phạm Văn Cường", "specialty_code": "TIM_MACH"},
        ),
    ],
)
async def test_contact_reply_commits_booking_request(turns, expected):
    _, captured = await _conversation(turns)
    assert len(captured) == 1
    for key, value in expected.items():
        assert captured[0][key] == value


@pytest.mark.asyncio
async def test_identity_answer_is_not_profile_lookup_and_no_default_facility():
    state, captured = await _conversation(
        ["Đặt lịch khám cho con tôi 3 tuổi bị sốt ho 2 ngày", "Tên tôi là Trần Thị Bình, sđt 0987654321"]
    )
    assert state["workflow_status"] == "CONFIRM_BOOKING_CONVERSATIONALLY"
    assert "Riverside" not in captured[0]["facility_preference"]  # không tự chọn cơ sở thay bệnh nhân


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("turns", "expected"),
    [
        (
            # Tên "Mai" không được hiểu là "ngày mai"; ngày lấy từ lượt trước.
            ["Tôi muốn đặt lịch khám da liễu thứ 6 tuần sau ở Times City", "Hoàng Thị Mai 0977111222"],
            {"patient_name": "Hoàng Thị Mai", "specialty_code": "DA_LIEU", "preferred_date": "2026-10-16"},
        ),
        (
            [
                "I want to book a dermatology appointment at Vinmec Times City tomorrow morning",
                "John Smith, 0912888777",
            ],
            {
                "patient_name": "John Smith",
                "specialty_code": "DA_LIEU",
                "preferred_period": "morning",
                "specialty_name": "Da liễu",
            },
        ),
    ],
)
async def test_booking_name_mai_and_english(turns, expected):
    from datetime import date

    with patch("src.medical_assistant.domain.booking_slot_service._get_vn_today", return_value=date(2026, 10, 10)):
        _, captured = await _conversation(turns)
    assert len(captured) == 1
    for key, value in expected.items():
        assert captured[0][key] == value


@pytest.mark.asyncio
async def test_invalid_phone_is_reasked_without_commit():
    state, captured = await _conversation(["Đặt lịch khám tai mũi họng sáng mai", "Nguyễn Văn Bé, 12345"])
    assert captured == []
    assert "chưa đúng định dạng" in state["response"]


@pytest.mark.asyncio
async def test_doctor_named_booking_uses_doctor_specialty():
    from unittest.mock import MagicMock

    fake_tool = MagicMock()
    fake_tool.invoke.return_value = {
        "found": True,
        "doctors": [{"full_name": "Nguyễn Vĩnh Toàn", "specialties": ["Tai mũi họng"]}],
    }
    with patch("src.medical_assistant.agent.tools.doctor_tools.search_doctors", fake_tool):
        _, captured = await _conversation(["Tôi muốn đặt lịch với bác sĩ Nguyễn Vĩnh Toàn", "Lý Thị Hoa 0944555666"])
    assert len(captured) == 1
    assert captured[0]["specialty_code"] == "TAI_MUI_HONG"
    assert "Nguyễn Vĩnh Toàn" in captured[0]["doctor_name"]


@pytest.mark.asyncio
async def test_english_booking_keeps_english_on_contact_turn():
    state, captured = await _conversation(
        ["I want to book a dermatology appointment tomorrow morning", "John Smith, 0912888777"]
    )
    assert len(captured) == 1
    assert "APPOINTMENT REQUEST RECEIVED" in state["response"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("result", "expected"),
    [("cancelled", "đã **hủy yêu cầu"), ("handoff", "điều phối viên sẽ liên hệ"), ("not_found", "không tìm thấy")],
)
async def test_patient_can_cancel_request_by_code(result, expected):
    from src.medical_assistant.domain.booking_lookup_service import BookingLookupService

    calls: list[str] = []

    async def fake_cancel(self, code, user_id=None, guest_token=None):
        calls.append(code)
        return {"result": result, "code": code}

    with patch.object(BookingLookupService, "cancel_patient_request", fake_cancel):
        state = await _ask("Tôi muốn hủy lịch mã yc-1a2b3c4d")
    assert calls == ["YC-1A2B3C4D"]
    assert expected in state["response"]


@pytest.mark.asyncio
async def test_cancel_without_code_explains_policy():
    state = await _ask("Tôi muốn hủy lịch khám đã đặt")
    assert "Chính sách Đổi & Hủy" in state["response"]


@pytest.mark.asyncio
async def test_patient_reschedule_by_code_passes_new_date():
    from datetime import date

    from src.medical_assistant.domain.booking_lookup_service import BookingLookupService

    calls: list[tuple] = []

    async def fake_reschedule(self, code, new_date, new_period, user_id=None, guest_token=None):
        calls.append((code, new_date, new_period))
        return {"result": "updated", "code": code}

    with (
        patch.object(BookingLookupService, "reschedule_patient_request", fake_reschedule),
        patch("src.medical_assistant.domain.booking_slot_service._get_vn_today", return_value=date(2026, 10, 10)),
    ):
        state = await _ask("Đổi lịch YC-1A2B3C4D sang sáng thứ 7 tuần sau")
    assert calls == [("YC-1A2B3C4D", "2026-10-17", "morning")]
    assert "đã cập nhật" in state["response"]


@pytest.mark.asyncio
async def test_reschedule_without_new_time_asks_for_it():
    state = await _ask("Tôi muốn đổi lịch mã YC-1A2B3C4D")
    assert "sang ngày/buổi nào" in state["response"]
