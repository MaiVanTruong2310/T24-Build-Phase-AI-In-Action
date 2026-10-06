"""Patient half-day requests and staff assignment of private doctor slots."""

import re
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_optional_user, require_patient
from src.api.dependencies import require_coordination_admin as require_staff
from src.api.response import success_response
from src.core.exceptions import ConflictError, NotFoundError
from src.db.dependencies import get_db_session
from src.models.coordination import (
    ConsultationRequest,
    ConsultationRequestEvent,
    ConsultationSession,
    ConsultationSlot,
    WeeklyShift,
)
from src.models.doctor import Doctor, DoctorFacility, DoctorSpecialty
from src.models.facility import Facility
from src.models.schedule import DoctorSchedule
from src.models.service import Service
from src.models.specialty import Specialty
from src.models.user import User

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
router = APIRouter(prefix="/coordination", tags=["coordination"])
staff_router = APIRouter(prefix="/staff/coordination", tags=["staff-coordination"])


class ShiftInput(BaseModel):
    doctor_id: UUID
    facility_id: UUID
    weekday: int = Field(ge=0, le=6)
    period: str = Field(pattern="^(morning|afternoon)$")
    start_time: time
    slot_minutes: int = Field(default=30, ge=5, le=240)
    slot_count: int = Field(default=5, ge=1, le=20)
    effective_from: date
    effective_until: date | None = None


class PublishInput(BaseModel):
    from_date: date
    through_date: date


class StandardWeekInput(BaseModel):
    doctor_id: UUID
    facility_id: UUID
    effective_from: date


class RequestInput(BaseModel):
    patient_profile_id: UUID | None = None
    session_id: UUID
    service_id: UUID
    specialty_id: UUID
    encounter_type: str = Field(default="in_person", pattern="^(in_person|telehealth)$")
    reason: str = Field(min_length=1, max_length=2000)
    patient_note: str | None = Field(default=None, max_length=2000)

    # Guest fields for unauthenticated patients
    patient_name: str | None = Field(default=None, max_length=120)
    patient_phone: str | None = Field(default=None, max_length=20)
    patient_email: str | None = Field(default=None, max_length=320)
    gender: str | None = Field(default=None, pattern="^(male|female|other|prefer_not_to_say)$")
    date_of_birth: date | None = None
    consent_to_contact: bool = False
    guardian_name: str | None = Field(default=None, max_length=120)
    guardian_phone: str | None = Field(default=None, max_length=20)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason must not be blank")
        return value.strip()


class DecisionInput(BaseModel):
    slot_id: UUID | None = None
    note: str | None = Field(default=None, max_length=2000)


def _request_dict(
    value: ConsultationRequest,
    session: ConsultationSession,
    patient: User | None = None,
    slot: DoctorSchedule | None = None,
) -> dict:
    return {
        "id": str(value.id), "patient_id": str(value.patient_id),
        "patient_profile_id": str(value.patient_profile_id) if value.patient_profile_id else None,
        "requested_by_user_id": str(value.requested_by_user_id) if value.requested_by_user_id else None,
        "patient_name": patient.full_name if patient else None,
        "patient_phone": patient.phone if patient else None,
        "patient_email": patient.email if patient else None,
        "gender": patient.gender if patient else None,
        "date_of_birth": patient.date_of_birth.isoformat() if patient and patient.date_of_birth else None,
        "session_id": str(session.id),
        "doctor_id": str(session.doctor_id),
        "facility_id": str(session.facility_id),
        "date": session.session_date.isoformat(),
        "period": session.period,
        "service_id": str(value.service_id),
        "specialty_id": str(value.specialty_id),
        "reason": value.reason,
        "patient_note": value.patient_note,
        "status": value.status,
        "staff_note": value.staff_note,
        "slot_id": str(value.assigned_slot_id) if value.assigned_slot_id else None,
        "starts_at": slot.starts_at.isoformat() if slot else None,
        "ends_at": slot.ends_at.isoformat() if slot else None,
        "created_at": value.created_at.isoformat() if value.created_at else None,
    }


