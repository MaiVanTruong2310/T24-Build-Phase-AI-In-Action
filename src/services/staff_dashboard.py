"""Read-only aggregate metrics for the staff operations dashboard."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.booking import Booking
from src.models.notification import Notification
from src.models.schedule import DoctorSchedule
from src.models.user import User
from src.models.workbench import CoordinationCase, CoordinationEvent

ESCALATION_ACTIONS = ("human_requested", "takeover_reopened")


async def dashboard_summary(
    db: AsyncSession,
    start: datetime,
    end: datetime,
    facility_id: UUID | None = None,
    doctor_id: UUID | None = None,
) -> dict[str, int]:
    case_filters = []
    booking_filters = []
    schedule_filters = []
    notification_filters = []
    if facility_id:
        case_filters.append(CoordinationCase.facility_id == facility_id)
        booking_filters.append(Booking.facility_id == facility_id)
        schedule_filters.append(DoctorSchedule.facility_id == facility_id)
        notification_filters.append(Booking.facility_id == facility_id)
    if doctor_id:
        case_filters.append(CoordinationCase.booking_id == Booking.id)
        case_filters.append(Booking.doctor_id == doctor_id)
        booking_filters.append(Booking.doctor_id == doctor_id)
        schedule_filters.append(DoctorSchedule.doctor_id == doctor_id)
        notification_filters.append(Booking.doctor_id == doctor_id)

    async def count(query):
        return int((await db.execute(query)).scalar_one() or 0)

    event_filter = [CoordinationEvent.created_at >= start, CoordinationEvent.created_at < end]
    event_from = CoordinationEvent.__table__.join(
        CoordinationCase.__table__, CoordinationCase.id == CoordinationEvent.case_id
    )
    event_filter.extend(case_filters)
    if doctor_id:
        event_from = event_from.join(Booking.__table__, CoordinationCase.booking_id == Booking.id)

    completed_event = select(CoordinationEvent.case_id).where(
        CoordinationEvent.case_id == CoordinationCase.id,
        CoordinationEvent.action == "complete",
        CoordinationEvent.created_at >= start,
        CoordinationEvent.created_at < end,
    )
    interventions = select(CoordinationEvent.id).where(
        CoordinationEvent.case_id == CoordinationCase.id,
        CoordinationEvent.actor_id.is_not(None) | CoordinationEvent.action.in_(ESCALATION_ACTIONS),
    )
    ai_completed_filters = [
        CoordinationCase.source == "chat",
        CoordinationCase.status == "completed",
        CoordinationCase.id.in_(completed_event),
        not_(interventions.exists()),
        *case_filters,
    ]
    if doctor_id:
        ai_completed_filters.append(CoordinationCase.booking_id == Booking.id)
        ai_query = (
            select(func.count(func.distinct(CoordinationCase.id)))
            .select_from(CoordinationCase.__table__.join(Booking.__table__, CoordinationCase.booking_id == Booking.id))
            .where(*ai_completed_filters)
        )
    else:
        ai_query = select(func.count(func.distinct(CoordinationCase.id))).where(*ai_completed_filters)

    booking_from = Booking
    if doctor_id and facility_id:
        booking_filters.extend([Booking.doctor_id == doctor_id, Booking.facility_id == facility_id])
    elif doctor_id:
        booking_filters.append(Booking.doctor_id == doctor_id)
    elif facility_id:
        booking_filters.append(Booking.facility_id == facility_id)

    notification_from = Notification
    if notification_filters:
        notification_from = Notification.__table__.join(Booking.__table__, Notification.booking_id == Booking.id)

    return {
        "cases_handled": await count(
            select(func.count(func.distinct(CoordinationEvent.case_id)))
            .select_from(event_from)
            .where(CoordinationEvent.action == "complete", *event_filter)
        ),
        "chat_escalations": await count(
            select(func.count(func.distinct(CoordinationEvent.case_id)))
            .select_from(event_from)
            .where(CoordinationCase.source == "chat", CoordinationEvent.action.in_(ESCALATION_ACTIONS), *event_filter)
        ),
        "patients_total": await count(
            select(func.count()).select_from(User).where(User.role == "patient", User.status == "active")
        ),
        "patients_new": await count(
            select(func.count())
            .select_from(User)
            .where(
                User.role == "patient",
                User.status == "active",
                User.created_at >= start,
                User.created_at < end,
            )
        ),
        "chat_cases_ai_handled_without_escalation": await count(ai_query),
        "cases_with_coordinator_intervention": await count(
            select(func.count(func.distinct(CoordinationEvent.case_id)))
            .select_from(event_from)
            .where(
                CoordinationEvent.actor_id.is_not(None) | CoordinationEvent.action.in_(ESCALATION_ACTIONS),
                *event_filter,
            )
        ),
        "bookings_created": await count(
            select(func.count())
            .select_from(booking_from)
            .where(Booking.created_at >= start, Booking.created_at < end, *booking_filters)
        ),
        "bookings_approved": await count(
            select(func.count())
            .select_from(booking_from)
            .where(
                Booking.status == "confirmed", Booking.reviewed_at >= start, Booking.reviewed_at < end, *booking_filters
            )
        ),
        "schedules_starting": await count(
            select(func.count())
            .select_from(DoctorSchedule)
            .where(DoctorSchedule.starts_at >= start, DoctorSchedule.starts_at < end, *schedule_filters)
        ),
        "reminders_delivered": await count(
            select(func.count())
            .select_from(notification_from)
            .where(
                Notification.kind == "appointment_reminder",
                Notification.status == "delivered",
                Notification.delivered_at >= start,
                Notification.delivered_at < end,
                *notification_filters,
            )
        ),
    }
