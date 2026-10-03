"""Doctor catalog and assignment endpoints."""

from datetime import date
from uuid import UUID

from fastapi import Depends, Query, status
from sqlalchemy import select, text

from src.api.dependencies import require_staff
from src.api.endpoints.catalog_common import get_catalog_service, router, staff_router
from src.api.response import success_response
from src.models.catalog import Doctor
from src.db.dependencies import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.user import User
from src.schemas.catalog import (
    DoctorCreate,
    DoctorFacilityResponse,
    DoctorResponse,
    DoctorServiceResponse,
    DoctorSpecialtyResponse,
    DoctorUpdate,
    FacilityResponse,
    ServiceResponse,
    SpecialtyResponse,
)
from src.schemas.common import ApiResponse
from src.services.catalog import CatalogService


@router.get("/doctors", response_model=ApiResponse[list[DoctorResponse]])
async def list_doctors(
    specialty_id: UUID | None = None,
    facility_id: UUID | None = None,
    service_id: UUID | None = None,
    name: str | None = Query(default=None, max_length=200),
    booking_enabled: bool | None = None,
    honor: str | None = Query(default=None, max_length=80),
    academic_rank: str | None = Query(default=None, max_length=80),
    degree: str | None = Query(default=None, max_length=80),
    language: str | None = Query(default=None, max_length=80),
    on_date: date | None = None,
    professional_role: str | None = Query(default=None, max_length=40),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[DoctorResponse]]:
    """Search public doctors by catalog filters."""
    values = await service.list_doctors(
        public_only=True,
        specialty_id=specialty_id,
        facility_id=facility_id,
        service_id=service_id,
        name=name,
        booking_enabled=booking_enabled,
        honor=honor,
        academic_rank=academic_rank,
        degree=degree,
        language=language,
        on_date=on_date,
        professional_role=professional_role,
        offset=offset,
        limit=limit,
    )
    return success_response([_doctor_response(value, public_only=True, on_date=on_date) for value in values], "Doctors retrieved")