async def _session_capacity(db: AsyncSession, session_id: UUID) -> tuple[int, int]:
    """Return published capacity and future slots not reserved by pending requests."""
    slots = (
        await db.execute(
            select(ConsultationSlot.id, DoctorSchedule.starts_at)
            .join(DoctorSchedule, DoctorSchedule.id == ConsultationSlot.schedule_id)
            .where(ConsultationSlot.session_id == session_id, DoctorSchedule.status == "blocked")
        )
    ).all()
    requests = (
        await db.execute(
            select(ConsultationRequest.status, ConsultationRequest.assigned_slot_id).where(
                ConsultationRequest.session_id == session_id, ConsultationRequest.status.in_(("pending", "confirmed"))
            )
        )
    ).all()
    assigned = {slot_id for status, slot_id in requests if status == "confirmed" and slot_id}
    pending = sum(1 for status, _ in requests if status == "pending")
    future_free = sum(1 for slot_id, starts_at in slots if slot_id not in assigned and starts_at > datetime.now(UTC))
    return len(slots), max(0, future_free - pending)


@router.get("/sessions")
async def list_sessions(
    doctor_id: UUID,
    selected_date: date = Query(alias="date"),
    facility_id: UUID | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    today = datetime.now(VN_TZ).date()
    if selected_date < today:
        raise ConflictError("INVALID_APPOINTMENT_DATE", "Ngày khám không được nằm trong quá khứ.")
    if selected_date > today + timedelta(days=90):
        raise ConflictError("INVALID_APPOINTMENT_DATE", "Chỉ được đặt ngày khám trong 90 ngày tới.")
    sessions = (await db.execute(select(ConsultationSession).where(
        ConsultationSession.doctor_id == doctor_id,
        ConsultationSession.session_date == selected_date,
        ConsultationSession.status == "open",
        *([ConsultationSession.facility_id == facility_id] if facility_id else []),
    ))).scalars().all()
    result = []
    for session in sessions:
        capacity, remaining = await _session_capacity(db, session.id)
        result.append(
            {
                "id": str(session.id),
                "date": session.session_date.isoformat(),
                "period": session.period,
                "remaining": remaining,
                "capacity": capacity,
                "facility_id": str(session.facility_id),
            }
        )
    return success_response(result, "Published half-day sessions")


@router.post("/requests", status_code=201)
async def create_request(
    payload: RequestInput,
    http_request: Request,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db_session),
):
    async with db.begin():
        from src.services.patient_profiles import resolve_booking_payload
        target, profile = await resolve_booking_payload(db, user, payload)
        if user is None:
            if not payload.patient_name or len(payload.patient_name.strip()) < 2:
                raise ConflictError("NAME_REQUIRED", "Vui lòng nhập họ và tên bệnh nhân (tối thiểu 2 ký tự)")
            if not payload.patient_phone:
                raise ConflictError("PHONE_REQUIRED", "Vui lòng nhập số điện thoại liên hệ")
            clean_phone = re.sub(r"[\s.()-]", "", payload.patient_phone)
            if not re.fullmatch(r"^(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-5]|9[0-9])\d{7}$", clean_phone):
                raise ConflictError("INVALID_PHONE", "Số điện thoại chưa đúng định dạng Việt Nam")
            if not payload.gender:
                raise ConflictError("GENDER_REQUIRED", "Vui lòng chọn giới tính")
            if not payload.date_of_birth:
                raise ConflictError("DOB_REQUIRED", "Vui lòng chọn ngày sinh")
            if payload.date_of_birth > datetime.now(VN_TZ).date():
                raise ConflictError("INVALID_DOB", "Ngày sinh không thể nằm trong tương lai")

            patient = User(
                full_name=payload.patient_name.strip(),
                phone=None,
                email=None,
                gender=payload.gender,
                date_of_birth=payload.date_of_birth,
                role="patient",
                status="guest",
            )
            db.add(patient)
            await db.flush()
        else:
            patient = target

        if not payload.consent_to_contact:
            raise ConflictError("CONSENT_REQUIRED", "Cần đồng ý để điều phối viên liên hệ và xử lý phiếu.")
        from src.medical_assistant.domain.booking_request_service import PHONE_PATTERN, _is_minor

        dob = payload.date_of_birth or patient.date_of_birth
        if (
            dob
            and _is_minor(dob)
            and (
                not payload.guardian_name
                or not PHONE_PATTERN.fullmatch(re.sub(r"[\s.()-]", "", payload.guardian_phone or ""))
            )
        ):
            raise ConflictError("GUARDIAN_REQUIRED", "Người dưới 18 tuổi cần họ tên và điện thoại người giám hộ.")

        session = (await db.execute(select(ConsultationSession).where(
            ConsultationSession.id == payload.session_id).with_for_update()
        )).scalar_one_or_none()
        if session is None or session.status != "open" or not datetime.now(VN_TZ).date() <= session.session_date <= datetime.now(VN_TZ).date() + timedelta(days=90):
            raise ConflictError("SESSION_UNAVAILABLE", "Buổi khám không còn nhận yêu cầu")
        doctor = await db.get(Doctor, session.doctor_id)
        facility = await db.get(Facility, session.facility_id)
        service = await db.get(Service, payload.service_id)
        specialty = await db.get(Specialty, payload.specialty_id)
        if (
            not doctor
            or doctor.professional_role != "Bác sĩ"
            or doctor.status != "active"
            or doctor.review_status != "approved"
            or not doctor.booking_enabled
        ):
            raise ConflictError("DOCTOR_UNAVAILABLE", "Bác sĩ chưa nhận lịch")
        if (
            not facility
            or facility.status != "active"
            or not service
            or service.status != "active"
            or not specialty
            or specialty.status != "active"
        ):
            raise ConflictError("CATALOG_UNAVAILABLE", "Thông tin khám không còn hiệu lực")
        has_specialty = (
            await db.execute(
                select(DoctorSpecialty.id).where(
                    DoctorSpecialty.doctor_id == session.doctor_id,
                    DoctorSpecialty.specialty_id == specialty.id,
                )
            )
        ).first()
        has_facility = (
            await db.execute(
                select(DoctorFacility.id).where(
                    DoctorFacility.doctor_id == session.doctor_id,
                    DoctorFacility.facility_id == facility.id,
                    (DoctorFacility.active_from.is_(None) | (DoctorFacility.active_from <= session.session_date)),
                    (DoctorFacility.active_to.is_(None) | (DoctorFacility.active_to >= session.session_date)),
                )
            )
        ).first()
        if not all((has_specialty, has_facility)):
            raise ConflictError("DOCTOR_CATALOG_MISMATCH", "Bác sĩ không thuộc chuyên khoa hoặc cơ sở đã chọn")
        existing = (await db.execute(select(ConsultationRequest.id).where(
            (ConsultationRequest.patient_id == patient.id) | (ConsultationRequest.requested_by_user_id == patient.id), ConsultationRequest.session_id == session.id,
            ConsultationRequest.status.in_(("pending", "confirmed")),
        ))).first()
        if existing:
            raise ConflictError("REQUEST_EXISTS", "Bạn đã gửi yêu cầu cho buổi khám này")
        _, remaining = await _session_capacity(db, session.id)
        if remaining < 1:
            raise ConflictError("SESSION_FULL", "Buổi khám đã đủ số yêu cầu")
        item = ConsultationRequest(patient_id=patient.id, requested_by_user_id=user.id if user else None,
                                   patient_profile_id=profile.id if profile else None, session_id=session.id,
                                   service_id=service.id, specialty_id=specialty.id,
                                   encounter_type=payload.encounter_type,
                                   reason=payload.reason.strip(), patient_note=payload.patient_note)
        db.add(item)
        await db.flush()
        db.add(ConsultationRequestEvent(request_id=item.id, actor_id=user.id if user else patient.id, action="requested"))
        from src.services.workbench import create_source_case

        receipt = await create_source_case(
            db, "consultation", item, patient, user, http_request.state.coordination_guest, payload, session.facility_id
        )

    result = _request_dict(item, session, patient)
    result.update(
        patient_name=receipt.patient.get("name"),
        patient_phone=receipt.patient.get("phone"),
        patient_email=receipt.patient.get("email"),
        coordination_session_id=receipt.session_id,
    )
    return success_response(result, "Yêu cầu đã gửi; nhân viên sẽ gọi lại để chốt giờ", 201)


