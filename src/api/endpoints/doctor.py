"""Doctor catalog and assignment endpoints."""

from uuid import UUID

from fastapi import Depends, Query, status

from src.api.dependencies import get_current_user, require_staff
from src.api.endpoints.catalog_common import get_catalog_service, router, staff_router
from src.api.response import success_response
from src.models.catalog import Doctor
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
    name: str | None = Query(default=None, max_length=200),
    booking_enabled: bool | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[DoctorResponse]]:
    """Search public doctors by catalog filters."""
    values = await service.list_doctors(
        public_only=True,
        specialty_id=specialty_id,
        facility_id=facility_id,
        name=name,
        booking_enabled=booking_enabled,
        offset=offset,
        limit=limit,
    )
    return success_response([_doctor_response(value, public_only=True) for value in values], "Doctors retrieved")


@router.get("/doctors/{doctor_id}", response_model=ApiResponse[DoctorResponse])
async def get_doctor(
    doctor_id: UUID,
    _: User = Depends(get_current_user),
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


def _doctor_response(value: Doctor, *, public_only: bool = False) -> DoctorResponse:
    """Map an ORM doctor with loaded assignments to its API response."""
    specialties = [
        item
        for item in value.specialties
        if not public_only or item.specialty is None or item.specialty.status == "active"
    ]
    facilities = [
        item
        for item in value.facilities
        if not public_only or item.facility is None or item.facility.status == "active"
    ]
    services = [
        item for item in value.services if not public_only or item.service is None or item.service.status == "active"
    ]
    return DoctorResponse(
        id=value.id,
        code=value.code,
        full_name=value.full_name,
        license_number=value.license_number,
        email=value.email,
        phone=value.phone,
        bio=value.bio,
        status=value.status,
        review_status=value.review_status,
        booking_enabled=value.booking_enabled,
        avatar_url=value.avatar_url,
        gender=value.gender,
        title=value.title,
        date_of_birth=value.date_of_birth,
        specialty_ids=[item.specialty_id for item in specialties],
        specialties=[
            DoctorSpecialtyResponse(
                specialty_id=item.specialty_id,
                is_primary=item.is_primary,
                specialty=SpecialtyResponse.model_validate(item.specialty) if item.specialty else None,
            )
            for item in specialties
        ],
        facilities=[
            DoctorFacilityResponse(
                facility_id=item.facility_id,
                department=item.department,
                room=item.room,
                active_from=item.active_from,
                active_to=item.active_to,
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
