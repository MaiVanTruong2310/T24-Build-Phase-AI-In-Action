"""Package booking endpoints for health packages and pathways."""

import re
from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_optional_user, require_patient
from src.api.dependencies import require_coordination_admin as require_staff
from src.api.response import success_response
from src.core.exceptions import ConflictError, NotFoundError
from src.db.dependencies import get_db_session
from src.models.facility import Facility
from src.models.package_request import PackageRequest
from src.models.service import Service
from src.models.user import User

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
router = APIRouter(prefix="/packages", tags=["packages"])
staff_router = APIRouter(prefix="/staff/packages", tags=["staff-packages"])


class PackageRequestInput(BaseModel):
    patient_profile_id: UUID | None = None
    service_id: UUID
    facility_id: UUID
    preferred_date: date
    preferred_period: str = Field(default="morning", pattern="^(morning|afternoon)$")
    note: str | None = Field(default=None, max_length=2000)

    # Guest fields
    patient_name: str | None = Field(default=None, max_length=120)
    patient_phone: str | None = Field(default=None, max_length=20)
    patient_email: str | None = Field(default=None, max_length=320)
    gender: str | None = Field(default=None, pattern="^(male|female|other|prefer_not_to_say)$")
    date_of_birth: date | None = None
    consent_to_contact: bool = True
    guardian_name: str | None = Field(default=None, max_length=120)
    guardian_phone: str | None = Field(default=None, max_length=20)


class StaffPackageStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|contacted|confirmed|cancelled|completed)$")
    staff_note: str | None = Field(default=None, max_length=2000)


