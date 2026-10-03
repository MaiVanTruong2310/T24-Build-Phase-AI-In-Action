"""Specialty catalog endpoints."""

from uuid import UUID

from fastapi import Depends, Query, status

from src.api.dependencies import require_coordination_admin as require_staff
from src.api.endpoints.catalog_common import get_catalog_service, router, staff_router
from src.api.response import success_response
from src.models.user import User
from src.schemas.catalog import SpecialtyCreate, SpecialtyResponse, SpecialtyUpdate
from src.schemas.common import ApiResponse
from src.services.catalog import CatalogService


import time

_SPECIALTIES_CACHE: dict[str, tuple[float, list[SpecialtyResponse]]] = {}
_CACHE_TTL = 300.0  # 5 minutes


@router.get("/specialties", response_model=ApiResponse[list[SpecialtyResponse]])
async def list_specialties(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    facility_id: UUID | None = Query(default=None, description="Filter specialties by facility"),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[SpecialtyResponse]]:
    """List active specialties."""
    cache_key = f"{offset}:{limit}:{facility_id}"
    now = time.monotonic()
    if cache_key in _SPECIALTIES_CACHE and (now - _SPECIALTIES_CACHE[cache_key][0]) < _CACHE_TTL:
        return success_response(_SPECIALTIES_CACHE[cache_key][1], "Specialties retrieved")

    values = await service.list_specialties(public_only=True, offset=offset, limit=limit, facility_id=facility_id)
    items = [SpecialtyResponse.model_validate(value) for value in values]
    _SPECIALTIES_CACHE[cache_key] = (now, items)
    return success_response(items, "Specialties retrieved")


@router.get("/specialties/{specialty_id}", response_model=ApiResponse[SpecialtyResponse])
async def get_specialty(
    specialty_id: UUID,
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[SpecialtyResponse]:
    """Get one active specialty."""
    value = await service.get_specialty(specialty_id, public_only=True)
    return success_response(SpecialtyResponse.model_validate(value), "Specialty retrieved")


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
