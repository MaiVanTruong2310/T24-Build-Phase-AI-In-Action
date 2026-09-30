from datetime import date
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Tin nhắn từ user")
    session_id: str = Field(default="default_patient_session", description="Thread ID / Session ID định danh phiên chat của bệnh nhân")
    user_id: Optional[str] = Field(default=None, description="Mã bệnh nhân nếu đã đăng nhập")
    enable_citation: bool = Field(default=True, description="Bật/tắt hiển thị link nguồn trích dẫn tài liệu y khoa (Citations)")


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
    ats_level: Optional[int] = Field(default=None, description="Cấp độ ATS (1-5)")
    max_booking_days: Optional[int] = Field(default=None, description="Số ngày tối đa cho phép đặt lịch")
    quick_replies: List[str] = Field(default_factory=list, description="Gợi ý chọn nhanh câu trả lời")
    is_emergency: bool = Field(default=False, description="Cờ báo động cấp cứu")
    token_usage: Optional[TokenUsage] = Field(default=None, description="Thông số sử dụng token qua thư viện tiktoken")
    workflow_status: Optional[str] = Field(default=None, description="Trạng thái nghiệp vụ hiện tại")
    booking_intake: Optional[dict[str, Any]] = Field(default=None, description="Cấu hình form HITL nếu cần")
    suggested_department: Optional[str] = Field(default=None, description="Chuyên khoa được đề xuất chính")
    candidate_specialties: List[dict[str, Any]] = Field(
        default_factory=list,
        description="Các chuyên khoa đang được cân nhắc khi có nhiều nhóm triệu chứng",
    )
    conflict_reason: Optional[str] = Field(default=None, description="Lý do cần làm rõ giữa các hướng chuyên khoa")
    acuity_status: Optional[str] = Field(default=None, description="Độ chắc chắn của mức khẩn cấp")
    disposition: Optional[str] = Field(default=None, description="Hướng xử lý an toàn hiện tại")


class BookingIntakeRequest(BaseModel):
    session_id: str = Field(..., min_length=8, max_length=200)
    patient_name: str = Field(..., min_length=2, max_length=120)
    patient_phone: str = Field(..., min_length=9, max_length=20)
    patient_email: Optional[str] = Field(default=None, max_length=254)
    date_of_birth: date
    gender: Optional[Literal["female", "male", "other", "prefer_not_to_say"]] = None
    guardian_name: Optional[str] = Field(default=None, max_length=120)
    guardian_phone: Optional[str] = Field(default=None, max_length=20)
    preferred_doctor_id: Optional[str] = Field(default=None, max_length=200)
    selected_slot_id: Optional[str] = Field(default=None, max_length=100)
    preferred_date: Optional[date] = None
    preferred_period: Optional[Literal["morning", "afternoon", "evening", "any"]] = "any"
    facility_preference: Optional[str] = Field(default=None, max_length=250)
    contact_time_preference: Optional[str] = Field(default=None, max_length=120)
    patient_notes: Optional[str] = Field(default=None, max_length=1000)
    consent_to_contact: bool


class BookingIntakeResponse(BaseModel):
    saved: bool
    request_id: str
    request_code: str
    status: Literal["PENDING_CONTACT"]
    message: str
