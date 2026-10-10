"""Hồi quy đa chuyên khoa (2026-10-10): trích đủ triệu chứng, nhóm mới, nhất quán chuyên khoa chính."""

import pytest

from src.medical_assistant.domain.clinical_fact_service import ClinicalFactService
from src.medical_assistant.domain.language_service import canonicalize_specialty_code
from src.medical_assistant.domain.triage_service import get_triage_service


def _resolve(*turns: str):
    fs, svc = ClinicalFactService(), get_triage_service()
    facts: dict = {}
    for i, text in enumerate(turns, start=1):
        facts = fs.merge(facts, fs.extract(text, turn_index=i))
    result = svc.resolve_multi_symptom(svc.evaluate_symptoms(" ".join(turns)), facts)
    return facts, result


def _active(text: str) -> list[str]:
    return [c["code"] for c in ClinicalFactService().extract(text, 1)["complaints"] if c["status"] == "active"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("đau lưng và ho kéo dài 2 tuần", {"back_pain", "cough"}),
        ("đau khớp gối, sốt nhẹ", {"joint_pain", "fever"}),
        ("đau họng, ho, sốt", {"sore_throat", "cough", "fever"}),
        ("đau dạ dày và đau vai gáy", {"abdominal_pain", "neck_shoulder_pain"}),
        ("mắt đỏ ngứa, nổi mẩn ngứa ở tay", {"eye_symptoms", "skin_lesion"}),
        ("tiểu buốt và đau lưng", {"urinary_symptoms", "back_pain"}),
        ("trễ kinh và đau đầu", {"gynecologic_symptoms", "headache"}),
        ("đau răng và đau tai", {"dental_pain", "ear_nose_symptoms"}),
    ],
)
def test_second_symptom_is_not_dropped(text, expected):
    assert expected <= set(_active(text))


@pytest.mark.parametrize("text", ["tôi và họ đi khám chung", "kết quả bị bỏ sót", "đi dạo quanh hồ"])
def test_ho_sot_without_symptom_context_is_ignored(text):
    assert not {"cough", "fever"} & set(_active(text))


def test_patient_order_drives_chief_complaint():
    facts = ClinicalFactService().extract("tiểu buốt và đau lưng", 1)
    assert facts["chief_complaint"] == "urinary_symptoms"


@pytest.mark.parametrize(
    ("turns", "required"),
    [
        (["đau lưng và ho kéo dài 2 tuần"], {"XUONG_KHOP", "HO_HAP"}),
        (["tiểu buốt và đau lưng"], {"THAN_TIET_NIEU"}),
        (["trễ kinh và đau đầu"], {"SAN_PHU_KHOA", "THAN_KINH"}),
        (["đau răng và đau tai"], {"RANG_HAM_MAT", "TAI_MUI_HONG"}),
        (["bé bị sốt, ho, nổi ban đỏ"], {"NHI_KHOA"}),
        (["tôi bị đau lưng", "tôi bị thêm đau họng nữa"], {"XUONG_KHOP", "TAI_MUI_HONG"}),
    ],
)
def test_multi_site_recommends_every_involved_specialty(turns, required):
    _, result = _resolve(*turns)
    assert required <= {c.code for c in result.recommended_specialties}


@pytest.mark.parametrize(
    "turns",
    [
        ["đau lưng và ho kéo dài 2 tuần"],
        ["Tôi bị ho nhiều và rát họng"],
        ["tôi đau đầu", "giờ thêm đau bụng", "à hết đau đầu rồi"],
    ],
)
def test_primary_specialty_is_first_recommendation(turns):
    _, result = _resolve(*turns)
    assert result.recommended_specialties
    assert canonicalize_specialty_code(result.suggested_specialty) == result.recommended_specialties[0].code


def test_cough_with_sore_throat_routes_to_ent_without_crash():
    # Trước đây IndexError khi chỉ 1 khoa được gợi ý nhưng 2 khoa cần hỏi lại.
    _, result = _resolve("đau họng, ho, sốt")
    assert result.recommended_specialties[0].code == "TAI_MUI_HONG"


def test_resolved_complaint_does_not_stay_primary():
    _, result = _resolve("tôi đau đầu", "giờ thêm đau bụng", "à hết đau đầu rồi")
    assert canonicalize_specialty_code(result.suggested_specialty) == "TIEU_HOA"


def test_lifting_heavy_objects_is_not_pediatric():
    assert not ClinicalFactService().extract("đau lưng sau khi bê đồ nặng", 1)["patient_is_child"]


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("Thận - Tiết niệu", "THAN_TIET_NIEU"),
        ("Sản phụ khoa", "SAN_PHU_KHOA"),
        ("Women's Health Center", "SAN_PHU_KHOA"),
        ("Nhi khoa", "NHI_KHOA"),
        ("Mắt (Nhãn khoa)", "MAT"),
        ("Răng - Hàm - Mặt", "RANG_HAM_MAT"),
        ("Oncology Center", "UNG_BUOU"),
        ("Nội tiết", "NOI_TIET"),
        ("Cấp cứu", "CAP_CUU"),
        ("ENT", "TAI_MUI_HONG"),
    ],
)
def test_specialties_no_longer_collapse_to_general(name, code):
    assert canonicalize_specialty_code(name) == code
