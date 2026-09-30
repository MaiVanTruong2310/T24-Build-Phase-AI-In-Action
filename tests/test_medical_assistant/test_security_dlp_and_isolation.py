import pytest

from src.medical_assistant.domain.security.dlp_service import get_dlp_service


@pytest.fixture
def dlp():
    return get_dlp_service()


def test_redact_openai_api_keys(dlp):
    text_with_key = "Internal debug: model loaded with key sk-abcdef1234567890abcdef1234567890 successfully."
    res = dlp.sanitize(text_with_key)
    assert not res.is_clean
    assert res.has_leakage
    assert "[REDACTED_OPENAI_KEY]" in res.sanitized_text
    assert "sk-abcde" not in res.sanitized_text


def test_redact_supabase_keys_and_jwt(dlp):
    supabase_key_text = "Supabase access token: sbp_1234567890abcdef1234567890abcdef."
    res = dlp.sanitize(supabase_key_text)
    assert "[REDACTED_SUPABASE_KEY]" in res.sanitized_text

    jwt_text = "JWT auth token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozGz_wT_testsignature123."
    res_jwt = dlp.sanitize(jwt_text)
    assert "[REDACTED_JWT_TOKEN]" in res_jwt.sanitized_text


def test_redact_database_url(dlp):
    db_text = "Connecting to database postgres://postgres:SuperSecretP@ssw0rd@db.supabase.co:5432/postgres"
    res = dlp.sanitize(db_text)
    assert "[REDACTED_DATABASE_URL]" in res.sanitized_text
    assert "SuperSecretP@ssw0rd" not in res.sanitized_text


def test_redact_patient_pii_cccd(dlp):
    # CCCD 12 số của người khác
    text = "Bệnh nhân có số CCCD là 001201004567 cần bổ sung hồ sơ."
    res = dlp.sanitize(text)
    assert "[REDACTED_CCCD]" in res.sanitized_text
    assert "001201004567" not in res.sanitized_text


def test_redact_patient_pii_bhyt(dlp):
    # Thẻ BHYT 15 ký tự
    text = "Mã số BHYT là GD4010123456789 áp dụng mức hưởng 80%."
    res = dlp.sanitize(text)
    assert "[REDACTED_BHYT]" in res.sanitized_text
    assert "GD4010123456789" not in res.sanitized_text


def test_redact_other_patient_phone_and_email(dlp):
    text = "Vui lòng liên hệ người nhà qua số 0987654321 hoặc email patient_secret@gmail.com"
    res = dlp.sanitize(text)
    assert "[REDACTED_PHONE]" in res.sanitized_text
    assert "[REDACTED_EMAIL]" in res.sanitized_text
    assert "0987654321" not in res.sanitized_text
    assert "patient_secret@gmail.com" not in res.sanitized_text


def test_preserve_allowed_current_user_phone(dlp):
    # Nếu người dùng hiện tại chủ động để lại số của chính họ để lễ tân gọi
    current_user_phone = "0912345678"
    text = "Hệ thống đã giữ chỗ. Lễ tân sẽ liên hệ số 0912345678 để xác nhận."
    res = dlp.sanitize(text, allowed_user_phone=current_user_phone)
    # Số của chính họ được giữ nguyên để xác nhận, không bị xóa nhầm
    assert "0912345678" in res.sanitized_text