@router.get("/requests/mine")
async def my_requests(patient: User = Depends(require_patient), db: AsyncSession = Depends(get_db_session)):
    rows = (await db.execute(select(ConsultationRequest, ConsultationSession, DoctorSchedule).join(
        ConsultationSession, ConsultationSession.id == ConsultationRequest.session_id,
    ).outerjoin(ConsultationSlot, ConsultationSlot.id == ConsultationRequest.assigned_slot_id)
        .outerjoin(DoctorSchedule, DoctorSchedule.id == ConsultationSlot.schedule_id)
        .where((ConsultationRequest.patient_id == patient.id) | (ConsultationRequest.requested_by_user_id == patient.id))
        .order_by(ConsultationRequest.created_at.desc()).limit(100))).all()
    return success_response([_request_dict(item, session, slot=slot) for item, session, slot in rows], "Your requests")


@router.post("/requests/{request_id}/cancel")
async def cancel_request(
    request_id: UUID, patient: User = Depends(require_patient), db: AsyncSession = Depends(get_db_session)
):
    async with db.begin():
        item = (await db.execute(select(ConsultationRequest).where(
            ConsultationRequest.id == request_id,
            (ConsultationRequest.patient_id == patient.id) | (ConsultationRequest.requested_by_user_id == patient.id),
        ).with_for_update())).scalar_one_or_none()
        if item is None:
            raise NotFoundError("Request not found")
        await db.execute(
            select(ConsultationSession.id)
            .where(
                ConsultationSession.id == item.session_id,
            )
            .with_for_update()
        )
        if item.status != "pending":
            raise ConflictError("REQUEST_NOT_PENDING", "Chỉ có thể huỷ yêu cầu đang chờ gọi lại")
        item.status = "cancelled"
        db.add(ConsultationRequestEvent(request_id=item.id, actor_id=patient.id, action="cancelled"))
    return success_response({"id": str(item.id)}, "Request cancelled")


