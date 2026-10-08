from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from src.api.dependencies import get_current_user
from src.api.response import success_response
from src.db.dependencies import get_db_session
from src.models.user import User
from src.models.workbench import CoordinationCase as Case
from src.models.workbench import CoordinationPolicy as Policy
from src.models.workbench import CoordinatorMember as Member
from src.schemas.workbench import (
    BulkCaseAction,
    CaseAction,
    DepositInput,
    MemberInput,
    MessageInput,
    PlanInput,
    PolicyInput,
    ShiftHandoverInput,
    VerifyInput,
    VersionInput,
)
from src.services import workbench as svc

router = APIRouter(prefix="/staff/workbench", tags=["coordinator-workbench"])
patient_router = APIRouter(prefix="/coordination/live", tags=["patient-coordination"])


async def access(user: User = Depends(get_current_user), db=Depends(get_db_session)):
    member = await svc.member_for(db, user)
    await db.commit()
    return user, member


@router.get("/me")
async def me(identity=Depends(access)):
    user, member = identity
    return success_response(
        {
            "user_id": str(user.id),
            "name": user.full_name,
            "is_admin": member.is_admin,
            "on_duty": member.on_duty,
            "facility_ids": member.facility_ids,
            "clinical_qualification": member.clinical_qualification,
        }
    )


@router.post("/duty/start")
async def start_duty(identity=Depends(access), db=Depends(get_db_session)):
    async with db.begin():
        member = await db.get(Member, identity[0].id, with_for_update=True)
        member.on_duty = True
        from src.models.audit import CatalogAuditEvent

        db.add(
            CatalogAuditEvent(
                actor_id=identity[0].id,
                entity_type="coordinator_duty",
                entity_id=identity[0].id,
                action="duty_started",
                payload={},
            )
        )
    return success_response({"on_duty": True})


