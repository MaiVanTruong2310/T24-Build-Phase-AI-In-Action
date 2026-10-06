"""Business workflow for durable staff takeover of patient chat sessions."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text

from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger, log_event
from src.models.chat_takeover import ChatTakeoverCase, ChatTakeoverMessage
from src.realtime.chat_takeover import chat_takeover_manager
from src.repositories.chat_takeover import ChatTakeoverRepository

TAKEOVER_STATUSES = ("queued", "taken_over", "released", "resolved")
logger = get_logger(__name__)


def priority_for_result(result: dict) -> str:
    ats_level = result.get("ats_level")
    if result.get("is_emergency") or (isinstance(ats_level, int) and ats_level <= 2):
        return "critical"
    if isinstance(ats_level, int) and ats_level == 3:
        return "high"
    return "normal"


class ChatTakeoverService:
    """Create, claim and message takeover cases with durable-before-realtime semantics."""

    def __init__(self, session):
        self.session = session
        self.repository = ChatTakeoverRepository(session)

    async def ensure_case_from_result(
        self,
        patient_user,
        session_id: str,
        patient_message: str,
        result: dict,
    ) -> ChatTakeoverCase | None:
        log_event(
            logger,
            logging.INFO,
            "handoff.case.ensure.start",
            description="Starting durable takeover case creation or update",
            patient_user_id=str(patient_user.id),
            session_id=session_id,
            workflow_status=result.get("workflow_status"),
        )
        if result.get("workflow_status") != "HUMAN_HELP_REQUESTED":
            return None

        now = datetime.now(UTC)
        patient_user_id = patient_user.id
        async with self.session.begin():
            case = await self.repository.get_by_patient_session(patient_user_id, session_id, for_update=True)
            patient_age = None
            if patient_user.date_of_birth:
                dob = patient_user.date_of_birth
                patient_age = now.year - dob.year - ((now.month, now.day) < (dob.month, dob.day))
            summary = {
                "patient_message": patient_message[:2000],
                "patient_name": patient_user.full_name,
                "patient_age": patient_age,
                "patient_gender": patient_user.gender,
                "workflow_status": result.get("workflow_status"),
                "ats_level": result.get("ats_level"),
                "suggested_department": result.get("suggested_department"),
                "candidate_specialties": result.get("candidate_specialties") or [],
            }
            reopened = case is not None and case.status == "resolved"
            if case is None:
                case = ChatTakeoverCase(
                    patient_user_id=patient_user_id,
                    session_id=session_id,
                    status="queued",
                    priority=priority_for_result(result),
                    workflow_status="HUMAN_HELP_REQUESTED",
                    summary=summary,
                )
                self.session.add(case)
                await self.session.flush()
                await self.repository.add_audit(case.id, None, "case_created", {"priority": case.priority})
            else:
                case.summary = summary
                case.priority = priority_for_result(result)
                case.workflow_status = "HUMAN_HELP_REQUESTED"
                if reopened:
                    case.status = "queued"
                    case.assigned_staff_id = None
                    case.claimed_at = None
                    case.resolved_at = None
                    await self.repository.add_audit(case.id, patient_user_id, "case_reopened")
            await self.session.flush()

        payload = {"type": "takeover.case_updated", "case": case_payload(case)}
        await chat_takeover_manager.publish_staff(payload)
        log_event(
            logger,
            logging.INFO,
            "handoff.case.updated",
            description="A human takeover case was created or updated from an agent result",
            case_id=str(case.id),
            status=case.status,
            priority=case.priority,
            reopened=reopened,
        )
        return case

    async def list_cases(self, status: str | None, offset: int, limit: int) -> list[ChatTakeoverCase]:
        log_event(
            logger,
            logging.INFO,
            "handoff.case.list.start",
            description="Starting staff takeover case queue query",
            status=status,
            offset=offset,
            limit=limit,
        )
        statuses = (status,) if status else ("queued", "taken_over", "released")
        if status and status not in TAKEOVER_STATUSES:
            log_event(
                logger,
                logging.WARNING,
                "handoff.case.list.invalid_status",
                description="Takeover case listing was rejected because the status filter is invalid",
            )
            raise HTTPException(422, "Trạng thái takeover không hợp lệ.")
        values = await self.repository.list_cases(statuses, offset, limit)
        log_event(
            logger,
            logging.INFO,
            "handoff.case.list.done",
            description="Human takeover cases were listed for staff",
            count=len(values),
        )
        return values

    async def get_case(self, case_id: UUID) -> ChatTakeoverCase:
        log_event(
            logger,
            logging.INFO,
            "handoff.case.get.start",
            description="Starting takeover case lookup",
            case_id=str(case_id),
        )
        case = await self.repository.get_case(case_id)
        if case is None:
            log_event(
                logger,
                logging.WARNING,
                "handoff.case.get.not_found",
                description="Takeover case lookup returned no matching case",
                case_id=str(case_id),
            )
            raise NotFoundError("Không tìm thấy ca takeover.")
        log_event(
            logger,
            logging.INFO,
            "handoff.case.get.done",
            description="Takeover case was loaded",
            case_id=str(case_id),
            status=case.status,
        )
        return case

    async def get_case_for_patient(self, patient_user_id: UUID, session_id: str) -> ChatTakeoverCase | None:
        """Return the case owned by one patient session without exposing other cases."""
        log_event(
            logger,
            logging.INFO,
            "handoff.case.patient_get.start",
            description="Starting patient takeover case lookup for a chat session",
            patient_user_id=str(patient_user_id),
            session_id=session_id,
        )
        async with self.session.begin():
            return await self.repository.get_by_patient_session(patient_user_id, session_id)

    async def active_case_for_patient(self, patient_user_id: UUID, session_id: str) -> ChatTakeoverCase | None:
        """Return a case that must remain in human-handling mode."""
        log_event(
            logger,
            logging.INFO,
            "handoff.case.active.start",
            description="Starting active takeover case check for a patient session",
            patient_user_id=str(patient_user_id),
            session_id=session_id,
        )
        case = await self.get_case_for_patient(patient_user_id, session_id)
        if case is None or case.status == "resolved":
            return None
        return case

    async def history(self, case: ChatTakeoverCase, limit: int = 200) -> list[dict]:
        log_event(
            logger,
            logging.INFO,
            "handoff.history.start",
            description="Starting combined chat and takeover message history query",
            case_id=str(case.id),
            patient_user_id=str(case.patient_user_id),
            limit=limit,
        )
        turns = (
            (
                await self.session.execute(
                    text(
                        """SELECT t.id, t.request_id, t.user_text, t.assistant_text, t.status, t.created_at
                    FROM public.chat_turns t
                    JOIN public.chat_conversations c ON c.id = t.conversation_id
                    WHERE c.user_id = :user_id AND c.session_id = :session_id
                    ORDER BY t.created_at ASC, t.id ASC LIMIT :limit"""
                    ),
                    {"user_id": case.patient_user_id, "session_id": case.session_id, "limit": limit},
                )
            )
            .mappings()
            .all()
        )
        staff_messages = await self.repository.list_messages(case.id, limit)
        takeover_request_ids = {
            message.client_message_id
            for message in staff_messages
            if message.author_type == "patient" and message.client_message_id
        }
        messages: list[dict] = []
        for turn in turns:
            if str(turn["request_id"]) not in takeover_request_ids:
                messages.append(
                    {
                        "id": str(turn["id"]),
                        "author_type": "patient",
                        "author_user_id": str(case.patient_user_id),
                        "content": turn["user_text"],
                        "created_at": turn["created_at"],
                    }
                )
            if turn["assistant_text"]:
                messages.append(
                    {
                        "id": f"{turn['id']}:assistant",
                        "author_type": "assistant",
                        "author_user_id": None,
                        "content": turn["assistant_text"],
                        "created_at": turn["created_at"],
                    }
                )
        messages.extend(message_payload(message) for message in staff_messages)
        messages.sort(key=lambda item: (item["created_at"], item["id"]))
        log_event(
            logger,
            logging.INFO,
            "handoff.history.done",
            description="Combined chat and takeover message history was loaded",
            case_id=str(case.id),
            message_count=min(len(messages), limit),
        )
        return messages[-limit:]

    async def claim(self, case_id: UUID, staff_user_id: UUID) -> ChatTakeoverCase:
        log_event(
            logger,
            logging.INFO,
            "handoff.case.claim.start",
            description="Starting staff claim of a takeover case",
            case_id=str(case_id),
            staff_user_id=str(staff_user_id),
        )
        async with self.session.begin():
            case = await self.repository.get_case(case_id, for_update=True)
            if case is None:
                raise NotFoundError("Không tìm thấy ca takeover.")
            if case.status == "taken_over" and case.assigned_staff_id == staff_user_id:
                return case
            if case.status not in ("queued", "released") or case.assigned_staff_id is not None:
                raise ConflictError("TAKEOVER_ALREADY_CLAIMED", "Ca takeover đã được nhân viên khác tiếp nhận.")
            case.status = "taken_over"
            case.assigned_staff_id = staff_user_id
            case.claimed_at = datetime.now(UTC)
            case.resolved_at = None
            await self.repository.add_audit(case.id, staff_user_id, "case_claimed")
            await self.session.flush()
        await self._publish_case(case, "takeover.case_updated")
        log_event(
            logger,
            logging.INFO,
            "handoff.case.claimed",
            description="Staff claimed a queued takeover case",
            case_id=str(case_id),
            staff_user_id=str(staff_user_id),
        )
        return case

    async def release(self, case_id: UUID, staff_user_id: UUID) -> ChatTakeoverCase:
        log_event(
            logger,
            logging.INFO,
            "handoff.case.release.start",
            description="Starting staff release of a takeover case back to the queue",
            case_id=str(case_id),
            staff_user_id=str(staff_user_id),
        )
        async with self.session.begin():
            case = await self._owned_case(case_id, staff_user_id, for_update=True)
            if case.status != "taken_over":
                raise ConflictError(
                    "TAKEOVER_NOT_ACTIVE", "Chá»‰ cÃ³ thá»ƒ tráº£ case Ä‘ang Ä‘Æ°á»£c tiáº¿p quáº£n vá» hÃ ng Ä‘á»£i."
                )
            case.status = "released"
            case.assigned_staff_id = None
            case.claimed_at = None
            await self.repository.add_audit(case.id, staff_user_id, "case_released")
            await self.session.flush()
        await self._publish_case(case, "takeover.case_updated")
        log_event(
            logger,
            logging.INFO,
            "handoff.case.released",
            description="Staff released a takeover case back to the queue",
            case_id=str(case_id),
            staff_user_id=str(staff_user_id),
        )
        return case

    async def resolve(self, case_id: UUID, staff_user_id: UUID) -> ChatTakeoverCase:
        log_event(
            logger,
            logging.INFO,
            "handoff.case.resolve.start",
            description="Starting staff resolution of a takeover case",
            case_id=str(case_id),
            staff_user_id=str(staff_user_id),
        )
        async with self.session.begin():
            case = await self._owned_case(case_id, staff_user_id, for_update=True)
            if case.status != "taken_over":
                raise ConflictError("TAKEOVER_NOT_ACTIVE", "Chá»‰ cÃ³ thá»ƒ resolve case Ä‘ang Ä‘Æ°á»£c tiáº¿p quáº£n.")
            case.status = "resolved"
            case.resolved_at = datetime.now(UTC)
            await self.repository.add_audit(case.id, staff_user_id, "case_resolved")
            await self.session.flush()
        await self._publish_case(case, "takeover.case_updated")
        log_event(
            logger,
            logging.INFO,
            "handoff.case.resolved",
            description="Staff resolved a takeover case",
            case_id=str(case_id),
            staff_user_id=str(staff_user_id),
        )
        return case

    async def send_staff_message(
        self, case_id: UUID, staff_user_id: UUID, content: str, client_message_id: str | None
    ) -> ChatTakeoverMessage:
        log_event(
            logger,
            logging.INFO,
            "handoff.message.send.start",
            description="Starting staff message persistence and publication",
            case_id=str(case_id),
            staff_user_id=str(staff_user_id),
            client_message_id_provided=bool(client_message_id),
        )
        async with self.session.begin():
            case = await self._owned_case(case_id, staff_user_id, for_update=True)
            if case.status != "taken_over":
                raise ConflictError("TAKEOVER_NOT_ACTIVE", "Chỉ được gửi tin nhắn khi case đang được tiếp quản.")
            if client_message_id:
                existing = await self.repository.get_message_by_client_id(case.id, client_message_id)
                if existing is not None:
                    return existing
            message = ChatTakeoverMessage(
                case_id=case.id,
                author_type="staff",
                author_user_id=staff_user_id,
                content=content,
                client_message_id=client_message_id,
            )
            self.session.add(message)
            await self.session.flush()
            await self.repository.add_audit(case.id, staff_user_id, "message_sent", {"message_id": str(message.id)})
        payload = {"type": "takeover.message_created", "message": message_payload(message)}
        await chat_takeover_manager.publish_session(case.session_id, payload)
        await chat_takeover_manager.publish_staff(
            {"type": "takeover.message_created", "case": case_payload(case), "message": message_payload(message)}
        )
        log_event(
            logger,
            logging.INFO,
            "handoff.message.sent",
            description="Staff message was persisted and published to the patient session",
            case_id=str(case_id),
            author_type="staff",
            staff_user_id=str(staff_user_id),
        )
        return message

    async def record_patient_message(
        self, patient_user_id: UUID, session_id: str, content: str, client_message_id: str
    ) -> ChatTakeoverMessage | None:
        """Persist a patient reply while AI handling is paused for takeover."""
        log_event(
            logger,
            logging.INFO,
            "handoff.message.receive.start",
            description="Starting patient takeover message persistence",
            patient_user_id=str(patient_user_id),
            session_id=session_id,
            client_message_id_provided=bool(client_message_id),
        )
        async with self.session.begin():
            case = await self.repository.get_by_patient_session(patient_user_id, session_id, for_update=True)
            if case is None or case.status == "resolved":
                return None
            existing = await self.repository.get_message_by_client_id(case.id, client_message_id)
            if existing is not None:
                return existing
            message = ChatTakeoverMessage(
                case_id=case.id,
                author_type="patient",
                author_user_id=patient_user_id,
                content=content,
                client_message_id=client_message_id,
            )
            self.session.add(message)
            await self.session.flush()
            await self.repository.add_audit(case.id, patient_user_id, "patient_message_received")
        payload = {"type": "takeover.message_created", "message": message_payload(message)}
        await chat_takeover_manager.publish_session(session_id, payload)
        await chat_takeover_manager.publish_staff(
            {"type": "takeover.message_created", "case": case_payload(case), "message": message_payload(message)}
        )
        log_event(
            logger,
            logging.INFO,
            "handoff.message.received",
            description="Patient takeover message was persisted and published to staff",
            case_id=str(case.id),
            author_type="patient",
            patient_user_id=str(patient_user_id),
        )
        return message

    async def _owned_case(self, case_id: UUID, staff_user_id: UUID, *, for_update: bool) -> ChatTakeoverCase:
        case = await self.repository.get_case(case_id, for_update=for_update)
        if case is None:
            raise NotFoundError("Không tìm thấy ca takeover.")
        if case.assigned_staff_id != staff_user_id:
            log_event(
                logger,
                logging.WARNING,
                "handoff.case.access.denied",
                description="Staff action was rejected because the takeover case is assigned to another user",
                case_id=str(case_id),
                staff_user_id=str(staff_user_id),
            )
            raise ConflictError("TAKEOVER_NOT_ASSIGNED", "Ca takeover không thuộc nhân viên hiện tại.")
        return case

    async def _publish_case(self, case: ChatTakeoverCase, event_type: str) -> None:
        await chat_takeover_manager.publish_session(case.session_id, {"type": event_type, "case": case_payload(case)})
        await chat_takeover_manager.publish_staff({"type": event_type, "case": case_payload(case)})


def case_payload(case: ChatTakeoverCase) -> dict:
    return {
        "id": str(case.id),
        "patient_user_id": str(case.patient_user_id),
        "session_id": case.session_id,
        "status": case.status,
        "priority": case.priority,
        "workflow_status": case.workflow_status,
        "summary": case.summary or {},
        "assigned_staff_id": str(case.assigned_staff_id) if case.assigned_staff_id else None,
        "claimed_at": case.claimed_at,
        "resolved_at": case.resolved_at,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


def message_payload(message: ChatTakeoverMessage) -> dict:
    return {
        "id": str(message.id),
        "case_id": str(message.case_id),
        "author_type": message.author_type,
        "author_user_id": str(message.author_user_id) if message.author_user_id else None,
        "content": message.content,
        "client_message_id": message.client_message_id,
        "metadata": message.message_metadata or {},
        "created_at": message.created_at,
    }