@staff_router.get("/rules")
async def list_rules(_: User = Depends(require_staff), db: AsyncSession = Depends(get_db_session)):
    rows = (
        (await db.execute(select(WeeklyShift).order_by(WeeklyShift.doctor_id, WeeklyShift.weekday, WeeklyShift.period)))
        .scalars()
        .all()
    )
    return success_response(
        [
            {
                "id": str(x.id),
                "doctor_id": str(x.doctor_id),
                "facility_id": str(x.facility_id),
                "weekday": x.weekday,
                "period": x.period,
                "start_time": x.start_time.isoformat(),
                "slot_minutes": x.slot_minutes,
                "slot_count": x.slot_count,
                "effective_from": x.effective_from.isoformat(),
                "active": x.active,
            }
            for x in rows
        ],
        "Weekly shifts",
    )


@staff_router.post("/rules/standard-week")
async def create_standard_week(
    payload: StandardWeekInput, _: User = Depends(require_staff), db: AsyncSession = Depends(get_db_session)
):
    async with db.begin():
        doctor = (
            await db.execute(select(Doctor).where(Doctor.id == payload.doctor_id).with_for_update())
        ).scalar_one_or_none()
        facility = await db.get(Facility, payload.facility_id)
        if doctor is None or facility is None:
            raise NotFoundError("Doctor or facility not found")
        if doctor.professional_role != "Bác sĩ":
            raise ConflictError("NOT_DOCTOR", "Nhân sự này không nhận lịch khám bác sĩ")
        linked = (
            await db.execute(
                select(DoctorFacility.id).where(
                    DoctorFacility.doctor_id == payload.doctor_id,
                    DoctorFacility.facility_id == payload.facility_id,
                    (DoctorFacility.active_from.is_(None) | (DoctorFacility.active_from <= payload.effective_from)),
                    (DoctorFacility.active_to.is_(None) | (DoctorFacility.active_to >= payload.effective_from)),
                )
            )
        ).first()
        if not linked:
            raise ConflictError("FACILITY_NOT_LINKED", "Bác sĩ chưa thuộc cơ sở này")
        existing = set(
            (
                await db.execute(
                    select(WeeklyShift.weekday, WeeklyShift.period).where(
                        WeeklyShift.doctor_id == payload.doctor_id,
                    )
                )
            ).all()
        )
        created = 0
        for weekday in range(7):
            for period, start in (("morning", time(8, 0)), ("afternoon", time(13, 30))):
                if (weekday, period) in existing:
                    continue
                db.add(
                    WeeklyShift(
                        doctor_id=payload.doctor_id,
                        facility_id=payload.facility_id,
                        weekday=weekday,
                        period=period,
                        start_time=start,
                        slot_minutes=30,
                        slot_count=5,
                        effective_from=payload.effective_from,
                    )
                )
                created += 1
    return success_response({"rules_created": created}, "Standard week created")


