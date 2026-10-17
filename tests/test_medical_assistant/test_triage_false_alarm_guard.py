"""Hồi quy từ triage eval (2026-10-10).

- Mảnh red flag rác từ disease_triage ("tiêu chảy", "ngoài ra", "suy tim"...) không được kích hoạt cấp cứu.
- Thai kỳ + ra máu / vỡ ối / tiền sản giật phải vào cấp cứu ATS 2, khám thai thường thì không.
- Triệu chứng bị phủ định không được quyết định chuyên khoa.
"""

import pytest

from src.medical_assistant.domain.triage_service import get_triage_service

FALSE_ALARMS = [
    "tôi bị tiêu chảy 2 ngày, vẫn ăn uống được",
    "con tôi sốt cao 39 độ từ tối qua, vẫn tỉnh táo chơi được",
    "ngoài ra tôi còn hơi đau đầu nhẹ",
    "đau răng, ví dụ khi ăn đồ lạnh thì ê buốt",
    "dạo này tôi hay nhầm lẫn đồ đạc, hay quên",
    "bố tôi bị suy tim, muốn đặt lịch tái khám",
    "tiểu đường giai đoạn 2 thì cần khám gì",
    "bụng chướng, đầy hơi sau ăn",
    "tôi hay bị chuột rút bắp chân ban đêm",
]

OBSTETRIC_EMERGENCIES = [
    "phụ nữ mang thai 8 tháng ra máu âm đạo nhiều, đau bụng",
    "bầu 7 tháng ra máu",
    "có thai 30 tuần bị ra huyết đỏ tươi",
    "thai 35 tuần vỡ ối, ra nước nhiều",
    "mang thai 34 tuần đau đầu dữ dội, nhìn mờ, phù chân",
    "bau 6 thang ra mau nhieu",
]

PREGNANCY_ROUTINE = [
    "mang thai 12 tuần muốn khám thai định kỳ",
    "bầu 20 tuần, không ra máu, không đau bụng, muốn siêu âm hình thái",
    "đang mang thai, bị đau lưng nhẹ",
]


@pytest.mark.parametrize("query", FALSE_ALARMS)
def test_junk_db_red_flag_does_not_trigger_emergency(query):
    assert get_triage_service().evaluate_symptoms(query).is_emergency is False


@pytest.mark.parametrize("query", OBSTETRIC_EMERGENCIES)
def test_obstetric_danger_sign_triggers_emergency(query):
    res = get_triage_service().evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level.value <= 2


@pytest.mark.parametrize("query", PREGNANCY_ROUTINE)
def test_routine_pregnancy_is_not_emergency(query):
    assert get_triage_service().evaluate_symptoms(query).is_emergency is False


def test_real_critical_sign_still_triggers_emergency():
    assert get_triage_service().evaluate_symptoms("bố tôi tự nhiên lơ mơ, gọi khó tỉnh").is_emergency is True


def test_cough_dyspnea_rule_ignores_hoan_toan_and_negated_dyspnea():
    res = get_triage_service().evaluate_symptoms(
        "Tôi bị đau tức bụng dưới 2 ngày, không sốt, không buồn nôn, ngực hoàn toàn bình thường không đau ngực không khó thở"
    )
    assert "COUGH_WITH_DYSPNEA" not in res.triggered_rule_ids
    assert get_triage_service().evaluate_symptoms("ho nhiều 3 ngày, khó thở khi nằm").ats_level.value <= 3


def test_negated_symptom_does_not_drive_specialty():
    res = get_triage_service().evaluate_symptoms("không đau ngực, không khó thở, chỉ hơi mệt vài hôm")
    assert res.suggested_specialty != "Trung tâm Tim mạch"
