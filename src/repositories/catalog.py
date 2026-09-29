"""Compatibility facade composing split catalog repositories."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.audit import AuditRepositoryMixin
from src.repositories.doctor import DoctorRepositoryMixin
from src.repositories.facility import FacilityRepositoryMixin
from src.repositories.schedule import ScheduleRepositoryMixin
from src.repositories.service import MedicalServiceRepositoryMixin
from src.repositories.specialty import SpecialtyRepositoryMixin


class CatalogRepository(
    SpecialtyRepositoryMixin,
    FacilityRepositoryMixin,
    MedicalServiceRepositoryMixin,
    DoctorRepositoryMixin,
    ScheduleRepositoryMixin,
    AuditRepositoryMixin,
):
    """Compose catalog persistence operations over one async session."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with the current request session."""
        self.session = session
