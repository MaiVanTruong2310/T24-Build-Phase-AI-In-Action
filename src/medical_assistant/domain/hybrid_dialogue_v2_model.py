from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class FactObservation(BaseModel):
    model_config = ConfigDict(extra='forbid')

    code: Optional[str] = None
    polarity: Literal["positive", "negative", "uncertain"]
    temporality: Literal["current", "historical", "resolved", "unknown"]
    subject: Literal["self", "other", "unknown"]
    evidence: str

class FactCorrection(BaseModel):
    model_config = ConfigDict(extra='forbid')

    field: str
    evidence: str


class ComplaintDelta(BaseModel):
    """One complaint explicitly introduced, updated, denied, or resolved this turn."""

    model_config = ConfigDict(extra="forbid")

    code: str
    system: Optional[str] = None
    status: Literal["active", "denied", "resolved", "uncertain"] = "active"
    evidence: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class FactsDelta(BaseModel):
    model_config = ConfigDict(extra='forbid')

    subject: Literal["self", "other", "unknown"]
    chief_complaint: Optional[str] = None
    complaints: List[ComplaintDelta] = Field(default_factory=list)
    observations: List[FactObservation] = Field(default_factory=list)
    duration_text: Optional[str] = None
    duration_days: Optional[int] = Field(None, ge=0)
    bowel_interval_text: Optional[str] = None
    bowel_interval_days: Optional[int] = Field(None, ge=0)
    onset: Literal["sudden", "gradual", "unknown"]
    location: Optional[str] = None
    severity: Literal["mild", "moderate", "severe", "null"] = "null"
    pain_severity_0_10: Optional[int] = Field(None, ge=0, le=10)
    qualifiers: List[str] = Field(default_factory=list)
    corrections: List[FactCorrection] = Field(default_factory=list)
    patient_name: Optional[str] = None

class SafetyConcern(BaseModel):
    model_config = ConfigDict(extra='forbid')

    observation_indexes: List[int]
    reason: str

class MissingFact(BaseModel):
    model_config = ConfigDict(extra='forbid')

    field: str
    reason: str

class ActionArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')

    specialty_key: Optional[str] = None
    slot_id: Optional[str] = None
    facility_id: Optional[str] = None
    requested_days: Optional[int] = Field(None, gt=0)
    preferred_date_text: Optional[str] = None
    preferred_period: Literal["morning", "afternoon", "evening", "null"] = "null"
    faq_key: Optional[str] = None
    department_key: Optional[str] = None
    comparison_requested: Optional[bool] = False

class CandidateSpecialty(BaseModel):
    model_config = ConfigDict(extra='forbid')

    specialty_key: str
    reason: str

class HybridDialogueResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')

    schema_version: Literal["2.0"]
    language: Literal["vi", "en"]
    primary_intent: Literal["symptom_report", "visit_request", "schedule_request", "slot_selection", "faq", "department_info", "facility_info", "medication_request", "diagnosis_request", "human_request", "language_change", "out_of_scope", "unclear"]
    secondary_intents: List[Literal["symptom_report", "visit_request", "schedule_request", "slot_selection", "faq", "department_info", "facility_info", "medication_request", "diagnosis_request", "human_request", "language_change", "out_of_scope", "unclear"]] = Field(default_factory=list)
    topic_change: Literal["none", "administrative_detour", "symptom_changed", "patient_changed", "correction"]
    facts_delta: FactsDelta
    safety_concerns: List[SafetyConcern] = Field(default_factory=list)
    missing_facts: List[MissingFact] = Field(default_factory=list)
    proposed_action: Literal[
        "clarify_visit_purpose", "ask_clarifying_question", "suggest_specialty",
        "search_available_slot", "hold_slot", "answer_faq", "show_department_info", "show_facility_info",
        "decline_medication_request", "respond_to_diagnosis_request", "request_safety_review",
        "request_human_help", "acknowledge_language_change", "out_of_scope_decline"
    ]
    action_args: ActionArgs
    candidate_specialties: List[CandidateSpecialty] = Field(default_factory=list)
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)
    action_confidence: float = Field(..., ge=0.0, le=1.0)
    draft_response: str
    quick_replies: List[str] = Field(default_factory=list)
