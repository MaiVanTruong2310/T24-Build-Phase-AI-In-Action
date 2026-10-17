"""Persistence for staff assistant conversations and scoped HITL reads."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.conversation import Conversation, ConversationParticipant, Message, StaffAgentContext
from src.models.doctor import Doctor, DoctorFacility, DoctorService, DoctorSpecialty
from src.models.facility import Facility
from src.models.service import Service
from src.models.specialty import Specialty
from src.models.workbench import CoordinationCase, CoordinatorMember
from src.services import workbench


class StaffAgentRepository:
    """Read and persist staff assistant data without exposing ORM rows to the agent."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_context(self, staff_id: UUID) -> StaffAgentContext:
        context = await self._context_for_staff(staff_id, lock=True)
        if context:
            return context

        now = datetime.now(UTC)
        conversation_id = uuid4()
        conversation = Conversation(
            id=conversation_id,
            category="STAFF_ASSISTANT",
            mode="AI",
            status="ACTIVE",
            patient_id=None,
            created_by_type="STAFF",
            created_by_id=staff_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(conversation)
        await self.session.flush()
        result = await self.session.execute(
            insert(StaffAgentContext)
            .values(conversation_id=conversation_id, staff_id=staff_id, created_at=now, updated_at=now)
            .on_conflict_do_nothing(index_elements=[StaffAgentContext.staff_id])
        )
        if result.rowcount:
            self.session.add_all(
                [
                    ConversationParticipant(
                        conversation_id=conversation_id,
                        participant_type="STAFF",
                        participant_id=staff_id,
                        role="staff",
                        joined_at=now,
                    ),
                    ConversationParticipant(
                        conversation_id=conversation_id,
                        participant_type="AGENT",
                        participant_id=None,
                        role="assistant",
                        joined_at=now,
                    ),
                ]
            )
            await self.session.flush()
            return await self._context_for_staff(staff_id, lock=True)

        await self.session.delete(conversation)
        await self.session.flush()
        return await self._context_for_staff(staff_id, lock=True)

    async def _context_for_staff(self, staff_id: UUID, *, lock: bool = False) -> StaffAgentContext | None:
        statement = select(StaffAgentContext).where(StaffAgentContext.staff_id == staff_id)
        if lock:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def conversation(self, conversation_id: UUID) -> Conversation | None:
        return await self.session.get(Conversation, conversation_id)

    async def messages(self, conversation_id: UUID, *, limit: int = 12) -> list[Message]:
        rows = (
            await self.session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id, Message.sender_type.in_(["STAFF", "AGENT"]))
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(limit)
            )
        ).scalars()
        return list(reversed(rows.all()))

    async def add_message(
        self, conversation_id: UUID, *, sender_type: str, sender_id: UUID | None, content: str
    ) -> Message:
        now = datetime.now(UTC)
        message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            sender_id=sender_id,
            message_type="TEXT",
            content=content,
            created_at=now,
        )
        self.session.add(message)
        conversation = await self.session.get(Conversation, conversation_id)
        if conversation:
            conversation.updated_at = now
        await self.session.flush()
        return message

    async def get_scoped_case(self, staff_id: UUID, case_id: UUID) -> CoordinationCase | None:
        member = await self._enabled_member(staff_id)
        statement = select(CoordinationCase).where(
            CoordinationCase.id == case_id,
            workbench.scope(member),
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def search_scoped_cases(
        self,
        staff_id: UUID,
        query: str | None,
        limit: int,
        *,
        status: str | None = None,
        sla_state: str = "any",
        assigned_to_me: bool = False,
        received_today: bool = False,
        emergency_only: bool = False,
        agent_consulting: bool = False,
        submitted_exam_forms: bool = False,
    ) -> list[CoordinationCase]:
        member = await self._enabled_member(staff_id)
        statement = select(CoordinationCase).where(workbench.scope(member))
        if received_today:
            vietnam_tz = ZoneInfo("Asia/Ho_Chi_Minh")
            local_today = datetime.now(vietnam_tz).date()
            local_start = datetime.combine(local_today, time.min, tzinfo=vietnam_tz)
            next_local_start = datetime.combine(local_today + timedelta(days=1), time.min, tzinfo=vietnam_tz)
            statement = statement.where(
                CoordinationCase.created_at >= local_start.astimezone(UTC),
                CoordinationCase.created_at < next_local_start.astimezone(UTC),
            )
        if emergency_only:
            statement = statement.where(CoordinationCase.ai_snapshot["is_emergency"].as_boolean().is_(True))
        if agent_consulting:
            statement = statement.where(
                CoordinationCase.source == "chat",
                CoordinationCase.status == "observing",
                CoordinationCase.control == "ai",
            )
        if submitted_exam_forms:
            statement = statement.where(CoordinationCase.source == "consultation")
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            statement = statement.where(CoordinationCase.patient["name"].as_string().ilike(pattern, escape="\\"))
        if status:
            statement = statement.where(CoordinationCase.status == status[:24])
        if assigned_to_me:
            statement = statement.where(CoordinationCase.assigned_to == staff_id)
        else:
            statement = statement.where(
                CoordinationCase.assigned_to.is_(None),
                CoordinationCase.status.notin_(["emergency_active", "emergency_transferred"]),
            )
        if sla_state not in {"any", "overdue", "on_track"}:
            raise ValueError("Unsupported case SLA filter")
        if sla_state != "any":
            now = datetime.now(UTC)
            active = CoordinationCase.status.notin_(["completed", "cancelled"])
            if sla_state == "overdue":
                statement = statement.where(active, CoordinationCase.due_at.is_not(None), CoordinationCase.due_at < now)
            else:
                statement = statement.where(
                    active, CoordinationCase.due_at.is_not(None), CoordinationCase.due_at >= now
                )
        statement = statement.order_by(CoordinationCase.priority, CoordinationCase.created_at.desc()).limit(limit)
        return list((await self.session.execute(statement)).scalars().all())

    async def get_staff_facility_scope(self, staff_id: UUID) -> list[UUID]:
        """Return the enabled coordinator's assigned facilities for server-side filtering."""
        member = await self._enabled_member(staff_id)
        return [UUID(str(value)) for value in member.facility_ids]

    async def search_scoped_doctors(
        self,
        staff_id: UUID,
        *,
        doctor_name: str | None,
        specialty: str | None,
        facility: str | None,
        service: str | None,
        limit: int,
    ) -> tuple[list[Doctor], list[UUID]]:
        """Find eligible doctors without returning assignments outside staff scope."""
        member = await self._enabled_member(staff_id)
        facility_ids = [UUID(str(value)) for value in member.facility_ids]
        today = date.today()
        statement = (
            select(Doctor)
            .options(
                selectinload(Doctor.specialties).selectinload(DoctorSpecialty.specialty),
                selectinload(Doctor.facilities).selectinload(DoctorFacility.facility),
                selectinload(Doctor.services).selectinload(DoctorService.service),
            )
            .where(
                Doctor.status == "active",
                Doctor.review_status == "approved",
                Doctor.booking_enabled.is_(True),
            )
        )
        if doctor_name:
            pattern = _contains_pattern(doctor_name)
            statement = statement.where(Doctor.full_name.ilike(pattern, escape="\\"))
        if specialty:
            pattern = _contains_pattern(specialty)
            statement = statement.where(
                exists(
                    select(DoctorSpecialty.id)
                    .join(Specialty, Specialty.id == DoctorSpecialty.specialty_id)
                    .where(
                        DoctorSpecialty.doctor_id == Doctor.id,
                        Specialty.status == "active",
                        Specialty.name.ilike(pattern, escape="\\"),
                    )
                )
            )
        if facility:
            pattern = _contains_pattern(facility)
            statement = statement.where(
                exists(
                    select(DoctorFacility.id)
                    .join(Facility, Facility.id == DoctorFacility.facility_id)
                    .where(
                        DoctorFacility.doctor_id == Doctor.id,
                        Facility.status == "active",
                        or_(
                            Facility.name.ilike(pattern, escape="\\"),
                            Facility.code.ilike(pattern, escape="\\"),
                        ),
                        or_(DoctorFacility.active_from.is_(None), DoctorFacility.active_from <= today),
                        or_(DoctorFacility.active_to.is_(None), DoctorFacility.active_to >= today),
                    )
                )
            )
        if service:
            pattern = _contains_pattern(service)
            statement = statement.where(
                exists(
                    select(DoctorService.id)
                    .join(Service, Service.id == DoctorService.service_id)
                    .where(
                        DoctorService.doctor_id == Doctor.id,
                        DoctorService.active.is_(True),
                        Service.status == "active",
                        Service.name.ilike(pattern, escape="\\"),
                    )
                )
            )
        if facility_ids:
            statement = statement.where(
                exists(
                    select(DoctorFacility.id).where(
                        DoctorFacility.doctor_id == Doctor.id,
                        DoctorFacility.facility_id.in_(facility_ids),
                        or_(DoctorFacility.active_from.is_(None), DoctorFacility.active_from <= today),
                        or_(DoctorFacility.active_to.is_(None), DoctorFacility.active_to >= today),
                    )
                )
            )
        statement = statement.order_by(Doctor.full_name).limit(limit)
        return list((await self.session.execute(statement)).scalars().unique().all()), facility_ids

    async def _enabled_member(self, staff_id: UUID) -> CoordinatorMember:
        member = await self.session.get(CoordinatorMember, staff_id)
        if member is None or not member.enabled:
            from src.core.exceptions import AuthorizationError

            raise AuthorizationError("Staff member is not authorized to view coordination cases")
        return member


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
