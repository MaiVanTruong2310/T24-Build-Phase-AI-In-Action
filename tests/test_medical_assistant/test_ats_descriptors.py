"""Mô tả lâm sàng ATS (ACEM 2023) + sinh hiệu tự báo. Câu ví dụ tự viết, không lấy từ bộ ETEK để tránh lộ đề."""

import pytest

from src.medical_assistant.domain.ats_descriptor_service import match_ats_descriptors
from src.medical_assistant.domain.triage_service import get_triage_service


@pytest.mark.parametrize(
    ("text", "max_ats"),
    [
        ("ông tôi ngã xong gọi thế nào cũng không tỉnh", 1),
        ("có người cầm dao dọa giết cả nhà", 1),
        ("đau bụng 10/10 không chịu nổi", 2),
        ("mẹ tôi tự nhiên vã mồ hôi lạnh, người tái lạnh", 2),
        ("bé thở rất gắng sức, co rút lồng ngực", 2),
        ("bị vôi bột bắn vào mắt", 2),
        ("bị rắn cắn vào chân", 2),
        ("đang hóa trị mà hôm nay sốt 38,5", 2),
        ("con tôi 2 tuần tuổi bú kém, li bì", 2),
        ("con tôi 3 tuần tuổi thở yếu, môi tím tái", 1),
        ("SpO2 đo ở nhà chỉ 88%", 2),
        ("huyết áp 75/40, chóng mặt", 1),
        ("huyet ap 200/120, dau dau", 3),
        ("đau lưng 8/10", 3),
        ("tôi 70 tuổi đau bụng âm ỉ", 3),
        ("bé nôn liên tục, nước tiểu sẫm màu", 3),
        ("bà tôi hôm nay tự nhiên lú lẫn", 3),
    ],
)
def test_descriptor_escalates_to_at_least(text, max_ats):
    match = match_ats_descriptors(text)
    assert match is not None and match.ats_level <= max_ats


@pytest.mark.parametrize(
    "text",
    [
        "con tôi nằm lắc lư dưới đất chơi",  # "lu du" nằm giữa "lắc lư dưới"
        "vừa uống 2 viên paracetamol",  # không phải quá liều
        "tiểu ít hơn vì dạo này uống ít nước",  # không có nôn/tiêu chảy
        "không lơ mơ, vẫn tỉnh táo",  # phủ định
        "đau đầu nhẹ 3/10",
        "SpO2 98%, huyết áp 120/80",
    ],
)
def test_descriptor_does_not_fire_on_benign_text(text):
    assert match_ats_descriptors(text) is None


@pytest.mark.parametrize(
    "text",
    [
        "chau toi 3 tuoi dang co giat, mat tron nguoc, khong tinh",
        "bo toi tu nhien meo mieng, noi ngong, yeu nua nguoi",
        "em toi uong nham thuoc diet chuot",
        "toi bi non ra mau tuoi rat nhieu",
    ],
)
def test_unaccented_emergency_is_still_emergency(text):
    assert get_triage_service().evaluate_symptoms(text).is_emergency is True


@pytest.mark.parametrize(
    "text",
    [
        "tôi muốn tìm bác sĩ khám lần đầu",  # có dấu: "tìm…lần" không được khớp "tim…lan"
        "be non 3 ngay, nuoc tieu sam mau",  # "màu" ≠ "máu" khi bỏ dấu
    ],
)
def test_accent_stripping_does_not_create_false_emergency(text):
    assert get_triage_service().evaluate_symptoms(text).is_emergency is False


@pytest.mark.asyncio
async def test_same_day_response_carries_safety_net_only_for_ats3():
    from unittest.mock import patch

    from src.medical_assistant.agent.graph import agent

    offline = RuntimeError("Offline test mode - LLM network disabled")
    with (
        patch("src.medical_assistant.infrastructure.llm.FailoverChatModel._ainvoke_candidates", side_effect=offline),
        patch("src.medical_assistant.domain.hybrid_dialogue_service.get_llm", side_effect=offline),
    ):
        same_day = await agent.ainvoke(
            {"query": "đau lưng sau khi té, khoảng 8/10"}, config={"configurable": {"thread_id": "safety_net_ats3"}}
        )
        routine = await agent.ainvoke(
            {"query": "tiểu buốt, tiểu rắt từ hôm qua"}, config={"configurable": {"thread_id": "safety_net_ats4"}}
        )
    assert same_day["ats_level"] == 3 and "gọi 115" in same_day["response"]
    assert routine["ats_level"] == 4 and "Trong lúc chờ khám" not in routine["response"]


def test_descriptor_drives_triage_emergency_and_same_day():
    svc = get_triage_service()
    assert svc.evaluate_symptoms("bị thuốc tẩy bồn cầu bắn vào mắt, rát lắm").is_emergency is True
    same_day = svc.evaluate_symptoms("đau lưng sau khi té, khoảng 8/10")
    assert same_day.is_emergency is False and same_day.ats_level.value == 3
