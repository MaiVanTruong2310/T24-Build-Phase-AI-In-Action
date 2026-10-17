"""Hồi quy 2 chiều: chuẩn hóa đầu vào (né từ khóa) + cổng cấp cứu xét các lượt gần nhất."""

import pytest
from pydantic import ValidationError

from src.medical_assistant.domain.schemas import ChatRequest
from src.medical_assistant.domain.text_normalization import normalize_user_message
from src.medical_assistant.domain.triage_service import get_triage_service


# ------------------------------------------------------------------ chuẩn hóa: phải làm sạch
@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("Bố tôi bị méo m\u200biệng, n\u200bói ngọng", "Bố tôi bị méo miệng, nói ngọng"),
        ("đặt lịch khám \u0441ho mẹ tôi", "đặt lịch khám cho mẹ tôi"),  # \u0441 Cyrillic
        ("70 tuổ\u0456, mé\u043e", "70 tuổi, méo"),  # \u0456, \u043e Cyrillic trong từ Latin
        ("tôi bị đ.a.u n.g.ự.c dữ dội, k.h.ó t.h.ở", "tôi bị đau ngực dữ dội, khó thở"),
        ("\uff44\uff41\uff55 \uff4e\uff47\uff55\uff43", "dau nguc"),  # full-width
        ("so\u00adt cao", "sot cao"),  # soft hyphen
    ],
)
def test_normalization_removes_evasion(raw, clean):
    assert normalize_user_message(raw) == clean


# ------------------------------------------------------------------ chuẩn hóa: không được đổi nghĩa
@pytest.mark.parametrize(
    "text",
    [
        "Tôi sốt 37.8 độ, uống 1.5 lít nước",
        "\u041f\u0440\u0438\u0432\u0435\u0442, \u043a\u0430\u043a \u0434\u0435\u043b\u0430",  # thuần Cyrillic: không phải homoglyph trộn
        "Bác sĩ 👨\u200d⚕️ khám giúp tôi",  # ZWJ trong emoji giữ nguyên
        "Tôi ở T.P. Hồ Chí Minh",  # viết tắt 2 chữ không bị gộp
        "Đau bụng dưới bên phải, sốt nhẹ từ sáng.",
    ],
)
def test_normalization_preserves_meaning(text):
    assert normalize_user_message(text) == text


def test_normalization_idempotent():
    raw = "đ.a.u n.g.ự.c \u0441ho m\u200bẹ"
    once = normalize_user_message(raw)
    assert normalize_user_message(once) == once


def test_chat_request_normalizes_and_rejects_invisible_only():
    assert ChatRequest(message="m\u200béo miệng").message == "méo miệng"
    with pytest.raises(ValidationError):
        ChatRequest(message="\u200b\u200b")


def test_obfuscated_stroke_reaches_emergency_after_normalization():
    triage = get_triage_service()
    raw = "Bố tôi 70 tuổ\u0456 tự nhiên bị mé\u043e m\u0456ệng, nó\u0456 ngọng."
    assert triage.evaluate_symptoms(normalize_user_message(raw)).is_emergency


# ------------------------------------------------------------------ cổng xét ngữ cảnh: phải bắt
def _history(*user_turns, assistant="Dạ, em đã ghi nhận."):
    out = []
    for t in user_turns:
        out += [{"role": "user", "content": t}, {"role": "assistant", "content": assistant}]
    return out


def test_context_gate_catches_progressive_anaphylaxis():
    triage = get_triage_service()
    history = _history("Tôi vừa ăn tôm xong thì nổi mẩn ngứa khắp người.", "Môi bắt đầu sưng lên.")
    query = "Giờ cổ họng thấy nghẹn, thở khò khè."
    assert not triage.evaluate_symptoms(query).is_emergency  # từng tin riêng không đủ
    result = triage.evaluate_with_recent_context(query, history)
    assert result.is_emergency and result.ats_level.value <= 2


# ------------------------------------------------------------------ cổng xét ngữ cảnh: không được bắt nhầm
def test_context_gate_no_false_alarm_on_benign_history():
    triage = get_triage_service()
    history = _history("Tôi bị ho có đờm 5 ngày nay, không sốt, không khó thở.", "Đờm màu trắng.")
    assert not triage.evaluate_with_recent_context("Ho nhiều hơn về đêm.", history).is_emergency


def test_context_gate_ignores_assistant_safety_warnings():
    """Lời nhắc an toàn của bot chứa từ cờ đỏ ("khó thở, đau ngực... gọi 115") không được tính là triệu chứng."""
    triage = get_triage_service()
    warning = "Nếu xuất hiện khó thở, đau ngực dữ dội, vã mồ hôi, co giật, hãy gọi 115 ngay."
    history = _history("Tôi bị đau đầu nhẹ.", assistant=warning)
    assert not triage.evaluate_with_recent_context("Tôi nên khám khoa nào?", history).is_emergency


def test_context_gate_window_is_bounded():
    """Chỉ xét tối đa 2 lượt người dùng trước: triệu chứng cũ hơn không cộng dồn."""
    triage = get_triage_service()
    history = _history(
        "Tôi vừa ăn tôm xong thì nổi mẩn ngứa khắp người.", "Môi bắt đầu sưng lên.", "Cảm ơn.", "Để tôi xem đã."
    )
    assert not triage.evaluate_with_recent_context("Giờ cổ họng thấy nghẹn, thở khò khè.", history).is_emergency


def test_context_gate_keeps_current_emergency():
    triage = get_triage_service()
    result = triage.evaluate_with_recent_context("Đau thắt ngực dữ dội lan ra tay trái, vã mồ hôi", [])
    assert result.is_emergency
