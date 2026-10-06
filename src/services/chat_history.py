"""Account-owned chat archive, idempotent turns, and bounded graph checkpoints."""

import json
import logging
from datetime import date
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text

from src.core.logging import get_logger, log_event

logger = get_logger(__name__)

STATE_FIELDS = {
    "messages",
    "language",
    "symptoms",
    "clinical_facts",
    "collected_details",
    "is_emergency",
    "emergency_warning",
    "ats_level",
    "urgency_tier",
    "max_booking_days",
    "acuity_status",
    "disposition",
    "probing_turn",
    "active_probing_category",
    "active_probing_categories",
    "probing_by_complaint",
    "suggested_department_code",
    "suggested_department_name",
    "candidate_specialties",
    "routing_candidates",
    "conflict_reason",
    "recommended_doctor_id",
    "available_slots",
    "selected_slot",
    "booking_id",
    "booking_code",
    "workflow_status",
    "metadata",
    "patient_name",
    "patient_phone",
    "patient_dob",
    "patient_gender",
    "patient_email",
    "facility_preference",
    "preferred_date",
    "preferred_period",
    "is_authenticated",
    "durable_soap_note",
    "active_open_loops",
    "patient_memory_profile",
}


def graph_thread(session_id, user=None, guest_token=""):
    if user:
        return f"user:{user.id}:{session_id}"
    import hashlib

    capability = hashlib.sha256(guest_token.encode()).hexdigest() if guest_token else "legacy"
    return f"guest:{capability}:{session_id}"


def health_record(user):
    details = user.patient_details or {}
    record = {
        key: details[key]
        for key in ("blood_type", "allergies", "current_medications", "medical_history", "height_cm", "weight_kg")
        if details.get(key) not in (None, "", [])
    }
    if user.date_of_birth:
        today = date.today()
        dob = user.date_of_birth
        record["age"] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if user.gender:
        record["gender"] = user.gender
    record["source"] = "patient_reported_profile"
    return record