def _package_request_dict(
    item: PackageRequest, service: Service | None = None, facility: Facility | None = None, patient: User | None = None
) -> dict:
    return {
        "id": str(item.id),
        "service_id": str(item.service_id),
        "service_name": service.name if service else None,
        "service_price": float(service.price) if service and service.price is not None else None,
        "facility_id": str(item.facility_id),
        "facility_name": facility.name if facility else None,
        "preferred_date": item.preferred_date.isoformat(),
        "preferred_period": item.preferred_period,
        "status": item.status,
        "note": item.note,
        "staff_note": item.staff_note,
        "patient_id": str(item.patient_id) if item.patient_id else None,
        "patient_name": item.patient_name or (patient.full_name if patient else None),
        "patient_phone": item.patient_phone or (patient.phone if patient else None),
        "patient_email": item.patient_email or (patient.email if patient else None),
        "gender": item.gender or (patient.gender if patient else None),
        "date_of_birth": (item.date_of_birth or (patient.date_of_birth if patient else None)).isoformat()
        if (item.date_of_birth or (patient and patient.date_of_birth))
        else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@router.post("/requests", status_code=status.HTTP_201_CREATED)
async def create_package_request(
    payload: PackageRequestInput,
    http_request: Request,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Register for a health package / pathway."""
    async with db.begin():
        from src.services.patient_profiles import resolve_booking_payload

        target, profile = await resolve_booking_payload(db, user, payload)
        from src.medical_assistant.domain.booking_request_service import PHONE_PATTERN, _is_minor

        if payload.consent_to_contact is False and not user:
            raise ConflictError("CONSENT_REQUIRED", "Cần đồng ý để điều phối viên liên hệ và xử lý phiếu.")
        patient_name = (
            payload.patient_name
            or (target.full_name if target else "")
            or (user.full_name if user else "")
            or (user.email.split("@")[0] if user and user.email else "")
        ).strip()
        if len(patient_name) < 2:
            raise ConflictError("NAME_REQUIRED", "Vui lòng nhập họ và tên người khám (tối thiểu 2 ký tự)")
        phone_raw = (
            payload.patient_phone
            or (profile.contact_phone if profile else None)
            or (target.phone if target else "")
            or (user.phone if user else "")
        )
        clean_phone = re.sub(r"[\s.()-]", "", phone_raw or "")
        if not PHONE_PATTERN.fullmatch(clean_phone):
            raise ConflictError("INVALID_PHONE", "Số điện thoại chưa đúng định dạng Việt Nam")
        gender = (
            payload.gender
            or (target.gender if target and target.gender in ("male", "female", "other", "prefer_not_to_say") else None)
            or (user.gender if user and user.gender in ("male", "female", "other", "prefer_not_to_say") else None)
            or "prefer_not_to_say"
        )
        dob = (
            payload.date_of_birth
            or (target.date_of_birth if target else None)
            or (user.date_of_birth if user else None)
        )
        if not dob and user:
            dob = date(2000, 1, 1)
        if not dob:
            raise ConflictError("DOB_REQUIRED", "Vui lòng chọn ngày sinh")
        if dob > datetime.now(VN_TZ).date():
            raise ConflictError("INVALID_DOB", "Ngày sinh không thể nằm trong tương lai")
        if _is_minor(dob, datetime.now(VN_TZ).date()) and (
            len((payload.guardian_name or "").strip()) < 2
            or not PHONE_PATTERN.fullmatch(re.sub(r"[\s.()-]", "", payload.guardian_phone or ""))
        ):
            raise ConflictError("GUARDIAN_REQUIRED", "Người dưới 18 tuổi cần họ tên và điện thoại người giám hộ.")
        if payload.preferred_date < datetime.now(VN_TZ).date():
            raise ConflictError("DATE_INVALID", "Ngày khám mong muốn không thể nằm trong quá khứ")
        if payload.preferred_date > datetime.now(VN_TZ).date() + timedelta(days=90):
            raise ConflictError("DATE_INVALID", "Chỉ được đặt ngày khám trong 90 ngày tới.")
        if user is None:
            patient = User(
                full_name=patient_name,
                phone=None,
                email=None,
                gender=gender,
                date_of_birth=dob,
                role="patient",
                status="guest",
            )
            db.add(patient)
            await db.flush()
        else:
            patient = target

        service = await db.get(Service, payload.service_id)
        if not service or service.status != "active":
            raise NotFoundError("Gói dịch vụ không tồn tại hoặc tạm ngưng tiếp nhận")

        facility = await db.get(Facility, payload.facility_id)
        if not facility or facility.status != "active":
            raise NotFoundError("Cơ sở bệnh viện không tồn tại hoặc tạm ngưng tiếp nhận")

        item = PackageRequest(
            patient_id=patient.id,
            patient_profile_id=profile.id if profile else None,
            requested_by_user_id=user.id if user else None,
            service_id=service.id,
            facility_id=facility.id,
            preferred_date=payload.preferred_date,
            preferred_period=payload.preferred_period,
            patient_name=patient_name,
            patient_phone=clean_phone,
            patient_email=payload.patient_email.lower().strip() if payload.patient_email else patient.email,
            gender=gender,
            date_of_birth=dob,
            note=payload.note.strip() if payload.note else None,
        )
        db.add(item)
        await db.flush()

        from src.services.workbench import create_source_case

        await create_source_case(
            db, "package", item, patient, user, http_request.state.coordination_guest, payload, facility.id
        )

    return success_response(
        _package_request_dict(item, service, facility, patient),
        "Đăng ký gói khám thành công; điều phối viên sẽ gọi lại để tư vấn lộ trình và xếp lịch",
        201,
    )


@router.get("/requests/mine")
async def list_my_package_requests(
    patient: User = Depends(require_patient),
    db: AsyncSession = Depends(get_db_session),
):
    """List current patient's package requests."""
    stmt = (
        select(PackageRequest, Service, Facility)
        .join(Service, Service.id == PackageRequest.service_id)
        .join(Facility, Facility.id == PackageRequest.facility_id)
        .where((PackageRequest.patient_id == patient.id) | (PackageRequest.requested_by_user_id == patient.id))
        .order_by(desc(PackageRequest.created_at))
    )
    res = await db.execute(stmt)
    items = []
    for pr, s, f in res.all():
        items.append(_package_request_dict(pr, s, f, patient))
    return success_response(items, "Danh sách gói khám đã đăng ký")


class PatientReschedulePackageInput(BaseModel):
    preferred_date: date
    preferred_period: str = Field(default="morning", pattern="^(morning|afternoon)$")
    facility_id: UUID | None = None
    note: str | None = Field(default=None, max_length=2000)


@router.patch("/requests/{request_id}/reschedule")
async def patient_reschedule_package_request(
    request_id: UUID,
    payload: PatientReschedulePackageInput,
    patient: User = Depends(require_patient),
    db: AsyncSession = Depends(get_db_session),
):
    """Patient updates preferred date, session, and optional facility for their package request."""
    async with db.begin():
        stmt = (
            select(PackageRequest, Service, Facility)
            .join(Service, Service.id == PackageRequest.service_id)
            .join(Facility, Facility.id == PackageRequest.facility_id)
            .where(
                PackageRequest.id == request_id,
                (PackageRequest.patient_id == patient.id) | (PackageRequest.requested_by_user_id == patient.id),
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        row = res.first()
        if not row:
            raise NotFoundError("Không tìm thấy đơn đăng ký gói khám")

        pr, s, f = row
        if pr.status == "cancelled":
            raise ConflictError("CANNOT_RESCHEDULE_CANCELLED", "Không thể đổi ngày cho gói khám đã hủy")
        if pr.status == "completed":
            raise ConflictError("CANNOT_RESCHEDULE_COMPLETED", "Không thể đổi ngày cho gói khám đã hoàn tất")

        if payload.facility_id and payload.facility_id != pr.facility_id:
            new_fac = await db.get(Facility, payload.facility_id)
            if not new_fac or new_fac.status != "active":
                raise NotFoundError("Cơ sở y tế không hợp lệ hoặc không hoạt động")
            pr.facility_id = new_fac.id
            f = new_fac

        pr.preferred_date = payload.preferred_date
        pr.preferred_period = payload.preferred_period
        if payload.note and payload.note.strip():
            reason_clean = payload.note.strip()
            pr.note = f"{pr.note or ''}\n[Đổi ngày: {reason_clean}]".strip()

        # Đồng bộ ngày và cơ sở sang ca điều phối tương ứng nếu có
        from src.models.workbench import CoordinationCase

        case_stmt = select(CoordinationCase).where(
            CoordinationCase.source == "package",
            CoordinationCase.source_id == str(request_id),
        )
        case_res = await db.execute(case_stmt)
        linked_case = case_res.scalar_one_or_none()
        if linked_case:
            case_patient = dict(linked_case.patient or {})
            case_patient["preferred_date"] = str(payload.preferred_date)
            case_patient["preferred_period"] = payload.preferred_period
            linked_case.patient = case_patient
            if payload.facility_id:
                linked_case.facility_id = payload.facility_id

    return success_response(_package_request_dict(pr, s, f, patient), "Đổi ngày gói khám thành công")


@staff_router.get("/requests")
async def staff_list_package_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db_session),
):
    """Staff list of all package registration requests."""
    stmt = (
        select(PackageRequest, Service, Facility, User)
        .join(Service, Service.id == PackageRequest.service_id)
        .join(Facility, Facility.id == PackageRequest.facility_id)
        .outerjoin(User, User.id == PackageRequest.patient_id)
        .order_by(desc(PackageRequest.created_at))
        .offset(offset)
        .limit(limit)
    )
    if status_filter:
        stmt = stmt.where(PackageRequest.status == status_filter)

    res = await db.execute(stmt)
    items = []
    for pr, s, f, u in res.all():
        items.append(_package_request_dict(pr, s, f, u))
    return success_response(items, "Danh sách yêu cầu gói khám")


@staff_router.patch("/requests/{request_id}")
async def staff_update_package_request(
    request_id: UUID,
    payload: StaffPackageStatusUpdate,
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db_session),
):
    """Staff update package request status and notes."""
    raise ConflictError("USE_WORKBENCH_PACKAGE", "Cập nhật phiếu qua bàn điều phối.")
