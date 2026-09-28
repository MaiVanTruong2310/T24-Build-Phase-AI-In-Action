"""Facility catalog endpoints."""

from uuid import UUID

from fastapi import Depends, Query, status

from src.api.dependencies import get_current_user, require_staff
from src.api.endpoints.catalog_common import get_catalog_service, router, staff_router
from src.api.response import success_response
from src.models.user import User
from src.schemas.catalog import FacilityCreate, FacilityResponse, FacilityUpdate
from src.schemas.common import ApiResponse
from src.services.catalog import CatalogService


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