class ChatHistoryService:
    def __init__(self, session):
        self.session = session

    async def begin_turn(self, user, request):
        log_event(
            logger,
            logging.INFO,
            "chat.turn.start",
            description="Starting chat turn lease and idempotency check",
            user_id=str(user.id),
            session_id=request.session_id,
            request_id=str(request.request_id),
            message_length=len(request.message),
        )
        lease = uuid4()
        async with self.session.begin():
            await self.session.execute(
                text("""INSERT INTO public.chat_conversations(id,user_id,session_id,title,patient_profile_id)
              VALUES(:id,:uid,:sid,:title,:pid) ON CONFLICT(user_id,session_id) DO NOTHING"""),
                {"id": uuid4(), "uid": user.id, "sid": request.session_id, "title": request.message[:80], "pid": getattr(request, "patient_profile_id", None)},
            )
            conv = (
                (
                    await self.session.execute(
                        text("""SELECT * FROM public.chat_conversations
              WHERE user_id=:uid AND session_id=:sid FOR UPDATE"""),
                        {"uid": user.id, "sid": request.session_id},
                    )
                )
                .mappings()
                .one()
            )
            if conv.get("patient_profile_id") != getattr(request, "patient_profile_id", None):
                raise HTTPException(409, "Hội thoại đã thuộc hồ sơ khác. Hãy mở hội thoại mới.")
            previous = (
                (
                    await self.session.execute(
                        text("""SELECT * FROM public.chat_turns
              WHERE conversation_id=:cid AND request_id=:rid"""),
                        {"cid": conv["id"], "rid": request.request_id},
                    )
                )
                .mappings()
                .first()
            )
            if previous and previous["user_text"] != request.message:
                log_event(
                    logger,
                    logging.WARNING,
                    "chat.turn.idempotency_conflict",
                    description="Chat turn request id was reused with different message content",
                    user_id=str(user.id),
                    session_id=request.session_id,
                    request_id=str(request.request_id),
                    conversation_id=str(conv["id"]),
                )
                raise HTTPException(409, "Mã lượt chat đã được dùng cho một tin nhắn khác.")
            if previous and previous["status"] == "completed":
                log_event(
                    logger,
                    logging.INFO,
                    "chat.turn.cached",
                    description="A completed chat turn was returned from the idempotency record",
                    user_id=str(user.id),
                    session_id=request.session_id,
                    request_id=str(request.request_id),
                    conversation_id=str(conv["id"]),
                )
                return {"cached": previous["result"], "conversation_id": conv["id"]}
            claimed = (
                await self.session.execute(
                    text("""UPDATE public.chat_conversations SET
              lease_token=:lease,busy_until=now()+interval '5 minutes'
              WHERE id=:cid AND (busy_until IS NULL OR busy_until<now()) RETURNING id"""),
                    {"lease": lease, "cid": conv["id"]},
                )
            ).first()
            if not claimed:
                log_event(
                    logger,
                    logging.WARNING,
                    "chat.turn.lease_unavailable",
                    description="Chat turn was rejected because the conversation is being processed",
                    user_id=str(user.id),
                    session_id=request.session_id,
                    request_id=str(request.request_id),
                    conversation_id=str(conv["id"]),
                )
                raise HTTPException(409, "Cuộc trò chuyện đang xử lý một tin nhắn. Vui lòng đợi.")
            await self.session.execute(
                text("""INSERT INTO public.chat_turns(id,conversation_id,request_id,user_text,status)
              VALUES(:id,:cid,:rid,:message,'processing') ON CONFLICT(conversation_id,request_id)
              DO UPDATE SET status='processing',assistant_text=NULL,result=NULL"""),
                {"id": uuid4(), "cid": conv["id"], "rid": request.request_id, "message": request.message},
            )
            turn = {
                "conversation_id": conv["id"],
                "lease": lease,
                "request_id": request.request_id,
                "checkpoint": conv["checkpoint"] or {},
            }
            log_event(
                logger,
                logging.INFO,
                "chat.turn.initialized",
                description="Chat turn was leased and marked as processing",
                user_id=str(user.id),
                session_id=request.session_id,
                request_id=str(request.request_id),
                conversation_id=str(conv["id"]),
            )
            return turn

    async def complete(self, turn, result, state):
        log_event(
            logger,
            logging.INFO,
            "chat.turn.complete.start",
            description="Starting chat turn checkpoint and response persistence",
            conversation_id=str(turn["conversation_id"]),
            request_id=str(turn["request_id"]),
            state_fields=sorted(key for key in state if key in STATE_FIELDS),
        )
        checkpoint = {key: state[key] for key in STATE_FIELDS if key in state}
        # These entries are data from the conversation, never authorization claims.
        async with self.session.begin():
            owned = (
                await self.session.execute(
                    text("""UPDATE public.chat_conversations SET checkpoint=CAST(:state AS jsonb),
              updated_at=now(),lease_token=NULL,busy_until=NULL WHERE id=:cid AND lease_token=:lease RETURNING id"""),
                    {
                        "state": json.dumps(checkpoint, ensure_ascii=False, default=str),
                        "cid": turn["conversation_id"],
                        "lease": turn["lease"],
                    },
                )
            ).first()
            if not owned:
                log_event(
                    logger,
                    logging.WARNING,
                    "chat.turn.complete.lease_expired",
                    description="Chat turn completion was rejected because the lease is no longer owned",
                    conversation_id=str(turn["conversation_id"]),
                    request_id=str(turn["request_id"]),
                )
                raise HTTPException(409, "Lượt chat đã hết hiệu lực. Vui lòng tải lại cuộc trò chuyện.")
            await self.session.execute(
                text("""UPDATE public.chat_turns SET status='completed',assistant_text=:answer,result=CAST(:result AS jsonb)
              WHERE conversation_id=:cid AND request_id=:rid"""),
                {
                    "answer": result["response"],
                    "result": json.dumps(result, ensure_ascii=False, default=str),
                    "cid": turn["conversation_id"],
                    "rid": turn["request_id"],
                },
            )

        log_event(
            logger,
            logging.INFO,
            "chat.turn.complete.done",
            description="Chat turn response and checkpoint were persisted",
            conversation_id=str(turn["conversation_id"]),
            request_id=str(turn["request_id"]),
            state_field_count=len(checkpoint),
        )

    async def fail(self, turn):
        log_event(
            logger,
            logging.INFO,
            "chat.turn.fail.start",
            description="Starting chat turn lease release after processing failure",
            conversation_id=str(turn["conversation_id"]),
            request_id=str(turn["request_id"]),
        )
        async with self.session.begin():
            owned = (
                await self.session.execute(
                    text("""UPDATE public.chat_conversations SET busy_until=NULL,lease_token=NULL
              WHERE id=:cid AND lease_token=:lease RETURNING id"""),
                    {"cid": turn["conversation_id"], "lease": turn["lease"]},
                )
            ).first()
            if owned:
                await self.session.execute(
                    text("UPDATE public.chat_turns SET status='failed' WHERE conversation_id=:cid AND request_id=:rid"),
                    {"cid": turn["conversation_id"], "rid": turn["request_id"]},
                )
        log_event(
            logger,
            logging.INFO,
            "chat.turn.fail.done",
            description="Chat turn lease was released and failure status was recorded when owned",
            conversation_id=str(turn["conversation_id"]),
            request_id=str(turn["request_id"]),
            turn_owned=bool(owned),
        )

    async def delete_conversation(self, user, session_id):
        # The same row lock as begin_turn prevents deletion during an active turn.
        async with self.session.begin():
            row = (
                (
                    await self.session.execute(
                        text("""SELECT id, busy_until > now() AS processing FROM public.chat_conversations
                WHERE user_id=:uid AND session_id=:sid FOR UPDATE"""),
                        {"uid": user.id, "sid": session_id},
                    )
                )
                .mappings()
                .first()
            )
            if not row:
                raise HTTPException(404, "Không tìm thấy cuộc trò chuyện.")
            if row["processing"]:
                raise HTTPException(409, "Cuộc trò chuyện đang xử lý. Vui lòng chờ trước khi xóa.")
            from src.medical_assistant.agent.graph import checkpointer

            await checkpointer.adelete_thread(graph_thread(session_id, user))
            await self.session.execute(
                text("DELETE FROM public.chat_conversations WHERE id=:cid AND user_id=:uid"),
                {"cid": row["id"], "uid": user.id},
            )

    async def list_conversations(self, user_id, limit=30, offset=0, patient_profile_id=None):
        log_event(
            logger,
            logging.INFO,
            "chat.conversation.list.start",
            description="Starting account conversation list query",
            user_id=str(user_id),
            limit=limit,
            offset=offset,
        )
        rows = (
            (
                await self.session.execute(
                    text("""SELECT session_id,title,created_at,updated_at FROM public.chat_conversations
          WHERE user_id=:uid AND (
            (CAST(:pid AS uuid) IS NOT NULL AND patient_profile_id=CAST(:pid AS uuid)) OR
            (CAST(:pid AS uuid) IS NULL AND (patient_profile_id IS NULL OR patient_profile_id IN
              (SELECT id FROM public.patient_profiles WHERE linked_user_id=:uid))))
          ORDER BY updated_at DESC,id DESC LIMIT :limit OFFSET :offset"""),
                    {"uid": user_id, "limit": limit + 1, "offset": offset, "pid": patient_profile_id},
                )
            )
            .mappings()
            .all()
        )
        await self.session.commit()
        response = {"conversations": [dict(r) for r in rows[:limit]], "has_more": len(rows) > limit}
        log_event(
            logger,
            logging.INFO,
            "chat.conversation.list.done",
            description="Account conversations were listed",
            user_id=str(user_id),
            count=len(response["conversations"]),
            has_more=response["has_more"],
        )
        return response

    async def history(self, user_id, session_id, limit=50, offset=0):
        log_event(
            logger,
            logging.INFO,
            "chat.history.start",
            description="Starting account chat history query",
            user_id=str(user_id),
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
        conv = (
            (
                await self.session.execute(
                    text(
                        "SELECT id,title,checkpoint FROM public.chat_conversations WHERE user_id=:uid AND session_id=:sid"
                    ),
                    {"uid": user_id, "sid": session_id},
                )
            )
            .mappings()
            .first()
        )
        if not conv:
            await self.session.commit()
            log_event(
                logger,
                logging.WARNING,
                "chat.history.not_found",
                description="Chat history lookup returned no conversation for the session",
                user_id=str(user_id),
                session_id=session_id,
            )
            return {
                "title": "Cuộc trò chuyện mới",
                "turns": [],
                "has_more": False,
            }
        rows = (
            (
                await self.session.execute(
                    text("""SELECT id,request_id,user_text,assistant_text,result,status,created_at FROM public.chat_turns
          WHERE conversation_id=:cid ORDER BY created_at DESC,id DESC LIMIT :limit OFFSET :offset"""),
                    {"cid": conv["id"], "limit": limit + 1, "offset": offset},
                )
            )
            .mappings()
            .all()
        )
        await self.session.commit()
        response = {
            "title": conv["title"],
            "turns": [dict(r) for r in reversed(rows[:limit])],
            "has_more": len(rows) > limit,
        }
        log_event(
            logger,
            logging.INFO,
            "chat.history.done",
            description="Account chat history was loaded",
            user_id=str(user_id),
            session_id=session_id,
            conversation_id=str(conv["id"]),
            turn_count=len(response["turns"]),
            has_more=response["has_more"],
        )
        return response

    async def checkpoint(self, user_id, session_id):
        log_event(
            logger,
            logging.INFO,
            "chat.checkpoint.start",
            description="Starting account chat checkpoint query",
            user_id=str(user_id),
            session_id=session_id,
        )
        result = (
            await self.session.execute(
                text("SELECT checkpoint FROM public.chat_conversations WHERE user_id=:uid AND session_id=:sid"),
                {"uid": user_id, "sid": session_id},
            )
        ).scalar_one_or_none()
        await self.session.commit()
        checkpoint = result or {}
        log_event(
            logger,
            logging.INFO,
            "chat.checkpoint.done",
            description="Account chat checkpoint was loaded",
            user_id=str(user_id),
            session_id=session_id,
            has_checkpoint=bool(checkpoint),
        )
        return checkpoint
