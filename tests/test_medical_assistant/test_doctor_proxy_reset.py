"""Đặt lịch theo tên bác sĩ, đặt hộ người nhà, bỏ ngữ cảnh — hồi quy hội thoại thật ngày 10/10/2026.

Người dùng: "đau chân" → xem lịch Chấn thương chỉnh hình → "khám khoa nội trú bác si Nguyên Thị Nga" →
"quên tất cả tư vấn trên… khám cho người nhà". Trước đây bot in lại lịch cũ 3 lần và tự điền thông tin
chủ tài khoản vào phiếu khám của người nhà.
"""

import re
import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain import probing_service
from src.medical_assistant.domain.booking_slot_service import (
    detect_booking_for,
    detect_context_reset,
    extract_booking_entities,
)
from src.medical_assistant.domain.cache_service import get_cache_service

OFFLINE = RuntimeError("Offline test mode - LLM network disabled")

THREE_NGA = {
    "found": True,
    "doctors": [
        {
            "full_name": "Nguyễn Thị Nga",
            "title": "Bác sĩ nội trú",
            "specialties": ["Bệnh lý huyết học, ung thư huyết học - Bệnh hiếm"],
            "workplace": "Bệnh viện Đa khoa Quốc tế Vinmec Times City",
        },
        {
            "full_name": "Nguyễn Thị Nga",
            "title": "Thạc sĩ, Bác sĩ",
            "specialties": ["Y học cổ truyền"],
            "workplace": "Bệnh viện Đa khoa Quốc tế Vinmec Central Park",
        },
        {
            "full_name": "Nguyễn Thị Nga",
            "title": "Thạc sĩ, Bác sĩ",
            "specialties": ["Hồi sức - Cấp cứu"],
            "workplace": "Bệnh viện Đa khoa Quốc tế Vinmec Đà Nẵng",
        },
    ],
}
# Hồ sơ chủ tài khoản (prepare_turn nạp vào mỗi lượt) — KHÔNG được xuất hiện trong phiếu của người nhà.
ACCOUNT = {
    "is_authenticated": True,
    "patient_profile": {"name": "Chủ Tài Khoản", "phone": "0900000001", "date_of_birth": "1990-05-05"},
    "patient_name": "Chủ Tài Khoản",
    "patient_phone": "0900000001",
    "patient_dob": "1990-05-05",
}


@pytest.mark.parametrize(
    ("text", "doctor", "title"),
    [
        ("tôi muốn khám khoa nội trú bác si Nguyên Thị Nga", "Nguyên Thị Nga", "noi tru"),
        (
            "quên tất cả tư vấn trên, tôi muốn gặp bác si nội trú Nguyên Thị Nga để khám cho người nhà",
            "Nguyên Thị Nga",
            "nội trú",
        ),
        ("Tôi cần gặp bac si Nguyen Thi Nga, người khám không phải tôi", "Nguyen Thi Nga", None),
        ("đặt lịch với BS CKII Trần Văn An", "Trần Văn An", "ckii"),
        ("đặt lịch với bác sĩ tim mạch", None, None),
    ],
)
def test_doctor_name_accepts_missing_diacritics_and_strips_titles(text, doctor, title):
    entities = extract_booking_entities(text, {})
    assert entities.get("doctor_preference") == doctor
    assert entities.get("doctor_title_hint") == title


@pytest.mark.parametrize(
    ("text", "reset"),
    [
        ("quên tất cả tư vấn trên, tôi muốn gặp bác sĩ khác", True),
        ("bỏ qua cái trên đi", True),
        ("bắt đầu lại", True),
        ("quên mật khẩu trên ứng dụng", False),
        ("tôi hay quên", False),
    ],
)
def test_context_reset_detection(text, reset):
    assert detect_context_reset(text) is reset


@pytest.mark.parametrize(
    ("text", "booking_for"),
    [
        ("đặt lịch khám cho mẹ tôi", "other"),
        ("gặp bác sĩ để khám cho người nhà", "other"),
        ("Tôi cần gặp bác sĩ, người khám không phải tôi", "other"),
        ("đặt lịch cho tôi", "self"),
        ("cho em hỏi khám da liễu ở đâu", None),
        ("con tôi bị sốt", None),
    ],
)
def test_booking_for_detection(text, booking_for):
    assert detect_booking_for(text) == booking_for


def test_casual_greeting_is_greeting_not_personal_matter():
    for text in ("ê ku", "ê bạn ơi", "alo"):
        hit = get_cache_service().check_cache(text, language="vi")
        assert hit is not None and hit[2] == "GREETING", text


