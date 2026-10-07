"""Resolve the clinical subject using server-checked delegated access."""
from datetime import UTC, datetime
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import select
from src.models.patient_profile import PatientProfile, PatientRelationship
from src.models.user import User


async def resolve_patient(db, user, profile_id=None):
    if profile_id is None:
        return user, None
    if user is None or user.role != 'patient':
        raise HTTPException(403, 'Cần tài khoản bệnh nhân để chọn hồ sơ người thân.')
    row = (await db.execute(select(PatientProfile, PatientRelationship).join(
        PatientRelationship, PatientRelationship.patient_profile_id == PatientProfile.id
    ).where(PatientProfile.id == profile_id, PatientRelationship.user_id == user.id,
            PatientRelationship.status == 'active', PatientRelationship.can_book.is_(True)))).first()
    if not row:
        raise HTTPException(403, 'Bạn không có quyền đặt lịch cho hồ sơ này.')
    profile, relation = row
    patient = await db.get(User, profile.patient_user_id)
    if not patient:
        raise HTTPException(404, 'Không tìm thấy hồ sơ người khám.')
    return patient, profile


async def resolve_booking_payload(db, user, payload):
    if user is not None and user.role != 'patient':
        raise HTTPException(403, 'Chỉ tài khoản bệnh nhân được gửi phiếu đặt khám.')
    patient, profile = await resolve_patient(db, user, getattr(payload, 'patient_profile_id', None))
    if profile:
        payload.patient_name = patient.full_name
        payload.date_of_birth = patient.date_of_birth
        payload.gender = patient.gender if patient.gender != 'unspecified' else 'prefer_not_to_say'
        payload.patient_phone = payload.patient_phone or profile.contact_phone or user.phone
        payload.patient_email = payload.patient_email or user.email
    if user is not None:
        from zoneinfo import ZoneInfo
        from src.medical_assistant.domain.booking_request_service import PHONE_PATTERN
        import re
        today = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date()
        phone = payload.patient_phone or (profile.contact_phone if profile else None) or user.phone or ''
        dob = payload.date_of_birth or patient.date_of_birth
        name = payload.patient_name or patient.full_name or ''
        gender = payload.gender or patient.gender
        if len(name.strip()) < 2 or not dob or dob > today or not gender or not PHONE_PATTERN.fullmatch(re.sub(r'[\s.()-]', '', phone)):
            raise HTTPException(422, 'Vui lòng bổ sung họ tên, ngày sinh, giới tính và số điện thoại hợp lệ cho người khám.')
    return patient, profile


def profile_dict(profile, relation, patient):
    return {'id': str(profile.id), 'full_name': patient.full_name,
            'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            'gender': patient.gender, 'contact_phone': profile.contact_phone,
            'citizen_id': patient.citizen_id, 'health_insurance_code': patient.health_insurance_code,
            'address': profile.address, 'relationship': relation.relationship,
            'is_self': profile.linked_user_id == relation.user_id, 'status': relation.status}


async def create_relative(db, user, payload):
    # Never attach an existing account by guessing phone, CCCD, or email.
    if payload.citizen_id:
        existing_cid = (await db.execute(select(User).where(User.citizen_id == payload.citizen_id))).scalar_one_or_none()
        if existing_cid:
            raise HTTPException(409, 'Số CCCD đã thuộc một hồ sơ khác trong hệ thống.')
    if payload.health_insurance_code:
        existing_bhyt = (await db.execute(select(User).where(User.health_insurance_code == payload.health_insurance_code))).scalar_one_or_none()
        if existing_bhyt:
            raise HTTPException(409, 'Số thẻ bảo hiểm y tế đã thuộc một hồ sơ khác trong hệ thống.')
    patient = User(full_name=payload.full_name, date_of_birth=payload.date_of_birth,
                   gender='unspecified' if payload.gender == 'prefer_not_to_say' else payload.gender, citizen_id=payload.citizen_id,
                   health_insurance_code=payload.health_insurance_code,
                   role='patient', status='dependent', patient_details={'address': payload.address})
    db.add(patient)
    await db.flush()
    profile = PatientProfile(patient_user_id=patient.id, full_name=patient.full_name,
        date_of_birth=patient.date_of_birth, gender=patient.gender, contact_phone=payload.contact_phone,
        citizen_id=payload.citizen_id, health_insurance_code=payload.health_insurance_code, address=payload.address)
    db.add(profile)
    await db.flush()
    relation = PatientRelationship(user_id=user.id, patient_profile_id=profile.id,
        relationship=payload.relationship, consent_at=datetime.now(UTC))
    db.add(relation)
    await db.flush()
    return profile_dict(profile, relation, patient)


async def ensure_self_profile(db, user):
    from uuid import uuid4
    from sqlalchemy.dialects.postgresql import insert
    await db.execute(insert(PatientProfile).values(id=uuid4(), patient_user_id=user.id, linked_user_id=user.id,
        full_name=(user.full_name or '')[:120], date_of_birth=user.date_of_birth, gender=user.gender,
        contact_phone=user.phone if user.phone and len(user.phone) <= 20 else None).on_conflict_do_nothing(index_elements=['patient_user_id']))
    profile = (await db.execute(select(PatientProfile).where(PatientProfile.patient_user_id == user.id))).scalar_one()
    await db.execute(insert(PatientRelationship).values(id=uuid4(), user_id=user.id, patient_profile_id=profile.id,
        relationship='self', status='active', can_book=True, can_view_medical=True).on_conflict_do_nothing(index_elements=['user_id','patient_profile_id']))
    return profile
