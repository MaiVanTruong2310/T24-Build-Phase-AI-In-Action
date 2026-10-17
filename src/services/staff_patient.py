"""Staff patient search use cases."""

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.models.user import User
from src.repositories.user import UserRepository
from src.schemas.staff_patient import StaffPatientAgentDetail, StaffPatientDetail, StaffPatientProfileSummary


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

    async def get_agent_detail(self, patient_id: UUID) -> StaffPatientAgentDetail:
        patient = await self.users.get_by_id(patient_id)
        if patient is None or patient.role != "patient":
            raise NotFoundError("Patient not found")
        profiles = await self.users.list_patient_profiles(patient_id)
        details = patient.patient_details or {}
        health_fields = ("blood_type", "allergies", "current_medications", "medical_history", "height_cm", "weight_kg")
        return StaffPatientAgentDetail(
            id=patient.id,
            full_name=patient.full_name,
            email=patient.email,
            phone=patient.phone,
            status=patient.status,
            gender=patient.gender,
            date_of_birth=patient.date_of_birth,
            patient_profiles=[
                StaffPatientProfileSummary(
                    id=profile.id,
                    full_name=profile.full_name,
                    date_of_birth=profile.date_of_birth,
                    gender=profile.gender,
                    contact_phone=profile.contact_phone,
                    citizen_id_masked=_mask_identifier(profile.citizen_id),
                    health_insurance_code_masked=_mask_identifier(profile.health_insurance_code),
                    address=profile.address,
                )
                for profile in profiles
            ],
            patient_details={key: details[key] for key in health_fields if details.get(key) not in (None, "", [])},
        )


def _mask_identifier(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:2]}••••{value[-2:]}" if len(value) > 4 else "••••"
