"""Persisted workbench alerts delivered only to authenticated staff sockets."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from src.core.logging import get_logger, log_event
from src.models.workbench import CoordinationCase, CoordinationEvent
from src.realtime.chat_takeover import chat_takeover_manager
from src.schemas.staff_alert import StaffAssistantAlert
from src.services import workbench

logger = get_logger(__name__)

ALERT_EVENT_TYPES = ("human_requested", "emergency_detected", "routing_conflict")
_WORKFLOW_REASONS = {
    "HUMAN_HELP_REQUESTED": "Bệnh nhân đã yêu cầu nhân viên hỗ trợ.",
    "BOOKING_CONTACT_REQUIRED": "Bệnh nhân cần nhân viên hỗ trợ về lịch khám.",
    "SAFETY_REVIEW": "Ca cần nhân viên xem xét an toàn.",
}
_DEFAULT_REASON = "Ca cần nhân viên kiểm tra."
_EMERGENCY_REASON = "Đã lưu cảnh báo cấp cứu; vui lòng mở hồ sơ ca để xem hướng dẫn đã lưu."


def alert_payload(event: CoordinationEvent, case: CoordinationCase) -> dict:
    snapshot = case.ai_snapshot or {}
    details = getattr(event, "details", None) or {}
    if event.action == "emergency_detected":
        reason = details.get("alert_reason") or snapshot.get("emergency_warning")
        reason = reason.strip()[:500] if isinstance(reason, str) and reason.strip() else _EMERGENCY_REASON
    elif event.action == "routing_conflict":
        reason = "Đã lưu xung đột điều phối cần nhân viên kiểm tra."
    else:
        reason = _WORKFLOW_REASONS.get(
            details.get("workflow_status") or snapshot.get("workflow_status"), _DEFAULT_REASON
        )
    return StaffAssistantAlert(
        event_id=event.id,
        case_id=case.legacy_takeover_case_id or case.id,
        event_type=event.action,
        reason=reason,
        created_at=event.created_at or datetime.now(UTC),
    ).model_dump(mode="json")


async def publish_staff_assistant_alert(event: CoordinationEvent | None, case: CoordinationCase) -> None:
    if event is None or event.action not in ALERT_EVENT_TYPES:
        return
    try:
        await chat_takeover_manager.publish_staff(
            {"type": "staff_assistant.alert", "alert": alert_payload(event, case)}
        )
    except Exception:
        log_event(logger, logging.WARNING, "staff_assistant.alert.publish_failed")


async def get_staff_assistant_alerts(session, member, since: datetime | None, limit: int) -> list[dict]:
    cutoff = since or datetime.now(UTC) - timedelta(hours=24)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    rows = (
        await session.execute(
            select(CoordinationEvent, CoordinationCase)
            .join(CoordinationCase, CoordinationCase.id == CoordinationEvent.case_id)
            .where(
                CoordinationEvent.action.in_(ALERT_EVENT_TYPES),
                CoordinationEvent.created_at >= cutoff,
                CoordinationCase.source == "chat",
                CoordinationCase.assigned_to.is_(None),
                CoordinationCase.status.notin_(["emergency_active", "emergency_transferred", "completed", "cancelled"]),
                workbench.scope(member),
            )
            .order_by(CoordinationEvent.created_at, CoordinationEvent.id)
            .limit(limit)
        )
    ).all()
    return [alert_payload(event, case) for event, case in rows]
