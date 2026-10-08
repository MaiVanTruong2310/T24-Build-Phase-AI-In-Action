from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FactObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = None
    polarity: Literal["positive", "negative", "uncertain"]
    temporality: Literal["current", "historical", "resolved", "unknown"]
    subject: Literal["self", "other", "unknown"]
    evidence: str


class FactCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    evidence: str


class ComplaintDelta(BaseModel):
    """One complaint explicitly introduced, updated, denied, or resolved this turn."""

    model_config = ConfigDict(extra="forbid")

    code: str | None = None
    system: str | None = None
    status: Literal["active", "denied", "resolved", "uncertain"] = "active"
    evidence: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class FactsDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: Literal["self", "other", "unknown"] = "self"
    chief_complaint: str | None = None
    complaints: list[ComplaintDelta] = Field(default_factory=list)
    observations: list[FactObservation] = Field(default_factory=list)
    duration_text: str | None = None
    duration_days: int | None = Field(None, ge=0)
    bowel_interval_text: str | None = None
    bowel_interval_days: int | None = Field(None, ge=0)
    onset: Literal["sudden", "gradual", "unknown"] = "unknown"
    location: str | None = None
    severity: Literal["mild", "moderate", "severe", "unknown", "null"] = "unknown"
    pain_severity_0_10: int | None = Field(None, ge=0, le=10)
    qualifiers: list[str] = Field(default_factory=list)
    body_regions: list[str] = Field(default_factory=list)
    primary_system: str | None = None
    functional_impairment: bool = False
    missing_dimensions: list[str] = Field(default_factory=list)
    corrections: list[FactCorrection] = Field(default_factory=list)
    patient_name: str | None = None
    patient_phone: str | None = None


class SafetyConcern(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_indexes: list[int] = Field(default_factory=list)
    reason: str
    evidence: str | None = None


class MissingFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    reason: str


class ActionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    specialty_key: str | None = None
    slot_id: str | None = None
    booking_id: str | None = None
    facility_id: str | None = None
    facility_name: str | None = None
    requested_days: int | None = Field(None, gt=0)
    preferred_date_text: str | None = None
    preferred_period: Literal["morning", "afternoon", "evening", "null"] = "null"
    faq_key: str | None = None
    department_key: str | None = None
    comparison_requested: bool | None = False


class CandidateSpecialty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    specialty_key: str
    reason: str


class HybridDialogueResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: Literal["2.0"] = "2.0"
    language: str = "vi"
    primary_intent: str = "unclear"
    secondary_intents: list[str] = Field(default_factory=list)
    topic_change: str = "none"
    facts_delta: FactsDelta = Field(default_factory=FactsDelta)
    safety_concerns: list[SafetyConcern] = Field(default_factory=list)
    missing_facts: list[MissingFact] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_reason: str | None = None
    proposed_action: str = "clarify_visit_purpose"
    action_args: ActionArgs = Field(default_factory=ActionArgs)
    candidate_specialties: list[CandidateSpecialty] = Field(default_factory=list)
    extraction_confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    action_confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    draft_response: str = ""
    quick_replies: list[str] = Field(default_factory=list)