def test_probing_templates_ask_one_question_per_turn():
    # Luật an toàn: mỗi lượt tối đa 1 câu hỏi.
    for tree in probing_service.PROBING_TREES if hasattr(probing_service, "PROBING_TREES") else []:
        for attr in dir(tree):
            if attr.endswith("_question_vi"):
                assert (getattr(tree, attr) or "").count("?") <= 1, (tree, attr)
    source = open(probing_service.__file__, encoding="utf-8").read()
    for block in re.findall(r'_question_vi=\(\n((?:\s+"[^"\n]*"\n)+)', source):
        assert "".join(re.findall(r'"([^"]*)"', block)).count("?") <= 1, block


async def _conversation(turns: list[str], doctors: dict) -> tuple[list[dict], list[dict]]:
    from src.medical_assistant.domain.booking_lookup_service import BookingLookupService

    captured: list[dict] = []

    async def fake_commit(self, intake_data, user=None, session_id="", guest_token="", state=None):
        captured.append(intake_data)
        return {"saved": True, "request_id": "00000000-test", "request_code": "YC-TEST", "status": "PENDING_CONTACT"}

    fake_search = MagicMock()
    fake_search.invoke.return_value = doctors
    config = {"configurable": {"thread_id": f"proxy-{uuid.uuid4().hex}"}}
    states: list[dict] = []
    with (
        patch("src.medical_assistant.infrastructure.llm.FailoverChatModel._ainvoke_candidates", side_effect=OFFLINE),
        patch("src.medical_assistant.domain.hybrid_dialogue_service.get_llm", side_effect=OFFLINE),
        patch.object(BookingLookupService, "auto_commit_conversational_booking", fake_commit),
        patch("src.medical_assistant.agent.tools.doctor_tools.search_doctors", fake_search),
    ):
        for turn in turns:
            states.append(await agent.ainvoke({"query": turn, **ACCOUNT}, config=config))
    return states, captured


@pytest.mark.asyncio
async def test_duplicate_doctor_names_are_listed_for_user_to_choose():
    states, _ = await _conversation(["tôi muốn đặt lịch với bác si Nguyên Thị Nga"], THREE_NGA)
    assert states[0]["workflow_status"] == "DOCTOR_CHOICE_REQUIRED"
    assert states[0]["response"].count("Nguyễn Thị Nga") == 3
    assert "bác sĩ nào" in states[0]["response"]


@pytest.mark.asyncio
async def test_unknown_doctor_is_reported_not_invented():
    states, _ = await _conversation(["đặt lịch với bác sĩ Trần Văn Không Có"], {"found": False, "doctors": []})
    assert states[0]["workflow_status"] == "DOCTOR_NOT_FOUND"


@pytest.mark.asyncio
async def test_reset_doctor_choice_and_proxy_booking_never_use_account_details():
    states, captured = await _conversation(
        [
            "tìm lịch khám chấn thương chỉnh hình ngày mai",
            "quên tất cả tư vấn trên, tôi muốn gặp bác si nội trú Nguyên Thị Nga để khám cho người nhà",
            "bác sĩ thứ 1",
            "Trần Thị Bình",
            "1958",
            "0912345678",
        ],
        THREE_NGA,
    )
    reset_turn, pick, ask_dob, ask_phone = states[1], states[2], states[3], states[4]
    # Bỏ ngữ cảnh: không còn khoa/ngày cũ; trùng tên → hỏi chọn.
    assert reset_turn["workflow_status"] == "DOCTOR_CHOICE_REQUIRED"
    assert reset_turn.get("preferred_date") is None
    # Chọn bác sĩ → hỏi lần lượt thông tin người khám, mỗi lượt 1 câu, không tự điền từ tài khoản.
    assert "tên là gì" in pick["response"] and pick["response"].count("?") == 1
    assert "Chủ Tài Khoản" not in pick["response"]
    assert "sinh năm" in ask_dob["response"]
    assert "số điện thoại" in ask_phone["response"]
    # Chốt phiếu đúng người khám.
    assert len(captured) == 1
    intake = captured[0]
    assert intake["patient_name"] == "Trần Thị Bình"
    assert intake["patient_phone"] == "0912345678"
    assert intake["date_of_birth"] == "1958-01-01"
    assert intake["doctor_name"] == "BS. Nguyễn Thị Nga"
    assert "Chủ Tài Khoản" not in str(intake) and "0900000001" not in str(intake)


@pytest.mark.asyncio
async def test_self_booking_still_prefills_from_account():
    _, captured = await _conversation(
        ["Tôi muốn đặt lịch khám da liễu", "Đồng ý, đặt lịch cho tôi"], {"found": False, "doctors": []}
    )
    assert captured and captured[0]["patient_name"] == "Chủ Tài Khoản"
