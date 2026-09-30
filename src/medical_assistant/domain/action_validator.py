from typing import List, Dict, Any

def has_clinical_evidence(clinical_facts: Dict[str, Any], v2_response: Any) -> bool:
    """Check if there is sufficient clinical evidence to treat as a symptom report rather than a generic visit."""
    if clinical_facts.get("chief_complaint"):
        return True
    if len(clinical_facts.get("positive_facts", [])) > 0:
        return True
    if clinical_facts.get("duration_days") is not None or clinical_facts.get("location"):
        return True
    if hasattr(v2_response.facts_delta, "observations") and any(obs.polarity != "negative" for obs in v2_response.facts_delta.observations):
        return True
    return False

def validate_action(
    action: str,
    clinical_facts: Dict[str, Any],
    v2_response: Any,
    allowed_actions: List[str]
) -> str:
    """Validate and safely fallback LLM actions based on clinical rules."""
    if action not in allowed_actions:
        action = "ask_clarifying_question"

    if action == "clarify_visit_purpose" and has_clinical_evidence(clinical_facts, v2_response):
        action = "ask_clarifying_question"

    if action == "suggest_specialty":
        if v2_response.missing_facts:
            action = "ask_clarifying_question"

    if action == "search_available_slot":
        has_spec = bool(
            v2_response.candidate_specialties
            or getattr(v2_response.action_args, "specialty_key", None)
            or getattr(v2_response.action_args, "department_key", None)
            or clinical_facts.get("chief_complaint")
        )
        if not has_spec:
            action = "clarify_visit_purpose"

    return action
