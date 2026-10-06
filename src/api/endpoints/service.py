"""Medical service catalog endpoints."""

from uuid import UUID

from fastapi import Depends, Query, Response, status

from src.api.dependencies import require_coordination_admin as require_staff
from src.api.endpoints.catalog_common import get_catalog_service, router, staff_router
from src.api.response import success_response
from src.core.cache import cache_key, get_catalog_cache, set_cache_headers
from src.models.user import User
from src.schemas.catalog import ServiceCreate, ServiceResponse, ServiceUpdate
from src.schemas.common import ApiResponse
from src.services.catalog import CatalogService


@router.get("/services", response_model=ApiResponse[list[ServiceResponse]])
async def list_public_services(
    response: Response,
    name: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=100),
    specialty_id: UUID | None = None,
    facility_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=250),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[ServiceResponse]]:
    """List active medical services for patient search and booking selection."""
    cache = get_catalog_cache()
    key = cache_key("services:list", name, category, specialty_id, facility_id, offset, limit)
    hit, cached = cache.get(key)
    if hit:
        set_cache_headers(response, hit=True)
        return success_response([ServiceResponse.model_validate(item) for item in cached], "Services retrieved")
    values = await service.list_services(
        public_only=True,
        offset=offset,
        limit=limit,
        name=name,
        category=category,
        specialty_id=specialty_id,
        facility_id=facility_id,
    )
    data = [ServiceResponse.model_validate(value) for value in values]
    cache.set(key, [item.model_dump(mode="json") for item in data])
    set_cache_headers(response, hit=False)
    return success_response(data, "Services retrieved")


import time

_CATEGORIES_CACHE: tuple[float, list[str]] | None = None
_CACHE_TTL = 300.0  # 5 minutes


@router.get("/services/categories", response_model=ApiResponse[list[str]])
async def list_service_categories(
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[list[str]]:
    """List distinct categories of active medical services and health packages."""
    global _CATEGORIES_CACHE
    now = time.monotonic()
    if _CATEGORIES_CACHE is not None and (now - _CATEGORIES_CACHE[0]) < _CACHE_TTL:
        return success_response(_CATEGORIES_CACHE[1], "Categories retrieved")

    from sqlalchemy import select
    from src.models.catalog import Service

    stmt = select(Service.category).where(Service.status == "active", Service.category.is_not(None)).distinct().order_by(Service.category)
    res = await service.session.execute(stmt)
    categories = [c for c in res.scalars().all() if c and c != "Khám Chuyên Khoa"]
    _CATEGORIES_CACHE = (now, categories)
    return success_response(categories, "Categories retrieved")


@router.get("/services/{service_id}", response_model=ApiResponse[ServiceResponse])
async def get_public_service(
    service_id: UUID,
    response: Response,
    _: User = Depends(get_current_user),
    service: CatalogService = Depends(get_catalog_service),
) -> ApiResponse[ServiceResponse]:
    """Get one active medical service for a patient."""
    cache = get_catalog_cache()
    key = cache_key("services:detail", service_id)
    hit, cached = cache.get(key)
    if hit:
        set_cache_headers(response, hit=True)
        return success_response(ServiceResponse.model_validate(cached), "Service retrieved")
    value = await service.get_service(service_id, public_only=True)
    data = ServiceResponse.model_validate(value)
    cache.set(key, data.model_dump(mode="json"))
    set_cache_headers(response, hit=False)
    return success_response(data, "Service retrieved")


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
