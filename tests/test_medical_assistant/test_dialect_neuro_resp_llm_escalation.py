"""Hồi quy 2 chiều: phương ngữ ở tầng phát hiện, luật thần kinh khu trú / suy hô hấp, LLM nâng mức cấp cứu.

Mỗi nhóm có ca PHẢI bắt và ca giống mà KHÔNG được bắt (tiêu chí chấp nhận eval/triage_eval/README.md).
Nguồn luật: ACEM ATS 2023; "Các dấu hiệu thần kinh khu trú" (ThS.BS Bùi Ngọc Phương Hòa, Vinmec);
youmed.vn/tin-tuc/suy-ho-hap.
"""

from types import SimpleNamespace

import pytest

from src.medical_assistant.domain.ats_descriptor_service import match_ats_descriptors
from src.medical_assistant.domain.booking_slot_service import detect_booking_for
from src.medical_assistant.domain.hybrid_dialogue_v2_model import LeanSafetyConcern
from src.medical_assistant.domain.llm_safety_escalation import evidence_in_text, llm_emergency_escalation
from src.medical_assistant.domain.text_normalization import canonicalize_for_matching
from src.medical_assistant.domain.triage_service import get_triage_service


def _emergency(text: str) -> bool:
    return get_triage_service().evaluate_symptoms(text).is_emergency


def _rule(text: str) -> str | None:
    m = match_ats_descriptors(text)
    return m.rule_id if m and m.ats_level <= 2 else None


# ------------------------------------------------------------------ phương ngữ (chỉ khi so khớp)
@pytest.mark.parametrize(
    ("raw", "canon"),
    [
        ("Tui hông muốn sống nữa", "tôi không muốn sống nữa"),
        ("ép mãi hông cầm được", "ép mãi không cầm được"),
        ("tui ko thở đc", "tôi không thở được"),
        ("Bé ói 5 lần", "Bé nôn 5 lần"),
    ],
)
def test_dialect_canonicalized_for_matching(raw, canon):
    assert canonicalize_for_matching(raw) == canon


@pytest.mark.parametrize(
    "text",
    ["đau hông trái 3 ngày", "đau ở hông bên phải khi cúi", "mỏi hông", "hông phải bị bầm", "Tôi nói không rõ"],
)
def test_hip_meaning_and_standard_text_untouched(text):
    assert canonicalize_for_matching(text) == text


def test_dialect_emergencies_caught():
    assert _emergency("Tui hông muốn sống nữa, tối nay tui định kết thúc tất cả nhen.")
    assert _emergency("Tôi bị dao cứa vô cổ tay, máu phun thành tia, ép mãi hông cầm được nhen.")


def test_dialect_negation_still_negates():
    assert not _emergency("tui hông khó thở, chỉ ho khan thôi")
    assert not _emergency("Tui bị đau hông trái 3 ngày nay")


def test_proxy_dialect_kinship():
    assert detect_booking_for("Tui muốn đặt lịch khám cho má tui, bả bị đau khớp gối") == "other"
    assert detect_booking_for("đặt lịch khám cho tía tui") == "other"
    assert detect_booking_for("đặt lịch khám cho tui") == "self"
    assert detect_booking_for("má tui sưng má bên trái, đặt lịch khám giúp") is None  # không có "cho/hộ"


# ------------------------------------------------------------------ thần kinh khu trú cấp
@pytest.mark.parametrize(
    "text",
    [
        "alo em ơi bố anh tự nhiên ngã ra nói không được tay phải không nhấc lên được mới cách đây mười phút",
        "Mẹ tôi sáng nay tự nhiên nói ngọng, uống nước bị sặc",
        "Ông tôi đột ngột nhìn thấy hai hình, đi loạng choạng",
        "Tay phải tôi bỗng nhiên yếu hẳn, cầm cốc không chặt",
        "tôi bị tê nửa người bên trái từ lúc ngủ dậy",
        "Mắt trái tự nhiên tối sầm một bên, tay trái vụng về cầm bút không được",
    ],
)
def test_acute_focal_neuro_is_emergency(text):
    assert _rule(text) == "ATS2_ACUTE_FOCAL_NEURO" or _emergency(text)
    assert _emergency(text)