@staff_router.post("/rules", status_code=201)
async def create_rule(
    payload: ShiftInput, _: User = Depends(require_staff), db: AsyncSession = Depends(get_db_session)
):
    if payload.effective_until and payload.effective_until < payload.effective_from:
        raise ConflictError("INVALID_DATE_RANGE", "Ngày kết thúc trước ngày bắt đầu")
    if payload.period == "morning" and payload.start_time.hour >= 12:
        raise ConflictError("INVALID_PERIOD", "Giờ bắt đầu phải thuộc buổi sáng")
    if payload.period == "afternoon" and payload.start_time.hour < 12:
        raise ConflictError("INVALID_PERIOD", "Giờ bắt đầu phải thuộc buổi chiều")
    end_minutes = payload.start_time.hour * 60 + payload.start_time.minute + payload.slot_count * payload.slot_minutes
    if end_minutes > (12 * 60 if payload.period == "morning" else 24 * 60):
        raise ConflictError("INVALID_SHIFT", "Các slot vượt quá phạm vi buổi khám")
    doctor = await db.get(Doctor, payload.doctor_id)
    facility = await db.get(Facility, payload.facility_id)
    if not doctor or not facility:
        raise NotFoundError("Doctor or facility not found")
    if doctor.professional_role != "Bác sĩ":
        raise ConflictError("NOT_DOCTOR", "Nhân sự này không nhận lịch khám bác sĩ")
    linked = (
        await db.execute(
            select(DoctorFacility.id).where(
                DoctorFacility.doctor_id == payload.doctor_id,
                DoctorFacility.facility_id == payload.facility_id,
                (DoctorFacility.active_from.is_(None) | (DoctorFacility.active_from <= payload.effective_from)),
                (DoctorFacility.active_to.is_(None) | (DoctorFacility.active_to >= payload.effective_from)),
            )
        )
    ).first()
    if not linked:
        raise ConflictError("FACILITY_NOT_LINKED", "Bác sĩ chưa thuộc cơ sở này")
    value = WeeklyShift(**payload.model_dump())
    try:
        db.add(value)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("SHIFT_EXISTS", "Bác sĩ đã có quy tắc cho thứ và buổi này") from exc
    return success_response({"id": str(value.id)}, "Weekly shift created", 201)


@staff_router.post("/publish")
async def publish_sessions(
    payload: PublishInput, staff: User = Depends(require_staff), db: AsyncSession = Depends(get_db_session)
):
    if (
        payload.from_date < datetime.now(VN_TZ).date()
        or payload.through_date < payload.from_date
        or (payload.through_date - payload.from_date).days > 42
    ):
        raise ConflictError("INVALID_RANGE", "Chỉ công bố tối đa 43 ngày trong tương lai")
    rules = (await db.execute(select(WeeklyShift).where(WeeklyShift.active.is_(True)))).scalars().all()
    await db.commit()
    created = 0
    for offset in range((payload.through_date - payload.from_date).days + 1):
        day = payload.from_date + timedelta(days=offset)
        for rule in rules:
            if (
                rule.weekday != day.weekday()
                or day < rule.effective_from
                or (rule.effective_until and day > rule.effective_until)
            ):
                continue
            async with db.begin():
                # Serializes publishing with patient requests and assignment for this doctor/date.
                await db.execute(select(Doctor.id).where(Doctor.id == rule.doctor_id).with_for_update())
                linked = (
                    await db.execute(
                        select(DoctorFacility.id).where(
                            DoctorFacility.doctor_id == rule.doctor_id,
                            DoctorFacility.facility_id == rule.facility_id,
                            (DoctorFacility.active_from.is_(None) | (DoctorFacility.active_from <= day)),
                            (DoctorFacility.active_to.is_(None) | (DoctorFacility.active_to >= day)),
                        )
                    )
                ).first()
                if not linked:
                    continue
                exists = (
                    await db.execute(
                        select(ConsultationSession.id).where(
                            ConsultationSession.doctor_id == rule.doctor_id,
                            ConsultationSession.session_date == day,
                            ConsultationSession.period == rule.period,
                        )
                    )
                ).first()
                if exists:
                    continue
                shift_start = datetime.combine(day, rule.start_time, VN_TZ).astimezone(UTC)
                shift_end = shift_start + timedelta(minutes=rule.slot_count * rule.slot_minutes)
                overlap = (
                    await db.execute(
                        select(DoctorSchedule.id)
                        .where(
                            DoctorSchedule.doctor_id == rule.doctor_id,
                            DoctorSchedule.status != "cancelled",
                            DoctorSchedule.starts_at < shift_end,
                            DoctorSchedule.ends_at > shift_start,
                        )
                        .limit(1)
                    )
                ).first()
                if overlap:
                    raise ConflictError(
                        "SCHEDULE_OVERLAP", f"Bác sĩ đã có lịch trùng ngày {day.isoformat()} ({rule.period})"
                    )
                session = ConsultationSession(
                    weekly_shift_id=rule.id,
                    doctor_id=rule.doctor_id,
                    facility_id=rule.facility_id,
                    session_date=day,
                    period=rule.period,
                )
                db.add(session)
                await db.flush()
                local_start = datetime.combine(day, rule.start_time, VN_TZ)
                for ordinal in range(1, rule.slot_count + 1):
                    start = local_start + timedelta(minutes=(ordinal - 1) * rule.slot_minutes)
                    schedule = DoctorSchedule(
                        doctor_id=rule.doctor_id,
                        facility_id=rule.facility_id,
                        starts_at=start.astimezone(UTC),
                        ends_at=(start + timedelta(minutes=rule.slot_minutes)).astimezone(UTC),
                        capacity=1,
                        status="blocked",
                        source_system="coordinator",
                        external_schedule_id=f"{session.id}:{ordinal}",
                        created_by=staff.id,
                    )
                    db.add(schedule)
                    await db.flush()
                    db.add(ConsultationSlot(session_id=session.id, schedule_id=schedule.id, ordinal=ordinal))
                created += 1
    return success_response({"sessions_created": created}, "Sessions published")


