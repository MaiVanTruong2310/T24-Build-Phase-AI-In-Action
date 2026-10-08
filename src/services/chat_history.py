"""Account-owned chat archive, idempotent turns, and bounded graph checkpoints."""

import json
import logging
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text

from src.config import get_settings
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
        now = datetime.now(UTC)

        if get_settings().use_unified_conversation:
            async with self.session.begin():
                row = (
                    (
                        await self.session.execute(
                            text("""SELECT c.id, ctx.context_data
                      FROM public.conversations c
                      JOIN public.patient_chat_context ctx ON ctx.conversation_id = c.id
                      WHERE c.patient_id = :uid AND ctx.context_data->>'session_id' = :sid
                      FOR UPDATE"""),
                            {"uid": user.id, "sid": request.session_id},
                        )
                    )
                    .mappings()
                    .first()
                )

                if not row:
                    cid = uuid4()
                    ctx_data = {
                        "session_id": request.session_id,
                        "title": request.message[:80],
                        "patient_profile_id": str(getattr(request, "patient_profile_id", None))
                        if getattr(request, "patient_profile_id", None)
                        else None,
                        "lease_token": str(lease),
                        "busy_until": (now + timedelta(minutes=5)).isoformat(),
                        "checkpoint": {},
                    }
                    await self.session.execute(
                        text("""INSERT INTO public.conversations (
                            id, category, mode, status, patient_id, created_by_type, created_by_id, created_at, updated_at
                        ) VALUES (
                            :cid, 'PATIENT_SUPPORT', 'AI', 'ACTIVE', :uid, 'PATIENT', :uid, :now, :now
                        )"""),
                        {"cid": cid, "uid": user.id, "now": now},
                    )
                    await self.session.execute(
                        text("""INSERT INTO public.patient_chat_context (
                            conversation_id, patient_id, current_stage, context_data, updated_at
                        ) VALUES (
                            :cid, :uid, 'GENERAL_SUPPORT', CAST(:ctx AS jsonb), :now
                        )"""),
                        {"cid": cid, "uid": user.id, "ctx": json.dumps(ctx_data), "now": now},
                    )
                    await self.session.execute(
                        text("""INSERT INTO public.conversation_participants (
                            id, conversation_id, participant_type, participant_id, role, joined_at
                        ) VALUES
                            (:p1, :cid, 'PATIENT', :uid, 'patient', :now),
                            (:p2, :cid, 'AGENT', NULL, 'assistant', :now)"""),
                        {"p1": uuid4(), "p2": uuid4(), "cid": cid, "uid": user.id, "now": now},
                    )
                    conv_id = cid
                    checkpoint = {}
                else:
                    conv_id = row["id"]
                    ctx = row["context_data"] or {}
                    pid = getattr(request, "patient_profile_id", None)
                    if pid and ctx.get("patient_profile_id") != str(pid):
                        raise HTTPException(409, "Hội thoại đã thuộc hồ sơ khác. Hãy mở hội thoại mới.")

                    prev_msg = (
                        (
                            await self.session.execute(
                                text("""SELECT content, metadata FROM public.messages
                          WHERE conversation_id = :cid AND metadata->>'request_id' = :rid AND sender_type = 'PATIENT'"""),
                                {"cid": conv_id, "rid": str(request.request_id)},
                            )
                        )
                        .mappings()
                        .first()
                    )

                    if prev_msg and prev_msg["content"] != request.message:
                        raise HTTPException(409, "Mã lượt chat đã được dùng cho một tin nhắn khác.")

                    if prev_msg:
                        agent_msg = (
                            (
                                await self.session.execute(
                                    text("""SELECT content, metadata FROM public.messages
                              WHERE conversation_id = :cid AND metadata->>'request_id' = :rid AND sender_type = 'AGENT'"""),
                                    {"cid": conv_id, "rid": str(request.request_id)},
                                )
                            )
                            .mappings()
                            .first()
                        )
                        if agent_msg and agent_msg.get("metadata", {}).get("result"):
                            return {"cached": agent_msg["metadata"]["result"], "conversation_id": conv_id}

                    ctx["lease_token"] = str(lease)
                    ctx["busy_until"] = (now + timedelta(minutes=5)).isoformat()
                    await self.session.execute(
                        text("""UPDATE public.patient_chat_context
                      SET context_data = CAST(:ctx AS jsonb), updated_at = :now
                      WHERE conversation_id = :cid"""),
                        {"cid": conv_id, "ctx": json.dumps(ctx), "now": now},
                    )
                    checkpoint = ctx.get("checkpoint") or {}

            turn = {
                "conversation_id": conv_id,
                "lease": lease,
                "request_id": request.request_id,
                "checkpoint": checkpoint,
                "user_text": request.message,
                "user_id": user.id,
                "session_id": request.session_id,
            }
            log_event(
                logger,
                logging.INFO,
                "chat.turn.initialized",
                description="Chat turn was leased and marked as processing",
                user_id=str(user.id),
                session_id=request.session_id,
                request_id=str(request.request_id),
                conversation_id=str(conv_id),
            )
            return turn

        # Fallback to legacy
        async with self.session.begin():
            await self.session.execute(
                text("""INSERT INTO public.chat_conversations(id,user_id,session_id,title,patient_profile_id)
              VALUES(:id,:uid,:sid,:title,:pid) ON CONFLICT(user_id,session_id) DO NOTHING"""),
                {
                    "id": uuid4(),
                    "uid": user.id,
                    "sid": request.session_id,
                    "title": request.message[:80],
                    "pid": getattr(request, "patient_profile_id", None),
                },
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
                raise HTTPException(409, "Mã lượt chat đã được dùng cho một tin nhắn khác.")
            if previous and previous["status"] == "completed":
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
                raise HTTPException(409, "Cuộc trò chuyện đang xử lý một tin nhắn. Vui lòng đợi.")
            await self.session.execute(
                text("""INSERT INTO public.chat_turns(id,conversation_id,request_id,user_text,status)
              VALUES(:id,:cid,:rid,:message,'processing') ON CONFLICT(conversation_id,request_id)
              DO UPDATE SET status='processing',assistant_text=NULL,result=NULL"""),
                {"id": uuid4(), "cid": conv["id"], "rid": request.request_id, "message": request.message},
            )
            return {
                "conversation_id": conv["id"],
                "lease": lease,
                "request_id": request.request_id,
                "checkpoint": conv["checkpoint"] or {},
            }

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
        now = datetime.now(UTC)
        cid = turn["conversation_id"]
        uid = turn.get("user_id")
        rid = str(turn["request_id"])

        if get_settings().use_unified_conversation:
            async with self.session.begin():
                ctx_row = (
                    (
                        await self.session.execute(
                            text(
                                "SELECT context_data FROM public.patient_chat_context WHERE conversation_id = :cid FOR UPDATE"
                            ),
                            {"cid": cid},
                        )
                    )
                    .mappings()
                    .first()
                )

                if ctx_row:
                    ctx = ctx_row["context_data"] or {}
                    ctx["checkpoint"] = checkpoint
                    ctx["lease_token"] = None
                    ctx["busy_until"] = None
                    await self.session.execute(
                        text("""UPDATE public.patient_chat_context
                      SET context_data = CAST(:ctx AS jsonb), updated_at = :now
                      WHERE conversation_id = :cid"""),
                        {"cid": cid, "ctx": json.dumps(ctx, ensure_ascii=False, default=str), "now": now},
                    )

                await self.session.execute(
                    text("UPDATE public.conversations SET updated_at = :now, status = 'ACTIVE' WHERE id = :cid"),
                    {"cid": cid, "now": now},
                )

                if turn.get("user_text"):
                    await self.session.execute(
                        text("""INSERT INTO public.messages (id, conversation_id, sender_type, sender_id, message_type, content, metadata, created_at)
                      VALUES (:id, :cid, 'PATIENT', :uid, 'TEXT', :content, CAST(:meta AS jsonb), :now)"""),
                        {
                            "id": uuid4(),
                            "cid": cid,
                            "uid": uid,
                            "content": turn["user_text"],
                            "meta": json.dumps({"request_id": rid}),
                            "now": now,
                        },
                    )

                agent_text = result.get("response", "")
                agent_meta = {
                    "request_id": rid,
                    "status": "completed",
                    "result": result,
                }
                await self.session.execute(
                    text("""INSERT INTO public.messages (id, conversation_id, sender_type, sender_id, message_type, content, metadata, created_at)
                  VALUES (:id, :cid, 'AGENT', NULL, 'TEXT', :content, CAST(:meta AS jsonb), :now)"""),
                    {
                        "id": uuid4(),
                        "cid": cid,
                        "content": agent_text,
                        "meta": json.dumps(agent_meta, ensure_ascii=False, default=str),
                        "now": now + timedelta(seconds=1),
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
            return

        # Fallback to legacy
        async with self.session.begin():
            await self.session.execute(
                text("""UPDATE public.chat_conversations SET checkpoint=CAST(:state AS jsonb),
              updated_at=now(),lease_token=NULL,busy_until=NULL WHERE id=:cid AND lease_token=:lease RETURNING id"""),
                {
                    "state": json.dumps(checkpoint, ensure_ascii=False, default=str),
                    "cid": turn["conversation_id"],
                    "lease": turn["lease"],
                },
            )
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

    async def fail(self, turn):
        cid = turn["conversation_id"]
        now = datetime.now(UTC)
        if get_settings().use_unified_conversation:
            async with self.session.begin():
                ctx_row = (
                    (
                        await self.session.execute(
                            text(
                                "SELECT context_data FROM public.patient_chat_context WHERE conversation_id = :cid FOR UPDATE"
                            ),
                            {"cid": cid},
                        )
                    )
                    .mappings()
                    .first()
                )
                if ctx_row:
                    ctx = ctx_row["context_data"] or {}
                    ctx["lease_token"] = None
                    ctx["busy_until"] = None
                    await self.session.execute(
                        text("""UPDATE public.patient_chat_context
                      SET context_data = CAST(:ctx AS jsonb), updated_at = :now
                      WHERE conversation_id = :cid"""),
                        {"cid": cid, "ctx": json.dumps(ctx), "now": now},
                    )
            return

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

    async def delete_conversation(self, user, session_id):
        if get_settings().use_unified_conversation:
            async with self.session.begin():
                row = (
                    (
                        await self.session.execute(
                            text("""SELECT c.id FROM public.conversations c
                      JOIN public.patient_chat_context ctx ON ctx.conversation_id = c.id
                      WHERE c.patient_id = :uid AND ctx.context_data->>'session_id' = :sid"""),
                            {"uid": user.id, "sid": session_id},
                        )
                    )
                    .mappings()
                    .first()
                )
                if not row:
                    raise HTTPException(404, "Không tìm thấy cuộc trò chuyện.")
                from src.medical_assistant.agent.graph import checkpointer

                await checkpointer.adelete_thread(graph_thread(session_id, user))
                await self.session.execute(
                    text("DELETE FROM public.conversations WHERE id = :cid"),
                    {"cid": row["id"]},
                )
            return

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
        if get_settings().use_unified_conversation:
            rows = (
                (
                    await self.session.execute(
                        text("""SELECT
                    c.id,
                    c.created_at,
                    c.updated_at,
                    ctx.context_data->>'session_id' as session_id,
                    COALESCE(ctx.context_data->>'title', 'Cuộc trò chuyện') as title
                  FROM public.conversations c
                  JOIN public.patient_chat_context ctx ON ctx.conversation_id = c.id
                  WHERE c.patient_id = :uid AND c.category = 'PATIENT_SUPPORT'
                  ORDER BY c.updated_at DESC
                  LIMIT :limit OFFSET :offset"""),
                        {"uid": user_id, "limit": limit + 1, "offset": offset},
                    )
                )
                .mappings()
                .all()
            )
            await self.session.commit()
            return {
                "conversations": [dict(r) for r in rows[:limit]],
                "has_more": len(rows) > limit,
            }

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
        return {"conversations": [dict(r) for r in rows[:limit]], "has_more": len(rows) > limit}

    async def history(self, user_id, session_id, limit=50, offset=0):
        if get_settings().use_unified_conversation:
            conv_row = (
                (
                    await self.session.execute(
                        text("""SELECT c.id, ctx.context_data
                  FROM public.conversations c
                  JOIN public.patient_chat_context ctx ON ctx.conversation_id = c.id
                  WHERE (:uid IS NULL OR c.patient_id = :uid) AND ctx.context_data->>'session_id' = :sid
                  ORDER BY c.updated_at DESC
                  LIMIT 1"""),
                        {"uid": user_id, "sid": session_id},
                    )
                )
                .mappings()
                .first()
            )

            if not conv_row:
                await self.session.commit()
                return {"title": "Cuộc trò chuyện mới", "turns": [], "has_more": False}

            cid = conv_row["id"]
            ctx = conv_row["context_data"] or {}
            title = ctx.get("title") or "Cuộc trò chuyện mới"

            msgs = (
                (
                    await self.session.execute(
                        text("""SELECT id, sender_type, content, metadata, created_at
                  FROM public.messages
                  WHERE conversation_id = :cid
                  ORDER BY created_at ASC"""),
                        {"cid": cid},
                    )
                )
                .mappings()
                .all()
            )
            await self.session.commit()

            turns = []
            i = 0
            while i < len(msgs):
                m = msgs[i]
                if m["sender_type"] == "PATIENT":
                    agent_msg = msgs[i + 1] if i + 1 < len(msgs) and msgs[i + 1]["sender_type"] == "AGENT" else None
                    meta = (agent_msg.get("metadata") or {}) if agent_msg else (m.get("metadata") or {})
                    turn_dict = {
                        "id": str(m["id"]),
                        "request_id": meta.get("request_id") or str(m["id"]),
                        "user_text": m["content"] or "",
                        "assistant_text": agent_msg["content"] if agent_msg else "",
                        "result": meta.get("result") or {"response": agent_msg["content"] if agent_msg else ""},
                        "status": meta.get("status") or "completed",
                        "created_at": m["created_at"].isoformat()
                        if hasattr(m["created_at"], "isoformat")
                        else str(m["created_at"]),
                    }
                    turns.append(turn_dict)
                    i += 2 if agent_msg else 1
                else:
                    i += 1

            paginated_turns = turns[-limit:] if limit else turns
            return {
                "title": title,
                "turns": paginated_turns,
                "has_more": len(turns) > limit,
            }

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
            return {"title": "Cuộc trò chuyện mới", "turns": [], "has_more": False}

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
        return {
            "title": conv["title"],
            "turns": [dict(r) for r in reversed(rows[:limit])],
            "has_more": len(rows) > limit,
        }

    async def checkpoint(self, user_id, session_id):
        if get_settings().use_unified_conversation:
            result = (
                await self.session.execute(
                    text("""SELECT ctx.context_data->'checkpoint' as checkpoint
                  FROM public.conversations c
                  JOIN public.patient_chat_context ctx ON ctx.conversation_id = c.id
                  WHERE (:uid IS NULL OR c.patient_id = :uid) AND ctx.context_data->>'session_id' = :sid
                  ORDER BY c.updated_at DESC LIMIT 1"""),
                    {"uid": user_id, "sid": session_id},
                )
            ).scalar_one_or_none()
            await self.session.commit()
            return result or {}

        result = (
            await self.session.execute(
                text("SELECT checkpoint FROM public.chat_conversations WHERE user_id=:uid AND session_id=:sid"),
                {"uid": user_id, "sid": session_id},
            )
        ).scalar_one_or_none()
        await self.session.commit()
        return result or {}
