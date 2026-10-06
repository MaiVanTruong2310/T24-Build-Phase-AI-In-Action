"""
Unit Tests for Enterprise Hybrid Guardrails System:
- Microsoft Presidio DLP with Vietnamese PII Recognizers (CCCD, BHYT, Mobile).
- Guardrails AI-style Medical Safety Validators (SAF-01 No Prescription, SAF-02 No Diagnosis).
- End-to-end integration into respond_node.
"""

import pytest

from src.medical_assistant.agent.nodes.respond_node import respond_node
from src.medical_assistant.agent.state import AgentState
from src.medical_assistant.domain.security.guardrail_validators import MedicalSafetyValidators
from src.medical_assistant.domain.security.presidio_dlp_service import get_presidio_dlp_service


def test_presidio_dlp_masks_vietnamese_pii():
    """Kiểm tra Presidio DLP nhận diện và che giấu CCCD, BHYT, SĐT cá nhân."""
    svc = get_presidio_dlp_service()
    raw = (
        "Bệnh nhân Trần Thị B có số CCCD: 001099012345, mã thẻ BHYT: DN4010123456789, "
        "SĐT riêng: 0987654321. Vui lòng liên hệ hotline Vinmec: 1900232389."
    )
    result = svc.sanitize(raw, mask_mode="partial")

    assert result.has_leakage is True
    # CCCD phải bị che dạng partial
    assert "001099012345" not in result.sanitized_text
    assert "001******345" in result.sanitized_text
    # BHYT phải bị che dạng partial
    assert "DN4010123456789" not in result.sanitized_text
    assert "DN4*******789" in result.sanitized_text
    # SĐT cá nhân bị che dạng partial
    assert "0987654321" not in result.sanitized_text
    assert "098****321" in result.sanitized_text
    # Hotline bệnh viện giữ nguyên
    assert "1900232389" in result.sanitized_text

    # Kiểm tra tag mode
    tag_result = svc.sanitize(raw, mask_mode="tag")
    assert "[REDACTED_CCCD]" in tag_result.sanitized_text
    assert "[REDACTED_BHYT]" in tag_result.sanitized_text
    assert "[REDACTED_PHONE]" in tag_result.sanitized_text


def test_presidio_dlp_masks_api_secrets():
    """Kiểm tra Presidio DLP lọc sạch API Key và Database URL."""
    svc = get_presidio_dlp_service()
    # Synthetic credential used only to verify masking.
    raw = "Hệ thống kết nối sk-proj-0000000000000000000000000000000000000000 và postgres://admin:secret@db.vinmec.internal:5432/patients"
    result = svc.sanitize(raw)

    assert result.has_leakage is True
    assert "sk-proj-" not in result.sanitized_text
    assert "[REDACTED_OPENAI_KEY]" in result.sanitized_text
    assert "[REDACTED_DATABASE_URL]" in result.sanitized_text


def test_medical_safety_validator_catches_prescription():
    """Kiểm tra SAF-01: Ngăn chặn tuyệt đối kê đơn liều dùng thuốc."""
    raw = "Bác nên uống 2 viên paracetamol 500mg mỗi ngày để hạ sốt."
    result = MedicalSafetyValidators.validate_no_prescription(raw)

    assert result.is_valid is False
    assert result.action_taken == "FIXED"
    assert "Lưu ý an toàn y tế" in result.sanitized_content
    assert "Bác sĩ sẽ thăm khám và chỉ định thuốc/liều dùng" in result.sanitized_content


def test_medical_safety_validator_catches_definitive_diagnosis():
    """Kiểm tra SAF-02: Ngăn chặn khẳng định chẩn đoán thay bác sĩ."""
    raw = "Qua triệu chứng này, chắc chắn bác bị viêm ruột thừa cấp tính rồi."
    result = MedicalSafetyValidators.validate_no_definitive_diagnosis(raw)

    assert result.is_valid is False
    assert result.action_taken == "FIXED"
    assert "chắc chắn bác bị viêm ruột thừa" not in result.sanitized_content
    assert "có thể liên quan đến" in result.sanitized_content


@pytest.mark.asyncio
async def test_end_to_end_respond_node_integrates_hybrid_guardrails():
    """Kiểm tra respond_node tự động áp dụng Presidio DLP và Safety Validators vào phản hồi cuối cùng."""
    state: AgentState = {
        "query": "Tôi muốn hỏi",
        "language": "vi",
        "workflow_status": "FAQ_ANSWERED",
        "probing_turn": 0,
        "collected_details": [],
        "metadata": {
            "cached_response": "Bác có thể để lại số CCCD 001099012345 và nhớ uống 1 viên panadol 500mg nhé.",
        },
    }

    result = await respond_node(state)
    resp = result["response"]

    # Phải che CCCD bằng Presidio DLP
    assert "001099012345" not in resp
    assert "[REDACTED_CCCD]" in resp
    # Phải chặn liều thuốc bằng SAF-01 Validator
    assert "uống 1 viên" not in resp
    assert "Lưu ý an toàn y tế" in resp
