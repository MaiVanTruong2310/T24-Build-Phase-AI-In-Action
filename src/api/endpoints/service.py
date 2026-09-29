"""Medical service catalog endpoints."""

from uuid import UUID

from fastapi import Depends, status

from src.api.dependencies import require_staff
from src.api.endpoints.catalog_common import get_catalog_service, staff_router
from src.api.response import success_response
from src.models.user import User
from src.schemas.catalog import ServiceCreate, ServiceResponse, ServiceUpdate
from src.schemas.common import ApiResponse
from src.services.catalog import CatalogService


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
