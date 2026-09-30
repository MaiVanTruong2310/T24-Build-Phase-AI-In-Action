from src.medical_assistant.domain.action_validator import validate_action, has_clinical_evidence

class MockV2Response:
    def __init__(self, facts_delta, missing_facts=None, candidate_specialties=None):
        self.facts_delta = facts_delta
        self.missing_facts = missing_facts or []
        self.candidate_specialties = candidate_specialties or []

class MockFactsDelta:
    def __init__(self, observations=None):
        self.observations = observations or []

def test_has_clinical_evidence():
    assert has_clinical_evidence({"chief_complaint": "đau đầu"}, None) == True
    assert has_clinical_evidence({"positive_facts": ["D01"]}, None) == True
    assert has_clinical_evidence({}, MockV2Response(MockFactsDelta())) == False

def test_validate_action():
    allowed_actions = ["ask_clarifying_question", "clarify_visit_purpose", "suggest_specialty"]

    # 1. Invalid action fallback
    assert validate_action("invalid_action", {}, MockV2Response(MockFactsDelta()), allowed_actions) == "ask_clarifying_question"

    # 2. clarify_visit_purpose overrides to ask_clarifying_question when there is clinical evidence
    v2_resp = MockV2Response(MockFactsDelta())
    assert validate_action("clarify_visit_purpose", {"chief_complaint": "đau bụng"}, v2_resp, allowed_actions) == "ask_clarifying_question"

    # 3. clarify_visit_purpose stays clarify_visit_purpose when there is no clinical evidence
    assert validate_action("clarify_visit_purpose", {}, v2_resp, allowed_actions) == "clarify_visit_purpose"
