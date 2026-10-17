"""Coordinator case lifecycle, clinical handoff and manually verified deposits."""

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert

from src.core.exceptions import ConflictError
from src.models.booking import Booking
from src.models.booking_hold import BookingHold
from src.models.coordination import ConsultationRequest, ConsultationRequestEvent, ConsultationSession, ConsultationSlot
from src.models.doctor import Doctor
from src.models.facility import Facility
from src.models.package_request import PackageRequest
from src.models.schedule import DoctorSchedule
from src.models.service import Service
from src.models.specialty import Specialty
from src.models.user import User
from src.models.workbench import CoordinationCase as Case
from src.models.workbench import CoordinationDeposit as Deposit
from src.models.workbench import CoordinationEvent as Event
from src.models.workbench import CoordinationPolicy as Policy
from src.models.workbench import CoordinatorMember as Member
from src.services.notification import NotificationService

EMERGENCY_CLAIM_MESSAGE = (
    "Nhân viên y tế đã tiếp nhận ca cấp cứu của bạn và đang ưu tiên hỗ trợ ngay. "
    "Nếu tình trạng nguy kịch hoặc cần trợ giúp tức thời, vui lòng gọi 115 hoặc đến khoa Cấp cứu gần nhất."
)


def now():
    return datetime.now(UTC)


