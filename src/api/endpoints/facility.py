"""Facility catalog endpoints."""

from uuid import UUID

from fastapi import Depends, Query, Response, status

from src.api.dependencies import require_coordination_admin as require_staff
from src.api.endpoints.catalog_common import get_catalog_service, router, staff_router
from src.api.response import success_response
from src.core.cache import cache_key, get_catalog_cache, set_cache_headers
from src.models.user import User
from src.schemas.catalog import FacilityCreate, FacilityResponse, FacilityUpdate
from src.schemas.common import ApiResponse
from src.services.catalog import CatalogService


import time

_FACILITIES_CACHE: dict[str, tuple[float, list[FacilityResponse]]] = {}
_CACHE_TTL = 300.0  # 5 minutes


@router.get("/facilities", response_model=ApiResponse[list[FacilityResponse]])
async def list_facilities(
    response: Response,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    specialty_id: UUID | None = Query(default=None, description="Filter facilities by specialty"),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[FacilityResponse]]:
    """List active facilities."""
    cache_key = f"{offset}:{limit}:{specialty_id}"
    now = time.monotonic()
    if cache_key in _FACILITIES_CACHE and (now - _FACILITIES_CACHE[cache_key][0]) < _CACHE_TTL:
        return success_response(_FACILITIES_CACHE[cache_key][1], "Facilities retrieved")

    values = await service.list_facilities(public_only=True, offset=offset, limit=limit, specialty_id=specialty_id)
    items = [FacilityResponse.model_validate(value) for value in values]
    _FACILITIES_CACHE[cache_key] = (now, items)
    return success_response(items, "Facilities retrieved")


@router.get("/facilities/{facility_id}", response_model=ApiResponse[FacilityResponse])
async def get_facility(
    facility_id: UUID,
    response: Response,
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[FacilityResponse]:
    """Get one active facility."""
    cache = get_catalog_cache()
    key = cache_key("facilities:detail", facility_id)
    hit, cached = cache.get(key)
    if hit:
        set_cache_headers(response, hit=True)
        return success_response(FacilityResponse.model_validate(cached), "Facility retrieved")
    value = await service.get_facility(facility_id, public_only=True)
    data = FacilityResponse.model_validate(value)
    cache.set(key, data.model_dump(mode="json"))
    set_cache_headers(response, hit=False)
    return success_response(data, "Facility retrieved")


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
