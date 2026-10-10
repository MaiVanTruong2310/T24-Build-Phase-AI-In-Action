"""Tin nhắn lạc đề / vô nghĩa giữa cuộc tư vấn và cách xưng hô theo giới tính — hồi quy 10/10/2026.

Hội thoại thật: "Tôi bị ho" → "Tôi muốn đi chơi" → "Tôi muốn ăn thanh long" → "Tôi muốn đi ngủ".
Trước đây câu lạc đề bị tính là câu trả lời nên bot nhảy sang chốt khoa khi chưa biết ho bao lâu,
kèm "em đã ghi nhận triệu chứng", nhãn ATS và khuyến cáo y tế; xưng hô lẫn "bác" và "anh/chị".
"""

import re
import uuid
from unittest.mock import patch

import pytest

from src.medical_assistant.agent.graph import agent
from src.medical_assistant.domain.language_service import apply_honorific, resolve_honorific
from src.medical_assistant.domain.turn_relevance import is_gibberish, last_question, looks_off_topic

OFFLINE = RuntimeError("Offline test mode - LLM network disabled")


@pytest.mark.parametrize(
    ("text", "gibberish", "off_topic"),
    [
        ("asdkjh qwe", True, False),
        ("kkkkk", True, False),
        ("Tôi muốn đi chơi", False, True),
        ("Tôi muốn ăn thanh long", False, True),
        ("Tôi muốn đi ngủ", False, True),
        # Câu trả lời thật / câu hỏi sức khỏe không được coi là lạc đề.
        ("3 ngày nay", False, False),
        ("bình thường", False, False),
        ("không", False, False),
        ("ok", False, False),
        ("đang ho có ăn thanh long được không", False, False),
        ("tôi muốn ngủ mà không ngủ được", False, False),
        ("tôi muốn đi khám", False, False),
        ("Nguyễn Văn An", False, False),
    ],
)
def test_relevance_heuristics_are_conservative(text, gibberish, off_topic):
    assert is_gibberish(text) is gibberish
    assert looks_off_topic(text) is off_topic


def test_last_question_ignores_disclaimer():
    text = (
        "Dạ, em đã ghi nhận.\n\nCơn ho kéo dài bao lâu rồi ạ?\n\nKhuyến cáo y tế: Thông tin chỉ mang tính định hướng?"
    )
    assert last_question(text) == "Cơn ho kéo dài bao lâu rồi ạ?"


@pytest.mark.parametrize(
    ("gender", "authenticated", "expected"),
    [("male", True, "anh"), ("female", True, "chị"), (None, True, "anh/chị"), ("male", False, "anh/chị")],
)
def test_honorific_follows_gender_and_guest_status(gender, authenticated, expected):
    assert resolve_honorific(gender, authenticated) == expected


def test_apply_honorific_keeps_doctor_word():
    text = "Dạ, em đã ghi nhận triệu chứng của bác. Bác nên gặp bác sĩ. Anh/chị cần thêm gì không?"
    assert apply_honorific(text, "chị") == (
        "Dạ, em đã ghi nhận triệu chứng của chị. Chị nên gặp bác sĩ. Chị cần thêm gì không?"
    )


async def _chat(turns: list[str], extra: dict | None = None) -> list[dict]:
    config = {"configurable": {"thread_id": f"offtopic-{uuid.uuid4().hex}"}}
    states = []
    with (
        patch("src.medical_assistant.infrastructure.llm.FailoverChatModel._ainvoke_candidates", side_effect=OFFLINE),
        patch("src.medical_assistant.domain.hybrid_dialogue_service.get_llm", side_effect=OFFLINE),
    ):
        for turn in turns:
            states.append(await agent.ainvoke({"query": turn, **(extra or {})}, config=config))
    return states


@pytest.mark.asyncio
async def test_off_topic_messages_do_not_advance_the_consultation():
    states = await _chat(["Tôi bị ho", "Tôi muốn đi chơi", "Tôi muốn ăn thanh long", "Tôi muốn đi ngủ", "3 ngày nay"])
    first, chơi, thanh_long, ngu, answer = states
    question = last_question(first["response"])
    assert question
    for off in (chơi, thanh_long):
        # Hỏi lại đúng câu đang chờ, không chốt khoa, không khuyến cáo, không "ghi nhận triệu chứng".
        assert question in off["response"]
        assert "hướng khám phù hợp" not in off["response"]
        assert "Khuyến cáo" not in off["response"]
        assert "ghi nhận triệu chứng" not in off["response"]
        assert off["probing_turn"] == first["probing_turn"]
        assert off["suggested_department_name"] == first["suggested_department_name"]
    # Lạc đề lần thứ 3 liên tiếp → hỏi tiếp tục hay bắt đầu lại.
    assert "bắt đầu lại" in ngu["response"]
    # Câu trả lời thật sau đó được ghi nhận: không hỏi lại thời gian nữa.
    assert answer["clinical_facts"].get("duration_days") == 3
    assert "từ khi nào" not in answer["response"]


@pytest.mark.asyncio
async def test_gibberish_is_reported_not_as_system_error():
    states = await _chat(["Tôi bị ho", "asdkjh qwe"])
    assert "chưa đọc được" in states[1]["response"]
    assert "trục trặc" not in states[1]["response"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("extra", "pronoun"),
    [
        ({"is_authenticated": True, "patient_gender": "male"}, "anh"),
        ({"is_authenticated": True, "patient_gender": "female"}, "chị"),
        ({}, "anh/chị"),
    ],
)
async def test_bot_addresses_user_by_gender(extra, pronoun):
    response = (await _chat(["Tôi bị ho"], extra))[0]["response"]
    without_doctor = re.sub(r"[Bb]ác sĩ", "", response)
    assert not re.search(r"\b[Bb]ác\b", without_doctor), response
    assert re.search(rf"\b{re.escape(pronoun)}\b", response.lower()), response


def test_off_topic_turn_hides_clinical_badges_in_api():
    from src.medical_assistant.api.routes import public_result

    result = {
        "response": "Dạ, em chỉ hỗ trợ được các vấn đề sức khỏe và đặt lịch khám ạ.",
        "ats_level": 4,
        "suggested_department_name": "Nội hô hấp",
        "candidate_specialties": [{"code": "HO_HAP"}],
        "metadata": {"off_topic": "off_topic"},
    }
    payload = public_result(result, "s1")
    assert payload["ats_level"] is None
    assert payload["candidate_specialties"] == []
    assert payload["suggested_department"] is None
