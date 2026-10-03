"""
Telemetry & Security Audit Service (Production Observability Layer)
Chuyên trách ghi nhận:
1. Security Audit Logs: Lưu vết các cuộc tấn công Prompt Injection, Jailbreak, vi phạm rào chắn ở Hook 1.
2. Session Telemetry Logs: Ghi nhận chi phí token ($ USD và VNĐ), latency và trạng thái vòng lặp ở Hook 6.
Tuân thủ nguyên tắc:
- Non-blocking: Lỗi kết nối DB không làm gián đoạn trải nghiệm của người bệnh.
- Zero-cost overhead: Thực thi nhẹ, sử dụng PostgREST insert_minimal.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Tỷ giá quy đổi cố định USD -> VNĐ cho mục đích ước tính telemetry chi phí
USD_TO_VND_RATE = 25400.0


class TelemetryService:
    def __init__(self):
        pass

    def record_security_event(
        self,
        attack_type: str,
        payload: str,
        blocked_reason: str,
        session_id: str | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Hook 1 Middleware: Ghi vết sự kiện vi phạm an toàn & an ninh vào Supabase.
        """
        try:
            from src.medical_assistant.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            row = {
                "session_id": session_id or "session_unknown",
                "user_id": user_id,
                "ip_address": ip_address,
                "attack_type": attack_type,
                "payload": payload[:1000] if payload else "",  # Giới hạn kích thước lưu vết
                "blocked_reason": blocked_reason,
                "metadata": metadata or {},
            }
            client.insert_minimal("security_audit_logs", row)
            return True
        except Exception as exc:
            logger.debug(f"[TelemetryService] Failed to record security event: {exc}")
            return False

    def record_turn_telemetry(
        self,
        session_id: str,
        turn_index: int = 1,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: float = 0.0,
        cost_usd: float = 0.0,
        model_name: str | None = "gpt-4o-mini",
        workflow_status: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Hook 6 Middleware: Ghi nhận số liệu tài nguyên, chi phí vận hành và độ trễ vào Supabase.
        """
        try:
            from src.medical_assistant.db.supabase_client import get_supabase_client

            client = get_supabase_client()
            total_tokens = prompt_tokens + completion_tokens
            cost_vnd = round(cost_usd * USD_TO_VND_RATE, 2)

            row = {
                "session_id": str(session_id),
                "turn_index": turn_index,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd,
                "cost_vnd": cost_vnd,
                "latency_ms": round(latency_ms, 2),
                "model_name": model_name,
                "workflow_status": workflow_status,
                "metadata": metadata or {},
            }
            client.insert_minimal("session_telemetry_logs", row)
            return True
        except Exception as exc:
            logger.debug(f"[TelemetryService] Failed to record session telemetry: {exc}")
            return False


_telemetry_service_instance: TelemetryService | None = None


def get_telemetry_service() -> TelemetryService:
    global _telemetry_service_instance
    if _telemetry_service_instance is None:
        _telemetry_service_instance = TelemetryService()
    return _telemetry_service_instance
