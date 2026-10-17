"""Định dạng sự kiện realtime của ca Workbench và phát qua WebSocket (kênh staff + phiên chat bệnh nhân)."""

from __future__ import annotations

import logging
from uuid import UUID

from src.core.logging import get_logger, log_event
from src.models.conversation import Message as UnifiedMessage
from src.realtime.chat_takeover import chat_takeover_manager

logger = get_logger(__name__)


def case_payload(case) -> dict:
    summary = (case.ai_snapshot or {}).get("takeover_summary") or {}
    patient_id = case.patient_id
    if patient_id is None and (case.owner_key or "").startswith("user:"):
        try:
            patient_id = UUID(case.owner_key[5:])
        except ValueError:
            patient_id = None
    if case.status in {"completed", "cancelled"}:
        status = "resolved"
    elif case.assigned_to and case.control == "human":
        status = "taken_over"
    elif case.control != "human" and (case.ai_snapshot or {}).get("workflow_status") == "HUMAN_HELP_REQUESTED":
        status = "released"
    elif (case.checkpoint or {}).get("takeover_released"):
        status = "released"
    else:
        status = "queued"
    priority = "critical" if case.priority == 0 else "high" if case.priority == 1 else "normal"
    return {
        "id": str(case.legacy_takeover_case_id or case.id),
        "patient_user_id": str(patient_id) if patient_id else str(UUID(int=0)),
        "session_id": case.session_id or "",
        "status": status,
        "priority": priority,
        "workflow_status": (case.ai_snapshot or {}).get("workflow_status") or "HUMAN_HELP_REQUESTED",
        "summary": summary or {"patient_name": (case.patient or {}).get("name")},
        "assigned_staff_id": str(case.assigned_to) if case.assigned_to else None,
        "claimed_at": (case.checkpoint or {}).get("takeover_claimed_at"),
        "resolved_at": (case.checkpoint or {}).get("takeover_resolved_at"),
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


def message_payload(message, case=None) -> dict:
    if isinstance(message, UnifiedMessage):
        author_type = {
            "STAFF": "staff",
            "PATIENT": "patient",
            "AGENT": "assistant",
            "SYSTEM": "system",
        }.get(message.sender_type, (message.sender_type or "system").lower())
        patient_id = None
        if case and (case.owner_key or "").startswith("user:"):
            try:
                patient_id = UUID(case.owner_key[5:])
            except ValueError:
                patient_id = None
        client_id = (message.msg_metadata or {}).get("client_id", str(message.id))
        return {
            "id": str(message.id),
            "case_id": str(case.legacy_takeover_case_id or case.id) if case else str(message.conversation_id),
            "author_type": author_type,
            "author_user_id": str(message.sender_id or patient_id) if (message.sender_id or patient_id) else None,
            "content": message.content or "",
            "client_message_id": client_id,
            "metadata": message.msg_metadata or {},
            "created_at": message.created_at,
        }
    author_type = {"coordinator": "staff", "ai": "assistant"}.get(message.sender, message.sender)
    patient_id = None
    if case and (case.owner_key or "").startswith("user:"):
        try:
            patient_id = UUID(case.owner_key[5:])
        except ValueError:
            patient_id = None
    return {
        "id": str(message.id),
        "case_id": str(case.legacy_takeover_case_id or case.id) if case else str(message.case_id),
        "author_type": author_type,
        "author_user_id": str(message.actor_id or patient_id) if message.actor_id or patient_id else None,
        "content": message.body,
        "client_message_id": message.client_id,
        "metadata": {},
        "created_at": message.created_at,
    }


async def publish_workbench_case_update(case) -> None:
    try:
        payload = {"type": "takeover.case_updated", "case": case_payload(case)}
        if case.session_id:
            await chat_takeover_manager.publish_session(case.session_id, payload)
        await chat_takeover_manager.publish_staff(payload)
    except Exception:
        log_event(logger, logging.WARNING, "workbench.websocket.publish_failed")


async def publish_workbench_message(case, message) -> None:
    try:
        message_event = {
            "type": "takeover.message_created",
            "message": message_payload(message, case),
        }
        if case.session_id:
            await chat_takeover_manager.publish_session(case.session_id, message_event)
        await chat_takeover_manager.publish_staff({**message_event, "case": case_payload(case)})
    except Exception:
        log_event(logger, logging.WARNING, "workbench.websocket.publish_failed")
