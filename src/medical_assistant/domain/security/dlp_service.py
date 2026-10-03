"""
Data Loss Prevention (DLP) & Output Sanitization Service.
Prevents leakage of:
1. Secret keys, API tokens, passwords, database URLs (OpenAI, Supabase, JWT, Postgres).
2. Customer / Patient PII & PHI (CCCD/CMND, BHYT, Phone numbers, Emails, medical records of others).
Provides automatic redaction and safety enforcement before sending any response to the user.
"""

import re
from dataclasses import dataclass, field


@dataclass
class DLPScanResult:
    is_clean: bool
    sanitized_text: str
    secrets_found: list[str] = field(default_factory=list)
    pii_found: list[str] = field(default_factory=list)
    has_leakage: bool = False


class DLPService:
    def __init__(self):
        # 1. Regex cho API Keys & Bí Mật Hạ Tầng
        self.secret_patterns = [
            # OpenAI API Keys
            (re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"), "[REDACTED_OPENAI_KEY]"),
            (re.compile(r"\bsk-proj-[a-zA-Z0-9_\-]{30,}\b"), "[REDACTED_OPENAI_KEY]"),
            # Supabase Keys
            (re.compile(r"\bsbp_[a-zA-Z0-9_]{20,}\b"), "[REDACTED_SUPABASE_KEY]"),
            # JWT Tokens (3 phần phân tách bằng dấu chấm)
            (
                re.compile(r"\beyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}\b"),
                "[REDACTED_JWT_TOKEN]",
            ),
            # Database Connection Strings (Postgres, Mongo, MySQL)
            (
                re.compile(r"(?:postgres|postgresql|mysql|mongodb|redis):\/\/[^\s:]+:[^\s@]+@[^\s\/]+"),
                "[REDACTED_DATABASE_URL]",
            ),
            # Private Keys
            (
                re.compile(
                    r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----[^-]+-----END (?:[A-Z]+ )?PRIVATE KEY-----", re.DOTALL
                ),
                "[REDACTED_PRIVATE_KEY]",
            ),
            # Generic password / secret assignments
            (
                re.compile(
                    r"(?:api[_-]?key|secret[_-]?key|db[_-]?password|access[_-]?token)\s*[:=]\s*['\"][^\s'\"]{6,}['\"]",
                    re.IGNORECASE,
                ),
                "[REDACTED_CREDENTIAL]",
            ),
        ]

        # 2. Regex cho Thông Tin Cá Nhân Bệnh Nhân (PII / PHI)
        # CCCD / CMND Việt Nam (12 số hoặc 9 số)
        self.cccd_pattern = re.compile(r"\b(?:\d{12}|\d{9})\b")
        # Thẻ BHYT Việt Nam (15 ký tự: 2 chữ cái đầu + 13 chữ số)
        self.bhyt_pattern = re.compile(r"\b[A-Z]{2}\d{13}\b")
        # Số điện thoại Việt Nam (10 số, đầu 03, 05, 07, 08, 09 hoặc +84)
        self.phone_pattern = re.compile(r"(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-5]|9[0-9])\d{7}\b")
        # Email
        self.email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

    def sanitize(
        self,
        text: str,
        allowed_user_phone: str | None = None,
        allowed_user_email: str | None = None,
        allowed_user_id: str | None = None,
    ) -> DLPScanResult:
        """
        Quét và làm sạch dữ liệu nhạy cảm trong câu trả lời.
        - Xóa sạch 100% secret keys, JWT, mật khẩu.
        - Xóa sạch PII (CCCD, BHYT, SĐT, Email) của người khác, ngoại trừ thông tin của chính người dùng hiện tại (nếu họ vừa cung cấp để đặt hẹn).
        """
        if not text:
            return DLPScanResult(is_clean=True, sanitized_text="")

        sanitized = text
        secrets_found = []
        pii_found = []

        # 1. Quét & Redact Secrets
        for pattern, placeholder in self.secret_patterns:
            matches = pattern.findall(sanitized)
            if matches:
                for match in matches:
                    snippet = match if isinstance(match, str) else match[0]
                    secrets_found.append(snippet[:8] + "...")
                sanitized = pattern.sub(placeholder, sanitized)

        # 2. Quét & Redact CCCD / CMND
        # Lưu ý: Tránh match nhầm các timestamp hoặc số slot 8 ký tự
        for match in self.cccd_pattern.finditer(sanitized):
            cccd_val = match.group(0)
            # Kiểm tra xem có trùng với ID được cấp phép không
            if allowed_user_id and cccd_val == allowed_user_id:
                continue
            pii_found.append(f"CCCD_{cccd_val[:3]}***")
            sanitized = sanitized.replace(cccd_val, "[REDACTED_CCCD]")

        # 3. Quét & Redact Thẻ BHYT
        for match in self.bhyt_pattern.finditer(sanitized):
            bhyt_val = match.group(0)
            pii_found.append(f"BHYT_{bhyt_val[:4]}***")
            sanitized = sanitized.replace(bhyt_val, "[REDACTED_BHYT]")

        # 4. Quét & Redact Số Điện Thoại
        for match in self.phone_pattern.finditer(sanitized):
            phone_val = match.group(0)
            # Cho phép nếu là số điện thoại người dùng chủ động gửi để nhận cuộc gọi lễ tân
            if allowed_user_phone and (phone_val == allowed_user_phone or phone_val in allowed_user_phone):
                continue
            pii_found.append(f"PHONE_{phone_val[:4]}***")
            sanitized = sanitized.replace(phone_val, "[REDACTED_PHONE]")

        # 5. Quét & Redact Email
        for match in self.email_pattern.finditer(sanitized):
            email_val = match.group(0)
            if allowed_user_email and email_val.lower() == allowed_user_email.lower():
                continue
            pii_found.append(f"EMAIL_{email_val.split('@')[0][:2]}***")
            sanitized = sanitized.replace(email_val, "[REDACTED_EMAIL]")

        has_leakage = len(secrets_found) > 0 or len(pii_found) > 0
        return DLPScanResult(
            is_clean=not has_leakage,
            sanitized_text=sanitized,
            secrets_found=secrets_found,
            pii_found=pii_found,
            has_leakage=has_leakage,
        )


_dlp_service_instance: DLPService | None = None


def get_dlp_service() -> DLPService:
    global _dlp_service_instance
    if _dlp_service_instance is None:
        _dlp_service_instance = DLPService()
    return _dlp_service_instance
