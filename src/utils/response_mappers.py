"""Map persisted entities to API response schemas."""

from src.models.booking import Booking
from src.models.notification import Notification
from src.schemas.booking import BookingResponse, StaffBookingResponse
from src.schemas.notification import NotificationResponse


def booking_response(value: Booking) -> BookingResponse:
    """Map a booking entity to the patient API response schema."""
    return BookingResponse(
        id=value.id,
        user_id=value.user_id,
        schedule_id=value.schedule_id,
        service_id=value.service_id,
        specialty_id=value.specialty_id,
        doctor_id=value.doctor_id,
        facility_id=value.facility_id,
        starts_at=value.starts_at,
        ends_at=value.ends_at,
        booking_mode=value.service.booking_mode,
        encounter_type=value.encounter_type,
        reason=value.reason,
        patient_note=value.patient_note,
        status=value.status,
        expired_at=value.expired_at,
        cancellation_reason=value.cancellation_reason,
        staff_note=value.staff_note,
        reviewed_by=value.reviewed_by,
        reviewed_at=value.reviewed_at,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def staff_booking_response(value: Booking) -> StaffBookingResponse:
    """Map a booking entity to the staff queue response schema."""
    base = booking_response(value)
    patient = value.user
    doctor = value.doctor
    facility = value.facility
    return StaffBookingResponse(
        **base.model_dump(),
        patient_name=patient.full_name if patient else None,
        patient_email=patient.email if patient else None,
        patient_phone=patient.phone if patient else None,
        patient_date_of_birth=patient.date_of_birth if patient else None,
        patient_gender=patient.gender if patient else None,
        patient_citizen_id=patient.citizen_id if patient else None,
        patient_health_insurance_code=patient.health_insurance_code if patient else None,
        doctor_name=doctor.full_name if doctor else None,
        doctor_title=doctor.title if doctor else None,
        doctor_avatar=doctor.avatar_url if doctor else None,
        specialty_name=value.specialty.name if value.specialty else None,
        service_name=value.service.name if value.service else None,
        facility_name=facility.name if facility else None,
        facility_address=facility.address if facility else None,
        room=None,
    )


def notification_response(value: Notification) -> NotificationResponse:
    """Map a notification entity to the API response schema."""
    return NotificationResponse(
        id=value.id,
        booking_id=value.booking_id,
        kind=value.kind,
        title=value.title,
        message=value.message,
        available_at=value.available_at,
        read_at=value.read_at,
        created_at=value.created_at,
    )