@pytest.mark.parametrize(
    "text",
    [
        "Không sốt, không nôn, không yếu tay chân, không nhìn mờ.",
        "Tôi từng bị đột quỵ nhẹ cách đây 3 năm, giờ đi lại bình thường, muốn khám định kỳ",
        "Dạo này tôi hay bị tê bì, châm chích ở hai bàn chân 2 tháng rồi, không yếu chân",
        "Tôi đau họng, khản tiếng từ sáng, nói không được",
        "Mắt tôi nhìn mờ dần mấy tháng nay, nhất là khi đọc sách.",
        "tay chân không yếu, nói bình thường, chỉ hơi chóng mặt",
        "Con tôi nói ngọng từ nhỏ, muốn khám chuyên khoa",
        "Bị đau lưng, chân phải tê mỏi 2 tuần nay",
    ],
)
def test_non_acute_or_negated_focal_not_emergency(text):
    assert _rule(text) != "ATS2_ACUTE_FOCAL_NEURO"
    assert not _emergency(text)


# ------------------------------------------------------------------ suy hô hấp
@pytest.mark.parametrize(
    "text",
    [
        "Tối nay tự nhiên khó thở nhiều, môi hơi tím, nói không hết câu.",
        "Bé thở rút lõm lồng ngực, cánh mũi phập phồng",
        "Bố tôi khó thở, đầu ngón tay tím",
        "khó thở quá, nói đứt quãng từng chữ",
        "bo toi kho tho, moi tim tai",
    ],
)
def test_respiratory_failure_is_emergency(text):
    assert _emergency(text)


@pytest.mark.parametrize(
    "text",
    [
        "Tôi hơi khó thở khi chạy bộ, môi không tím",
        "Tôi mới tìm hiểu về bệnh tim, hơi khó thở khi lo lắng",  # bỏ dấu "mới tìm" = "môi tím"
        "Tôi bị hồi hộp, tim đập nhanh, hơi khó thở khi leo cầu thang mấy tháng nay",
        "Tôi bị ho có đờm 5 ngày nay, không sốt, không khó thở.",
    ],
)
def test_mild_or_negated_respiratory_not_emergency(text):
    assert not _emergency(text)


# ------------------------------------------------------------------ LLM nâng mức (không gọi API)
def _v2(*concerns):
    return SimpleNamespace(safety_concerns=[LeanSafetyConcern(**c) for c in concerns])


SUICIDE = "Tui hông muốn sống nữa, tối nay tui định kết thúc tất cả"


def test_llm_escalates_with_verbatim_evidence():
    v2 = _v2({"reason": "ý định tự sát", "evidence": "tối nay tui định kết thúc tất cả", "severity": "emergency",
              "category": "self_harm"})  # fmt: skip
    out = llm_emergency_escalation(v2, SUICIDE, [], "vi")
    assert out and out["is_emergency"] and out["ats_level"].value == 2
    assert out["triggered_rule_ids"] == ["LLM_SAFETY_ESCALATION:self_harm"]
    assert "115" in out["patient_guidance"]


def test_llm_evidence_matches_across_dialect_and_accents():
    assert evidence_in_text("không muốn sống nữa", [SUICIDE])
    assert evidence_in_text("ep mai hong cam duoc", ["máu phun thành tia, ép mãi hông cầm được nhen"])


@pytest.mark.parametrize(
    ("concern", "query"),
    [
        # chỉ "urgent" → không nâng
        ({"reason": "x", "evidence": "tối nay tui định kết thúc tất cả", "severity": "urgent"}, SUICIDE),
        # evidence bịa, không có trong lời người dùng
        ({"reason": "x", "evidence": "đau ngực dữ dội lan ra tay trái", "severity": "emergency"}, SUICIDE),
        # evidence quá ngắn
        ({"reason": "x", "evidence": "sống", "severity": "emergency"}, SUICIDE),
        # câu hỏi kiến thức / giả định
        (
            {"reason": "x", "evidence": "chảy máu không cầm", "severity": "emergency", "category": "bleeding"},
            "Nếu bị chảy máu không cầm thì sơ cứu thế nào?",
        ),
    ],
)
def test_llm_does_not_escalate_without_safeguards(concern, query):
    assert llm_emergency_escalation(_v2(concern), query, [], "vi") is None


def test_llm_unknown_values_fall_back_to_no_escalation():
    c = LeanSafetyConcern(reason="x", evidence="tối nay tui định kết thúc", severity="critical", category="stroke")
    assert c.severity == "urgent" and c.category == "other"
    assert llm_emergency_escalation(SimpleNamespace(safety_concerns=[c]), SUICIDE, [], "vi") is None


def test_llm_none_response_is_noop():
    assert llm_emergency_escalation(None, SUICIDE, [], "vi") is None
