"""Medical catalog, availability, and staff endpoints."""

from datetime import date, datetime, time, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_staff
from src.api.response import success_response
from src.db.dependencies import get_db_session
from src.models.catalog import Doctor
from src.models.user import User
from src.schemas.catalog import (
    DoctorCreate,
    DoctorResponse,
    DoctorScheduleResponse,
    DoctorUpdate,
    FacilityCreate,
    FacilityResponse,
    FacilityUpdate,
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
    SpecialtyCreate,
    SpecialtyResponse,
    SpecialtyUpdate,
)
from src.schemas.common import ApiResponse
from src.services.catalog import CatalogService

router = APIRouter(tags=["catalog"])
staff_router = APIRouter(prefix="/staff", tags=["staff-catalog"])


def get_catalog_service(session: AsyncSession = Depends(get_db_session)) -> CatalogService:
    """Build the catalog service for the current request."""
    return CatalogService(session)


@router.get("/specialties", response_model=ApiResponse[list[SpecialtyResponse]])
async def list_specialties(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[SpecialtyResponse]]:
    """List active specialties."""
    values = await service.list_specialties(public_only=True, offset=offset, limit=limit)
    return success_response([SpecialtyResponse.model_validate(value) for value in values], "Specialties retrieved")


@router.get("/specialties/{specialty_id}", response_model=ApiResponse[SpecialtyResponse])
async def get_specialty(
    specialty_id: UUID,
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[SpecialtyResponse]:
    """Get one active specialty."""
    value = await service.get_specialty(specialty_id, public_only=True)
    return success_response(SpecialtyResponse.model_validate(value), "Specialty retrieved")


@router.get("/facilities", response_model=ApiResponse[list[FacilityResponse]])
async def list_facilities(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[FacilityResponse]]:
    """List active facilities."""
    values = await service.list_facilities(public_only=True, offset=offset, limit=limit)
    return success_response([FacilityResponse.model_validate(value) for value in values], "Facilities retrieved")


@router.get("/facilities/{facility_id}", response_model=ApiResponse[FacilityResponse])
async def get_facility(
    facility_id: UUID,
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[FacilityResponse]:
    """Get one active facility."""
    value = await service.get_facility(facility_id, public_only=True)
    return success_response(FacilityResponse.model_validate(value), "Facility retrieved")


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
    return success_response([_doctor_response(value) for value in values], "Doctors retrieved")


@router.get("/doctors/{doctor_id}/availability", response_model=ApiResponse[list[DoctorScheduleResponse]])
async def doctor_availability(
    doctor_id: UUID,
    facility_id: UUID | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    selected_date: date | None = Query(default=None, alias="date"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[DoctorScheduleResponse]]:
    """Return only available slots with positive capacity."""
    starts_from, starts_to = _availability_window(from_date, to_date, selected_date)
    values = await service.list_schedules(
        doctor_id=doctor_id,
        facility_id=facility_id,
        starts_from=starts_from,
        starts_to=starts_to,
        public_only=True,
        offset=offset,
        limit=limit,
    )
    return success_response(
        [DoctorScheduleResponse.model_validate(value) for value in values], "Availability retrieved"
    )


@router.get("/doctors/{doctor_id}", response_model=ApiResponse[DoctorResponse])
async def get_doctor(
    doctor_id: UUID,
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[DoctorResponse]:
    """Get one public doctor."""
    value = await service.get_doctor(doctor_id, public_only=True)
    return success_response(_doctor_response(value), "Doctor retrieved")


@staff_router.post("/specialties", response_model=ApiResponse[SpecialtyResponse], status_code=status.HTTP_201_CREATED)
async def staff_create_specialty(
    request: SpecialtyCreate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[SpecialtyResponse]:
    """Create a specialty as staff."""
    value = await service.create_specialty(request, current_user.id)
    return success_response(SpecialtyResponse.model_validate(value), "Specialty created", 201)


@staff_router.patch("/specialties/{specialty_id}", response_model=ApiResponse[SpecialtyResponse])
async def staff_update_specialty(
    specialty_id: UUID,
    request: SpecialtyUpdate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[SpecialtyResponse]:
    """Update a specialty as staff."""
    value = await service.update_specialty(specialty_id, request, current_user.id)
    return success_response(SpecialtyResponse.model_validate(value), "Specialty updated")


@staff_router.post("/facilities", response_model=ApiResponse[FacilityResponse], status_code=status.HTTP_201_CREATED)
async def staff_create_facility(
    request: FacilityCreate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[FacilityResponse]:
    """Create a facility as staff."""
    value = await service.create_facility(request, current_user.id)
    return success_response(FacilityResponse.model_validate(value), "Facility created", 201)


@staff_router.patch("/facilities/{facility_id}", response_model=ApiResponse[FacilityResponse])
async def staff_update_facility(
    facility_id: UUID,
    request: FacilityUpdate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[FacilityResponse]:
    """Update a facility as staff."""
    value = await service.update_facility(facility_id, request, current_user.id)
    return success_response(FacilityResponse.model_validate(value), "Facility updated")


@staff_router.get("/services", response_model=ApiResponse[list[ServiceResponse]])
async def staff_list_services(
    _: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[ServiceResponse]]:
    """List all services for staff."""
    values = await service.list_services(public_only=False, offset=0, limit=100)
    return success_response([ServiceResponse.model_validate(value) for value in values], "Services retrieved")


@staff_router.post("/services", response_model=ApiResponse[ServiceResponse], status_code=status.HTTP_201_CREATED)
async def staff_create_service(
    request: ServiceCreate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[ServiceResponse]:
    """Create a service as staff."""
    value = await service.create_service(request, current_user.id)
    return success_response(ServiceResponse.model_validate(value), "Service created", 201)


@staff_router.patch("/services/{service_id}", response_model=ApiResponse[ServiceResponse])
async def staff_update_service(
    service_id: UUID,
    request: ServiceUpdate,
    current_user: User = Depends(require_staff),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[ServiceResponse]:
    """Update a service as staff."""
    value = await service.update_service(service_id, request, current_user.id)
    return success_response(ServiceResponse.model_validate(value), "Service updated")


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


def _doctor_response(value: Doctor) -> DoctorResponse:
    """Map an ORM doctor with loaded assignments to its API response."""
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
        specialty_ids=[item.specialty_id for item in value.specialties],
        facility_ids=[item.facility_id for item in value.facilities],
        service_ids=[item.service_id for item in value.services],
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def _availability_window(
    from_date: date | None,
    to_date: date | None,
    selected_date: date | None,
) -> tuple[datetime | None, datetime | None]:
    """Normalize range and single-day availability query parameters."""
    if selected_date:
        return datetime.combine(selected_date, time.min, tzinfo=datetime.now().astimezone().tzinfo), datetime.combine(
            selected_date + timedelta(days=1), time.min, tzinfo=datetime.now().astimezone().tzinfo
        )
    starts_from = (
        datetime.combine(from_date, time.min, tzinfo=datetime.now().astimezone().tzinfo) if from_date else None
    )
    starts_to = datetime.combine(to_date, time.min, tzinfo=datetime.now().astimezone().tzinfo) if to_date else None
    return starts_from, starts_to
