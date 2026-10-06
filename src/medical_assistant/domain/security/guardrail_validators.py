"""
Guardrail Validators for Medical AI (inspired by Guardrails AI & Vinmec Safety Protocols).
Enforces:
1. SAF-01: No prescribing or medication dosage instructions.
2. SAF-02: No definitive clinical diagnosis without doctor examination.
3. Department Validity: Must match Vinmec official clinical departments.
4. Schema & Output Structural Integrity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    is_valid: bool
    sanitized_content: str
    violations: list[str] = field(default_factory=list)
    action_taken: str = "PASS"  # "PASS", "FIXED", "BLOCKED"


class MedicalSafetyValidators:
    """Enterprise-grade Validators for LLM Generated Output."""

    # 1. Regex phát hiện kê đơn thuốc & liều lượng (SAF-01)
    PRESCRIPTION_PATTERNS = [
        re.compile(
            r"\b(?:uống|tiêm|dùng|uong|dung)\s+\d+\s*(?:viên|v|ống|gói|mg|ml|gam|giọt)(?:\s*/\s*ngày|\s+mỗi\s+ngày)?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:liều\s+dùng|liều\s+lượng|đơn\s+thuốc|kê\s+đơn|chỉ\s+định\s+thuốc)\s*[:\-]\s*[A-Za-zÀ-ỹ0-9\s,]{4,}",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:paracetamol|panadol|ibuprofen|amoxicillin|aspirin|antibiotic|kháng\s+sinh)\s+\d+\s*(?:mg|g|viên)\b",
            re.IGNORECASE,
        ),
    ]

    # 2. Regex phát hiện khẳng định chẩn đoán tuyệt đối (SAF-02)
    DEFINITIVE_DIAGNOSIS_PATTERNS = [
        re.compile(
            r"\b(?:bác\s+đã\s+bị|chắc\s+chắn\s+bác\s+bị|khẳng\s+định\s+bác\s+mắc|bạn\s+đang\s+bị)\s+(?:ung\s+thư|đột\s+quỵ|suy\s+tim|viêm\s+ruột\s+thừa|viêm\s+tụy|u\s+não)\b",
            re.IGNORECASE,
        ),
    ]

    # 3. Danh mục 18 chuyên khoa chuẩn Vinmec
    VALID_VINMEC_DEPARTMENTS = {
        "Trung tâm Tim mạch",
        "Nội hô hấp",
        "Tiêu hóa - Gan mật",
        "Tai - Mũi - Họng",
        "Thần kinh",
        "Nội thần kinh",
        "Miễn dịch - Dị ứng",
        "Truyền nhiễm",
        "Chấn thương chỉnh hình & Cột sống",
        "Chấn thương chỉnh hình - Y học thể thao",
        "Cơ xương khớp",
        "Da liễu",
        "Nội tiết - Đái tháo đường",
        "Thận - Tiết niệu",
        "Sản phụ khoa",
        "Nhi khoa",
        "Mắt",
        "Nha khoa",
        "Răng - Hàm - Mặt",
        "Ung bướu",
        "Sức khỏe tổng quát",
        "Cấp cứu",
        "Nội đa khoa",
    }

    @classmethod
    def validate_no_prescription(cls, text: str) -> ValidationResult:
        """Kiểm tra và ngăn chặn LLM kê đơn thuốc hoặc chỉ định liều lượng cụ thể."""
        violations = []
        sanitized = text

        for pattern in cls.PRESCRIPTION_PATTERNS:
            matches = list(pattern.finditer(sanitized))
            if matches:
                for match in matches:
                    violations.append(f"SAF-01: Phát hiện chỉ định liều/kê đơn thuốc trái phép ('{match.group(0)}')")
                # Tự động thay thế phần kê đơn bằng khuyến cáo đi khám an toàn
                sanitized = pattern.sub(
                    "[Bác sĩ sẽ thăm khám và chỉ định thuốc/liều dùng an toàn trực tiếp]",
                    sanitized,
                )

        if violations:
            sanitized += (
                "\n\n*(Lưu ý an toàn y tế: Trợ lý AI không được phép kê đơn hoặc chỉ định liều lượng thuốc. "
                "Bác sĩ chuyên khoa sẽ thăm khám và đưa ra phác đồ điều trị chính xác nhất cho bác.)*"
            )
            return ValidationResult(
                is_valid=False,
                sanitized_content=sanitized,
                violations=violations,
                action_taken="FIXED",
            )

        return ValidationResult(is_valid=True, sanitized_content=text, action_taken="PASS")

    @classmethod
    def validate_no_definitive_diagnosis(cls, text: str) -> ValidationResult:
        """Kiểm tra và ngăn chặn LLM khẳng định chẩn đoán bệnh thay bác sĩ."""
        violations = []
        sanitized = text

        for pattern in cls.DEFINITIVE_DIAGNOSIS_PATTERNS:
            matches = list(pattern.finditer(sanitized))
            if matches:
                for match in matches:
                    violations.append(f"SAF-02: Phát hiện khẳng định chẩn đoán thay bác sĩ ('{match.group(0)}')")
                sanitized = pattern.sub("triệu chứng của bác có thể liên quan đến", sanitized)

        if violations:
            return ValidationResult(
                is_valid=False,
                sanitized_content=sanitized,
                violations=violations,
                action_taken="FIXED",
            )

        return ValidationResult(is_valid=True, sanitized_content=text, action_taken="PASS")

    @classmethod
    def validate_specialty_name(cls, department_name: str | None) -> str:
        """Đảm bảo tên chuyên khoa trả về luôn chuẩn hóa theo danh mục Vinmec."""
        if not department_name or not department_name.strip():
            return "Nội đa khoa"

        dep_clean = department_name.strip()
        if dep_clean in cls.VALID_VINMEC_DEPARTMENTS:
            return dep_clean

        # Fuzzy lookup
        dep_lower = dep_clean.lower()
        for valid in cls.VALID_VINMEC_DEPARTMENTS:
            if dep_lower in valid.lower() or valid.lower() in dep_lower:
                return valid

        return "Nội đa khoa"
