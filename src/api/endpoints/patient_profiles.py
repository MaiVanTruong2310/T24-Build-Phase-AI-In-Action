from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import require_patient
from src.api.response import success_response
from src.db.dependencies import get_db_session
from src.models.user import User
from src.models.patient_profile import PatientProfile, PatientRelationship
from src.schemas.patient_profile import RelativeInput
from src.services.patient_profiles import create_relative, profile_dict

router = APIRouter(prefix='/patient-profiles', tags=['patient-profiles'])


@router.get('')
async def profiles(user: User = Depends(require_patient), db: AsyncSession = Depends(get_db_session)):
    from src.services.patient_profiles import ensure_self_profile
    async with db.begin():
        await ensure_self_profile(db, user)
    rows = (await db.execute(select(PatientProfile, PatientRelationship, User)
        .join(PatientRelationship, PatientRelationship.patient_profile_id == PatientProfile.id)
        .join(User, User.id == PatientProfile.patient_user_id)
        .where(PatientRelationship.user_id == user.id, PatientRelationship.status == 'active')
        .order_by(PatientProfile.created_at))).all()
    return success_response([profile_dict(*row) for row in rows], 'Hồ sơ người khám')


@router.post('', status_code=201)
async def add_profile(payload: RelativeInput, user: User = Depends(require_patient), db: AsyncSession = Depends(get_db_session)):
    async with db.begin():
        result = await create_relative(db, user, payload)
    return success_response(result, 'Đã thêm hồ sơ người thân', 201)


@router.patch('/{profile_id}')
async def edit_profile(profile_id: UUID, payload: RelativeInput, user: User = Depends(require_patient), db: AsyncSession = Depends(get_db_session)):
    async with db.begin():
        row = (await db.execute(select(PatientProfile, PatientRelationship)
            .join(PatientRelationship, PatientRelationship.patient_profile_id == PatientProfile.id)
            .where(PatientProfile.id == profile_id, PatientRelationship.user_id == user.id,
                   PatientRelationship.status == 'active').with_for_update())).first()
        if not row:
            raise HTTPException(403, 'Bạn không có quyền sửa hồ sơ này.')
        profile, relation = row
        if profile.linked_user_id is not None:
            raise HTTPException(409, 'Cập nhật hồ sơ bản thân tại trang Hồ sơ cá nhân.')
        patient = await db.get(User, profile.patient_user_id)
        for field in ('full_name', 'date_of_birth', 'gender', 'citizen_id', 'health_insurance_code'):
            setattr(patient, field, 'unspecified' if field == 'gender' and payload.gender == 'prefer_not_to_say' else getattr(payload, field))
            setattr(profile, field, getattr(payload, field))
        profile.contact_phone, profile.address = payload.contact_phone, payload.address
        patient.patient_details = {**(patient.patient_details or {}), 'address': payload.address}
        relation.relationship = payload.relationship
        result = profile_dict(profile, relation, patient)
    return success_response(result, 'Đã cập nhật hồ sơ người thân')


@router.delete('/{profile_id}')
async def archive_profile(profile_id: UUID, user: User = Depends(require_patient), db: AsyncSession = Depends(get_db_session)):
    async with db.begin():
        row = (await db.execute(select(PatientProfile, PatientRelationship)
            .join(PatientRelationship, PatientRelationship.patient_profile_id == PatientProfile.id)
            .where(PatientProfile.id == profile_id, PatientRelationship.user_id == user.id)
            .with_for_update())).first()
        if not row or row[0].linked_user_id:
            raise HTTPException(403, 'Không thể gỡ hồ sơ này.')
        row[1].status = 'revoked'
    return success_response(None, 'Đã gỡ hồ sơ khỏi danh sách; lịch sử đặt khám được giữ lại')