@router.post("/duty/handover")
async def handover_duty(payload: ShiftHandoverInput, identity=Depends(access), db=Depends(get_db_session)):
    if payload.assigned_to == identity[0].id or not payload.note.strip():
        raise HTTPException(422, "Chọn người nhận khác và ghi tóm tắt ca trực.")
    async with db.begin():
        members = (
            (
                await db.execute(
                    select(Member)
                    .where(Member.user_id.in_([identity[0].id, payload.assigned_to]))
                    .order_by(Member.user_id)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        target = next((m for m in members if m.user_id == payload.assigned_to), None)
        if not target or not target.enabled or not target.on_duty:
            raise HTTPException(409, "Người nhận chưa bắt đầu ca trực.")
        rows = (
            (
                await db.execute(
                    select(Case)
                    .where(
                        Case.assigned_to == identity[0].id,
                        Case.status.notin_(["completed", "cancelled"]),
                        svc.scope(identity[1]),
                    )
                    .order_by(Case.id)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        for case in rows:
            decision = CaseAction(
                version=case.version, action="handover", assigned_to=payload.assigned_to, note=payload.note
            )
            await svc.action(db, case, *identity, decision)
        current = next(m for m in members if m.user_id == identity[0].id)
        current.on_duty = False
        from src.models.audit import CatalogAuditEvent

        db.add(
            CatalogAuditEvent(
                actor_id=identity[0].id,
                entity_type="coordinator_duty",
                entity_id=identity[0].id,
                action="duty_handed_over",
                payload={"to": str(payload.assigned_to), "case_count": len(rows), "summary": payload.note},
            )
        )
    return success_response({"on_duty": False, "cases_transferred": len(rows)})


@router.post("/duty/end")
async def end_duty(identity=Depends(access), db=Depends(get_db_session)):
    async with db.begin():
        member = await db.get(Member, identity[0].id, with_for_update=True)
        remaining = (
            await db.execute(
                select(Case.id)
                .where(Case.assigned_to == identity[0].id, Case.status.notin_(["completed", "cancelled"]))
                .limit(1)
            )
        ).first()
        if remaining:
            raise HTTPException(409, "Cần bàn giao các ca đang mở trước khi kết thúc ca trực.")
        member.on_duty = False
    return success_response({"on_duty": False})


@router.get("/catalog")
async def catalog(doctor_id: UUID | None = None, identity=Depends(access), db=Depends(get_db_session)):
    from src.models.doctor import Doctor, DoctorFacility, DoctorSpecialty
    from src.models.facility import Facility
    from src.models.schedule import DoctorSchedule
    from src.models.service import Service
    from src.models.specialty import Specialty

    member = identity[1]
    result = {}
    for name, model, label in [
        ("doctors", Doctor, "full_name"),
        ("facilities", Facility, "name"),
        ("services", Service, "name"),
        ("specialties", Specialty, "name"),
    ]:
        query = select(model).where(model.status == "active")
        if model == Doctor:
            query = query.where(
                Doctor.professional_role == "Bác sĩ",
                Doctor.review_status == "approved",
                Doctor.booking_enabled.is_(True),
            )
        if model == Doctor and member.facility_ids:
            query = query.where(
                select(DoctorFacility.id)
                .where(
                    DoctorFacility.doctor_id == Doctor.id,
                    DoctorFacility.facility_id.in_([UUID(x) for x in member.facility_ids]),
                )
                .exists()
            )
        if doctor_id and model == Specialty:
            query = query.where(
                select(DoctorSpecialty.id)
                .where(DoctorSpecialty.doctor_id == doctor_id, DoctorSpecialty.specialty_id == Specialty.id)
                .exists()
            )
        if doctor_id and model == Facility:
            query = query.where(
                select(DoctorFacility.id)
                .where(DoctorFacility.doctor_id == doctor_id, DoctorFacility.facility_id == Facility.id)
                .exists()
            )
        if model == Facility and member.facility_ids:
            query = query.where(Facility.id.in_([UUID(x) for x in member.facility_ids]))
        rows = (await db.execute(query.order_by(getattr(model, label)))).scalars().all()
        result[name] = [{"id": str(r.id), "name": getattr(r, label)} for r in rows]
    query = select(DoctorSchedule).where(
        DoctorSchedule.starts_at > svc.now(),
        or_(
            DoctorSchedule.status == "available",
            (DoctorSchedule.status == "blocked") & (DoctorSchedule.source_system == "coordinator"),
        ),
    )
    if doctor_id:
        query = query.where(DoctorSchedule.doctor_id == doctor_id)
    if member.facility_ids:
        query = query.where(DoctorSchedule.facility_id.in_([UUID(x) for x in member.facility_ids]))
    schedules = (
        (await db.execute(query.order_by(DoctorSchedule.starts_at).limit(200))).scalars().all() if doctor_id else []
    )
    result["schedules"] = [
        {
            "id": str(s.id),
            "starts_at": s.starts_at.isoformat(),
            "ends_at": s.ends_at.isoformat(),
            "facility_id": str(s.facility_id),
            "capacity": s.capacity,
        }
        for s in schedules
    ]
    await db.commit()
    return success_response(result)


@router.get("/cases")
async def cases(
    status: str | None = None,
    priority: int | None = Query(None, ge=0, le=3),
    mine: bool = False,
    conversations: bool = False,
    q: str = Query("", max_length=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    identity=Depends(access),
    db=Depends(get_db_session),
):
    user, member = identity
    filters = [svc.scope(member)]
    if conversations:
        # Chỉ hiển thị các hội thoại khi bệnh nhân chủ động yêu cầu hỗ trợ hoặc đang cần cấp cứu:
        # - Đang cần cấp cứu: priority == 0 hoặc status in ('emergency_active', 'emergency_transferred')
        # - Chủ động yêu cầu hỗ trợ: control == 'human' hoặc status != 'observing' (đã tiếp nhận yêu cầu hỗ trợ)
        emergency_or_support = or_(
            Case.priority == 0,
            Case.status.in_(["emergency_active", "emergency_transferred"]),
            Case.control == "human",
            Case.status != "observing",
        )
        filters.append(Case.source == "chat")
        filters.append(emergency_or_support)
        if not status:
            filters.append(Case.status.notin_(["cancelled", "completed"]))
    else:
        filters.append(Case.status != "observing")

    if status:
        if conversations and status == "observing":
            filters.append(Case.status == "__none__")
        else:
            filters.append(Case.status == status)
    if priority is not None:
        filters.append(Case.priority == priority)
    if mine:
        filters.append(Case.assigned_to == user.id)
    if q.strip():
        # Parameterized query. Escape LIKE wildcard input.
        query = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        from sqlalchemy import String, cast

        filters.append(
            or_(cast(Case.id, String).ilike(query, escape="\\"), cast(Case.patient, String).ilike(query, escape="\\"))
        )
    total = (await db.execute(select(func.count()).select_from(Case).where(*filters))).scalar_one()
    rows = (
        (
            await db.execute(
                select(Case).where(*filters).order_by(Case.priority, Case.created_at).offset(offset).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return success_response({"items": [svc.case_dict(x) for x in rows], "total": total})


@router.get("/dashboard")
async def dashboard(identity=Depends(access), db=Depends(get_db_session)):
    user, member = identity
    async with db.begin():
        rows = (
            await db.execute(
                select(Case.status, func.count())
                .where(svc.scope(member), Case.status != "observing")
                .group_by(Case.status)
            )
        ).all()
        active = [svc.scope(member), Case.status.notin_(["observing", "cancelled", "completed"])]
        overdue = (
            await db.execute(select(func.count()).select_from(Case).where(*active, Case.due_at < svc.now()))
        ).scalar_one()
        followups = (
            (
                await db.execute(
                    select(Case).where(*active, Case.follow_up_at <= svc.now()).order_by(Case.follow_up_at).limit(50)
                )
            )
            .scalars()
            .all()
        )
        emergency = (
            await db.execute(select(func.count()).select_from(Case).where(*active, Case.priority == 0))
        ).scalar_one()
    return success_response(
        {
            "counts": dict(rows),
            "overdue": overdue,
            "emergency": emergency,
            "followups": [svc.case_dict(c) for c in followups],
        }
    )


@router.get("/cases/{case_id}")
async def case_detail(case_id: UUID, identity=Depends(access), db=Depends(get_db_session)):
    async with db.begin():
        case = await svc.locked_case(db, case_id, identity[1])
        return success_response(await svc.detail(db, case))


async def mutate(case_id, identity, db, operation, additional_member_ids=()):
    try:
        async with db.begin():
            # Lock both sides of handover in stable order, before the case lock.
            locked_members = (
                (
                    await db.execute(
                        select(Member)
                        .where(Member.user_id.in_([identity[0].id, *additional_member_ids]))
                        .order_by(Member.user_id)
                        .with_for_update()
                        .execution_options(populate_existing=True)
                    )
                )
                .scalars()
                .all()
            )
            member = next((m for m in locked_members if m.user_id == identity[0].id), None)
            if not member or not member.enabled:
                raise HTTPException(403, "Quyền điều phối đã bị thu hồi.")
            case = await svc.locked_case(db, case_id, member)
            await operation(case)
            await db.flush()
            value = await svc.detail(db, case)
        return success_response(value)
    except IntegrityError as exc:
        raise HTTPException(409, "Giao dịch hoặc lịch đã được sử dụng. Vui lòng tải lại.") from exc


@router.post("/cases/{case_id}/actions")
async def case_action(case_id: UUID, payload: CaseAction, identity=Depends(access), db=Depends(get_db_session)):
    return await mutate(
        case_id,
        identity,
        db,
        lambda c: svc.action(db, c, *identity, payload),
        additional_member_ids=[payload.assigned_to] if payload.action == "handover" and payload.assigned_to else [],
    )


@router.post("/cases/bulk-actions")
async def bulk_case_actions(payload: BulkCaseAction, identity=Depends(access), db=Depends(get_db_session)):
    user, member = identity
    if not member or not member.enabled:
        raise HTTPException(403, "Quyền điều phối đã bị thu hồi.")
    if payload.action == "claim":
        member.on_duty = True

    processed = []
    async with db.begin():
        if payload.action == "claim":
            db_member = await db.get(Member, user.id, with_for_update=True)
            if db_member and not db_member.on_duty:
                db_member.on_duty = True
        query = select(Case).where(Case.id.in_(payload.case_ids), svc.scope(member)).with_for_update()
        cases = (await db.execute(query)).scalars().all()
        for case in cases:
            if case.status in {"completed", "cancelled"}:
                continue
            if payload.action == "claim":
                if case.assigned_to and case.assigned_to != user.id:
                    continue
                case.assigned_to = user.id
                case.due_at = None
                if case.status in {"new", "observing"}:
                    case.status = "emergency_active" if case.priority == 0 else "contacting"
                case.control = "human"
                svc.bump(case)
                svc.event(db, case, user, "claim", payload.note or "Nhận ca")
                processed.append(str(case.id))
            elif payload.action == "decline":
                await svc.release_hold(db, case)
                case.status = "cancelled"
                case.control = "ai"
                case.follow_up_at = None
                svc.bump(case)
                svc.event(db, case, user, "decline", payload.note or "Bác sĩ từ chối nhận ca")
                if case.session_id:
                    await svc.add_message(
                        db,
                        case,
                        str(uuid4()),
                        "system",
                        "Bác sĩ điều phối hiện không thể tiếp nhận cuộc trò chuyện này. Nếu cần hỗ trợ khẩn cấp, vui lòng liên hệ hotline 1900 232 389.",
                    )
                processed.append(str(case.id))
    return success_response({"processed": processed, "count": len(processed)})


@router.put("/cases/{case_id}/plan")
async def plan(case_id: UUID, payload: PlanInput, identity=Depends(access), db=Depends(get_db_session)):
    return await mutate(case_id, identity, db, lambda c: svc.set_plan(db, c, *identity, payload))


@router.post("/cases/{case_id}/deposits")
async def deposit(case_id: UUID, payload: DepositInput, identity=Depends(access), db=Depends(get_db_session)):
    return await mutate(case_id, identity, db, lambda c: svc.request_deposit(db, c, *identity, payload))


@router.post("/cases/{case_id}/verify-deposit")
async def verify(case_id: UUID, payload: VerifyInput, identity=Depends(access), db=Depends(get_db_session)):
    return await mutate(case_id, identity, db, lambda c: svc.verify_deposit(db, c, identity[0], payload))


@router.post("/cases/{case_id}/confirm")
async def confirm(case_id: UUID, payload: VersionInput, identity=Depends(access), db=Depends(get_db_session)):
    return await mutate(case_id, identity, db, lambda c: svc.confirm(db, c, *identity, payload.version))


@router.post("/cases/{case_id}/messages")
async def message(case_id: UUID, payload: MessageInput, identity=Depends(access), db=Depends(get_db_session)):
    async def send(case):
        svc.assert_owner(case, identity[0])
        if not case.session_id or case.status in {"cancelled", "completed"}:
            raise HTTPException(409, "Hội thoại không khả dụng hoặc ca đã đóng.")
        if case.control != "human":
            case.control = "human"
        from src.services.coordinator_chat import validate_guidance

        validate_guidance(payload.body)
        await svc.add_message(db, case, payload.client_id, "coordinator", payload.body, identity[0])
        svc.bump(case)

    return await mutate(case_id, identity, db, send)


@router.get("/members")
async def members(identity=Depends(access), db=Depends(get_db_session)):
    member = identity[1]
    rows = (
        await db.execute(
            select(Member, User)
            .join(User, User.id == Member.user_id)
            .where(Member.enabled.is_(True), User.status == "active")
        )
    ).all()
    await db.commit()
    return success_response(
        [
            {
                "user_id": str(u.id),
                "name": u.full_name,
                "email": u.email if member.is_admin else None,
                "is_admin": m.is_admin,
                "on_duty": m.on_duty,
                "facility_ids": m.facility_ids,
                "clinical_qualification": m.clinical_qualification,
            }
            for m, u in rows
        ]
    )


@router.put("/members")
async def save_member(payload: MemberInput, identity=Depends(access), db=Depends(get_db_session)):
    if not identity[1].is_admin or identity[1].facility_ids:
        raise HTTPException(403, "Chỉ quản trị viên điều phối được cấp quyền.")
    if payload.user_id == identity[0].id and (not payload.enabled or not payload.is_admin):
        raise HTTPException(409, "Không tự thu hồi quyền quản trị trong phiên hiện tại.")
    async with db.begin():
        user = await db.get(User, payload.user_id, with_for_update=True)
        if not user or user.status != "active":
            raise HTTPException(422, "Cần tài khoản đã xác thực và đang hoạt động.")
        from src.models.facility import Facility

        for facility_id in payload.facility_ids:
            if not await db.get(Facility, facility_id):
                raise HTTPException(422, "Cơ sở không tồn tại.")
        member = await db.get(Member, user.id, with_for_update=True)
        if not member:
            member = Member(user_id=user.id)
            db.add(member)
        for key, value in payload.model_dump(exclude={"user_id"}).items():
            setattr(member, key, [str(x) for x in value] if key == "facility_ids" else value)
        user.role = "staff"
        from src.models.audit import CatalogAuditEvent

        db.add(
            CatalogAuditEvent(
                actor_id=identity[0].id,
                entity_type="coordinator_member",
                entity_id=user.id,
                action="permissions_updated",
                payload=payload.model_dump(mode="json"),
            )
        )
    return success_response({"saved": True})


@router.get("/policy")
async def policy(identity=Depends(access), db=Depends(get_db_session)):
    p = await db.get(Policy, 1)
    await db.commit()
    return success_response({col.name: getattr(p, col.name) for col in Policy.__table__.columns} if p else None)


@router.put("/policy")
async def save_policy(payload: PolicyInput, identity=Depends(access), db=Depends(get_db_session)):
    if not identity[1].is_admin or identity[1].facility_ids:
        raise HTTPException(403, "Chỉ quản trị viên điều phối được cấu hình chính sách.")
    async with db.begin():
        p = await db.get(Policy, 1, with_for_update=True)
        if not p:
            p = Policy(id=1)
            db.add(p)
        for key, value in payload.model_dump().items():
            setattr(p, key, value)
        from src.models.audit import CatalogAuditEvent

        db.add(
            CatalogAuditEvent(
                actor_id=identity[0].id,
                entity_type="coordination_policy",
                entity_id=UUID(int=1),
                action="policy_updated",
                payload=payload.model_dump(mode="json"),
            )
        )
    return success_response(payload.model_dump())


async def patient_identity(request: Request, db=Depends(get_db_session)):
    from src.services.cookie_session import request_token

    token = request_token(request)
    user = None
    if token:
        try:
            user = await get_current_user(token, db)
        except Exception:
            user = None
    return svc.owner_key(user, request.state.coordination_guest)


@patient_router.get("/mine")
async def my_cases(request: Request, key=Depends(patient_identity), db=Depends(get_db_session)):
    from src.services.cookie_session import request_token

    token = request_token(request)
    user = None
    if token:
        try:
            user = await get_current_user(token, db)
        except Exception:
            user = None
    conditions = [Case.owner_key == key]
    if user:
        conditions.append(Case.patient_id == user.id)
        conditions.append(Case.owner_key == f"user:{user.id}")

    rows = (
        (
            await db.execute(
                select(Case)
                .where(or_(*conditions), Case.status != "observing")
                .order_by(Case.created_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )

    result = [
        {
            "id": str(c.id),
            "session_id": c.session_id,
            "status": c.status,
            "created_at": c.created_at.isoformat(),
            "name": c.patient.get("name"),
            "patient": c.patient,
            "plan": {k: v for k, v in c.plan.items() if k not in {"hold_id", "reason"}},
            "ai_snapshot": c.ai_snapshot,
            "booking_id": str(c.booking_id) if c.booking_id else None,
        }
        for c in rows
    ]
    await db.commit()
    return success_response(result)


@patient_router.get("/{session_id}")
async def updates(
    session_id: str, after: UUID | None = None, key=Depends(patient_identity), db=Depends(get_db_session)
):
    case = (
        await db.execute(select(Case).where(Case.owner_key == key, Case.session_id == session_id))
    ).scalar_one_or_none()
    if not case:
        await db.commit()
        return success_response({"control": "ai", "messages": [], "case": None})
    from src.models.conversation import Message as UnifiedMsg

    query = select(UnifiedMsg).where(
        UnifiedMsg.conversation_id == case.id,
        UnifiedMsg.sender_type.in_(["STAFF", "PATIENT", "SYSTEM", "coordinator", "patient", "system"]),
    )
    if after:
        previous = await db.get(UnifiedMsg, after)
        if not previous or previous.conversation_id != case.id:
            raise HTTPException(422, "Mốc tin nhắn không hợp lệ.")
        query = query.where(
            or_(
                UnifiedMsg.created_at > previous.created_at,
                (UnifiedMsg.created_at == previous.created_at) & (UnifiedMsg.id > previous.id),
            )
        )
    raw_messages = (await db.execute(query.order_by(UnifiedMsg.created_at, UnifiedMsg.id).limit(100))).scalars().all()
    filtered_messages = []
    for m in raw_messages:
        meta = m.msg_metadata or {}
        client_id = str(meta.get("client_id") or "")
        legacy_sender = str(meta.get("legacy_sender") or "").lower()
        sender_t = (m.sender_type or "").upper()
        # Loại bỏ triệt để các tin nhắn do AI Bot sinh ra
        if (
            sender_t in ("AGENT", "BOT", "AI")
            or legacy_sender in ("ai", "assistant", "bot")
            or client_id.endswith(":ai")
        ):
            continue
        sender = (
            "coordinator"
            if sender_t in ("STAFF", "COORDINATOR") or legacy_sender in ("coordinator", "staff")
            else "patient"
            if sender_t in ("PATIENT", "USER") or legacy_sender in ("patient", "user")
            else "system"
        )
        filtered_messages.append(
            {"id": str(m.id), "sender": sender, "body": m.content or "", "created_at": m.created_at.isoformat()}
        )
    result = {
        "control": case.control,
        "messages": filtered_messages,
        "case": {
            "id": str(case.id),
            "status": case.status,
            "plan": {k: v for k, v in case.plan.items() if k not in {"hold_id", "reason"}},
            "priority": case.priority,
        },
    }
    await db.commit()
    return success_response(result)


@patient_router.post("/{session_id}/request-human")
async def request_human(session_id: str, key=Depends(patient_identity), db=Depends(get_db_session)):
    async with db.begin():
        case = (
            await db.execute(select(Case).where(Case.owner_key == key, Case.session_id == session_id).with_for_update())
        ).scalar_one_or_none()
        if not case:
            raise HTTPException(409, "Gửi tin nhắn đầu tiên trước khi yêu cầu điều phối viên.")
        if case.status in {"completed", "cancelled"}:
            raise HTTPException(409, "Phiếu đã đóng. Vui lòng tạo yêu cầu mới.")
        if case.status == "observing":
            case.status = "new"
            case.priority = 1
            svc.bump(case)
            svc.event(db, case, None, "human_requested")
    return success_response({"saved": True})


@patient_router.post("/{session_id}/messages")
async def patient_message(
    session_id: str, payload: MessageInput, key=Depends(patient_identity), db=Depends(get_db_session)
):
    async with db.begin():
        case = (
            await db.execute(select(Case).where(Case.owner_key == key, Case.session_id == session_id).with_for_update())
        ).scalar_one_or_none()
        if not case:
            raise HTTPException(404, "Không tìm thấy phiếu trong phiên này.")
        if case.status in {"cancelled", "completed"}:
            raise HTTPException(409, "Phiếu đã đóng. Vui lòng tạo yêu cầu mới.")
        await svc.add_message(db, case, payload.client_id, "patient", payload.body)
        from src.medical_assistant.domain.triage_service import get_triage_service

        triage = get_triage_service().evaluate_symptoms(payload.body)
        if triage.is_emergency:
            case.priority = 0
            case.ai_snapshot = {
                **case.ai_snapshot,
                "is_emergency": True,
                "max_booking_days": 0,
                "emergency_warning": triage.patient_guidance,
            }
            await svc.release_hold(db, case)
            await svc.add_message(db, case, str(uuid4()), "system", triage.patient_guidance)
            case.status = "emergency_active" if case.assigned_to else "new"
            svc.event(db, case, None, "emergency_detected", payload.body)
        elif case.status == "observing":
            case.status, case.priority = "new", 1
        svc.bump(case)
    return success_response(
        {"saved": True, "emergency_guidance": triage.patient_guidance if triage.is_emergency else None}
    )
