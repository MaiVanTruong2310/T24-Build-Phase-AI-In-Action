"""Staff-only patient search endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_staff
from src.api.response import success_response
from src.db.dependencies import get_auth_db_session
from src.models.user import User
from src.schemas.common import ApiResponse
from src.schemas.staff_patient import StaffPatientDetail, StaffPatientListItem, StaffPatientPage
from src.services.staff_patient import StaffPatientService

router = APIRouter(prefix="/staff/patients", tags=["staff-patients"])


def get_staff_patient_service(session: AsyncSession = Depends(get_auth_db_session)) -> StaffPatientService:
    return StaffPatientService(session)


@router.get("", response_model=ApiResponse[StaffPatientPage])
async def search_patients(
    q: str | None = Query(default=None, max_length=200),
    status: str | None = Query(default=None, min_length=1, max_length=32),
    gender: str | None = Query(default=None, pattern="^(male|female|other|unspecified)$"),
    created_from: date | None = None,
    created_to: date | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_staff),
    service: StaffPatientService = Depends(get_staff_patient_service),
) -> ApiResponse[StaffPatientPage]:
    """Search all patient accounts for staff with bounded offset pagination."""
    if created_from and created_to and created_to < created_from:
        raise HTTPException(status_code=422, detail="created_to must be on or after created_from")
    patients, total = await service.search(
        query=q.strip() or None if q else None,
        status=status,
        gender=gender,
        created_from=created_from,
        created_to=created_to,
        offset=offset,
        limit=limit,
    )
    return success_response(
        StaffPatientPage(
            items=[StaffPatientListItem.model_validate(patient) for patient in patients],
            total=total,
            offset=offset,
            limit=limit,
        ),
        "Patients retrieved",
    )


@router.get("/{patient_id}", response_model=ApiResponse[StaffPatientDetail])
async def get_patient_detail(
    patient_id: UUID,
    _: User = Depends(require_staff),
    service: StaffPatientService = Depends(get_staff_patient_service),
) -> ApiResponse[StaffPatientDetail]:
    """Return an allowlisted patient profile with sensitive IDs masked."""
    return success_response(await service.get_detail(patient_id), "Patient retrieved")
