"""SQLAlchemy persistence models."""

from src.models.auth import OtpChallenge, RefreshSession
from src.models.booking import Booking
from src.models.booking_hold import BookingHold
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
from src.models.chat_takeover import ChatTakeoverAuditEvent, ChatTakeoverCase, ChatTakeoverMessage
from src.models.coordination import (
    ConsultationRequest,
    ConsultationRequestEvent,
    ConsultationSession,
    ConsultationSlot,
    WeeklyShift,
)
from src.models.notification import Notification
from src.models.package_request import PackageRequest
from src.models.patient_profile import PatientProfile, PatientRelationship
from src.models.user import User
from src.models.workbench import (
    CoordinationCase,
    CoordinationDeposit,
    CoordinationEvent,
    CoordinationMessage,
    CoordinationPolicy,
    CoordinatorMember,
)
from src.models.zalo import ZaloUserMapping

__all__ = [
    "PackageRequest",
    "PatientProfile",
    "PatientRelationship",
    "CatalogAuditEvent",
    "Booking",
    "ChatTakeoverAuditEvent",
    "ChatTakeoverCase",
    "ChatTakeoverMessage",
    "BookingHold",
    "Notification",
    "Doctor",
    "DoctorFacility",
    "DoctorSchedule",
    "DoctorService",
    "DoctorSpecialty",
    "Facility",
    "OtpChallenge",
    "RefreshSession",
    "Service",
    "Specialty",
    "User",
    "ZaloUserMapping",
    "ConsultationRequest",
    "ConsultationRequestEvent",
    "ConsultationSession",
    "ConsultationSlot",
    "WeeklyShift",
    "CoordinationCase",
    "CoordinationDeposit",
    "CoordinationEvent",
    "CoordinationMessage",
    "CoordinationPolicy",
    "CoordinatorMember",
]
