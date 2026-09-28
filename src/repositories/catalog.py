"""Persistence operations for the medical catalog bounded context."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.catalog import (
    CatalogAuditEvent,
    Doctor,
    DoctorFacility,
    DoctorSchedule,
    DoctorService,
    DoctorSpecialty,
    Facility,
    Service,
    Specialty,
)


class CatalogRepository:
    """Repository containing catalog and schedule persistence queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository with the current request session."""
        self.session = session

    async def get_specialty(self, resource_id: UUID, *, public_only: bool = False) -> Specialty | None:
        """Fetch one specialty."""
        statement = select(Specialty).where(Specialty.id == resource_id)
        if public_only:
            statement = statement.where(Specialty.status == "active")
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_specialties(self, *, public_only: bool, offset: int, limit: int) -> list[Specialty]:
        """List specialties with pagination."""
        statement = select(Specialty).order_by(Specialty.name).offset(offset).limit(limit)
        if public_only:
            statement = statement.where(Specialty.status == "active")
        return list((await self.session.execute(statement)).scalars().all())

    async def get_facility(self, resource_id: UUID, *, public_only: bool = False) -> Facility | None:
        """Fetch one facility."""
        statement = select(Facility).where(Facility.id == resource_id)
        if public_only:
            statement = statement.where(Facility.status == "active")
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_facilities(self, *, public_only: bool, offset: int, limit: int) -> list[Facility]:
        """List facilities with pagination."""
        statement = select(Facility).order_by(Facility.name).offset(offset).limit(limit)
        if public_only:
            statement = statement.where(Facility.status == "active")
        return list((await self.session.execute(statement)).scalars().all())

    async def get_service(self, resource_id: UUID, *, public_only: bool = False) -> Service | None:
        """Fetch one service."""
        statement = select(Service).where(Service.id == resource_id)
        if public_only:
            statement = statement.where(Service.status == "active")
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_services(self, *, public_only: bool, offset: int, limit: int) -> list[Service]:
        """List services with pagination."""
        statement = select(Service).order_by(Service.name).offset(offset).limit(limit)
        if public_only:
            statement = statement.where(Service.status == "active")
        return list((await self.session.execute(statement)).scalars().all())

    async def get_doctor(self, resource_id: UUID, *, public_only: bool = False) -> Doctor | None:
        """Fetch a doctor and assignment collections."""
        statement = (
            select(Doctor)
            .options(
                selectinload(Doctor.specialties),
                selectinload(Doctor.facilities),
                selectinload(Doctor.services),
            )
            .where(Doctor.id == resource_id)
        )
        if public_only:
            statement = statement.where(
                Doctor.status == "active",
                Doctor.review_status == "approved",
                Doctor.booking_enabled.is_(True),
            )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_doctors(
        self,
        *,
        public_only: bool,
        specialty_id: UUID | None,
        facility_id: UUID | None,
        name: str | None,
        booking_enabled: bool | None,
        offset: int,
        limit: int,
    ) -> list[Doctor]:
        """List doctors with catalog filters and assignment collections."""
        statement = (
            select(Doctor)
            .options(
                selectinload(Doctor.specialties),
                selectinload(Doctor.facilities),
                selectinload(Doctor.services),
            )
            .order_by(Doctor.full_name)
            .offset(offset)
            .limit(limit)
        )
        if public_only:
            statement = statement.where(
                Doctor.status == "active",
                Doctor.review_status == "approved",
                Doctor.booking_enabled.is_(True),
            )
        if booking_enabled is not None:
            statement = statement.where(Doctor.booking_enabled.is_(booking_enabled))
        if name:
            statement = statement.where(Doctor.full_name.ilike(f"%{name.strip()}%"))
        if specialty_id:
            statement = statement.join(DoctorSpecialty).where(DoctorSpecialty.specialty_id == specialty_id)
        if facility_id:
            statement = statement.join(DoctorFacility).where(DoctorFacility.facility_id == facility_id)
        if specialty_id or facility_id:
            statement = statement.distinct()
        return list((await self.session.execute(statement)).scalars().unique().all())

    async def get_schedule(self, schedule_id: UUID) -> DoctorSchedule | None:
        """Fetch a schedule with its doctor and facility."""
        statement = (
            select(DoctorSchedule)
            .options(selectinload(DoctorSchedule.doctor), selectinload(DoctorSchedule.facility))
            .where(DoctorSchedule.id == schedule_id)
        )
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_schedule_by_external_identity(
        self,
        source_system: str,
        external_schedule_id: str,
        *,
        for_update: bool = False,
    ) -> DoctorSchedule | None:
        """Find an imported schedule by its idempotency identity."""
        statement = select(DoctorSchedule).where(
            DoctorSchedule.source_system == source_system,
            DoctorSchedule.external_schedule_id == external_schedule_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list_schedules(
        self,
        *,
        doctor_id: UUID | None,
        facility_id: UUID | None,
        starts_from: datetime | None,
        starts_to: datetime | None,
        public_only: bool,
        offset: int,
        limit: int,
    ) -> list[DoctorSchedule]:
        """List schedule slots, optionally restricted to public availability."""
        statement = (
            select(DoctorSchedule)
            .join(Doctor)
            .join(Facility)
            .options(selectinload(DoctorSchedule.doctor), selectinload(DoctorSchedule.facility))
            .order_by(DoctorSchedule.starts_at)
            .offset(offset)
            .limit(limit)
        )
        if doctor_id:
            statement = statement.where(DoctorSchedule.doctor_id == doctor_id)
        if facility_id:
            statement = statement.where(DoctorSchedule.facility_id == facility_id)
        if starts_from:
            statement = statement.where(DoctorSchedule.starts_at >= starts_from)
        if starts_to:
            statement = statement.where(DoctorSchedule.starts_at < starts_to)
        if public_only:
            statement = statement.where(
                DoctorSchedule.status == "available",
                DoctorSchedule.capacity > 0,
                Doctor.status == "active",
                Doctor.review_status == "approved",
                Doctor.booking_enabled.is_(True),
                Facility.status == "active",
            )
        return list((await self.session.execute(statement)).scalars().all())

    async def list_audit_events(self, entity_id: UUID, *, limit: int = 100) -> list[CatalogAuditEvent]:
        """Return newest audit events for an entity."""
        statement = (
            select(CatalogAuditEvent)
            .where(CatalogAuditEvent.entity_id == entity_id)
            .order_by(CatalogAuditEvent.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def add_audit_event(self, event: CatalogAuditEvent) -> CatalogAuditEvent:
        """Persist an audit event."""
        self.session.add(event)
        await self.session.flush()
        return event

    async def replace_doctor_assignments(
        self,
        doctor: Doctor,
        *,
        specialty_ids: list[UUID] | None = None,
        facilities: list[Any] | None = None,
        service_ids: list[UUID] | None = None,
    ) -> None:
        """Replace supplied assignment collections while preserving omitted ones."""
        if specialty_ids is not None:
            await self.session.execute(delete(DoctorSpecialty).where(DoctorSpecialty.doctor_id == doctor.id))
            doctor.specialties = [
                DoctorSpecialty(doctor_id=doctor.id, specialty_id=value, is_primary=index == 0)
                for index, value in enumerate(dict.fromkeys(specialty_ids))
            ]
        if facilities is not None:
            await self.session.execute(delete(DoctorFacility).where(DoctorFacility.doctor_id == doctor.id))
            seen = set()
            unique_facilities = []
            for f in facilities:
                if f.facility_id not in seen:
                    seen.add(f.facility_id)
                    unique_facilities.append(f)
            doctor.facilities = [
                DoctorFacility(
                    doctor_id=doctor.id,
                    facility_id=f.facility_id,
                    department=f.department,
                    room=f.room,
                    active_from=f.active_from,
                    active_to=f.active_to,
                )
                for f in unique_facilities
            ]
        if service_ids is not None:
            await self.session.execute(delete(DoctorService).where(DoctorService.doctor_id == doctor.id))
            doctor.services = [
                DoctorService(doctor_id=doctor.id, service_id=value) for value in dict.fromkeys(service_ids)
            ]

    async def remove_doctor_specialty(self, doctor_id: UUID, specialty_id: UUID) -> None:
        """Remove one doctor-specialty assignment."""
        await self.session.execute(
            delete(DoctorSpecialty).where(
                DoctorSpecialty.doctor_id == doctor_id,
                DoctorSpecialty.specialty_id == specialty_id,
            )
        )

    async def remove_doctor_service(self, doctor_id: UUID, service_id: UUID) -> None:
        """Remove one doctor-service assignment."""
        await self.session.execute(
            delete(DoctorService).where(DoctorService.doctor_id == doctor_id, DoctorService.service_id == service_id)
        )
