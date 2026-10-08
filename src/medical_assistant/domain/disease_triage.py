from enum import Enum

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python 3.10 compatibility

    class StrEnum(str, Enum):  # noqa: UP042 - retain the Python 3.10 fallback.
        """Python 3.10 fallback for StrEnum."""

        pass


from pydantic import BaseModel, Field, model_validator


class ATSLevel(int, Enum):
    """Thang phân cấp cấp cứu ATS (Australasian Triage Scale)"""

    LEVEL_1_RESUSCITATION = 1  # Đe dọa mạng sống ngay lập tức -> 115
    LEVEL_2_EMERGENT = 2  # Nguy kịch cao / Time-sensitive -> Đến phòng Cấp cứu ngay
    LEVEL_3_URGENT = 3  # Bán khẩn -> Khám trong ngày (Same-day / < 24h)
    LEVEL_4_STANDARD = 4  # Tiêu chuẩn mạn tính -> Trong tuần (2-7 ngày)
    LEVEL_5_NON_URGENT = 5  # Không khẩn / Gói khám / Định kỳ -> Linh hoạt (1-4 tuần)


class UrgencyTier(StrEnum):
    EMERGENCY_BLOCK = "EMERGENCY_BLOCK"  # Khóa đặt lịch hẹn, chuyển cấp cứu
    SAME_DAY = "SAME_DAY"  # Chỉ mở slot trong ngày hôm nay hoặc sáng mai
    WITHIN_WEEK = "WITHIN_WEEK"  # Mở slot khám trong tuần (1-7 ngày)
    FLEXIBLE = "FLEXIBLE"  # Đặt lịch tự do theo nhu cầu (đến 30 ngày)


class AcuityProfile(BaseModel):
    ats_level: ATSLevel = Field(..., description="Cấp độ ATS từ 1 đến 5")
    urgency_tier: UrgencyTier = Field(..., description="Phân nhóm khẩn cấp để xử lý đặt lịch")
    max_booking_days: int = Field(..., ge=0, le=30, description="Giới hạn số ngày tối đa cho phép đặt lịch (0: block)")
    action_directive: str = Field(..., description="Chỉ thị hành động cho Agent (VD: TRIGGER_115, RESTRICT_SAME_DAY)")


class SymptomHierarchy(BaseModel):
    red_flags: list[str] = Field(
        default_factory=list,
        description="Các triệu chứng báo động cấp tính / tối khẩn (Gặp là ép Level 1 hoặc Level 2 ngay)",
    )
    warning_signs: list[str] = Field(
        default_factory=list,
        description="Các dấu hiệu cảnh báo tiến triển xấu hoặc triệu chứng cấp tính (Level 3 - Khám trong ngày)",
    )
    typical_or_mild: list[str] = Field(
        default_factory=list, description="Các triệu chứng mạn tính hoặc mức độ nhẹ/ổn định (Level 4/5)"
    )


class SyndromeCombination(BaseModel):
    combination_name: str = Field(..., description="Tên tổ hợp triệu chứng (VD: Đau ngực + khó thở)")
    required_symptoms: list[str] = Field(..., min_length=2, description="Tổ hợp gồm ít nhất 2 triệu chứng")
    severity_override: ATSLevel = Field(..., description="Cấp độ ATS khi tổ hợp này xuất hiện đồng thời")
    clinical_rationale: str = Field(default="", description="Giải thích y khoa vì sao tổ hợp này nguy hiểm")


class DiseaseTriageRecord(BaseModel):
    disease_key: str = Field(..., description="Key định danh mặt bệnh từ crawled data")
    name: str = Field(..., description="Tên đầy đủ của bệnh")
    primary_specialty_code: str = Field(..., description="Mã chuyên khoa (VD: TIM_MACH, TIEU_HOA, THAN_KINH)")
    primary_specialty_name: str = Field(..., description="Tên chuyên khoa tiếp nhận")
    acuity: AcuityProfile = Field(..., description="Hồ sơ phân cấp khẩn cấp của bệnh")
    symptom_hierarchy: SymptomHierarchy = Field(..., description="Phân cấp triệu chứng 3 tầng")
    syndrome_combinations: list[SyndromeCombination] = Field(
        default_factory=list, description="Danh sách các tổ hợp triệu chứng đặc thù dẫn đến biến chứng nguy hiểm"
    )
    probing_questions: list[str] = Field(
        default_factory=list, description="Câu hỏi làm rõ Agent dùng khi bệnh nhân chỉ mô tả mơ hồ 1 triệu chứng"
    )


class TriageSpecialtyCandidate(BaseModel):
    code: str
    name: str
    score: float = Field(ge=0.0)
    ats_level: ATSLevel
    evidence: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    source: str = "deterministic_multi_symptom"
    routing_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_strength: str = "weak"
    has_independent_evidence: bool = False
    publicly_recommended: bool = False
    suppression_reason: str | None = None


class TriageEvaluationResult(BaseModel):
    """Kết quả phân tích khi bệnh nhân nhập triệu chứng vào Agent"""

    matched_disease_key: str | None = None
    matched_disease_name: str | None = None
    ats_level: ATSLevel
    urgency_tier: UrgencyTier
    max_booking_days: int
    is_emergency: bool = False
    care_setting: str = "OUTPATIENT_CLINIC"  # EMERGENCY_DEPT hoặc OUTPATIENT_CLINIC
    triggered_red_flags: list[str] = Field(default_factory=list)
    triggered_rule_ids: list[str] = Field(default_factory=list)
    suggested_specialty: str
    candidate_specialties: list[TriageSpecialtyCandidate] = Field(default_factory=list)
    recommended_specialties: list[TriageSpecialtyCandidate] = Field(default_factory=list)
    conflict_reason: str | None = None
    needs_multi_symptom_clarification: bool = False
    clarification_question: str | None = None
    patient_guidance: str
    acuity_status: str = "DETERMINED"
    disposition: str | None = None

    @model_validator(mode="after")
    def derive_disposition(self):
        if self.disposition is None:
            if self.is_emergency or self.urgency_tier == UrgencyTier.EMERGENCY_BLOCK:
                self.disposition = "EMERGENCY_NOW"
            elif self.urgency_tier == UrgencyTier.SAME_DAY:
                self.disposition = "URGENT_SAME_DAY"
            else:
                self.disposition = "ROUTINE"
        return self
