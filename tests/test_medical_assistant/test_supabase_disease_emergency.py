import pytest

from src.medical_assistant.domain.disease_triage import ATSLevel, UrgencyTier
from src.medical_assistant.domain.triage_service import ClinicalTriageService


@pytest.fixture
def triage_service():
    return ClinicalTriageService()


def test_supabase_emergency_cardiac_dyspnea(triage_service):
    """Bệnh nhân đau tim kèm khó thở: Phải kích hoạt khẩn cấp ATS 1 hoặc 2."""
    res = triage_service.evaluate_symptoms("Tôi bị khó thở và đau tim, tôi phải làm sao")
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.urgency_tier == UrgencyTier.EMERGENCY_BLOCK
    assert res.max_booking_days == 0
    assert "Trung tâm Tim mạch" in res.suggested_specialty


def test_supabase_emergency_boerhaave_syndrome(triage_service):
    """Hội chứng Boerhaave (thủng thực quản sau nôn ói) từ Supabase disease_triage."""
    res = triage_service.evaluate_symptoms("Bác sĩ ơi tôi đau ngực dữ dội sau khi nôn, nôn ra máu và khó thở")
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.urgency_tier == UrgencyTier.EMERGENCY_BLOCK
    assert res.max_booking_days == 0


def test_supabase_emergency_spontaneous_pneumothorax(triage_service):
    """Tràn khí màng phổi tự phát từ Supabase disease_triage."""
    res = triage_service.evaluate_symptoms("Tôi bị đau ngực dữ dội đột ngột như dao đâm và khó thở dữ dội")
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.urgency_tier == UrgencyTier.EMERGENCY_BLOCK


def test_supabase_emergency_anaphylaxis_airway(triage_service):
    """Sốc phản vệ phù môi lưỡi khó thở từ Supabase disease_triage."""
    res = triage_service.evaluate_symptoms("Tôi ăn hải sản xong bị sưng phù môi lưỡi, nổi mề đay và khó thở thở rít")
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.urgency_tier == UrgencyTier.EMERGENCY_BLOCK


def test_supabase_emergency_epiglottitis(triage_service):
    """Viêm nắp thanh quản cấp (thở rít, chảy dãi) từ Supabase disease_triage."""
    res = triage_service.evaluate_symptoms("Bé bị khó thở dữ dội, thở rít, nuốt đau chảy nước dãi không nuốt được")
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.urgency_tier == UrgencyTier.EMERGENCY_BLOCK


def test_supabase_emergency_stroke_fast(triage_service):
    """Đột quỵ não dấu hiệu FAST."""
    res = triage_service.evaluate_symptoms("Người nhà tôi bị méo miệng, liệt nửa người và nói khó")
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.urgency_tier == UrgencyTier.EMERGENCY_BLOCK


def test_supabase_emergency_massive_gi_bleeding(triage_service):
    """Xuất huyết tiêu hóa cấp nôn ra máu."""
    res = triage_service.evaluate_symptoms("Tôi bị nôn ra máu ồ ạt, người lả đi")
    assert res.is_emergency is True
    assert res.ats_level in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)
    assert res.urgency_tier == UrgencyTier.EMERGENCY_BLOCK


def test_supabase_non_emergency_outpatient_complaint(triage_service):
    """Triệu chứng ngoại trú thông thường: Rụng tóc và mất ngủ (ATS 4 - Không cấp cứu)."""
    res = triage_service.evaluate_symptoms("Tôi bị rụng tóc nhiều và mất ngủ 3-4 ngày nay rồi")
    assert res.is_emergency is False
    assert res.ats_level == ATSLevel.LEVEL_4_STANDARD
    assert res.urgency_tier == UrgencyTier.WITHIN_WEEK
    assert res.max_booking_days > 0


def test_supabase_non_emergency_periodic_checkup(triage_service):
    """Khám sức khỏe tổng quát định kỳ (ATS 5 - Không cấp cứu)."""
    res = triage_service.evaluate_symptoms("Tôi muốn đăng ký kiểm tra sức khỏe định kỳ")
    assert res.is_emergency is False
    assert res.ats_level == ATSLevel.LEVEL_5_NON_URGENT
    assert res.urgency_tier == UrgencyTier.FLEXIBLE
    assert res.max_booking_days == 30
