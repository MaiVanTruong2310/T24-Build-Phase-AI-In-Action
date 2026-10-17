from src.medical_assistant.domain.clinical_fact_service import ClinicalFactService
from src.medical_assistant.domain.fact_catalog import (
    CLINICAL_FACT_CATALOG,
    build_compiled_fact_patterns,
    normalize_term,
)


def test_collision_prevention_dau_rang_not_straining():
    """Ensure 'đau răng' does not trigger constipation straining."""
    svc = ClinicalFactService()
    facts = svc.extract("tôi bị đau răng dữ dội mấy bữa nay")
    assert "straining" not in facts["positive_facts"]


def test_collision_prevention_me_day_not_skin_lesion():
    """Ensure 'mẹ dạy em' does not trigger skin_lesion (mề đay)."""
    svc = ClinicalFactService()
    facts = svc.extract("mẹ dạy em phải uống nhiều nước")
    assert "skin_lesion" not in facts["positive_facts"]

    # In contrast, actual urticaria must match
    facts_real = svc.extract("tôi bị nổi mề đay ngứa khắp người")
    assert "skin_lesion" in facts_real["positive_facts"]


def test_collision_prevention_khong_ho_tro_not_cough_negation():
    """Ensure 'không hỗ trợ' or 'không hỏi' does not falsely negate cough."""
    svc = ClinicalFactService()
    facts = svc.extract("tôi bị ho 3 ngày, bệnh viện có không hỗ trợ bảo hiểm không?")
    assert "cough" in facts["positive_facts"]
    assert "cough" not in facts["negative_facts"]


def test_conversational_yesterday_does_not_set_duration_days():
    """Ensure conversational 'hôm qua' without clinical symptoms does not assign duration_days=1."""
    svc = ClinicalFactService()
    facts_chat = svc.extract("hôm qua em bận không gọi được")
    assert facts_chat["duration_days"] is None

    # But with a clinical symptom, it must record duration_days=1
    facts_clinical = svc.extract("hôm qua tôi bị đau đầu dữ dội")
    assert facts_clinical["duration_days"] == 1
    assert "headache" in facts_clinical["positive_facts"]


def test_diacritics_normalization_vomiting_and_neck_pain():
    """Ensure vomiting ('nôn') and neck pain ('cổ vai gáy') match properly."""
    svc = ClinicalFactService()

    # Vomiting with diacritics
    facts_vomit = svc.extract("tôi bị nôn ói liên tục")
    assert "vomiting" in facts_vomit["positive_facts"]

    # Neck pain with diacritics
    facts_neck = svc.extract("tôi bị đau cổ vai gáy")
    assert "neck_shoulder_pain" in facts_neck["positive_facts"]


def test_fact_catalog_compilation_and_red_flags():
    """Verify CLINICAL_FACT_CATALOG compiles patterns with boundaries and detects red flags."""
    pos_pats, neg_pats, red_flags = build_compiled_fact_patterns()

    # Check that chest_pain and shortness_of_breath are in red flags
    assert len(red_flags) > 0
    assert "chest_pain" in pos_pats
    assert "shortness_of_breath" in pos_pats
    assert "syncope" in CLINICAL_FACT_CATALOG
    assert CLINICAL_FACT_CATALOG["syncope"].is_red_flag is True

    # Test compiled regex on a dangerous phrase
    test_str = normalize_term("bác ấy bị ngất xỉu rồi")
    matched_flags = [p.pattern for p in red_flags if p.search(test_str)]
    assert len(matched_flags) > 0
