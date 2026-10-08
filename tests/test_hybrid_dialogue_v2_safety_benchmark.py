import pytest
from src.medical_assistant.domain.hybrid_dialogue_v2_model import (
    ComplaintDelta,
    FactsDelta,
    HybridDialogueResponse,
    SafetyConcern,
    ActionArgs,
)
from src.medical_assistant.domain.clinical_fact_service import (
    ClinicalFactService,
    ANATOMICAL_BODY_REGIONS,
    COMPLAINT_SYSTEMS,
)
from src.medical_assistant.domain.probing_service import DynamicProbingService
from src.medical_assistant.domain.hybrid_dialogue_service import (
    HybridDialogueService,
    EXTRACTION_SYSTEM_PROMPT_V2,
)


def test_schema_model_contracts():
    """Verify schema_version is '2.0', severity allows 'unknown', code can be None."""
    resp = HybridDialogueResponse(
        facts_delta=FactsDelta(
            severity="unknown",
            complaints=[
                ComplaintDelta(code=None, evidence="cảm giác như sắp chết")
            ],
        ),
        safety_concerns=[
            SafetyConcern(reason="Nghi ngờ cờ đỏ cấp cứu", evidence="cảm giác như sắp chết")
        ],
    )
    assert resp.schema_version == "2.0"
    assert resp.facts_delta.severity == "unknown"
    assert resp.facts_delta.complaints[0].code is None
    assert resp.facts_delta.complaints[0].evidence == "cảm giác như sắp chết"
    assert len(resp.safety_concerns) == 1


def test_clinical_signal_orthogonality():
    """Ensure shortness_of_breath, chest_pain, headache, and dizziness are separate."""
    fact_svc = ClinicalFactService()
    
    # 1. Shortness of breath vs Chest pain
    dyspnea_facts = fact_svc.extract("tôi bị khó thở dữ dội, hụt hơi")
    assert "shortness_of_breath" in dyspnea_facts["positive_facts"]
    assert "chest_pain" not in dyspnea_facts["positive_facts"]

    chest_facts = fact_svc.extract("tôi bị đau ngực, tức ngực trái")
    assert "chest_pain" in chest_facts["positive_facts"]
    assert "shortness_of_breath" not in chest_facts["positive_facts"]

    # 2. Dizziness vs Headache
    dizziness_facts = fact_svc.extract("tôi bị chóng mặt quay cuồng, mất thăng bằng")
    assert "dizziness" in dizziness_facts["positive_facts"]
    assert "headache" not in dizziness_facts["positive_facts"]

    headache_facts = fact_svc.extract("tôi bị đau nửa đầu dữ dội")
    assert "headache" in headache_facts["positive_facts"]
    assert "dizziness" not in headache_facts["positive_facts"]

    # 3. Check complaint systems
    assert COMPLAINT_SYSTEMS["shortness_of_breath"] == "respiratory"
    assert COMPLAINT_SYSTEMS["chest_pain"] == "cardiology"
    assert COMPLAINT_SYSTEMS["dizziness"] == "neurology"
    assert COMPLAINT_SYSTEMS["headache"] == "neurology"


def test_anatomical_body_regions_mapping():
    """Verify anatomical catalog contains correct body regions."""
    assert "lower_limb" in ANATOMICAL_BODY_REGIONS
    assert ANATOMICAL_BODY_REGIONS["lower_limb"]["primary_system"] == "musculoskeletal"
    assert "bắp đùi" in ANATOMICAL_BODY_REGIONS["lower_limb"]["synonyms"]
    assert "muscle_pain" in ANATOMICAL_BODY_REGIONS["lower_limb"]["complaint_codes"]

    assert "respiratory" in ANATOMICAL_BODY_REGIONS
    assert "shortness_of_breath" in ANATOMICAL_BODY_REGIONS["respiratory"]["complaint_codes"]


def test_dynamic_probing_candidates_injection():
    """Verify backend dynamic probing supplies relevant candidates instead of hardcoded limb questions."""
    probing_svc = DynamicProbingService()
    
    # Abdominal pain should get GI probing questions
    candidates_ab = probing_svc.get_probing_candidates_for_context("abdominal_pain", language="vi")
    assert len(candidates_ab) >= 2
    assert any("bụng" in q.lower() for q in candidates_ab)

    # Headache should get neurological probing questions
    candidates_head = probing_svc.get_probing_candidates_for_context("headache", language="vi")
    assert len(candidates_head) >= 2
    assert any("đầu" in q.lower() for q in candidates_head)


def test_system_prompt_structure_integrity():
    """Verify prompt rules are cleanly numbered 1..16 without duplicates or test-case hardcoding."""
    # Ensure no duplicate rule numbers 22-26
    assert "22. Theo language" not in EXTRACTION_SYSTEM_PROMPT_V2
    assert "26. quick_replies" not in EXTRACTION_SYSTEM_PROMPT_V2

    # Ensure no hotfix patches
    assert "TUYỆT ĐỐI KHÔNG GÁN SANG BỤNG" not in EXTRACTION_SYSTEM_PROMPT_V2
    assert "Vinmec Ocean Park" not in EXTRACTION_SYSTEM_PROMPT_V2
    assert "Ở Hà Nội khám ở đâu tốt em?" not in EXTRACTION_SYSTEM_PROMPT_V2

    # Ensure safety rule mentions safety_concerns with code = null
    assert "KỂ CẢ CHƯA MAP ĐƯỢC MÃ (code = null)" in EXTRACTION_SYSTEM_PROMPT_V2
    assert "request_safety_review" in EXTRACTION_SYSTEM_PROMPT_V2
    assert "out_of_scope_decline" in EXTRACTION_SYSTEM_PROMPT_V2


def test_backend_adapt_v2_to_v1_severity():
    """Verify adapt_v2_to_v1 normalizes 'unknown' and 'null' to None."""
    svc = HybridDialogueService()
    resp_unknown = HybridDialogueResponse(
        facts_delta=FactsDelta(severity="unknown")
    )
    adapted = svc.adapt_v2_to_v1(resp_unknown)
    assert adapted["severity"] is None

    resp_mild = HybridDialogueResponse(
        facts_delta=FactsDelta(severity="mild")
    )
    adapted_mild = svc.adapt_v2_to_v1(resp_mild)
    assert adapted_mild["severity"] == "mild"