def aware(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def owner_key(user, guest_token):
    return f"user:{user.id}" if user else "guest:" + hashlib.sha256(guest_token.encode()).hexdigest()


def scope(member):
    return (
        or_(Case.facility_id.is_(None), Case.facility_id.in_([UUID(x) for x in member.facility_ids]))
        if member.facility_ids
        else True
    )


def event(db, case, actor, action, note="", details=None):
    event_row = Event(
        case_id=case.id, actor_id=actor.id if actor else None, action=action, note=note, details=details or {}
    )
    db.add(event_row)
    return event_row


def bump(case):
    case.version += 1
    case.updated_at = now()


def require_version(case, version):
    if case.version != version:
        raise HTTPException(409, "Ca đã được cập nhật. Vui lòng tải lại trước khi thao tác.")


def assert_owner(case, actor):
    if case.assigned_to != actor.id:
        raise HTTPException(409, "Hãy nhận ca trước khi thực hiện thao tác.")


# Từ chối chỉ dành cho ca chưa có phương án/cọc/lịch; ca đã đi xa hơn phải dùng "Hủy ca" để xử lý cọc và lịch.
DECLINABLE_STATUSES = {"new", "observing", "contacting", "waiting_patient"}


def decline_error(case, actor):
    """Lý do không được từ chối ca, hoặc None nếu được phép."""
    if case.assigned_to and case.assigned_to != actor.id:
        return "Ca đang do điều phối viên khác phụ trách; chỉ người phụ trách mới được từ chối."
    if case.priority == 0 or (case.ai_snapshot or {}).get("is_emergency"):
        return "Ca có cảnh báo cấp cứu không được từ chối. Hãy nhận ca và xử lý theo luồng cấp cứu."
    if case.status not in DECLINABLE_STATUSES:
        return "Ca đã đóng hoặc đã có phương án, cọc hay lịch khám. Hãy dùng thao tác Hủy ca."
    return None


def reopen_for_patient(db, case, note=""):
    """Bệnh nhân cần hỗ trợ lại trên ca đã đóng: đưa ca về hàng đợi, chưa gán người.

    Ca đã hoàn tất sau khi chốt lịch giữ trạng thái "confirmed" để không mất lịch khám và vẫn hoàn tất lại được.
    Mỗi lần mở lại cần điều phối viên đóng ca trước đó, nên bệnh nhân không thể tạo vòng lặp mở lại liên tục.
    """
    case.status = "confirmed" if case.status == "completed" and case.booking_id else "new"
    case.control = "ai"
    case.assigned_to = None
    case.follow_up_at = None
    case.due_at = None
    event(db, case, None, "takeover_reopened", note)


CONSULT_STATUSES = {"contacting", "waiting_patient"}


async def is_consult_only(db, case):
    """Ca chat chỉ tư vấn: không cấp cứu, chưa có phương án/lịch và không còn khoản cọc đang mở."""
    if (
        case.source != "chat"
        or case.status not in CONSULT_STATUSES
        or case.priority == 0
        or (case.ai_snapshot or {}).get("is_emergency")
        or case.booking_id
        or (case.plan or {}).get("schedule_id")
    ):
        return False
    open_deposit = (
        await db.execute(
            select(Deposit.id)
            .where(Deposit.case_id == case.id, Deposit.status.in_(["requested", "verified", "refund_pending"]))
            .limit(1)
        )
    ).first()
    return open_deposit is None


async def reset_due(db, case):
    """Đặt hạn phản hồi cho ca chưa có người nhận; chỉ rút ngắn, không kéo dài hạn đang có."""
    if case.assigned_to:
        return
    policy = await db.get(Policy, 1)
    if not policy:
        return
    minutes = policy.emergency_response_minutes if case.priority == 0 else policy.response_minutes
    due = now() + timedelta(minutes=minutes)
    if case.due_at is None or aware(case.due_at) > due:
        case.due_at = due


async def ensure_on_duty(db, user_id, member=None):
    """Nhận ca nghĩa là đang làm việc: tự bắt đầu ca trực và ghi nhật ký như thao tác "Bắt đầu ca trực"."""
    db_member = await db.get(Member, user_id, with_for_update=True)
    if db_member and not db_member.on_duty:
        from src.models.audit import CatalogAuditEvent

        db_member.on_duty = True
        db.add(
            CatalogAuditEvent(
                actor_id=user_id,
                entity_type="coordinator_duty",
                entity_id=user_id,
                action="duty_started",
                payload={"reason": "auto_on_claim"},
            )
        )
    if member is not None:
        member.on_duty = True


def claim_error(case, actor_id):
    """Lý do không được nhận ca, hoặc None."""
    if case.status in {"completed", "cancelled"}:
        return "Ca đã đóng."
    if case.status == "observing" and case.priority != 0:
        # Chỉ can thiệp khi bệnh nhân chủ động yêu cầu hỗ trợ hoặc có cảnh báo cấp cứu.
        return "Bệnh nhân chưa yêu cầu hỗ trợ; AI đang xử lý hội thoại này."
    if case.assigned_to and case.assigned_to != actor_id:
        return "Ca đã có người phụ trách."
    return None


def assert_can_reopen(case, actor, member):
    # Ca bị từ chối khi chưa ai nhận không có người phụ trách: cho phép điều phối viên trong phạm vi mở lại.
    if case.assigned_to and case.assigned_to != actor.id and not member.is_admin:
        raise HTTPException(409, "Chỉ người phụ trách cũ hoặc quản trị viên điều phối được mở lại ca này.")


def snapshot(state):
    keys = (
        "symptoms",
        "clinical_facts",
        "collected_details",
        "ats_level",
        "urgency_tier",
        "max_booking_days",
        "is_emergency",
        "emergency_warning",
        "suggested_department_name",
        "suggested_department_code",
        "candidate_specialties",
        "routing_candidates",
        "conflict_reason",
        "critic_status",
        "critic_critique",
        "workflow_status",
    )
    result = {k: state.get(k) for k in keys if state.get(k) is not None}
    result["care_pipeline"] = (state.get("metadata") or {}).get("care_pipeline")
    result["captured_at"] = now().isoformat()
    # Store data, not model chain-of-thought or credentials.
    return result


# Dữ liệu do bác sĩ điều phối / bệnh nhân tạo ra, không được mất khi AI ghi lại snapshot mỗi lượt chat.
PRESERVED_SNAPSHOT_KEYS = ("sos", "handover_summary", "takeover_summary", "emergency_dismissed")
EMERGENCY_STATE_KEYS = ("emergency_warning", "max_booking_days")


def merge_snapshot(previous, state):
    previous = previous or {}
    return {**snapshot(state), **{k: previous[k] for k in PRESERVED_SNAPSHOT_KEYS if k in previous}}


def without_emergency(data):
    """Gỡ cờ cấp cứu (dùng khi bác sĩ đã xác nhận không phải cấp cứu)."""
    return {**{k: v for k, v in (data or {}).items() if k not in EMERGENCY_STATE_KEYS}, "is_emergency": False}


def mark_emergency(snapshot_data, **values):
    """Dấu hiệu cấp cứu mới: nâng cờ và hủy xác nhận "không phải cấp cứu" trước đó."""
    kept = {k: v for k, v in (snapshot_data or {}).items() if k != "emergency_dismissed"}
    return {**kept, "is_emergency": True, **values}


async def member_for(db, user):
    member = await db.get(Member, user.id)
    if user.role != "staff" or not member or not member.enabled:
        raise HTTPException(403, "Tài khoản chưa được cấp quyền điều phối viên.")
    return member


async def locked_case(db, case_id, member):
    case = (
        await db.execute(select(Case).where(Case.id == case_id, scope(member)).with_for_update())
    ).scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Không tìm thấy ca trong phạm vi truy cập.")
    return case


async def ensure_chat_case(db, request, user, token):
    from src.services.patient_profiles import resolve_patient

    target, selected_profile = await resolve_patient(db, user, getattr(request, "patient_profile_id", None))
    key = owner_key(user, token)
    case = (
        await db.execute(
            select(Case).where(Case.owner_key == key, Case.session_id == request.session_id).with_for_update()
        )
    ).scalar_one_or_none()
    if not case:
        profile = request.patient_profile.model_dump(exclude_none=True) if request.patient_profile else {}
        if target:
            profile.update(
                name=target.full_name,
                phone=selected_profile.contact_phone if selected_profile else getattr(user, "phone", None),
                email=getattr(user, "email", None),
                date_of_birth=str(target.date_of_birth) if target.date_of_birth else None,
                gender=target.gender,
            )
        values = dict(
            id=uuid4(),
            source="chat",
            source_id=hashlib.sha256((key + ":" + request.session_id).encode()).hexdigest(),
            owner_key=key,
            session_id=request.session_id,
            patient_id=target.id if target else None,
            patient_profile_id=selected_profile.id if selected_profile else None,
            requested_by_user_id=user.id if user else None,
            patient=profile,
            ai_snapshot={},
            plan={},
            status="observing",
            priority=3,
            control="ai",
            version=1,
        )
        await db.execute(
            insert(Case).values(**values).on_conflict_do_nothing(index_elements=["owner_key", "session_id"])
        )
        case = (
            await db.execute(
                select(Case).where(Case.owner_key == key, Case.session_id == request.session_id).with_for_update()
            )
        ).scalar_one()
    if case.patient_id and target and case.patient_id != target.id:
        raise HTTPException(409, "Hội thoại đã thuộc người khám khác. Hãy mở hội thoại mới.")
    return case


async def add_message(db, case, client_id, sender, body, actor=None, channel: str | None = None):
    from src.models.conversation import Conversation
    from src.models.conversation import Message as UnifiedMsg

    sender_type = (
        "PATIENT"
        if sender in ("patient", "user")
        else "STAFF"
        if sender in ("coordinator", "staff")
        else "AGENT"
        if sender in ("ai", "assistant", "bot")
        else "SYSTEM"
    )
    now = datetime.now(UTC)
    await db.execute(
        insert(Conversation)
        .values(
            id=case.id,
            category="PATIENT_SUPPORT",
            mode="HUMAN" if getattr(case, "control", "ai") == "human" else "AI",
            status="ACTIVE" if getattr(case, "status", "new") not in ("completed", "cancelled") else "RESOLVED",
            patient_id=case.patient_id,
            created_by_type="PATIENT" if case.patient_id else "SYSTEM",
            created_by_id=case.patient_id,
            created_at=getattr(case, "created_at", None) or now,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    msg_meta = {"client_id": str(client_id), "legacy_sender": sender}
    if channel:
        msg_meta["channel"] = channel
    message_id = uuid5(NAMESPACE_URL, f"workbench-message:{case.id}:{client_id}")
    result = await db.execute(
        insert(UnifiedMsg)
        .values(
            id=message_id,
            conversation_id=case.id,
            sender_type=sender_type,
            sender_id=actor.id if actor else None,
            message_type="TEXT",
            content=body,
            msg_metadata=msg_meta,
            created_at=now,
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    message = await db.get(UnifiedMsg, message_id, populate_existing=True)
    if message is None:
        raise HTTPException(409, "Không thể lưu tin nhắn. Vui lòng thử lại.")
    if (
        message.conversation_id != case.id
        or message.sender_type != sender_type
        or message.sender_id != (actor.id if actor else None)
        or message.content != body
    ):
        raise HTTPException(409, "Mã tin nhắn đã được dùng với nội dung khác.")
    message._created_by_request = result.rowcount == 1
    return message


async def capture_chat(db, case, request, response, state):
    from src.services.chat_history import STATE_FIELDS

    previous_emergency = bool((case.ai_snapshot or {}).get("is_emergency"))
    case.checkpoint = {k: state[k] for k in STATE_FIELDS if k in state}
    case.ai_snapshot = merge_snapshot(case.ai_snapshot, state)
    emergency = state.get("is_emergency")
    if case.ai_snapshot.get("emergency_dismissed"):
        # Bác sĩ đã xác nhận không phải cấp cứu: cờ cấp cứu dính lại từ trạng thái AI các lượt trước không được
        # tự nâng mức lại. Dấu hiệu cấp cứu mới qua bộ luật (before_turn/tin nhắn/SOS) sẽ xóa xác nhận này.
        emergency = False
        case.ai_snapshot = without_emergency(case.ai_snapshot)
        case.checkpoint = without_emergency(case.checkpoint)
    elif case.ai_snapshot.get("sos"):
        # Bệnh nhân đã bấm SOS: giữ cờ cấp cứu cho tới khi bác sĩ xác nhận.
        case.ai_snapshot = {**case.ai_snapshot, "is_emergency": True}
    needs_human = (
        emergency
        or state.get("workflow_status")
        # HITL_ESCALATED_COORDINATOR: người dùng bấm "Có" khi được gợi ý gặp điều phối viên (trước đây bot báo đã
        # chuyển nhưng không tạo ca)
        in {"HUMAN_HELP_REQUESTED", "BOOKING_CONTACT_REQUIRED", "SAFETY_REVIEW", "HITL_ESCALATED_COORDINATOR"}
        or state.get("action") == "request_human_help"
        or (state.get("metadata") or {}).get("action") == "request_human_help"
        or state.get("conflict_reason")
    )
    alert_event = None
    if needs_human:
        if case.status in {"completed", "cancelled"}:
            reopen_for_patient(db, case, "Bệnh nhân cần hỗ trợ lại trong cùng hội thoại.")
        case.priority = 0 if emergency else min(case.priority, 1)
        was_observing = case.status == "observing"
        if was_observing:
            case.status = "new"
        if emergency and not previous_emergency:
            alert_event = event(
                db, case, None, "emergency_detected", details={"alert_reason": state.get("emergency_warning")}
            )
        elif was_observing and not state.get("conflict_reason"):
            alert_event = event(
                db, case, None, "human_requested", details={"workflow_status": state.get("workflow_status")}
            )
        policy = await db.get(Policy, 1)
        if policy and not case.due_at:
            case.due_at = now() + timedelta(
                minutes=policy.emergency_response_minutes if emergency else policy.response_minutes
            )
    if case.priority == 0:
        case.ai_snapshot = {**case.ai_snapshot, "is_emergency": True}
    await add_message(db, case, str(request.request_id) + ":ai", "ai", response["response"])
    bump(case)
    return [alert_event] if alert_event is not None else []


# Trạng thái chưa có phương án/giữ chỗ/cọc: gửi form được đưa ca về hàng đợi liên hệ.
INTAKE_RESETTABLE_STATUSES = {"observing", "new", "contacting", "waiting_patient"}


async def intake(db, request, user, token, state):
    import re
    from zoneinfo import ZoneInfo

    from src.medical_assistant.domain.booking_request_service import PHONE_PATTERN, _is_minor

    today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    from src.services.patient_profiles import resolve_booking_payload

    target, profile = await resolve_booking_payload(db, user, request)
    phone = re.sub(r"[\s.()-]", "", request.patient_phone)
    if len(request.patient_name.strip()) < 2:
        raise HTTPException(422, "Họ tên người khám cần ít nhất 2 ký tự.")
    if not PHONE_PATTERN.fullmatch(phone) or request.date_of_birth > today:
        raise HTTPException(422, "Thông tin điện thoại hoặc ngày sinh không hợp lệ.")
    if request.preferred_date is None or request.preferred_date < today:
        raise HTTPException(422, "Ngày khám mong muốn không thể bỏ trống hoặc nằm trong quá khứ.")
    if request.preferred_date > today + timedelta(days=90):
        raise HTTPException(422, "Chỉ được đặt ngày khám trong 90 ngày tới.")
    if _is_minor(request.date_of_birth, today) and (
        len((request.guardian_name or "").strip()) < 2
        or not PHONE_PATTERN.fullmatch(re.sub(r"[\s.()-]", "", request.guardian_phone or ""))
    ):
        raise HTTPException(422, "Người dưới 18 tuổi cần thông tin người giám hộ hợp lệ.")
    case = (
        await db.execute(
            select(Case)
            .where(Case.owner_key == owner_key(user, token), Case.session_id == request.session_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not case:
        from types import SimpleNamespace

        case = await ensure_chat_case(
            db,
            SimpleNamespace(
                session_id=request.session_id, patient_profile=None, patient_profile_id=profile.id if profile else None
            ),
            user,
            token,
        )
    dismissed = (case.ai_snapshot or {}).get("emergency_dismissed")
    if state.get("is_emergency") and not dismissed:
        raise HTTPException(409, "Ca cấp cứu không được chuyển sang đặt lịch thường.")
    if case.priority == 0 or case.ai_snapshot.get("is_emergency"):
        raise HTTPException(409, "Ca có cảnh báo cấp cứu chưa được chuyển sang đăng ký khám thường.")
    if case.status in {"confirmed", "completed", "cancelled"}:
        raise HTTPException(409, "Ca đã đóng hoặc chốt lịch. Vui lòng mở hội thoại mới.")
    if target and case.patient_id and case.patient_id != target.id:
        raise HTTPException(409, "Phiếu không khớp người khám của hội thoại.")
    if target:
        case.patient_id = target.id
        case.patient_profile_id = profile.id if profile else case.patient_profile_id
        case.requested_by_user_id = user.id
    case.patient = {
        "name": request.patient_name.strip(),
        "phone": phone,
        "email": request.patient_email,
        "date_of_birth": request.date_of_birth.isoformat(),
        "gender": request.gender,
        "guardian_name": request.guardian_name,
        "guardian_phone": request.guardian_phone,
        "consent_to_contact": True,
        "preferred_date": str(request.preferred_date) if request.preferred_date else None,
        "preferred_period": request.preferred_period,
        "facility_preference": request.facility_preference,
        "contact_time_preference": request.contact_time_preference,
        "notes": request.patient_notes,
    }
    case.ai_snapshot = merge_snapshot(case.ai_snapshot, state)
    if dismissed:
        case.ai_snapshot = without_emergency(case.ai_snapshot)
    if case.status in INTAKE_RESETTABLE_STATUSES:
        case.status = "contacting" if case.assigned_to else "new"
        await reset_due(db, case)
        action = "intake_submitted"
    else:
        # Ca đã có phương án/giữ chỗ/cọc: chỉ cập nhật thông tin, giữ nguyên trạng thái để không kẹt luồng chốt lịch.
        action = "intake_updated"
    bump(case)
    event(db, case, user, action, request.patient_notes or "")
    return case


async def sync_sources(db, limit_per_source: int = 50, days_back: int = 14):
    """Import existing requests idempotently with a bounded window; never move a case backwards."""
    # Transaction-scoped, nonblocking lock coordinates background workers.
    if not (await db.execute(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": 124_20261005})).scalar_one():
        return
    cutoff = now() - timedelta(days=days_back)
    sources = [(ConsultationRequest, "consultation"), (PackageRequest, "package"), (Booking, "booking")]
    for model, source in sources:
        # Filter imported rows BEFORE LIMIT so each batch advances the backlog.
        imported = select(Case.id).where(Case.source == source, Case.source_id == cast(model.id, String)).exists()
        query = (
            select(model)
            .where(model.created_at >= cutoff, ~imported)
            .order_by(model.created_at, model.id)
            .limit(limit_per_source)
        )
        if source == "booking":
            query = query.where(~select(Case.id).where(Case.booking_id == Booking.id).exists())
        rows = (await db.execute(query)).scalars().all()
        for item in rows:
            patient_id = getattr(item, "patient_id", getattr(item, "user_id", None))
            patient = await db.get(User, patient_id) if patient_id else None
            profile = {
                "name": getattr(item, "patient_name", None) or (patient.full_name if patient else None),
                "phone": getattr(item, "patient_phone", None) or (patient.phone if patient else None),
                "email": getattr(item, "patient_email", None) or (patient.email if patient else None),
                "notes": getattr(item, "reason", getattr(item, "note", "")),
            }
            facility_id = getattr(item, "facility_id", None)
            plan = {"service_id": str(item.service_id)}
            if source == "consultation":
                session = await db.get(ConsultationSession, item.session_id)
                facility_id = session.facility_id if session else None
                plan.update(
                    specialty_id=str(item.specialty_id),
                    doctor_id=str(session.doctor_id) if session else "",
                    preferred_date=str(session.session_date) if session else "",
                    preferred_period=session.period if session else "",
                )
            status = {
                "pending": "new",
                "pending_approval": "new",
                "contacted": "contacting",
                "rejected": "cancelled",
            }.get(item.status, item.status)
            owner = "user:" + str(patient_id) if patient and patient.status == "active" else None
            await db.execute(
                insert(Case)
                .values(
                    id=uuid4(),
                    source=source,
                    source_id=str(item.id),
                    owner_key=owner,
                    session_id="request-" + str(item.id) if owner else None,
                    patient_id=patient_id,
                    patient=profile,
                    ai_snapshot={},
                    plan=plan,
                    facility_id=facility_id,
                    status=status,
                    priority=3,
                    control="ai",
                    version=1,
                    booking_id=item.id if source == "booking" else getattr(item, "booking_id", None),
                    created_at=item.created_at,
                )
                .on_conflict_do_nothing(index_elements=["source", "source_id"])
            )
    # Patient cancellations made through the existing portal also close the workbench case.
    for model, source in sources:
        affected = (
            (
                await db.execute(
                    select(Case)
                    .join(model, (Case.source == source) & (Case.source_id == cast(model.id, String)))
                    .where(
                        model.created_at >= cutoff,
                        model.status.in_(["cancelled", "rejected"]),
                        Case.status.notin_(["cancelled", "completed"]),
                    )
                    .order_by(Case.id)
                    .limit(limit_per_source)
                    .with_for_update(of=Case, skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        for case in affected:
            await release_hold(db, case)
            for deposit in (
                await db.execute(
                    select(Deposit).where(Deposit.case_id == case.id, Deposit.status.in_(["requested", "verified"]))
                )
            ).scalars():
                deposit.status = "refund_pending" if deposit.status == "verified" else "voided"
            case.status, case.control = "cancelled", "ai"
            case.follow_up_at = None
            bump(case)
            event(db, case, None, "source_cancelled")


async def record_booking_review(db, booking, actor_id, status, note=""):
    """Keep the workbench receipt aligned with an atomic staff booking review."""
    source_id = str(booking.id)
    cases = (
        (
            await db.execute(
                select(Case)
                .where(or_(Case.booking_id == booking.id, (Case.source == "booking") & (Case.source_id == source_id)))
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    if len(cases) > 1:
        raise ConflictError(
            "BOOKING_CASE_MAPPING_CONFLICT",
            "Booking is linked to multiple coordination cases; resolve the duplicate mapping before review.",
        )
    case = cases[0] if cases else None
    if case is None:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        patient = booking.user
        values = {
            "id": uuid4(),
            "source": "booking",
            "source_id": source_id,
            "owner_key": "user:" + str(booking.user_id),
            "patient_id": booking.user_id,
            "requested_by_user_id": booking.requested_by_user_id or booking.user_id,
            "patient": {
                "name": patient.full_name if patient else None,
                "phone": patient.phone if patient else None,
                "email": patient.email if patient else None,
                "notes": booking.reason,
            },
            "ai_snapshot": {},
            "plan": {
                "service_id": str(booking.service_id) if booking.service_id else None,
                "specialty_id": str(booking.specialty_id),
                "schedule_id": str(booking.schedule_id) if booking.schedule_id else None,
                "reason": booking.reason,
            },
            "facility_id": booking.facility_id,
            "status": "new",
            "priority": 3,
            "control": "ai",
            "version": 1,
            "booking_id": booking.id,
        }
        await db.execute(
            pg_insert(Case).values(**values).on_conflict_do_nothing(index_elements=["source", "source_id"])
        )
        case = (
            await db.execute(
                select(Case).where(Case.source == "booking", Case.source_id == source_id).with_for_update()
            )
        ).scalar_one()

    case.booking_id = booking.id
    case.status = "confirmed" if status == "confirmed" else "cancelled"
    case.control = "ai"
    case.follow_up_at = None
    case.updated_at = now()
    case.version += 1
    if status == "rejected":
        await release_hold(db, case)
        deposits = (
            await db.execute(
                select(Deposit)
                .where(Deposit.case_id == case.id, Deposit.status.in_(["requested", "verified"]))
                .with_for_update()
            )
        ).scalars()
        for deposit in deposits:
            deposit.status = "refund_pending" if deposit.status == "verified" else "voided"
    db.add(
        Event(
            case_id=case.id,
            actor_id=actor_id,
            action="booking_reviewed",
            note=note,
            details={"booking_id": source_id, "status": status},
        )
    )
    return case


async def create_source_case(db, source, item, patient, user, guest_token, payload, facility_id):
    """Persist a receipt alongside form intake, with verified account/cookie ownership."""
    text = getattr(payload, "reason", None) or getattr(payload, "note", "") or ""
    from src.medical_assistant.domain.triage_service import get_triage_service

    evaluation = get_triage_service().evaluate_symptoms(text) if text else None
    ai = (
        {
            "is_emergency": evaluation.is_emergency,
            "ats_level": evaluation.ats_level.value,
            "max_booking_days": evaluation.max_booking_days,
            "suggested_department_name": evaluation.suggested_specialty,
            "emergency_warning": evaluation.patient_guidance if evaluation.is_emergency else None,
            "captured_at": now().isoformat(),
            "source": "intake_safety_rules",
        }
        if evaluation
        else {}
    )
    profile = {
        "name": payload.patient_name or patient.full_name,
        "phone": payload.patient_phone or patient.phone,
        "email": payload.patient_email or patient.email,
        "notes": text,
        "date_of_birth": str(payload.date_of_birth or patient.date_of_birth)
        if payload.date_of_birth or patient.date_of_birth
        else None,
        "gender": payload.gender or patient.gender,
        "consent_to_contact": payload.consent_to_contact,
        "guardian_name": payload.guardian_name,
        "guardian_phone": payload.guardian_phone,
    }
    plan = {"service_id": str(item.service_id)}
    if hasattr(item, "specialty_id"):
        plan["specialty_id"] = str(item.specialty_id)
    policy = await db.get(Policy, 1)
    emergency = bool(evaluation and evaluation.is_emergency)
    case = Case(
        id=uuid4(),
        source=source,
        source_id=str(item.id),
        owner_key=owner_key(user, guest_token),
        session_id="request-" + str(item.id),
        patient_id=patient.id,
        patient_profile_id=getattr(item, "patient_profile_id", None),
        requested_by_user_id=user.id if user else None,
        patient=profile,
        ai_snapshot=ai,
        plan=plan,
        facility_id=facility_id,
        status="new",
        priority=0 if emergency else 3,
        due_at=now() + timedelta(minutes=policy.emergency_response_minutes if emergency else policy.response_minutes)
        if policy
        else None,
    )
    db.add(case)
    await db.flush()
    event(db, case, user, "intake_submitted", text)
    if emergency:
        await add_message(db, case, str(uuid4()), "system", evaluation.patient_guidance)
    return case


def case_dict(case):
    return {
        k: (str(v) if isinstance(v, UUID) else v.isoformat() if isinstance(v, datetime) else v)
        for k in (
            "id",
            "source",
            "source_id",
            "session_id",
            "patient_id",
            "patient_profile_id",
            "requested_by_user_id",
            "patient",
            "ai_snapshot",
            "plan",
            "facility_id",
            "assigned_to",
            "status",
            "priority",
            "control",
            "version",
            "due_at",
            "follow_up_at",
            "booking_id",
            "created_at",
            "updated_at",
        )
        for v in [getattr(case, k)]
    }


async def detail(db, case):
    value = case_dict(case)
    patient = dict(value.get("patient") or {})
    if not patient.get("email") and case.patient_id:
        linked_patient = await db.get(User, case.patient_id)
        if linked_patient and linked_patient.email:
            patient["email"] = linked_patient.email
    value["patient"] = patient

    for name, model in [("events", Event), ("deposits", Deposit)]:
        rows = (
            (await db.execute(select(model).where(model.case_id == case.id).order_by(model.created_at))).scalars().all()
        )
        value[name] = [
            {
                col.name: (str(v) if isinstance(v, UUID) else v.isoformat() if isinstance(v, datetime) else v)
                for col in model.__table__.columns
                for v in [getattr(row, col.name)]
            }
            for row in rows
        ]

    from src.models.conversation import Message as UnifiedMsg

    msg_rows = (
        (
            await db.execute(
                select(UnifiedMsg).where(UnifiedMsg.conversation_id == case.id).order_by(UnifiedMsg.created_at)
            )
        )
        .scalars()
        .all()
    )
    messages_list = []
    for m in msg_rows:
        meta = m.msg_metadata or {}
        legacy_sender = str(meta.get("legacy_sender") or "").lower()
        sender_t = (m.sender_type or "").upper()
        sender = (
            "coordinator"
            if sender_t in ("STAFF", "COORDINATOR") or legacy_sender in ("coordinator", "staff")
            else "patient"
            if sender_t in ("PATIENT", "USER") or legacy_sender in ("patient", "user")
            else "ai"
            if sender_t in ("AGENT", "BOT", "AI") or legacy_sender in ("ai", "assistant", "bot")
            else "system"
        )
        messages_list.append(
            {
                "id": str(m.id),
                "case_id": str(m.conversation_id),
                "client_id": str(meta.get("client_id") or ""),
                "sender": sender,
                "actor_id": str(m.sender_id) if m.sender_id else None,
                "body": m.content or "",
                "created_at": m.created_at.isoformat() if m.created_at else now().isoformat(),
            }
        )
    value["messages"] = messages_list
    return value


async def release_hold(db, case):
    if case.plan.get("hold_id"):
        hold = await db.get(BookingHold, UUID(case.plan["hold_id"]), with_for_update=True)
        if hold and hold.status == "active":
            hold.status = "released"
            hold.released_at = now()


async def action(db, case, actor, member, payload):
    require_version(case, payload.version)
    a, note = payload.action, payload.note.strip()
    patient_message = None
    if a == "claim":
        newly_claimed = case.assigned_to is None
        reason = claim_error(case, actor.id)
        if reason:
            raise HTTPException(409, reason)
        await ensure_on_duty(db, actor.id, member)
        case.assigned_to = actor.id
        case.due_at = None
        if case.priority == 0:
            case.status = "emergency_active"
            if newly_claimed and getattr(case, "session_id", None):
                patient_message = await add_message(
                    db,
                    case,
                    str(uuid4()),
                    "coordinator",
                    EMERGENCY_CLAIM_MESSAGE,
                    actor,
                )
        elif case.status in {"new", "observing"}:
            case.status = "contacting"
        case.control = "human"
    elif a == "decline":
        reason = decline_error(case, actor)
        if reason:
            raise HTTPException(409, reason)
        await release_hold(db, case)
        case.status = "cancelled"
        case.control = "ai"
        case.follow_up_at = None
        if not note:
            note = "Bác sĩ từ chối nhận ca"
        if case.session_id:
            await add_message(
                db,
                case,
                str(uuid4()),
                "system",
                "Bác sĩ điều phối hiện không thể tiếp nhận cuộc trò chuyện này. Nếu cần hỗ trợ khẩn cấp, vui lòng liên hệ hotline 1900 232 389.",
            )
    else:
        if a == "reopen":
            assert_can_reopen(case, actor, member)
        else:
            assert_owner(case, actor)
        if case.status in {"completed", "cancelled"} and a not in {
            "reopen",
            "refund_request",
            "refund_confirm",
        }:
            raise HTTPException(409, "Ca đã đóng.")
        if (
            a
            in {
                "handover",
                "resume",
                "contact",
                "emergency_ack",
                "emergency_transfer",
                "emergency_dismiss",
                "complete",
                "cancel",
                "reopen",
                "refund_request",
                "refund_confirm",
            }
            and not note
        ):
            raise HTTPException(422, "Cần ghi lý do hoặc kết quả xử lý.")
        if a == "handover":
            target = await db.get(Member, payload.assigned_to) if payload.assigned_to else None
            target_user = await db.get(User, payload.assigned_to) if payload.assigned_to else None
            if (
                not target
                or not target.enabled
                or not target_user
                or target_user.status != "active"
                or target_user.role != "staff"
                or (target.facility_ids and case.facility_id and str(case.facility_id) not in target.facility_ids)
            ):
                raise HTTPException(422, "Người nhận không có quyền hoặc không thuộc phạm vi ca.")
            if payload.assigned_to == actor.id or not target.on_duty:
                raise HTTPException(409, "Chọn điều phối viên khác đang trực để nhận ca.")
            case.assigned_to = payload.assigned_to
        elif a == "takeover":
            if not case.session_id:
                raise HTTPException(409, "Ca này không có hội thoại.")
            case.control = "human"
        elif a == "resume":
            case.control = "ai"
            case.ai_snapshot = {**case.ai_snapshot, "handover_summary": note}
        elif a == "contact":
            if case.status in {"new", "contacting", "waiting_patient"}:
                case.status = "contacting"
        elif a == "follow_up":
            if not payload.follow_up_at or aware(payload.follow_up_at) <= now():
                raise HTTPException(422, "Chọn thời điểm nhắc việc trong tương lai.")
            case.follow_up_at = payload.follow_up_at
            if case.status in {"new", "contacting", "waiting_patient"}:
                case.status = "waiting_patient"
        elif a in {"emergency_ack", "emergency_transfer"}:
            if case.priority != 0:
                raise HTTPException(409, "Ca không có cảnh báo cấp cứu.")
            if a == "emergency_transfer" and not (payload.reference or "").strip():
                raise HTTPException(422, "Cần ghi rõ đơn vị hoặc người nhận bàn giao.")
            case.status = "emergency_active" if a == "emergency_ack" else "emergency_transferred"
            case.control = "human"
        elif a == "emergency_dismiss":
            if case.priority != 0 and not (case.ai_snapshot or {}).get("is_emergency"):
                raise HTTPException(409, "Ca không có cảnh báo cấp cứu.")
            if case.status == "emergency_transferred":
                raise HTTPException(409, "Ca đã bàn giao cấp cứu, không hạ mức.")
            case.priority = 1
            case.ai_snapshot = {
                **without_emergency(case.ai_snapshot),
                "emergency_dismissed": {"by": str(actor.id), "at": now().isoformat(), "note": note},
            }
            # Checkpoint của khách được nạp lại vào lượt chat sau: gỡ cờ để AI không tiếp tục coi là cấp cứu.
            case.checkpoint = without_emergency(case.checkpoint)
            if case.status == "emergency_active":
                case.status = "contacting"
        elif a == "complete":
            consult_only = await is_consult_only(db, case)
            if case.status not in {"confirmed", "emergency_transferred"} and not consult_only:
                raise HTTPException(
                    409,
                    "Chỉ hoàn tất ca đã chốt khám, đã bàn giao cấp cứu, hoặc ca chat chỉ tư vấn "
                    "(chưa có phương án, cọc hay lịch). Ca còn phương án/cọc hãy dùng Hủy ca.",
                )
            case.status = "completed"
            case.control = "ai"
            case.follow_up_at = None
            if consult_only:
                # AI tiếp tục hội thoại với tóm tắt của bác sĩ điều phối làm ngữ cảnh.
                case.ai_snapshot = {**(case.ai_snapshot or {}), "handover_summary": note}
                await add_message(
                    db,
                    case,
                    str(uuid4()),
                    "system",
                    "Bác sĩ điều phối đã kết thúc phiên hỗ trợ. Trợ lý AI sẽ tiếp tục hỗ trợ bạn trong cuộc hội thoại này.",
                )
        elif a == "cancel":
            await release_hold(db, case)
            for deposit in (
                await db.execute(
                    select(Deposit).where(Deposit.case_id == case.id, Deposit.status.in_(["requested", "verified"]))
                )
            ).scalars():
                deposit.status = "refund_pending" if deposit.status == "verified" else "voided"
            if case.booking_id:
                booking = await db.get(Booking, case.booking_id, with_for_update=True)
                booking.status = "cancelled"
                booking.cancellation_reason = note
                await NotificationService(db).discard_reminders_for_booking(booking.id)
            case.status = "cancelled"
            case.control = "ai"
            case.follow_up_at = None
            await update_source(db, case, "cancelled", actor, note)
        elif a == "reopen":
            if case.status not in {"cancelled", "completed"} or case.booking_id:
                raise HTTPException(409, "Ca có lịch đã chốt cần tạo phương án đổi lịch, không mở lại trực tiếp.")
            case.status = "contacting"
            case.assigned_to = actor.id
            if case.session_id:
                await add_message(
                    db,
                    case,
                    str(uuid4()),
                    "system",
                    "Bác sĩ điều phối đã mở lại yêu cầu của bạn và sẽ tiếp tục hỗ trợ trong cuộc hội thoại này.",
                )
        elif a in {"refund_request", "refund_confirm"}:
            deposit = (
                (
                    await db.execute(
                        select(Deposit)
                        .where(Deposit.case_id == case.id, Deposit.status.in_(["verified", "refund_pending"]))
                        .order_by(Deposit.created_at.desc())
                        .with_for_update()
                    )
                )
                .scalars()
                .first()
            )
            if not deposit:
                raise HTTPException(409, "Không có khoản cọc cần hoàn.")
            if a == "refund_confirm":
                if deposit.status != "refund_pending" or not payload.reference or not payload.reference.strip():
                    raise HTTPException(422, "Cần yêu cầu hoàn và mã giao dịch hoàn tiền thực tế.")
                deposit.refund_reference = payload.reference.strip()
                deposit.status = "refunded"
            else:
                deposit.status = "refund_pending"
    bump(case)
    event_action = "emergency_ack" if a == "claim" and case.priority == 0 else a
    event_note = note or ("Tiếp nhận và bắt đầu xử lý ca cấp cứu" if event_action == "emergency_ack" else note)
    event(
        db,
        case,
        actor,
        event_action,
        event_note,
        {
            "assigned_to": str(case.assigned_to) if case.assigned_to else None,
            "reference": payload.reference.strip() if payload.reference else None,
        },
    )
    return patient_message


async def validate_plan(db, case, payload, member):
    if case.priority == 0 or case.ai_snapshot.get("is_emergency"):
        raise HTTPException(409, "Không giữ chỗ hoặc thu cọc cho ca cấp cứu.")
    schedule = await db.get(DoctorSchedule, payload.schedule_id, with_for_update=True)
    if not schedule or schedule.starts_at <= now() or schedule.status not in {"available", "blocked"}:
        raise HTTPException(409, "Lịch không còn nhận khám.")
    if schedule.status == "blocked" and schedule.source_system != "coordinator":
        raise HTTPException(409, "Lịch đang bị khóa.")
    if (
        case.source == "consultation"
        and not (
            await db.execute(select(ConsultationSlot.id).where(ConsultationSlot.schedule_id == schedule.id))
        ).first()
    ):
        raise HTTPException(409, "Phiếu khám theo buổi cần giờ khám thuộc buổi đã công bố.")
    if member.facility_ids and str(schedule.facility_id) not in member.facility_ids:
        raise HTTPException(403, "Cơ sở ngoài phạm vi điều phối.")
    from src.services.booking import BookingService

    service = await db.get(Service, payload.service_id) if payload.service_id else None
    specialty = await db.get(Specialty, payload.specialty_id)
    doctor = await db.get(Doctor, schedule.doctor_id)
    facility = await db.get(Facility, schedule.facility_id)
    if (
        (payload.service_id is not None and (not service or service.status != "active"))
        or not specialty
        or specialty.status != "active"
        or not doctor
        or doctor.status != "active"
        or doctor.review_status != "approved"
        or not doctor.booking_enabled
        or doctor.professional_role != "Bác sĩ"
        or not facility
        or facility.status != "active"
    ):
        raise HTTPException(409, "Danh mục bác sĩ hoặc dịch vụ chưa được phê duyệt.")
    if service is None and schedule.service_id is not None:
        raise HTTPException(409, "Private examination requires a service-less schedule")
    if service is not None and (
        schedule.service_id not in (None, service.id)
        or not await BookingService(db).bookings.has_doctor_service(schedule.doctor_id, service.id)
    ):
        raise HTTPException(409, "Service is not assigned to the selected doctor or schedule")
    await BookingService(db)._validate_catalog_relationships(schedule, service, specialty)
    max_days = case.ai_snapshot.get("max_booking_days")
    if max_days is not None:
        from zoneinfo import ZoneInfo

        if (
            aware(schedule.starts_at).astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
            - now().astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
        ).days > max_days:
            raise HTTPException(409, "Lịch vượt cửa sổ khám được khuyến nghị.")
    return schedule


async def set_plan(db, case, actor, member, payload):
    require_version(case, payload.version)
    assert_owner(case, actor)
    if case.status in {"cancelled", "completed"}:
        raise HTTPException(409, "Ca đã đóng.")
    if not payload.patient_agreed:
        raise HTTPException(422, "Cần ghi nhận bệnh nhân đồng ý phương án.")
    schedule = await validate_plan(db, case, payload, member)
    await release_hold(db, case)
    for d in (
        await db.execute(select(Deposit).where(Deposit.case_id == case.id, Deposit.status == "requested"))
    ).scalars():
        d.status = "voided"
    old = case.plan
    specialty = await db.get(Specialty, payload.specialty_id)
    service = await db.get(Service, payload.service_id)
    doctor = await db.get(Doctor, schedule.doctor_id)
    facility = await db.get(Facility, schedule.facility_id)
    case.plan = {
        "specialty_id": str(payload.specialty_id),
        "specialty_name": specialty.name,
        "service_id": str(payload.service_id),
        "service_name": service.name,
        "schedule_id": str(schedule.id),
        "doctor_id": str(schedule.doctor_id),
        "doctor_name": doctor.full_name,
        "facility_id": str(schedule.facility_id),
        "facility_name": facility.name,
        "starts_at": schedule.starts_at.isoformat(),
        "ends_at": schedule.ends_at.isoformat(),
        "patient_agreed": True,
        "reason": payload.reason,
    }
    case.facility_id = schedule.facility_id
    case.status = "planned"
    bump(case)
    event(db, case, actor, "plan_updated", payload.reason, {"before": old, "after": case.plan})


async def create_case_booking(db, case, actor, member, payload):
    from types import SimpleNamespace

    from src.services.booking import BookingService

    if not payload.patient_agreed:
        raise HTTPException(422, "Cần ghi nhận bệnh nhân đồng ý xác nhận lịch.")
    if case.booking_id:
        booking = await db.get(Booking, case.booking_id, with_for_update=True)
        same_schedule = bool(
            booking
            and (
                booking.schedule_id == payload.schedule_id
                if payload.schedule_id
                else booking.starts_at == payload.starts_at
                and booking.ends_at == payload.ends_at
                and booking.doctor_id == payload.doctor_id
                and booking.facility_id == payload.facility_id
            )
        )
        patient = await db.get(User, case.patient_id) if case.patient_id else None
        guest_matches = bool(
            patient
            and (
                (
                    patient.status == "guest"
                    and case.patient.get("name") == payload.patient_name
                    and case.patient.get("phone") == payload.patient_phone
                    and case.patient.get("email") == payload.patient_email
                    and case.patient.get("date_of_birth")
                    == (payload.patient_date_of_birth.isoformat() if payload.patient_date_of_birth else None)
                    and case.patient.get("gender") == payload.patient_gender
                )
                or (
                    patient.status != "guest"
                    and not any(
                        (
                            payload.patient_name,
                            payload.patient_email,
                            payload.patient_phone,
                            payload.patient_date_of_birth,
                            payload.patient_gender,
                        )
                    )
                )
            )
        )
        if (
            booking
            and same_schedule
            and (
                booking.service_id == payload.service_id
                and booking.specialty_id == payload.specialty_id
                and booking.encounter_type == payload.encounter_type
                and booking.reason == payload.reason
                and booking.patient_note == payload.patient_note
                and guest_matches
            )
        ):
            return
        raise HTTPException(409, "Ca này đã có booking. Hãy tải lại để xem lịch đã tạo.")
    require_version(case, payload.version)
    assert_owner(case, actor)
    if case.priority == 0 or case.ai_snapshot.get("is_emergency"):
        raise HTTPException(409, "Không tạo lịch khám thường cho ca cấp cứu.")
    if case.status in {"cancelled", "completed"}:
        raise HTTPException(409, "Ca đã đóng.")
    if not case.patient_id and not payload.patient_name:
        raise HTTPException(422, "Cần nhập họ tên bệnh nhân.")
    if not case.patient_id and not (payload.patient_email or payload.patient_phone):
        raise HTTPException(422, "Cần nhập email hoặc số điện thoại bệnh nhân.")

    if payload.schedule_id:
        schedule = await validate_plan(
            db,
            case,
            SimpleNamespace(
                schedule_id=payload.schedule_id,
                service_id=payload.service_id,
                specialty_id=payload.specialty_id,
            ),
            member,
        )
    else:
        from src.services.catalog import CatalogService

        catalog = CatalogService(db)
        if case.source == "consultation":
            raise HTTPException(409, "Consultation cases require their published session schedule")
        if member.facility_ids and str(payload.facility_id) not in member.facility_ids:
            raise HTTPException(403, "Facility is outside coordinator scope")
        await catalog._validate_schedule_owners(payload.doctor_id, payload.facility_id, lock_doctor=True)
        await catalog._validate_schedule_service(
            payload.doctor_id, payload.service_id, required=payload.service_id is not None
        )
        from zoneinfo import ZoneInfo

        facility_date = payload.starts_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
        if not await BookingService(db).bookings.has_doctor_facility(
            payload.doctor_id, payload.facility_id, facility_date
        ):
            raise HTTPException(409, "Doctor is not assigned to this facility")
        conflict = await catalog.catalog.find_schedule_conflict(
            doctor_id=payload.doctor_id, starts_at=payload.starts_at, ends_at=payload.ends_at
        )
        if conflict:
            raise HTTPException(409, "Doctor already has an overlapping schedule")
        schedule = DoctorSchedule(
            id=uuid4(),
            doctor_id=payload.doctor_id,
            facility_id=payload.facility_id,
            service_id=payload.service_id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            capacity=1,
            status="available",
            note="Created from coordinator queue",
            created_by=actor.id,
            updated_by=actor.id,
        )
        db.add(schedule)
        await db.flush()
        await catalog._audit(actor.id, "doctor_schedule", schedule.id, "created", {"version": schedule.version})
        schedule = await validate_plan(
            db,
            case,
            SimpleNamespace(schedule_id=schedule.id, service_id=payload.service_id, specialty_id=payload.specialty_id),
            member,
        )
    await release_hold(db, case)
    for deposit in (
        await db.execute(select(Deposit).where(Deposit.case_id == case.id, Deposit.status == "requested"))
    ).scalars():
        deposit.status = "voided"
    is_guest_intake = case.patient_id is None
    guest_patient = (
        SimpleNamespace(
            full_name=payload.patient_name,
            email=payload.patient_email,
            phone=payload.patient_phone,
            date_of_birth=payload.patient_date_of_birth,
            gender=payload.patient_gender,
        )
        if not case.patient_id
        else None
    )
    booking = await BookingService(db).create_staff_confirmed_in_transaction(
        schedule,
        actor_id=actor.id,
        service_id=payload.service_id,
        specialty_id=payload.specialty_id,
        patient_id=case.patient_id,
        guest_patient=guest_patient,
        requested_by_user_id=case.requested_by_user_id,
        patient_profile_id=case.patient_profile_id,
        encounter_type=payload.encounter_type,
        reason=payload.reason,
        patient_note=payload.patient_note,
    )
    case.patient_id = booking.user_id
    if is_guest_intake:
        case.patient = {
            **case.patient,
            "name": payload.patient_name,
            "phone": payload.patient_phone,
            "email": payload.patient_email,
            "date_of_birth": payload.patient_date_of_birth.isoformat() if payload.patient_date_of_birth else None,
            "gender": payload.patient_gender,
        }
    specialty = await db.get(Specialty, payload.specialty_id)
    service = await db.get(Service, payload.service_id) if payload.service_id else None
    doctor = await db.get(Doctor, schedule.doctor_id)
    facility = await db.get(Facility, schedule.facility_id)
    case.plan = {
        "specialty_id": str(specialty.id),
        "specialty_name": specialty.name,
        "service_id": str(service.id) if service else None,
        "service_name": service.name if service else None,
        "schedule_id": str(schedule.id),
        "doctor_id": str(schedule.doctor_id),
        "doctor_name": doctor.full_name,
        "facility_id": str(schedule.facility_id),
        "facility_name": facility.name,
        "starts_at": schedule.starts_at.isoformat(),
        "ends_at": schedule.ends_at.isoformat(),
        "patient_agreed": True,
        "reason": payload.reason,
    }
    case.facility_id = schedule.facility_id
    case.booking_id = booking.id
    case.status = "confirmed"
    case.follow_up_at = None
    await update_source(db, case, "confirmed", actor, "Booking confirmed from staff queue")
    bump(case)
    event(db, case, actor, "booking_confirmed", "Booking confirmed from staff queue", {"booking_id": str(booking.id)})


async def request_deposit(db, case, actor, member, payload):
    require_version(case, payload.version)
    assert_owner(case, actor)
    policy = await db.get(Policy, 1)
    if not policy:
        raise HTTPException(409, "Quản trị viên cần cấu hình điều khoản cọc trước.")
    if case.status != "planned" or not case.plan.get("patient_agreed"):
        raise HTTPException(409, "Cần thống nhất phương án khám trước khi yêu cầu cọc.")
    from types import SimpleNamespace

    schedule = await validate_plan(
        db,
        case,
        SimpleNamespace(
            schedule_id=UUID(case.plan["schedule_id"]),
            service_id=UUID(case.plan["service_id"]),
            specialty_id=UUID(case.plan["specialty_id"]),
        ),
        member,
    )
    # Use the existing hold table so both patient and coordinator flows count the same capacity.
    bookings = (
        await db.execute(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.schedule_id == schedule.id,
                Booking.status.notin_(["cancelled", "rejected"]),
                Booking.id != case.booking_id if case.booking_id else True,
            )
        )
    ).scalar_one()
    holds = (
        await db.execute(
            select(func.count())
            .select_from(BookingHold)
            .where(
                BookingHold.schedule_id == schedule.id, BookingHold.status == "active", BookingHold.expires_at > now()
            )
        )
    ).scalar_one()
    if bookings + holds >= schedule.capacity:
        raise HTTPException(409, "Giờ khám đã đủ số lượng hoặc đang được giữ chỗ.")
    if not case.patient_id:
        # Guest intake does not acquire an existing account by supplying its phone/email.
        patient = User(full_name=case.patient.get("name"), role="patient", status="guest")
        db.add(patient)
        await db.flush()
        case.patient_id = patient.id
    expires = min(now() + timedelta(minutes=policy.hold_minutes), aware(schedule.starts_at))
    hold = BookingHold(
        user_id=case.patient_id,
        requested_by_user_id=case.requested_by_user_id,
        patient_profile_id=case.patient_profile_id,
        schedule_id=schedule.id,
        service_id=UUID(case.plan["service_id"]),
        specialty_id=UUID(case.plan["specialty_id"]),
        status="active",
        expires_at=expires,
    )
    db.add(hold)
    await db.flush()
    case.plan = {**case.plan, "hold_id": str(hold.id)}
    verified = (
        await db.execute(select(Deposit.id).where(Deposit.case_id == case.id, Deposit.status == "verified"))
    ).first()
    if verified:
        case.status = "deposit_verified"
    else:
        deposit = Deposit(
            case_id=case.id,
            amount=payload.amount,
            instructions=policy.payment_instructions,
            refund_policy=policy.refund_policy,
            expires_at=expires,
        )
        db.add(deposit)
        case.status = "waiting_deposit"
    bump(case)
    event(db, case, actor, "deposit_requested", details={"amount": payload.amount, "expires_at": expires.isoformat()})
    await add_message(
        db,
        case,
        str(uuid4()),
        "system",
        f"Đã giữ lại giờ khám đến {expires.isoformat()} bằng khoản cọc đã xác minh."
        if verified
        else f"Yêu cầu cọc: {payload.amount:,} VND. Hạn: {expires.isoformat()}. {policy.payment_instructions}\nĐiều kiện hoàn cọc: {policy.refund_policy}",
    )
    from src.models.notification import Notification

    db.add(
        Notification(
            user_id=case.requested_by_user_id or case.patient_id,
            kind="deposit_requested",
            status="delivered",
            title="Phương án khám và cọc",
            message=f"Kiểm tra phiếu điều phối và điều khoản tại /patient/requests. Hạn giữ chỗ: {expires.isoformat()}.",
            dedupe_key=f"coordination:{case.id}:{case.version}:deposit",
            available_at=now(),
            delivered_at=now(),
        )
    )


async def verify_deposit(db, case, actor, payload):
    require_version(case, payload.version)
    assert_owner(case, actor)
    if case.status not in {"waiting_deposit", "deposit_expired"}:
        raise HTTPException(
            409,
            "Chỉ xác minh cọc cho ca đang chờ cọc hoặc cọc hết hạn. Ca đã đóng cần xử lý tiền đến muộn theo luồng hoàn tiền.",
        )
    if case.priority == 0 or case.ai_snapshot.get("is_emergency"):
        raise HTTPException(409, "Không xử lý cọc trong luồng cấp cứu.")
    deposit = (
        (
            await db.execute(
                select(Deposit)
                .where(Deposit.case_id == case.id, Deposit.status.in_(["requested", "expired"]))
                .order_by(Deposit.created_at.desc())
                .with_for_update()
            )
        )
        .scalars()
        .first()
    )
    if not deposit:
        raise HTTPException(409, "Không có yêu cầu cọc chờ xác minh.")
    deposit.transaction_reference = payload.reference
    deposit.evidence = payload.evidence
    deposit.verified_by = actor.id
    deposit.status = "verified"
    hold = (
        await db.get(BookingHold, UUID(case.plan["hold_id"]), with_for_update=True)
        if case.plan.get("hold_id")
        else None
    )
    case.status = (
        "deposit_verified" if hold and hold.status == "active" and aware(hold.expires_at) > now() else "deposit_late"
    )
    bump(case)
    event(
        db,
        case,
        actor,
        "deposit_verified",
        payload.evidence,
        {"reference": payload.reference, "late": case.status == "deposit_late"},
    )


async def update_source(db, case, status, actor, note=""):
    if case.source == "consultation":
        item = await db.get(ConsultationRequest, UUID(case.source_id), with_for_update=True)
        item.status = status
        item.booking_id = case.booking_id
        item.staff_note = note
        item.reviewed_by = actor.id
        item.reviewed_at = now()
        if status == "confirmed":
            slot = (
                await db.execute(
                    select(ConsultationSlot).where(ConsultationSlot.schedule_id == UUID(case.plan["schedule_id"]))
                )
            ).scalar_one_or_none()
            if slot:
                item.session_id = slot.session_id
                item.assigned_slot_id = slot.id
            else:
                item.assigned_slot_id = None
            item.specialty_id = UUID(case.plan["specialty_id"])
            item.service_id = UUID(case.plan["service_id"])
        db.add(ConsultationRequestEvent(request_id=item.id, actor_id=actor.id, action=status, note=note))
    elif case.source == "package":
        item = await db.get(PackageRequest, UUID(case.source_id), with_for_update=True)
        item.status = status
        item.staff_note = note


async def confirm(db, case, actor, member, version):
    require_version(case, version)
    assert_owner(case, actor)
    deposits = (
        (await db.execute(select(Deposit).where(Deposit.case_id == case.id, Deposit.status == "verified")))
        .scalars()
        .all()
    )
    if not deposits or case.status not in {"deposit_verified", "waiting_deposit"}:
        raise HTTPException(409, "Cần xác minh cọc trước khi chốt lịch.")
    from types import SimpleNamespace

    schedule = await validate_plan(
        db,
        case,
        SimpleNamespace(
            schedule_id=UUID(case.plan["schedule_id"]),
            service_id=UUID(case.plan["service_id"]),
            specialty_id=UUID(case.plan["specialty_id"]),
        ),
        member,
    )
    hold = await db.get(BookingHold, UUID(case.plan["hold_id"]), with_for_update=True)
    if not hold or hold.status != "active" or aware(hold.expires_at) <= now():
        raise HTTPException(409, "Giữ chỗ đã hết hạn. Cần chọn lại phương án và giữ chỗ mới.")
    other_bookings = (
        await db.execute(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.schedule_id == schedule.id,
                Booking.status.notin_(["cancelled", "rejected"]),
                Booking.id != case.booking_id if case.booking_id else True,
            )
        )
    ).scalar_one()
    other_holds = (
        await db.execute(
            select(func.count())
            .select_from(BookingHold)
            .where(
                BookingHold.schedule_id == schedule.id,
                BookingHold.id != hold.id,
                BookingHold.status == "active",
                BookingHold.expires_at > now(),
            )
        )
    ).scalar_one()
    if other_bookings + other_holds >= schedule.capacity:
        raise HTTPException(409, "Lịch không còn đủ công suất.")
    booking = (
        await db.get(Booking, case.booking_id, with_for_update=True)
        if case.booking_id
        else Booking(
            user_id=case.patient_id,
            requested_by_user_id=case.requested_by_user_id,
            patient_profile_id=case.patient_profile_id,
        )
    )
    if case.booking_id:
        await NotificationService(db).discard_reminders_for_booking(booking.id)
    booking.schedule_id = schedule.id
    booking.doctor_id, booking.facility_id = schedule.doctor_id, schedule.facility_id
    booking.starts_at, booking.ends_at = schedule.starts_at, schedule.ends_at
    booking.service_id, booking.specialty_id = UUID(case.plan["service_id"]), UUID(case.plan["specialty_id"])
    booking.encounter_type = "in_person"
    booking.reason = case.patient.get("notes") or case.plan["reason"]
    booking.status, booking.reviewed_by, booking.reviewed_at = "confirmed", actor.id, now()
    db.add(booking)
    await db.flush()
    hold.status, hold.released_at = "consumed", now()
    case.booking_id, case.status = booking.id, "confirmed"
    case.follow_up_at = None
    await update_source(db, case, "confirmed", actor, case.plan["reason"])
    notification_service = NotificationService(db)
    context = await notification_service.appointment_context(booking)
    from src.models.notification import Notification

    db.add(
        Notification(
            user_id=booking.requested_by_user_id or booking.user_id,
            booking_id=booking.id,
            kind="booking_confirmed",
            status="delivered",
            title="Lịch khám đã xác nhận",
            message=f"Lịch khám của bạn đã được xác nhận.\n{context}",
            dedupe_key=f"coordination:{case.id}:{case.version}:confirmed",
            available_at=now(),
            delivered_at=now(),
        )
    )
    db.add(
        Notification(
            user_id=booking.requested_by_user_id or booking.user_id,
            booking_id=booking.id,
            kind="appointment_reminder",
            status="pending",
            title="Nhắc lịch khám",
            message=f"Bạn sắp đến lịch khám.\n{context}\nVui lòng có mặt trước giờ hẹn.",
            dedupe_key=f"coordination:{case.id}:{case.version}:reminder",
            available_at=max(now(), booking.starts_at - timedelta(hours=24)),
        )
    )
    await add_message(
        db,
        case,
        str(uuid4()),
        "system",
        f"Lịch khám đã xác nhận. Mã: {booking.id}. Giờ: {booking.starts_at.isoformat()}.",
    )
    bump(case)
    event(db, case, actor, "booking_confirmed", details={"booking_id": str(booking.id)})


async def expire_deposits(db):
    expired = []
    cases = (
        (await db.execute(select(Case).where(Case.status == "waiting_deposit").with_for_update(skip_locked=True)))
        .scalars()
        .all()
    )
    for case in cases:
        d = (
            (
                await db.execute(
                    select(Deposit)
                    .where(Deposit.case_id == case.id, Deposit.status == "requested", Deposit.expires_at <= now())
                    .with_for_update()
                )
            )
            .scalars()
            .first()
        )
        if d:
            d.status = "expired"
            await release_hold(db, case)
            case.status = "deposit_expired"
            bump(case)
            event(db, case, None, "deposit_expired")
            expired.append(case)
    return expired


async def run_maintenance(session_factory):
    """Bảo trì định kỳ bàn điều phối: hết hạn cọc, nhập phiếu từ nguồn khác và đồng bộ hủy."""
    from src.services.chat_takeover import publish_workbench_case_update

    async with session_factory() as db:
        async with db.begin():
            expired = await expire_deposits(db)
        async with db.begin():
            await sync_sources(db)
    for case in expired:
        await publish_workbench_case_update(case)
    return len(expired)