@staff_router.get("/doctors", response_model=ApiResponse[list[DoctorResponse]])
async def staff_list_doctors(
    specialty_id: UUID | None = None,
    facility_id: UUID | None = None,
    name: str | None = Query(default=None, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[DoctorResponse]]:
    values = await service.list_doctors(public_only=False, specialty_id=specialty_id,
        facility_id=facility_id, service_id=None, name=name, booking_enabled=None,
        offset=offset, limit=limit)
    return success_response([_doctor_response(value) for value in values], "Doctors retrieved")


@router.get("/doctors/facets")
async def doctor_facets(db: AsyncSession = Depends(get_db_session)):
    columns = {"honors": "honors", "academic_ranks": "academic_ranks", "degrees": "degrees", "languages": "languages"}
    result = {}
    for key, column in columns.items():
        values = (await db.execute(text(f"""
            SELECT DISTINCT value FROM doctors, unnest({column}) AS value
            WHERE status = 'active' AND review_status = 'approved'
            ORDER BY value
        """))).scalars().all()
        result[key] = values
    result["professional_roles"] = (await db.execute(text("""
        SELECT DISTINCT professional_role FROM doctors
        WHERE status = 'active' AND review_status = 'approved'
        ORDER BY professional_role
    """))).scalars().all()
    return success_response(result, "Doctor filter options")


@router.get("/doctors/{doctor_id}", response_model=ApiResponse[DoctorResponse])
async def get_doctor(
    doctor_id: UUID,
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[DoctorResponse]:
    """Get one public doctor."""
    value = await service.get_doctor(doctor_id, public_only=True)
    return success_response(_doctor_response(value, public_only=True), "Doctor retrieved")


@staff_router.post("/doctors", response_model=ApiResponse[DoctorResponse], status_code=status.HTTP_201_CREATED)
async def staff_create_doctor(
    request: DoctorCreate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[DoctorResponse]:
    """Create a doctor as staff."""
    value = await service.create_doctor(request, current_user.id)
    return success_response(_doctor_response(value), "Doctor created", 201)


@staff_router.get("/doctors/{doctor_id}", response_model=ApiResponse[DoctorResponse])
async def staff_get_doctor(doctor_id: UUID, _: User = Depends(require_staff),
                           service: CatalogService = Depends(get_catalog_service)) -> ApiResponse[DoctorResponse]:
    value = await service.get_doctor(doctor_id, public_only=False)
    return success_response(_doctor_response(value), "Doctor retrieved")


@staff_router.patch("/doctors/{doctor_id}", response_model=ApiResponse[DoctorResponse])
async def staff_update_doctor(
    doctor_id: UUID,
    request: DoctorUpdate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[DoctorResponse]:
    """Update a doctor as staff."""
    value = await service.update_doctor(doctor_id, request, current_user.id)
    return success_response(_doctor_response(value), "Doctor updated")


@staff_router.patch("/doctors/{doctor_id}/toggle-booking", response_model=ApiResponse[DoctorResponse])
async def staff_toggle_booking(
    doctor_id: UUID,
    enabled: bool,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[DoctorResponse]:
    """Toggle a doctor's booking availability."""
    value = await service.toggle_doctor_booking(doctor_id, enabled, current_user.id)
    return success_response(_doctor_response(value), "Doctor booking setting updated")


def _doctor_response(value: Doctor, *, public_only: bool = False, on_date: date | None = None) -> DoctorResponse:
    """Map an ORM doctor with loaded assignments to its API response."""
    specialties = [
        item
        for item in value.specialties
        if not public_only or item.specialty is None or item.specialty.status == "active"
    ]
    day = on_date or date.today()
    facilities = [
        item
        for item in value.facilities
        if not public_only or (
            (item.facility is None or item.facility.status == "active")
            and (item.active_from is None or item.active_from <= day)
            and (item.active_to is None or item.active_to >= day)
        )
    ]
    services = [
        item for item in value.services if not public_only or item.service is None or item.service.status == "active"
    ]
    return DoctorResponse(
        id=value.id,
        code=value.code,
        full_name=value.full_name,
        bio=value.bio,
        status=value.status,
        review_status=value.review_status,
        booking_enabled=value.booking_enabled,
        avatar_url=value.avatar_url,
        title=value.title,
        professional_role=getattr(value, "professional_role", None) or "Bác sĩ",
        honors=getattr(value, "honors", None) or [],
        academic_ranks=getattr(value, "academic_ranks", None) or [],
        degrees=getattr(value, "degrees", None) or [],
        languages=getattr(value, "languages", None) or [],
        position=getattr(value, "position", None),
        experience_years=getattr(value, "experience_years", None),
        education=getattr(value, "education", None) or [],
        work_history=getattr(value, "work_history", None) or [],
        awards=getattr(value, "awards", None) or [],
        specialty_ids=[item.specialty_id for item in specialties],
        specialties=[
            DoctorSpecialtyResponse(
                specialty_id=item.specialty_id,
                is_primary=bool(item.is_primary),
                specialty=SpecialtyResponse.model_validate(item.specialty) if item.specialty else None,
            )
            for item in specialties
        ],
        facilities=[
            DoctorFacilityResponse(
                facility_id=item.facility_id,
                department=item.department,
                room=item.room if not public_only else None,
                active_from=item.active_from,
                active_to=item.active_to,
                position=getattr(item, "position", None),
                is_primary=bool(getattr(item, "is_primary", False)),
                facility=FacilityResponse.model_validate(item.facility) if item.facility else None,
            )
            for item in facilities
        ],
        facility_ids=[item.facility_id for item in facilities],
        service_ids=[item.service_id for item in services],
        services=[
            DoctorServiceResponse(
                service_id=item.service_id,
                active=item.active,
                service=ServiceResponse.model_validate(item.service) if item.service else None,
            )
            for item in services
        ],
        created_at=value.created_at,
        updated_at=value.updated_at,
    )