@staff_router.get("/requests")
async def staff_requests(_: User = Depends(require_staff), db: AsyncSession = Depends(get_db_session)):
    rows = (
        await db.execute(
            select(ConsultationRequest, ConsultationSession, User, DoctorSchedule, Doctor, Facility, Service, Specialty)
            .join(ConsultationSession, ConsultationSession.id == ConsultationRequest.session_id)
            .join(User, User.id == ConsultationRequest.patient_id)
            .join(Doctor, Doctor.id == ConsultationSession.doctor_id)
            .join(Facility, Facility.id == ConsultationSession.facility_id)
            .join(Service, Service.id == ConsultationRequest.service_id)
            .join(Specialty, Specialty.id == ConsultationRequest.specialty_id)
            .outerjoin(ConsultationSlot, ConsultationSlot.id == ConsultationRequest.assigned_slot_id)
            .outerjoin(DoctorSchedule, DoctorSchedule.id == ConsultationSlot.schedule_id)
            .order_by(ConsultationRequest.created_at.desc())
            .limit(200)
        )
    ).all()
    session_ids = {session.id for _, session, *_ in rows}
    all_slots = (
        (
            await db.execute(
                select(ConsultationSlot, DoctorSchedule)
                .join(DoctorSchedule, DoctorSchedule.id == ConsultationSlot.schedule_id)
                .where(ConsultationSlot.session_id.in_(session_ids))
                .order_by(ConsultationSlot.ordinal)
            )
        ).all()
        if session_ids
        else []
    )
    occupied_ids = (
        set(
            (
                await db.execute(
                    select(ConsultationRequest.assigned_slot_id).where(
                        ConsultationRequest.session_id.in_(session_ids),
                        ConsultationRequest.status == "confirmed",
                        ConsultationRequest.assigned_slot_id.is_not(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        if session_ids
        else set()
    )
    slots_by_session: dict[UUID, list[dict]] = {}
    now = datetime.now(UTC)
    for slot, schedule in all_slots:
        slots_by_session.setdefault(slot.session_id, []).append(
            {
                "id": str(slot.id),
                "starts_at": schedule.starts_at.isoformat(),
                "ends_at": schedule.ends_at.isoformat(),
                "available": slot.id not in occupied_ids and schedule.status == "blocked" and schedule.starts_at > now,
            }
        )
    result = []
    for item, session, patient, assigned, doctor, facility, service, specialty in rows:
        value = _request_dict(item, session, patient, assigned)
        value.update(
            {
                "doctor_name": doctor.full_name,
                "facility_name": facility.name,
                "service_name": service.name,
                "specialty_name": specialty.name,
                "slots": slots_by_session.get(session.id, []),
            }
        )
        result.append(value)
    return success_response(result, "Coordinator requests")


@staff_router.post("/requests/{request_id}/assign")
async def assign_request(request_id: UUID, payload: DecisionInput, staff: User = Depends(require_staff)):
    raise ConflictError("USE_WORKBENCH", "Chốt lịch qua bàn điều phối sau khi xác minh cọc.")


@staff_router.post("/requests/{request_id}/reject")
async def reject_request(request_id: UUID, payload: DecisionInput, staff: User = Depends(require_staff)):
    raise ConflictError("USE_WORKBENCH_REJECT", "Đóng phiếu qua bàn điều phối để xử lý cọc và lịch sử.")
