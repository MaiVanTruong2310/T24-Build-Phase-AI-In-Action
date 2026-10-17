"""Specialty catalog endpoints."""

from uuid import UUID

from fastapi import Depends, Query, Response, status

from src.api.dependencies import get_current_user, require_coordination_admin
from src.api.endpoints.catalog_common import get_catalog_service, router, staff_router
from src.api.response import success_response
from src.core.cache import (
    cache_key,
    get_catalog_cache,
    get_redis_api_cache,
    set_cache_headers,
    set_redis_api_cache,
)
from src.models.user import User
from src.schemas.catalog import SpecialtyCreate, SpecialtyResponse, SpecialtyUpdate
from src.schemas.common import ApiResponse
from src.services.catalog import CatalogService


@router.get("/specialties", response_model=ApiResponse[list[SpecialtyResponse]])
async def list_specialties(
    response: Response,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    facility_id: UUID | None = Query(default=None, description="Filter specialties by facility"),
    search: str | None = Query(default=None, max_length=200, description="Search specialty name or code"),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[SpecialtyResponse]]:
    """List active specialties."""
    params = (offset, limit, facility_id, search)
    hit, cached, generation = await get_redis_api_cache("catalog", ("specialties", params))
    if hit:
        set_cache_headers(response, hit=True)
        return success_response([SpecialtyResponse.model_validate(item) for item in cached], "Specialties retrieved")

    values = await service.list_specialties(
        public_only=True, offset=offset, limit=limit, facility_id=facility_id, search=search
    )
    items = [SpecialtyResponse.model_validate(value) for value in values]
    await set_redis_api_cache(
        "catalog", ("specialties", params), [item.model_dump(mode="json") for item in items], generation
    )
    set_cache_headers(response, hit=False)
    return success_response(items, "Specialties retrieved")


@router.get("/specialties/{specialty_id}", response_model=ApiResponse[SpecialtyResponse])
async def get_specialty(
    specialty_id: UUID,
    response: Response,
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[SpecialtyResponse]:
    """Get one active specialty."""
    cache = get_catalog_cache()
    key = cache_key("specialties:detail", specialty_id)
    hit, cached = cache.get(key)
    if hit:
        set_cache_headers(response, hit=True)
        return success_response(SpecialtyResponse.model_validate(cached), "Specialty retrieved")
    value = await service.get_specialty(specialty_id, public_only=True)
    data = SpecialtyResponse.model_validate(value)
    cache.set(key, data.model_dump(mode="json"))
    set_cache_headers(response, hit=False)
    return success_response(data, "Specialty retrieved")


@staff_router.post("/specialties", response_model=ApiResponse[SpecialtyResponse], status_code=status.HTTP_201_CREATED)
async def staff_create_specialty(
    request: SpecialtyCreate,
    current_user: User = Depends(require_coordination_admin),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[SpecialtyResponse]:
    """Create a specialty as staff."""
    value = await service.create_specialty(request, current_user.id)
    return success_response(SpecialtyResponse.model_validate(value), "Specialty created", 201)


@staff_router.patch("/specialties/{specialty_id}", response_model=ApiResponse[SpecialtyResponse])
async def staff_update_specialty(
    specialty_id: UUID,
    request: SpecialtyUpdate,
    current_user: User = Depends(require_coordination_admin),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[SpecialtyResponse]:
    """Update a specialty as staff."""
    value = await service.update_specialty(specialty_id, request, current_user.id)
    return success_response(SpecialtyResponse.model_validate(value), "Specialty updated")
