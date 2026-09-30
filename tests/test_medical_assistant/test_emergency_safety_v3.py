"""
Regression Test Suite for Safety Engine v3.
Target: 100% detection of the 12 previously missed emergency cases in DDXPlus 150-case benchmark.
Rules:
- Must predict ATS 1 or ATS 2
- Must set is_emergency = True
- Must set care_setting = 'EMERGENCY_DEPT'
- Must record triggered_rule_ids for clinical auditability
"""

import pytest

from src.medical_assistant.domain.disease_triage import ATSLevel
from src.medical_assistant.domain.triage_service import ClinicalTriageService


@pytest.fixture(scope="module")
def triage_service():
    return ClinicalTriageService()


def test_missed_case_1_laryngospasm_stridor(triage_service):
    """[1] Case ddx_00015: Laryngospasm (ATS 2) - Stridor / High pitched sound when breathing in"""
    query = "Bác sĩ ơi, tôi bị thở rít khi hít vào, cảm thấy nghẹt thở."
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True, "Phải nhận diện cấp cứu cho thở rít thanh quản"
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"
    assert len(res.triggered_rule_ids) > 0


def test_missed_case_2_pneumothorax_violent_chest_pain(triage_service):
    """[2] Case ddx_00022: Spontaneous pneumothorax (ATS 1) - Violent pleuritic chest pain"""
    query = "Bác sĩ ơi, tôi bị đau ở vùng ngực dưới, mạn sườn ngực phải, vùng ngực trên, vú phải, vú trái, tính chất nhói buốt thắt lòng, dữ dội dữ tợn"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True, "Phải nhận diện cấp cứu cho đau ngực dữ dội nhói buốt thắt lòng"
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"
    assert "PNEUMOTHORAX_ACUTE" in res.triggered_rule_ids or len(res.triggered_rule_ids) > 0


def test_missed_case_3_laryngospasm_bilingual(triage_service):
    """[3] Case ddx_00059: Laryngospasm (ATS 2) - High pitched sound when breathing in (Bilingual)"""
    query = "Doctor, I noticed a high pitched sound when breathing in and feel suffocating."
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"


def test_missed_case_4_epiglottitis_acute_odynophagia(triage_service):
    """[4] Case ddx_00068: Epiglottitis (ATS 1) - Severe odynophagia, fever, dyspnea, dysphagia"""
    query = "Bác sĩ ơi, tôi bị đau ở amidan phải, cạnh cổ bên phải, vòm họng, họng, dưới hàm, tính chất nhói như dao đâm, nhói buốt, kèm theo khó thở, hụt hơi, kèm theo sốt, kèm theo khó nuốt, nuốt vướng"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"
    assert "EPIGLOTTITIS_ACUTE" in res.triggered_rule_ids or len(res.triggered_rule_ids) > 0


def test_missed_case_5_psvt_palpitations_presyncope(triage_service):
    """[5] Case ddx_00074: PSVT (ATS 2) - Palpitations + Dizziness/presyncope"""
    query = "Bác sĩ ơi, tôi bị đau ở sau đầu, thái dương phải, tính chất âm ỉ dai dẳng, chuột rút co quắp, nặng trịch đè nén, kèm theo chóng mặt, xây xẩm, kèm theo tim đập nhanh, hồi hộp đánh trống ngực"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"
    assert "PSVT_ARRHYTHMIA_ACUTE" in res.triggered_rule_ids or len(res.triggered_rule_ids) > 0


def test_missed_case_6_copd_anthonisen_triad(triage_service):
    """[6] Case ddx_00082: Acute COPD exacerbation (ATS 2) - Dyspnea + purulent sputum + wheezing"""
    query = "Bác sĩ ơi, tôi bị ho có đờm đặc, kèm theo khó thở, hụt hơi, kèm theo thở khò khè thở rít"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"
    assert "COPD_ASTHMA_EXACERBATION" in res.triggered_rule_ids or len(res.triggered_rule_ids) > 0


def test_missed_case_7_pulmonary_edema_diaphoresis(triage_service):
    """[7] Case ddx_00095: Acute pulmonary edema (ATS 1) - Dyspnea + diaphoresis + swelling"""
    query = "Bác sĩ ơi, tôi bị đau ở cổ chân trái, mạn sườn ngực trái, vùng ngực trên, bắp chân trái, thành ngực sau bên trái, tính chất đau âm ỉ khó chịu, kèm theo khó thở, hụt hơi, kèm theo vã mồ hôi nhiều, kèm theo sưng phù"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"
    assert "ACUTE_PULMONARY_EDEMA" in res.triggered_rule_ids or len(res.triggered_rule_ids) > 0


def test_missed_case_8_bronchospasm_severe_wheezing(triage_service):
    """[8] Case ddx_00103: Bronchospasm / Acute asthma (ATS 2) - Dyspnea + Wheezing/stridor"""
    query = "Bác sĩ ơi, tôi bị khó thở, hụt hơi, kèm theo thở khò khè thở rít"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"


def test_missed_case_9_anaphylaxis_multisystem(triage_service):
    """[9] Case ddx_00126: Anaphylaxis (ATS 1) - Multisystem: rash + swelling + dyspnea + wheeze + GI"""
    query = "Bác sĩ ơi, tôi bị đau ở hông sườn trái, hố chậu phải vùng bẹn, hố chậu trái vùng bẹn, vùng bụng, vùng thượng vị, tính chất nhói như dao đâm, kèm theo khó thở, hụt hơi, kèm theo thở khò khè thở rít, kèm theo buồn nôn, kèm theo sưng phù, kèm theo nổi ban đỏ mẩn ngứa trên da"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level == ATSLevel.LEVEL_1_RESUSCITATION
    assert res.care_setting == "EMERGENCY_DEPT"
    assert "ANAPHYLAXIS_ACUTE" in res.triggered_rule_ids or len(res.triggered_rule_ids) > 0


def test_missed_case_10_copd_purulent_sputum_wheezing(triage_service):
    """[10] Case ddx_00142: Acute COPD exacerbation (ATS 2) - Cough abundant sputum + wheezing sound"""
    query = "Bác sĩ ơi, tôi bị ho có đờm đặc, kèm theo ho, kèm theo thở khò khè thở rít"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"


def test_missed_case_11_boerhaave_chest_epigastric_vomiting(triage_service):
    """[11] Case ddx_00146: Boerhaave (ATS 1) - Violent chest/epigastric pain + vomiting/nausea"""
    query = "Bác sĩ ơi, tôi bị đau ở vùng ngực dưới, hông sườn phải, hông sườn trái, vùng ngực trên, vùng thượng vị, tính chất nhói buốt thắt lòng, âm ỉ dai dẳng, nhói như dao đâm, dữ dội dữ tợn, kèm theo buồn nôn"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"
    assert "BOERHAAVE_ACUTE" in res.triggered_rule_ids or len(res.triggered_rule_ids) > 0


def test_missed_case_12_scombroid_acute_flushing_nausea(triage_service):
    """[12] Case ddx_00149: Scombroid food poisoning (ATS 2) - Acute rash/flushing + nausea"""
    query = "Bác sĩ ơi, tôi bị buồn nôn, kèm theo nổi ban đỏ mẩn ngứa trên da, đột ngột đỏ bừng mặt"
    res = triage_service.evaluate_symptoms(query)
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.care_setting == "EMERGENCY_DEPT"
    assert "SCOMBROID_POISONING_ACUTE" in res.triggered_rule_ids or len(res.triggered_rule_ids) > 0
