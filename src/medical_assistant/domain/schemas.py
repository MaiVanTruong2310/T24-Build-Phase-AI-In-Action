from datetime import date
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ChatPatientProfile(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(default="", max_length=20)
    date_of_birth: str | None = Field(default=None, max_length=20)
    gender: str | None = Field(default=None, max_length=20)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        import re
        phone = re.sub(r"[\s().-]", "", value)
        if phone and not re.fullmatch(r"\+?\d{9,15}", phone):
            raise ValueError("Số điện thoại không hợp lệ")
        return phone


class ChatRequest(BaseModel):
    patient_profile_id: UUID | None = None
    request_id: UUID = Field(default_factory=uuid4)
    patient_profile: ChatPatientProfile | None = None
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")
    session_id: str = Field(
        default_factory=lambda: str(uuid4()), min_length=1, max_length=200,
        pattern=r"^[A-Za-z0-9_-]+$", description="Thread ID / Session ID định danh phiên chat của bệnh nhân"
    )
    user_id: str | None = Field(default=None, description="Mã bệnh nhân nếu đã đăng nhập")
    enable_citation: bool = Field(
        default=True, description="Bật/tắt hiển thị link nguồn trích dẫn tài liệu y khoa (Citations)"
    )


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(default=0, description="Số token đầu vào (prompt)")
    completion_tokens: int = Field(default=0, description="Số token đầu ra (completion)")
    total_tokens: int = Field(default=0, description="Tổng số token thực tế sử dụng")
    tokens_saved: int = Field(default=0, description="Số token tiết kiệm được nhờ Cache/Zero-token rules")
    model: str = Field(default="gpt-4o-mini", description="Model tokenizer dùng để tính toán")
    estimated_cost_usd: float = Field(default=0.0, description="Ước tính chi phí USD")
    execution_mode: str = Field(default="llm_or_estimated", description="Cơ chế thực thi thực tế")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")
    session_id: str = Field(default="", description="ID phiên hiện tại")
    ats_level: int | None = Field(default=None, description="Cấp độ ATS (1-5)")
    max_booking_days: int | None = Field(default=None, description="Số ngày tối đa cho phép đặt lịch")
    quick_replies: list[str] = Field(default_factory=list, description="Gợi ý chọn nhanh câu trả lời")
    is_emergency: bool = Field(default=False, description="Cờ báo động cấp cứu")
    token_usage: TokenUsage | None = Field(default=None, description="Thông số sử dụng token qua thư viện tiktoken")
    workflow_status: str | None = Field(default=None, description="Trạng thái nghiệp vụ hiện tại")
    booking_intake: dict[str, Any] | None = Field(default=None, description="Cấu hình form HITL nếu cần")
    suggested_department: str | None = Field(default=None, description="Chuyên khoa được đề xuất chính")
    candidate_specialties: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Các chuyên khoa đang được cân nhắc khi có nhiều nhóm triệu chứng",
    )
    conflict_reason: str | None = Field(default=None, description="Lý do cần làm rõ giữa các hướng chuyên khoa")
    acuity_status: str | None = Field(default=None, description="Độ chắc chắn của mức khẩn cấp")
    disposition: str | None = Field(default=None, description="Hướng xử lý an toàn hiện tại")
    elapsed_ms: float | None = Field(default=None, description="Thời gian phản hồi (ms)")


class BookingIntakeRequest(BaseModel):
    patient_profile_id: UUID | None = None
    session_id: str = Field(..., min_length=8, max_length=200)
    patient_name: str = Field(..., min_length=2, max_length=120)
    patient_phone: str = Field(..., min_length=9, max_length=20)
    patient_email: str | None = Field(default=None, max_length=254)
    date_of_birth: date
    gender: Literal["female", "male", "other", "prefer_not_to_say"] | None = None
    guardian_name: str | None = Field(default=None, max_length=120)
    guardian_phone: str | None = Field(default=None, max_length=20)
    specialty_name: str | None = Field(default=None, max_length=120)
    specialty_code: str | None = Field(default=None, max_length=60)
    preferred_doctor_id: str | None = Field(default=None, max_length=200)
    selected_slot_id: str | None = Field(default=None, max_length=100)
    preferred_date: date | None = None
    preferred_period: Literal["morning", "afternoon", "evening", "any"] | None = "any"
    facility_preference: str | None = Field(default=None, max_length=250)
    contact_time_preference: str | None = Field(default=None, max_length=120)
    patient_notes: str | None = Field(default=None, max_length=1000)
    consent_to_contact: bool


class BookingIntakeResponse(BaseModel):
    saved: bool
    request_id: str
    request_code: str
    status: Literal["PENDING_CONTACT"]
    message: str
