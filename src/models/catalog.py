"""Compatibility facade for split catalog persistence models."""

from src.models.audit import CatalogAuditEvent
from src.models.doctor import Doctor, DoctorFacility, DoctorSpecialty
from src.models.facility import Facility
from src.models.schedule import DoctorSchedule
from src.models.service import Service
from src.models.specialty import Specialty

__all__ = [
    "CatalogAuditEvent",
    "Doctor",
    "DoctorFacility",
    "DoctorSchedule",
    "DoctorSpecialty",
    "Facility",
    "Service",
    "Specialty",
]

