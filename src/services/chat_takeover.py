"""Compatibility operations for takeover, backed by coordination workbench rows."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import or_, select

from src.config import get_settings
from src.core.exceptions import ConflictError, NotFoundError
from src.core.logging import get_logger
from src.models.conversation import Message as UnifiedMessage
from src.models.workbench import CoordinationCase, CoordinationMessage
from src.realtime.chat_takeover import chat_takeover_manager
from src.services import workbench

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
    """Adapt the existing takeover API/socket lifecycle to canonical workbench state."""

    def __init__(self, session):
        self.session = session

    async def ensure_case_from_result(self, patient_user, session_id: str, patient_message: str, result: dict):
        if result.get("workflow_status") != "HUMAN_HELP_REQUESTED":
            return None
        async with self.session.begin():
            case = await workbench.ensure_chat_case(
                self.session,
                SimpleNamespace(session_id=session_id, patient_profile=None, patient_profile_id=None),
                patient_user,
                None,
            )
            reopened = case.status in {"completed", "cancelled"}
            case.status = "new" if reopened or case.status == "observing" else case.status
            case.control = "human"
            case.priority = (
                0 if priority_for_result(result) == "critical" else 1 if priority_for_result(result) == "high" else 2
            )
            case.assigned_to = None if reopened else case.assigned_to
            summary = {
                "patient_message": patient_message[:2000],
                "patient_name": patient_user.full_name,
                "patient_age": _age(patient_user.date_of_birth),
                "patient_gender": patient_user.gender,
                "workflow_status": result.get("workflow_status"),
                "ats_level": result.get("ats_level"),
                "suggested_department": result.get("suggested_department"),
                "candidate_specialties": result.get("candidate_specialties") or [],
            }
            case.ai_snapshot = {
                **(case.ai_snapshot or {}),
                "workflow_status": "HUMAN_HELP_REQUESTED",
                "takeover_summary": summary,
            }
            workbench.bump(case)
            workbench.event(
                self.session,
                case,
                None,
                "human_requested" if not reopened else "takeover_reopened",
                details={"priority": case.priority},
            )
        await self._publish_case(case, "takeover.case_updated", staff=True)
        return case

    async def list_cases(self, status: str | None, offset: int, limit: int, staff_user_id: UUID):
        if status and status not in TAKEOVER_STATUSES:
            raise HTTPException(422, "Trạng thái takeover không hợp lệ.")
        member = await self._member(staff_user_id)
        query = select(CoordinationCase).where(CoordinationCase.source == "chat", workbench.scope(member))
        if status in {"queued", "released"}:
            query = query.where(
                CoordinationCase.control == "human",
                CoordinationCase.assigned_to.is_(None),
                CoordinationCase.status.notin_(["completed", "cancelled"]),
            )
        elif status == "taken_over":
            query = query.where(
                CoordinationCase.control == "human",
                CoordinationCase.assigned_to.is_not(None),
                CoordinationCase.status.notin_(["completed", "cancelled"]),
            )
        elif status == "resolved":
            query = query.where(CoordinationCase.status.in_(["completed", "cancelled"]))
        else:
            query = query.where(
                CoordinationCase.control == "human",
                CoordinationCase.status.notin_(["completed", "cancelled"]),
            )
        rows = (
            (
                await self.session.execute(
                    query.order_by(CoordinationCase.priority, CoordinationCase.created_at).offset(offset).limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return rows

    async def get_case(self, case_id: UUID, staff_user_id: UUID):
        member = await self._member(staff_user_id)
        case = await self._case(case_id, member)
        if case.source != "chat":
            raise NotFoundError("Không tìm thấy ca takeover.")
        return case

    async def get_case_for_patient(self, patient_user_id: UUID, session_id: str):
        async with self.session.begin():
            return (
                await self.session.execute(
                    select(CoordinationCase).where(
                        CoordinationCase.source == "chat",
                        CoordinationCase.owner_key == f"user:{patient_user_id}",
                        CoordinationCase.session_id == session_id,
                    )
                )
            ).scalar_one_or_none()

    async def active_case_for_patient(self, patient_user_id: UUID, session_id: str):
        case = await self.get_case_for_patient(patient_user_id, session_id)
        if case is None or case.control != "human" or case.status in {"completed", "cancelled"}:
            return None
        return case

    async def history(self, case, limit: int = 200) -> list[dict]:
        if get_settings().use_unified_conversation:
            messages = (
                (
                    await self.session.execute(
                        select(UnifiedMessage)
                        .where(UnifiedMessage.conversation_id == case.id)
                        .order_by(UnifiedMessage.created_at, UnifiedMessage.id)
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            return [message_payload(message, case) for message in messages]

        messages = (
            (
                await self.session.execute(
                    select(CoordinationMessage)
                    .where(CoordinationMessage.case_id == case.id)
                    .order_by(CoordinationMessage.created_at, CoordinationMessage.id)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [message_payload(message, case) for message in messages]

    async def claim(self, case_id: UUID, staff_user_id: UUID):
        async with self.session.begin():
            member = await self._member(staff_user_id, for_update=True)
            if not member.on_duty:
                raise ConflictError("STAFF_NOT_ON_DUTY", "Hãy bắt đầu ca trực trước khi tiếp nhận ca.")
            case = await self._case(case_id, member, for_update=True)
            if case.source != "chat" or case.control != "human" or case.status in {"completed", "cancelled"}:
                raise ConflictError("TAKEOVER_NOT_ACTIVE", "Ca chat không còn chờ tiếp nhận.")
            if case.assigned_to == staff_user_id:
                return case
            if case.assigned_to is not None:
                raise ConflictError("TAKEOVER_ALREADY_CLAIMED", "Ca takeover đã được nhân viên khác tiếp nhận.")
            if member.facility_ids and case.facility_id and str(case.facility_id) not in member.facility_ids:
                raise HTTPException(403, "Ca chat nằm ngoài phạm vi cơ sở của bạn.")
            case.assigned_to = staff_user_id
            case.status = "contacting" if case.status in {"new", "observing"} else case.status
            case.checkpoint = {**(case.checkpoint or {}), "takeover_claimed_at": datetime.now(UTC).isoformat()}
            workbench.bump(case)
            workbench.event(self.session, case, SimpleNamespace(id=staff_user_id), "takeover_claimed")
        await self._publish_case(case, "takeover.case_updated", staff=True)
        return case

    async def release(self, case_id: UUID, staff_user_id: UUID):
        async with self.session.begin():
            member = await self._member(staff_user_id, for_update=True)
            case = await self._case(case_id, member, for_update=True)
            self._assert_owner(case, staff_user_id)
            case.assigned_to = None
            case.status = "new"
            case.control = "human"
            case.checkpoint = {**(case.checkpoint or {}), "takeover_released": True}
            workbench.bump(case)
            workbench.event(self.session, case, SimpleNamespace(id=staff_user_id), "takeover_released")
        await self._publish_case(case, "takeover.case_updated", staff=True)
        return case

    async def resolve(self, case_id: UUID, staff_user_id: UUID):
        async with self.session.begin():
            member = await self._member(staff_user_id, for_update=True)
            case = await self._case(case_id, member, for_update=True)
            self._assert_owner(case, staff_user_id)
            case.status = "completed"
            case.control = "ai"
            case.assigned_to = None
            case.follow_up_at = None
            case.checkpoint = {**(case.checkpoint or {}), "takeover_resolved_at": datetime.now(UTC).isoformat()}
            workbench.bump(case)
            workbench.event(self.session, case, SimpleNamespace(id=staff_user_id), "takeover_resolved")
        await self._publish_case(case, "takeover.case_updated", staff=True)
        return case

    async def send_staff_message(self, case_id: UUID, staff_user_id: UUID, content: str, client_message_id: str | None):
        async with self.session.begin():
            member = await self._member(staff_user_id, for_update=True)
            case = await self._case(case_id, member, for_update=True)
            self._assert_owner(case, staff_user_id)
            if case.control != "human" or case.status in {"completed", "cancelled"}:
                raise ConflictError("TAKEOVER_NOT_ACTIVE", "Chỉ được gửi tin nhắn khi ca đang được tiếp nhận.")
            message_id = client_message_id or str(uuid4())
            message = await workbench_message(self.session, case, message_id, content, staff_user_id)
        await self._publish_message(case, message)
        return message

    async def record_patient_message(
        self, patient_user_id: UUID, session_id: str, content: str, client_message_id: str
    ):
        async with self.session.begin():
            case = (
                await self.session.execute(
                    select(CoordinationCase)
                    .where(
                        CoordinationCase.source == "chat",
                        CoordinationCase.owner_key == f"user:{patient_user_id}",
                        CoordinationCase.session_id == session_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if case is None or case.control != "human" or case.status in {"completed", "cancelled"}:
                return None
            message = await workbench_message(self.session, case, client_message_id, content, None, sender="patient")
        await self._publish_message(case, message)
        return message

    async def staff_access(self, staff_user_id: UUID) -> bool:
        member = await self.session.get(workbench.Member, staff_user_id)
        await self.session.commit()
        return bool(member and member.enabled)

    async def _member(self, staff_user_id: UUID, *, for_update: bool = False):
        member_query = select(workbench.Member).where(workbench.Member.user_id == staff_user_id)
        if for_update:
            member_query = member_query.with_for_update()
        member = (await self.session.execute(member_query)).scalar_one_or_none()
        if not member or not member.enabled:
            raise HTTPException(403, "Tài khoản chưa được cấp quyền điều phối viên.")
        return member

    async def _case(self, case_id: UUID, member, *, for_update: bool = False):
        query = select(CoordinationCase).where(
            or_(CoordinationCase.id == case_id, CoordinationCase.legacy_takeover_case_id == case_id),
            workbench.scope(member),
        )
        if for_update:
            query = query.with_for_update()
        case = (await self.session.execute(query)).scalar_one_or_none()
        if case is None:
            raise NotFoundError("Không tìm thấy ca takeover.")
        return case

    @staticmethod
    def _assert_owner(case, staff_user_id: UUID) -> None:
        if case.assigned_to != staff_user_id:
            raise ConflictError("TAKEOVER_NOT_ASSIGNED", "Ca takeover không thuộc nhân viên hiện tại.")

    async def _publish_case(self, case, event_type: str, *, staff: bool):
        payload = {"type": event_type, "case": case_payload(case)}
        await chat_takeover_manager.publish_session(case.session_id, payload)
        if staff:
            await chat_takeover_manager.publish_staff(payload)

    async def _publish_message(self, case, message):
        payload = {"type": "takeover.message_created", "message": message_payload(message, case)}
        await chat_takeover_manager.publish_session(case.session_id, payload)
        await chat_takeover_manager.publish_staff(
            {"type": "takeover.message_created", "case": case_payload(case), "message": payload["message"]}
        )


async def workbench_message(session, case, client_id: str, content: str, actor_id, *, sender="coordinator"):
    if get_settings().use_unified_conversation:
        stmt = select(UnifiedMessage).where(UnifiedMessage.conversation_id == case.id)
        candidates = (await session.execute(stmt)).scalars().all()
        existing = next(
            (m for m in candidates if (m.msg_metadata or {}).get("client_id") == client_id or str(m.id) == client_id),
            None,
        )
        if existing is not None:
            return existing

        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from src.models.conversation import Conversation
        now = datetime.now(UTC)
        await session.execute(
            pg_insert(Conversation).values(
                id=case.id,
                category="PATIENT_SUPPORT",
                mode="HUMAN" if getattr(case, "control", "ai") == "human" else "AI",
                status="ACTIVE" if getattr(case, "status", "new") not in ("completed", "cancelled") else "RESOLVED",
                patient_id=case.patient_id,
                created_by_type="PATIENT" if case.patient_id else "SYSTEM",
                created_by_id=case.patient_id,
                created_at=getattr(case, "created_at", None) or now,
                updated_at=now,
            ).on_conflict_do_nothing(index_elements=["id"])
        )

        sender_type = "STAFF" if sender in ("coordinator", "staff") else "PATIENT"
        message = UnifiedMessage(
            id=uuid4(),
            conversation_id=case.id,
            sender_type=sender_type,
            sender_id=actor_id,
            message_type="TEXT",
            content=content,
            msg_metadata={"client_id": client_id, "legacy_sender": sender},
            created_at=now,
        )
        session.add(message)
        await session.flush()
        return message

    existing = (
        await session.execute(
            select(CoordinationMessage).where(
                CoordinationMessage.case_id == case.id,
                CoordinationMessage.client_id == client_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    message = CoordinationMessage(
        case_id=case.id,
        client_id=client_id,
        sender=sender,
        actor_id=actor_id,
        body=content,
    )
    session.add(message)
    await session.flush()
    return message


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


def _age(birth_date):
    if birth_date is None:
        return None
    today = datetime.now(UTC).date()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
