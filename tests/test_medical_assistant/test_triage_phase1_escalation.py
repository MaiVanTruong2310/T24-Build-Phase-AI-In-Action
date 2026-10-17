"""Giai đoạn 1 nâng cấp triage: chỉ NÂNG mức khẩn (chặn hạ mức), kèm ca đối chứng không được bị đẩy lên.

Mỗi luật có 2 chiều: ca cần bắt phải bắt, ca giống mà không nguy hiểm thì không bắt.
"""

import pytest

from src.medical_assistant.domain.disease_triage import ATSLevel
from src.medical_assistant.domain.triage_service import get_triage_service


def _triage(text: str):
    return get_triage_service().evaluate_symptoms(text)


# ---- Người > 65 tuổi đau bụng nặng (>= 8/10, sốt, tăng dần) → ATS 2; ngưỡng đau chung giữ nguyên ----


@pytest.mark.parametrize(
    "text",
    [
        "Tôi 66 tuổi, từ cuối tuần đau bụng trên ngày càng tăng, đau nhói khoảng 8/10, buồn nôn, sốt nhẹ 37,8.",
        "Mẹ tôi 72 tuổi đau bụng khoảng 8 trên 10 từ chiều",
        "ong toi 80 tuoi dau bung, sot tu sang",
    ],
)
def test_elderly_severe_abdominal_pain_is_ats2(text):
    result = _triage(text)
    assert result.ats_level.value <= ATSLevel.LEVEL_2_EMERGENT.value, result.triggered_rule_ids


def test_elderly_mild_abdominal_pain_stays_ats3():
    result = _triage("Tôi 70 tuổi, đau bụng âm ỉ khoảng 3/10 từ hôm qua")
    assert result.ats_level == ATSLevel.LEVEL_3_URGENT
    assert "ATS3_ABD_PAIN_ELDERLY" in result.triggered_rule_ids


def test_pain_9_of_10_any_cause_is_ats2():
    assert _triage("dau bung 9/10 tu sang").ats_level.value <= ATSLevel.LEVEL_2_EMERGENT.value


@pytest.mark.parametrize("text", ["Tôi đau lưng khoảng 7/10 từ hôm qua", "đau lưng sau khi té, khoảng 8/10"])
def test_pain_7_to_8_under_65_stays_ats3(text):
    # Ngưỡng 8/10 → ATS 2 (khóa đặt lịch, gọi 115) là quyết định chính sách lâm sàng, chưa đổi.
    result = _triage(text)
    assert result.ats_level == ATSLevel.LEVEL_3_URGENT
    assert "ATS3_MODERATELY_SEVERE_PAIN" in result.triggered_rule_ids


# ---- Ý nghĩ tự tử: giữ ATS 1, gắn đúng nhãn (không phải "Ngộ độc cấp tính") ----


def test_suicidal_thought_stays_ats1_with_suicide_label():
    result = _triage(
        "Dạo này tôi nghĩ đến chuyện tự tử, có tiếng nói bảo tôi bước ra trước tàu hỏa. Tôi muốn được giúp."
    )
    assert result.ats_level == ATSLevel.LEVEL_1_RESUSCITATION
    assert "SUICIDAL_IDEATION" in result.triggered_rule_ids
    assert "ACUTE_TOXIC_OVERDOSE" not in result.triggered_rule_ids


def test_real_poisoning_still_toxic_overdose():
    result = _triage("Con tôi uống nhầm thuốc diệt chuột cách đây 30 phút")
    assert result.ats_level == ATSLevel.LEVEL_1_RESUSCITATION
    assert "ACUTE_TOXIC_OVERDOSE" in result.triggered_rule_ids


# ---- Trẻ < 3 tháng nổi vân tím / gọi rất khó tỉnh → ATS 1 (kể cả gõ không dấu) ----


def test_infant_mottled_hard_to_rouse_no_diacritics_is_ats1():
    result = _triage(
        "con toi 10 tuan tuoi, 2 hom nay bu kem, li bi dan, tu hom qua sot. Gio be tai nhot, "
        "2 chan noi van tim den dau goi, nguoi hoi lanh, goi rat kho tinh."
    )
    assert result.ats_level == ATSLevel.LEVEL_1_RESUSCITATION
    assert "ATS1_INFANT_CRITICAL" in result.triggered_rule_ids


# ---- ATS 3 mới: ngất vừa xảy ra ----


def test_recent_syncope_is_at_least_ats3():
    result = _triage("Tôi vừa bị ngất trong nhà vệ sinh, giờ người xanh, mệt.")
    assert result.ats_level.value <= ATSLevel.LEVEL_3_URGENT.value
    assert "ATS3_SYNCOPE" in result.triggered_rule_ids


@pytest.mark.parametrize(
    "text",
    ["Tôi bị ngạt mũi, sổ mũi 2 hôm nay", "Tôi đau đầu một xíu từ sáng", "Hoa sữa thơm ngát làm tôi hắt hơi"],
)
def test_syncope_rule_ignores_lookalike_words(text):
    assert "ATS3_SYNCOPE" not in _triage(text).triggered_rule_ids


# ---- ATS 3 mới: ngã không đứng dậy được / ôm hông ----


def test_fall_cannot_bear_weight_is_at_least_ats3():
    result = _triage("Bố tôi 68 tuổi, sáng nay bị ngã cạnh giường, giờ không đứng dậy được, cứ ôm hông phải và rên.")
    assert result.ats_level.value <= ATSLevel.LEVEL_3_URGENT.value
    assert "ATS3_FALL_CANNOT_BEAR_WEIGHT" in result.triggered_rule_ids


def test_minor_fall_walking_normally_not_flagged():
    result = _triage("Hôm qua tôi bị ngã xe, trầy đầu gối, vẫn đi lại bình thường")
    assert "ATS3_FALL_CANNOT_BEAR_WEIGHT" not in result.triggered_rule_ids


# ---- ATS 3 mới: say / dùng chất kèm hành vi nguy hiểm ----


def test_intoxicated_dangerous_behaviour_is_at_least_ats3():
    result = _triage(
        "Có một anh vừa đứng giữa đường cao tốc, giờ nằm lắc lư dưới đất, có mùi rượu, hỏi gì cũng nói rất ít."
    )
    assert result.ats_level.value <= ATSLevel.LEVEL_3_URGENT.value
    assert "ATS3_INTOXICATED_AT_RISK" in result.triggered_rule_ids


def test_hangover_without_risk_not_flagged():
    result = _triage("Tối qua tôi uống say rượu, sáng nay đau đầu")
    assert "ATS3_INTOXICATED_AT_RISK" not in result.triggered_rule_ids
