"""Staff agent tool adapters; business operations remain in service/repository layers."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.staff_agent_cache import (
    cached_case_results,
    cached_profile,
    profile_version,
    store_case_results,
    store_profile,
)
from src.agents.staff_agent_runtime import current_session
from src.agents.staff_guardrails import _normalize_staff_input
from src.core.exceptions import AuthorizationError, NotFoundError
from src.models.doctor import Doctor
from src.models.facility import Facility
from src.models.service import Service
from src.models.specialty import Specialty
from src.models.user import User
from src.repositories.staff_agent import StaffAgentRepository
from src.schemas.staff_agent_query import StaffQueryPlan, StaffQuerySubject
from src.schemas.workbench import CaseBookingInput
from src.services.booking import BookingService
from src.services.catalog import CatalogService
from src.services.staff_agent_query import StaffAgentQueryService
from src.services.staff_patient import StaffPatientService


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _staff_local_time(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware_value = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware_value.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat()


def build_staff_tools(
    staff: User,
    *,
    session: AsyncSession,
    patient_service: StaffPatientService,
    repository: StaffAgentRepository,
    query_service: StaffAgentQueryService,
    pending_action_ref: list[dict | None] | None = None,
    facility_scope: str = "",
    force_emergency_cases: bool = False,
    force_agent_consulting_cases: bool = False,
    force_submitted_exam_forms: bool = False,
    continue_case_booking_after_claim: bool = False,
    forced_booking_date: dict[str, str] | None = None,
) -> list[Any]:
    if staff.role != "staff":
        raise AuthorizationError()

    def active_session() -> AsyncSession:
        return current_session(session)

    def active_patient_service() -> StaffPatientService:
        current = active_session()
        return patient_service if current is session else StaffPatientService(current)

    def active_repository() -> StaffAgentRepository:
        current = active_session()
        return repository if current is session else StaffAgentRepository(current)

    def active_booking_service() -> BookingService:
        return BookingService(active_session())

    @tool
    async def search_staff_patients(query: str, limit: int = 10) -> str:
        """Tìm bệnh nhân theo tên, email hoặc số điện thoại; chỉ trả các trường danh sách cho phép."""
        patients, total = await active_patient_service().search(
            query=query.strip(),
            status=None,
            gender=None,
            created_from=None,
            created_to=None,
            offset=0,
            limit=max(1, min(limit, 10)),
        )
        return _json(
            {
                "items": [
                    {
                        "id": str(p.id),
                        "full_name": p.full_name,
                        "status": p.status,
                        "gender": p.gender,
                        "created_at": p.created_at,
                    }
                    for p in patients
                ],
                "total": total,
                "more_available": total > len(patients),
            }
        )

    @tool
    async def get_staff_patient_profile(patient_id: str) -> str:
        """Đọc hồ sơ bệnh nhân đã chọn, gồm hồ sơ người thân liên kết và thông tin sức khỏe allowlist."""
        patient_uuid = UUID(patient_id)
        cached = await cached_profile(patient_uuid, staff.id, facility_scope)
        if cached is not None:
            return _json(cached)
        version = await profile_version(patient_uuid)
        profile = await active_patient_service().get_agent_detail(patient_uuid)
        result = profile.model_dump(mode="json")
        await store_profile(patient_uuid, staff.id, facility_scope, result, version)
        return _json(result)

    @tool
    async def search_staff_bookings(
        query: str = "", status: str = "", selected_date: str = "", service_id: str = "", limit: int = 10
    ) -> str:
        """Tra cứu booking; `booking_created_at` là ngày đặt, appointment_start/end là giờ hẹn, `status` là trạng thái đã lưu."""
        if forced_booking_date and forced_booking_date.get("booking_status"):
            status = forced_booking_date["booking_status"]
        if not forced_booking_date and not any(value.strip() for value in (query, status, selected_date, service_id)):
            return _json(
                {"needs_refinement": True, "message": "Hãy cung cấp tên/mã lịch, trạng thái, ngày hoặc dịch vụ."}
            )
        if status.strip() and status.strip() not in {
            "pending",
            "pending_approval",
            "confirmed",
            "rejected",
            "cancelled",
            "attended",
        }:
            return _json({"needs_refinement": True, "message": "Trạng thái lịch không hợp lệ."})
        try:
            service_uuid = UUID(service_id) if service_id.strip() else None
        except ValueError:
            return _json({"needs_refinement": True, "message": "Ngày hoặc mã dịch vụ không hợp lệ."})
        if forced_booking_date:
            selected_date = forced_booking_date.get("booking_date", "")
            date_field = forced_booking_date["booking_date_field"]
            date_from = forced_booking_date.get("booking_date_from", "")
            date_to = forced_booking_date.get("booking_date_to", "")
        else:
            date_field = "starts_at"
            date_from = date_to = ""
        try:
            selected = date.fromisoformat(selected_date) if selected_date.strip() else None
            selected_from = date.fromisoformat(date_from) if date_from else None
            selected_to = date.fromisoformat(date_to) if date_to else None
        except ValueError:
            return _json({"needs_refinement": True, "message": "Ngày không hợp lệ."})
        values, total, _, triage = await active_booking_service().list_for_staff(
            status.strip() or None,
            selected,
            0,
            max(1, min(limit, 10)),
            query.strip() or None,
            service_uuid,
            date_field=date_field,
            include_cancelled=True,
            date_from=selected_from,
            date_to=selected_to,
        )
        return _json(
            {
                "items": [_booking_summary(item, triage.get(item.id)) for item in values],
                "total": total,
                "more_available": total > len(values),
                "checked_date": selected.isoformat() if selected else None,
                "checked_from": selected_from.isoformat() if selected_from else None,
                "checked_to_exclusive": selected_to.isoformat() if selected_to else None,
                "date_field": date_field if selected or selected_from else None,
                "checked_status": status.strip() or None,
            }
        )

    @tool
    async def get_staff_booking(booking_id: str) -> str:
        """Đọc một lịch khám và assessment triage đã lưu nếu có; không đánh giá lại mức nguy cấp."""
        booking = await active_booking_service().get_for_staff(UUID(booking_id))
        triage = await active_booking_service().get_staff_ai_triage(booking.id)
        return _json(_booking_summary(booking, triage))

    @tool
    async def search_staff_doctors(
        doctor_name: str = "", specialty: str = "", facility: str = "", service: str = "", limit: int = 10
    ) -> str:
        """Tra cứu bác sĩ theo tên, chuyên khoa, cơ sở hoặc dịch vụ trong phạm vi được cấp quyền."""
        terms = [value.strip() for value in (doctor_name, specialty, facility, service) if value.strip()]
        if not terms:
            return _json(
                {"needs_refinement": True, "message": "Hãy cung cấp tên bác sĩ, chuyên khoa, cơ sở hoặc dịch vụ."}
            )
        doctors, facility_ids = await active_repository().search_scoped_doctors(
            staff.id,
            doctor_name=doctor_name.strip() or None,
            specialty=specialty.strip() or None,
            facility=facility.strip() or None,
            service=service.strip() or None,
            limit=max(1, min(limit, 10)) + 1,
        )
        today = date.today()
        result_limit = max(1, min(limit, 10))
        more_available = len(doctors) > result_limit
        doctors = doctors[:result_limit]
        items = []
        for doctor in doctors:
            specialties = [
                item.specialty.name
                for item in doctor.specialties
                if item.specialty and item.specialty.status == "active"
            ]
            facilities = [
                {"id": str(item.facility.id), "name": item.facility.name}
                for item in doctor.facilities
                if item.facility
                and item.facility.status == "active"
                and (not facility_ids or item.facility_id in facility_ids)
                and (item.active_from is None or item.active_from <= today)
                and (item.active_to is None or item.active_to >= today)
            ]
            services = [
                item.service.name
                for item in doctor.services
                if item.active and item.service and item.service.status == "active"
            ]
            items.append(
                {
                    "id": str(doctor.id),
                    "name": doctor.full_name,
                    "title": doctor.title,
                    "specialties": specialties,
                    "facilities": facilities,
                    "services": services,
                }
            )
        return _json({"items": items, "count": len(items), "limit": result_limit, "more_available": more_available})

    @tool
    async def search_staff_availability(
        starts_from: str,
        starts_to: str,
        doctor_name: str = "",
        specialty: str = "",
        facility: str = "",
        service: str = "",
        limit: int = 10,
    ) -> str:
        """Tìm lịch tương lai còn chỗ; bắt buộc có khoảng thời gian và tên bác sĩ hoặc chuyên khoa."""
        if not doctor_name.strip() and not specialty.strip():
            return _json({"needs_refinement": True, "message": "Hãy cung cấp tên bác sĩ hoặc chuyên khoa."})
        try:
            start = datetime.fromisoformat(starts_from.replace("Z", "+00:00"))
            end = datetime.fromisoformat(starts_to.replace("Z", "+00:00"))
        except ValueError:
            return _json({"needs_refinement": True, "message": "Khoảng thời gian cần ở định dạng ISO-8601."})
        now = datetime.now(UTC)
        if (
            start.tzinfo is None
            or end.tzinfo is None
            or start < now
            or end <= start
            or end - start > timedelta(days=31)
        ):
            return _json(
                {"needs_refinement": True, "message": "Hãy chọn khoảng thời gian tương lai không quá 31 ngày."}
            )
        doctors, scope_ids = await active_repository().search_scoped_doctors(
            staff.id,
            doctor_name=doctor_name.strip() or None,
            specialty=specialty.strip() or None,
            facility=facility.strip() or None,
            service=service.strip() or None,
            limit=21,
        )
        more_doctors = len(doctors) > 20
        doctors = doctors[:20]
        if doctor_name.strip() and len(doctors) > 1:
            return _json({"needs_clarification": True, "matches": [item.full_name for item in doctors[:10]]})
        if not doctors:
            return _json(
                {
                    "items": [],
                    "count": 0,
                    "more_available": more_doctors,
                    "checked_from": start,
                    "checked_to": end,
                }
            )
        doctor_ids = [item.id for item in doctors]
        facility_ids = set(scope_ids)
        if facility.strip():
            matching_facilities = {
                item.facility_id
                for doctor in doctors
                for item in doctor.facilities
                if item.facility
                and item.facility.status == "active"
                and (
                    facility.strip().casefold() in item.facility.name.casefold()
                    or facility.strip().casefold() in item.facility.code.casefold()
                )
                and (not scope_ids or item.facility_id in scope_ids)
                and (item.active_from is None or item.active_from <= date.today())
                and (item.active_to is None or item.active_to >= date.today())
            }
            if len(matching_facilities) > 1:
                return _json(
                    {
                        "needs_clarification": True,
                        "message": "Có nhiều cơ sở phù hợp; vui lòng chọn chính xác cơ sở.",
                    }
                )
            facility_ids = matching_facilities
        elif not facility_ids:
            facility_ids = {
                item.facility_id
                for doctor in doctors
                for item in doctor.facilities
                if item.facility
                and item.facility.status == "active"
                and (item.active_from is None or item.active_from <= date.today())
                and (item.active_to is None or item.active_to >= date.today())
            }
        schedules = []
        catalog = CatalogService(active_session())
        result_limit = max(1, min(limit, 10))
        for doctor_id in doctor_ids:
            for facility_id in sorted(facility_ids, key=str):
                doctor = next(item for item in doctors if item.id == doctor_id)
                service_ids = (
                    [
                        item.service_id
                        for item in doctor.services
                        if item.active
                        and item.service
                        and item.service.status == "active"
                        and service.strip().casefold() in item.service.name.casefold()
                    ]
                    if service.strip()
                    else [None]
                )
                for service_id in service_ids:
                    rows = await catalog.list_schedules(
                        doctor_id=doctor_id,
                        facility_id=facility_id,
                        service_id=service_id,
                        starts_from=start,
                        starts_to=end,
                        public_only=True,
                        offset=0,
                        limit=max(1, result_limit + 1 - len(schedules)),
                    )
                    schedules.extend(item for item in rows if item.starts_at >= start)
                    if len(schedules) >= result_limit + 1:
                        break
                if len(schedules) >= result_limit + 1:
                    break
            if len(schedules) >= max(1, min(limit, 10)):
                break
        items = [
            {
                "schedule_id": str(item.id),
                "doctor_id": str(item.doctor_id),
                "doctor": item.doctor.full_name,
                "facility_id": str(item.facility_id),
                "facility": item.facility.name,
                "service_id": str(item.service_id) if item.service_id else None,
                "service": item.service.name if item.service else None,
                "specialties": [
                    {"id": str(link.specialty.id), "name": link.specialty.name}
                    for link in next(doctor for doctor in doctors if doctor.id == item.doctor_id).specialties
                    if link.specialty and link.specialty.status == "active"
                ],
                "starts_at": _staff_local_time(item.starts_at),
                "ends_at": _staff_local_time(item.ends_at),
                "remaining_capacity": item.capacity,
            }
            for item in schedules
        ]
        return _json(
            {
                "items": items[:result_limit],
                "count": min(len(items), result_limit),
                "more_available": len(items) > result_limit or more_doctors,
                "checked_from": start,
                "checked_to": end,
            }
        )

    @tool(args_schema=StaffQueryPlan)
    async def query_staff_operations(
        subject: StaffQuerySubject,
        select: list[str],
        filters: list[dict],
        sort: list[dict] | None = None,
        limit: int = 10,
    ) -> str:
        """Tra cứu câu hỏi vận hành chưa có công cụ riêng bằng kế hoạch trường/điều kiện allowlist; chỉ đọc."""
        try:
            plan = StaffQueryPlan.model_validate(
                {"subject": subject, "select": select, "filters": filters, "sort": sort or [], "limit": limit}
            )
        except ValidationError:
            return _json(
                {"needs_refinement": True, "message": "Kế hoạch tra cứu không hợp lệ; hãy làm rõ dữ liệu cần tìm."}
            )
        facility_ids = await active_repository().get_staff_facility_scope(staff.id)
        if plan.subject == StaffQuerySubject.CASE_OPERATIONS and not facility_ids:
            # Empty scope follows the existing coordinator case policy (all authorized facilities).
            pass
        return _json(await query_service.query(staff.id, facility_ids, plan))

    @tool
    async def prepare_booking_review(
        booking_id: str,
        decision: Literal["confirmed", "rejected"],
        reason: str = "",
    ) -> str:
        """Tạo đề xuất sau yêu cầu review rõ ràng của staff.

        `confirmed` đồng ý duyệt, `rejected` từ chối. Lý do tùy chọn khi duyệt,
        bắt buộc khi từ chối. Chỉ đọc, chưa cập nhật booking.
        """
        if decision not in {"confirmed", "rejected"}:
            return _json({"available": False, "message": "Quyết định không hợp lệ."})
        if decision == "rejected" and not reason.strip():
            return _json({"available": False, "message": "Cần có lý do từ chối."})
        booking = await active_booking_service().get_for_staff(UUID(booking_id))
        if booking.status != "pending_approval":
            return _json({"available": False, "message": "Lịch không còn chờ duyệt."})
        triage = await active_booking_service().get_staff_ai_triage(booking.id)
        action = {
            "id": str(uuid4()),
            "booking_id": str(booking.id),
            "decision": decision,
            "reason": reason.strip() or None,
            "booking_summary": _booking_summary(booking, triage),
            "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "state": "pending",
        }
        if pending_action_ref is not None:
            pending_action_ref[0] = action
        return _json({key: value for key, value in action.items() if key != "state"})

    @tool
    async def search_staff_cases(
        query: str = "",
        status: str = "",
        sla_state: str = "any",
        assigned_to_me: bool = False,
        received_today: bool = False,
        emergency_only: bool = False,
        agent_consulting: bool = False,
        submitted_exam_forms: bool = False,
        limit: int = 10,
    ) -> str:
        """Tìm ca trong phạm vi cơ sở; mặc định chỉ trả ca chưa được tiếp nhận. received_today lọc ngày Việt Nam."""
        emergency_only = emergency_only or force_emergency_cases
        agent_consulting = agent_consulting or force_agent_consulting_cases
        submitted_exam_forms = submitted_exam_forms or force_submitted_exam_forms
        if not any(
            (
                query.strip(),
                status.strip(),
                sla_state != "any",
                assigned_to_me,
                received_today,
                emergency_only,
                agent_consulting,
                submitted_exam_forms,
            )
        ):
            return _json(
                {
                    "needs_refinement": True,
                    "message": "Hãy cung cấp tên bệnh nhân, trạng thái, bộ lọc SLA hoặc người phụ trách.",
                }
            )
        if sla_state not in {"any", "overdue", "on_track"}:
            return _json({"needs_refinement": True, "message": "Bộ lọc SLA không hợp lệ."})
        result_limit = max(1, min(limit, 10))
        cache_type = (
            "agent_consulting"
            if force_agent_consulting_cases and not force_submitted_exam_forms
            else "submitted_exam_forms"
            if force_submitted_exam_forms and not force_agent_consulting_cases
            else None
        )
        cacheable = cache_type is not None and not any(
            (
                query.strip(),
                status.strip(),
                sla_state != "any",
                assigned_to_me,
                received_today,
                emergency_only,
            )
        )
        if cacheable:
            cached = await cached_case_results(staff.id, facility_scope, cache_type, result_limit)
            if cached is not None:
                return _json(cached)
        rows = await active_repository().search_scoped_cases(
            staff.id,
            query.strip() or None,
            result_limit + 1,
            status=status.strip() or None,
            sla_state=sla_state,
            assigned_to_me=assigned_to_me,
            received_today=received_today,
            emergency_only=emergency_only,
            agent_consulting=agent_consulting,
            submitted_exam_forms=submitted_exam_forms,
        )
        result = {
            "items": [_case_summary(item) for item in rows[:result_limit]],
            "count": min(len(rows), result_limit),
            "more_available": len(rows) > result_limit,
        }
        if cacheable:
            await store_case_results(staff.id, facility_scope, cache_type, result_limit, result)
        return _json(result)

    @tool
    async def get_staff_case(case_id: str) -> str:
        """Đọc một ca hỗ trợ/HITL trong phạm vi cơ sở được cấp quyền, cùng snapshot triage đã lưu."""
        case = await active_repository().get_scoped_case(staff.id, UUID(case_id))
        if case is None:
            raise NotFoundError("Case not found")
        return _json(_case_summary(case))

    @tool
    async def prepare_case_claim(case_id: str) -> str:
        """Chuẩn bị nhận một ca điều phối theo yêu cầu rõ ràng; chỉ đổi trạng thái sau khi coordinator xác nhận."""
        case = await active_repository().get_scoped_case(staff.id, UUID(case_id))
        if case is None:
            raise NotFoundError("Case not found")
        if case.status in {"completed", "cancelled"}:
            return _json({"available": False, "message": "Ca đã đóng."})
        if case.assigned_to == staff.id:
            return _json({"available": False, "message": "Ca này đã do bạn tiếp nhận."})
        if case.assigned_to:
            return _json({"available": False, "message": "Ca đã được điều phối viên khác tiếp nhận."})
        action = {
            "id": str(uuid4()),
            "kind": "case_claim",
            "case_id": str(case.id),
            "version": case.version,
            "case_summary": _case_summary(case),
            "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "state": "pending",
        }
        if continue_case_booking_after_claim:
            action["continue_to_booking"] = True
        if pending_action_ref is not None:
            pending_action_ref[0] = action
        return _json({key: value for key, value in action.items() if key != "state"})

    @tool
    async def prepare_case_booking(
        case_id: str,
        schedule_id: str,
        specialty_id: str,
        service_id: str = "",
        reason: str = "",
        patient_note: str = "",
        encounter_type: str = "in_person",
    ) -> str:
        """Chuẩn bị booking từ slot đã công bố cho ca bạn đã nhận; cần coordinator xác nhận và xác nhận bệnh nhân đồng ý."""
        from types import SimpleNamespace

        from src.services import workbench

        case = await active_repository().get_scoped_case(staff.id, UUID(case_id))
        if case is None:
            raise NotFoundError("Case not found")
        if case.assigned_to != staff.id:
            return _json({"available": False, "message": "Bạn cần tiếp nhận ca trước khi tạo booking."})
        if case.booking_id or case.status in {"completed", "cancelled"}:
            return _json({"available": False, "message": "Ca đã đóng hoặc đã có booking."})
        if case.priority == 0 or (case.ai_snapshot or {}).get("is_emergency"):
            return _json(
                {"available": False, "message": "Ca cấp cứu cần xử lý theo quy trình cấp cứu, không tạo booking."}
            )
        patient = case.patient if isinstance(case.patient, dict) else {}
        if case.patient_id is None and (not patient.get("name") or not (patient.get("phone") or patient.get("email"))):
            return _json(
                {
                    "available": False,
                    "needs_refinement": True,
                    "message": "Ca khách cần có họ tên và số điện thoại hoặc email.",
                }
            )
        try:
            payload = CaseBookingInput.model_validate(
                {
                    "version": case.version,
                    "schedule_id": schedule_id,
                    "specialty_id": specialty_id,
                    "service_id": service_id or None,
                    "reason": reason,
                    "patient_note": patient_note or None,
                    "encounter_type": encounter_type,
                    "patient_agreed": False,
                    "patient_name": patient.get("name") if case.patient_id is None else None,
                    "patient_email": (patient.get("email") or None) if case.patient_id is None else None,
                    "patient_phone": (patient.get("phone") or None) if case.patient_id is None else None,
                    "patient_date_of_birth": patient.get("date_of_birth") if case.patient_id is None else None,
                    "patient_gender": patient.get("gender") if case.patient_id is None else None,
                }
            )
        except (ValueError, TypeError) as exc:
            return _json({"available": False, "needs_refinement": True, "message": str(exc)[:300]})
        member_scope = await active_repository().get_staff_facility_scope(staff.id)
        schedule = await workbench.validate_plan(
            active_session(),
            case,
            SimpleNamespace(
                schedule_id=payload.schedule_id,
                specialty_id=payload.specialty_id,
                service_id=payload.service_id,
            ),
            SimpleNamespace(facility_ids=[str(value) for value in member_scope]),
        )
        doctor = await active_session().get(Doctor, schedule.doctor_id)
        facility = await active_session().get(Facility, schedule.facility_id)
        specialty = await active_session().get(Specialty, payload.specialty_id)
        service = await active_session().get(Service, payload.service_id) if payload.service_id else None
        action = {
            "id": str(uuid4()),
            "kind": "case_booking",
            "case_id": str(case.id),
            "version": case.version,
            "booking_payload": payload.model_dump(mode="json"),
            "booking_summary": {
                "patient_name": patient.get("name"),
                "doctor_name": doctor.full_name if doctor else None,
                "facility": facility.name if facility else None,
                "specialty": specialty.name if specialty else None,
                "service": service.name if service else "Khám riêng",
                "appointment_start": _staff_local_time(schedule.starts_at),
                "appointment_end": _staff_local_time(schedule.ends_at),
                "reason": payload.reason,
            },
            "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
            "state": "pending",
        }
        if pending_action_ref is not None:
            pending_action_ref[0] = action
        return _json({key: value for key, value in action.items() if key != "state"})

    @tool
    async def search_approved_staff_procedures(query: str) -> str:
        """Tra cứu quy trình nội bộ đã được duyệt; trích dẫn tài liệu và điều khoản liên quan."""
        sop_dir = Path(__file__).resolve().parents[3] / "data" / "sop"
        if not sop_dir.is_dir():
            return _json({"available": False, "message": "Chưa có kho quy trình nội bộ được duyệt."})

        cleaned = _normalize_staff_input(query).strip()
        if not cleaned:
            return _json({"needs_refinement": True, "message": "Vui lòng nhập nội dung quy trình cần tra cứu."})

        stop_words = {
            "thu",
            "tuc",
            "quy",
            "trinh",
            "ve",
            "cho",
            "cua",
            "va",
            "theo",
            "toi",
            "la",
            "mua",
            "sam",
            "may",
            "bay",
        }
        query_terms = set(cleaned.split()) - stop_words
        if not query_terms:
            return _json(
                {
                    "available": True,
                    "matches": [],
                    "message": f"Không tìm thấy quy trình nội bộ phù hợp với từ khóa '{query}'.",
                }
            )
        results = []
        for file in sorted(sop_dir.glob("*.md")):
            try:
                content = file.read_text(encoding="utf-8")
            except OSError:
                continue

            normalized_content = _normalize_staff_input(content)
            content_terms = set(normalized_content.split())
            matched_terms = query_terms & content_terms
            score = len(matched_terms)
            if score >= 2 or any(len(term) >= 7 for term in matched_terms):
                lines = content.splitlines()
                title = lines[0].lstrip("# ").strip() if lines else file.stem
                citation = next(
                    (line.split(":", 1)[1].strip() for line in lines if "Mã tài liệu" in line),
                    file.stem,
                )
                sections = [sec.strip() for sec in content.split("## ") if sec.strip()]
                relevant = [sec[:800] for sec in sections if matched_terms & set(_normalize_staff_input(sec).split())]
                excerpt = "\n\n".join(relevant[:2]) if relevant else content[:800]
                results.append(
                    {
                        "document": title,
                        "citation": citation,
                        "excerpt": excerpt,
                        "match_score": score,
                    }
                )

        if not results:
            return _json(
                {
                    "available": True,
                    "matches": [],
                    "message": f"Không tìm thấy quy trình nội bộ phù hợp với từ khóa '{query}'.",
                }
            )

        results.sort(key=lambda item: item["match_score"], reverse=True)
        return _json(
            {
                "available": True,
                "matches": [
                    {
                        "document": item["document"],
                        "citation": item["citation"],
                        "excerpt": item["excerpt"],
                    }
                    for item in results[:3]
                ],
                "total": len(results),
            }
        )

    tools = [
        search_staff_patients,
        get_staff_patient_profile,
        search_staff_bookings,
        get_staff_booking,
        prepare_booking_review,
        search_staff_cases,
        get_staff_case,
        prepare_case_claim,
        prepare_case_booking,
        search_staff_doctors,
        search_staff_availability,
        query_staff_operations,
        search_approved_staff_procedures,
    ]
    patient_tools = {"search_staff_patients", "get_staff_patient_profile"}
    for item in tools:
        item.metadata = {
            **(item.metadata or {}),
            "parallel_safe": item.name not in {"prepare_booking_review", "prepare_case_claim", "prepare_case_booking"},
            "database": "auth" if item.name in patient_tools else "application",
        }
    return tools


def _booking_summary(booking: Any, triage: dict | None) -> dict[str, Any]:
    patient = booking.user
    selected_profile = booking.patient_profile
    doctor = booking.doctor
    triage_fields = (
        "is_emergency",
        "urgency_tier",
        "ats_level",
        "acuity_status",
        "disposition",
        "suggested_department_name",
        "suggested_department_code",
        "captured_at",
        "source",
    )
    saved_triage = {key: triage[key] for key in triage_fields if triage and triage.get(key) is not None}
    return {
        "id": str(booking.id),
        "status": booking.status,
        "source_schedule_status": booking.schedule.status if booking.schedule else None,
        "appointment_schedule_status": (booking.appointment_schedule.status if booking.appointment_schedule else None),
        "patient_name": selected_profile.full_name if selected_profile else patient.full_name if patient else None,
        "booking_created_at": _staff_local_time(booking.created_at),
        "appointment_start": _staff_local_time(booking.starts_at),
        "appointment_end": _staff_local_time(booking.ends_at),
        "doctor_name": doctor.full_name if doctor else None,
        "specialty": booking.specialty.name if booking.specialty else None,
        "service": booking.service.name if booking.service else None,
        "facility": booking.facility.name if booking.facility else None,
        "saved_triage": saved_triage or None,
        "triage_available": bool(saved_triage),
    }


def _case_summary(case: Any) -> dict[str, Any]:
    patient = case.patient if isinstance(case.patient, dict) else {}
    snapshot = case.ai_snapshot if isinstance(case.ai_snapshot, dict) else {}
    plan = case.plan if isinstance(getattr(case, "plan", None), dict) else {}
    allowed = (
        "symptoms",
        "clinical_facts",
        "collected_details",
        "is_emergency",
        "emergency_warning",
        "ats_level",
        "urgency_tier",
        "acuity_status",
        "disposition",
        "suggested_department_name",
        "suggested_department_code",
        "workflow_status",
        "captured_at",
    )
    saved_triage = {key: snapshot[key] for key in allowed if snapshot.get(key) is not None}
    return {
        "id": str(case.id),
        "source": getattr(case, "source", None),
        "status": case.status,
        "control": getattr(case, "control", None),
        "priority": case.priority,
        "patient_name": patient.get("name"),
        "booking_id": str(case.booking_id) if case.booking_id else None,
        "facility_id": str(case.facility_id) if case.facility_id else None,
        "assigned_to": str(case.assigned_to) if case.assigned_to else None,
        "created_at": case.created_at,
        "patient_request": {
            key: patient[key]
            for key in ("notes", "preferred_date", "preferred_period", "facility_preference")
            if patient.get(key) is not None
        },
        "saved_triage": saved_triage or None,
        "triage_available": bool(saved_triage),
        "plan": {
            key: plan[key]
            for key in (
                "specialty_name",
                "service_name",
                "doctor_name",
                "facility_name",
                "starts_at",
                "ends_at",
                "reason",
            )
            if plan.get(key) is not None
        },
    }
