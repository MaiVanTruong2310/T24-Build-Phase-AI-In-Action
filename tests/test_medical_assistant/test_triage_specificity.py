"""Mức khẩn từ KB, gõ không dấu, viêm ruột thừa, ngày khám vs thang điểm đau — hồi quy 2026-10-10."""

from datetime import date

import pytest

from src.medical_assistant.domain.ats_descriptor_service import strip_accents
from src.medical_assistant.domain.booking_slot_service import parse_vietnamese_date
from src.medical_assistant.domain.triage_service import get_triage_service

REF = date(2026, 10, 10)


@pytest.mark.parametrize("query", ["bụng chướng, đầy hơi sau ăn", "buồn nôn nhẹ sau khi ăn đồ dầu mỡ"])
def test_loose_typical_symptom_match_does_not_raise_urgency(query):
    # Trùng khớp chỉ bằng triệu chứng điển hình (đầy hơi ↔ "Vàng da bệnh lý") không được đẩy lên ATS 3.
    assert get_triage_service().evaluate_symptoms(query).ats_level.value == 4


@pytest.mark.parametrize(
    "query",
    [
        "con tôi sốt cao 39 độ từ tối qua, vẫn tỉnh táo chơi được",
        "bụng chướng, đầy hơi sau ăn",
        "tôi bị đau họng ho khan 3 ngày",
    ],
)
def test_typing_without_diacritics_keeps_same_ats(query):
    service = get_triage_service()
    assert service.evaluate_symptoms(strip_accents(query)).ats_level == service.evaluate_symptoms(query).ats_level


@pytest.mark.parametrize(
    ("query", "ats"),
    [
        ("Tôi đau bụng dưới bên phải và sốt nhẹ từ hôm qua", 3),
        ("tôi đau hạ vị phải 2 ngày", 3),
        ("đau bụng dưới bên trái", 4),
        ("tôi đau đầu, không đau bụng dưới bên phải", 4),
    ],
)
def test_right_lower_quadrant_pain_is_same_day(query, ats):
    assert get_triage_service().evaluate_symptoms(query).ats_level.value == ats


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Đau khoảng 6/10, đi lại thấy đau hơn", None),
        ("mức đau 8/10", None),
        ("sốt 37.8 độ", None),
        ("khám ngày 20/10 nhé", date(2026, 10, 20)),
        ("Đặt lịch cho bé chiều nay", REF),
        ("sốt từ chiều nay", None),
    ],
)
def test_pain_scores_and_onset_times_are_not_booking_dates(text, expected):
    assert parse_vietnamese_date(text, reference_date=REF) == expected


@pytest.mark.parametrize(
    "query",
    [
        "tôi muốn chết",
        "tôi không muốn sống nữa",
        "toi khong muon song nua",
        "tôi buồn chán muốn chết",
        "tôi đã uống cả lọ thuốc ngủ",
        "tôi uống 20 viên paracetamol",
    ],
)
def test_self_harm_and_overdose_trigger_emergency(query):
    assert get_triage_service().evaluate_symptoms(query).is_emergency


@pytest.mark.parametrize(
    ("query", "ats"),
    [
        ("đau bụng muốn chết", 3),  # thành ngữ: đau rất nặng, không phải ý nghĩ tự sát
        ("mệt muốn chết", 4),
        ("tôi muốn uống thuốc giảm đau", 4),
        ("tôi không muốn tự tử, chỉ mất ngủ", 4),
    ],
)
def test_intensity_idioms_are_not_suicidal(query, ats):
    result = get_triage_service().evaluate_symptoms(query)
    assert not result.is_emergency and result.ats_level.value == ats


@pytest.mark.parametrize(
    ("query", "specialty"),
    [
        ("Dạo này tôi buồn chán, không muốn làm gì cả", "Trung tâm Chăm sóc sức khỏe tinh thần"),
    ],
)
def test_low_mood_routes_to_mental_health(query, specialty):
    assert get_triage_service().evaluate_symptoms(query).suggested_specialty == specialty


@pytest.mark.parametrize(
    ("query", "code"),
    [
        ("Ông tôi 70 tuổi hay đi tiểu đêm", "urinary_symptoms"),
        ("Tôi sờ thấy cục ở cổ", "neck_lump"),
        ("Tôi mang thai 20 tuần muốn khám thai", "pregnancy_care"),
    ],
)
def test_new_complaint_facts_are_extracted(query, code):
    from src.medical_assistant.domain.clinical_fact_service import get_clinical_fact_service

    assert get_clinical_fact_service().extract(query).get("chief_complaint") == code
