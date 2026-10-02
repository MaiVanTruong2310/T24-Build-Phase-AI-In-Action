"""Account-owned chat archive, idempotent turns, and bounded graph checkpoints."""

import json
from datetime import date
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text

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
}


def graph_thread(session_id, user=None):
    return f"user:{user.id}:{session_id}" if user else f"guest:{session_id}"


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
        lease = uuid4()
        async with self.session.begin():
            await self.session.execute(
                text("""INSERT INTO public.chat_conversations(id,user_id,session_id,title)
              VALUES(:id,:uid,:sid,:title) ON CONFLICT(user_id,session_id) DO NOTHING"""),
                {"id": uuid4(), "uid": user.id, "sid": request.session_id, "title": request.message[:80]},
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

    async def fail(self, turn):
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

    async def list_conversations(self, user_id, limit=30, offset=0):
        rows = (
            (
                await self.session.execute(
                    text("""SELECT session_id,title,created_at,updated_at FROM public.chat_conversations
          WHERE user_id=:uid ORDER BY updated_at DESC,id DESC LIMIT :limit OFFSET :offset"""),
                    {"uid": user_id, "limit": limit + 1, "offset": offset},
                )
            )
            .mappings()
            .all()
        )
        await self.session.commit()
        return {"conversations": [dict(r) for r in rows[:limit]], "has_more": len(rows) > limit}

    async def history(self, user_id, session_id, limit=50, offset=0):
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
            raise HTTPException(404, "Không tìm thấy cuộc trò chuyện.")
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
        result = (
            await self.session.execute(
                text("SELECT checkpoint FROM public.chat_conversations WHERE user_id=:uid AND session_id=:sid"),
                {"uid": user_id, "sid": session_id},
            )
        ).scalar_one_or_none()
        await self.session.commit()
        return result or {}
