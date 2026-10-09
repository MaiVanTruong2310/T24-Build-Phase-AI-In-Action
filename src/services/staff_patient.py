"""Staff patient search use cases."""

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.staff_patient import StaffPatientDetail


class StaffPatientService:
    """Search patient accounts for authenticated staff workflows."""

    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)

    async def search(
        self,
        *,
        query: str | None,
        status: str | None,
        gender: str | None,
        created_from: date | None,
        created_to: date | None,
        offset: int,
        limit: int,
    ) -> tuple[list[User], int]:
        return await self.users.search_patients(
            query=query,
            status=status,
            gender=gender,
            created_from=created_from,
            created_to=created_to,
            offset=offset,
            limit=limit,
        )

    async def get_detail(self, patient_id: UUID) -> StaffPatientDetail:
        patient = await self.users.get_by_id(patient_id)
        if patient is None or patient.role != "patient":
            raise NotFoundError("Patient not found")
        return StaffPatientDetail(
            id=patient.id,
            full_name=patient.full_name,
            email=patient.email,
            phone=patient.phone,
            status=patient.status,
            gender=patient.gender,
            date_of_birth=patient.date_of_birth,
            citizen_id_masked=_mask_identifier(patient.citizen_id),
            health_insurance_code_masked=_mask_identifier(patient.health_insurance_code),
        )


def _mask_identifier(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:2]}••••{value[-2:]}" if len(value) > 4 else "••••"
