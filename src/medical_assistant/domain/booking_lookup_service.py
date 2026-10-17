"""Booking lookup and conversational booking confirmation service."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select

from src.db.session import get_session_factory
from src.models.booking import Booking
from src.models.doctor import Doctor
from src.models.facility import Facility
from src.models.specialty import Specialty
from src.models.user import User
from src.models.workbench import CoordinationCase as Case

logger = logging.getLogger(__name__)
VN_TZ = timezone(timedelta(hours=7))


def _format_vn_date_str(iso_or_str: str | None) -> str:
    if not iso_or_str:
        return "Theo điều phối viên sắp xếp"
    try:
        # Check if contains time
        if "t" in iso_or_str.lower():
            dt = datetime.fromisoformat(iso_or_str)
            weekday_vn = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ nhật"}.get(
                dt.weekday(), ""
            )
            return f"{weekday_vn}, ngày {dt.strftime('%d/%m/%Y')} (lúc {dt.strftime('%H:%M')})"
        else:
            d = date.fromisoformat(iso_or_str)
            weekday_vn = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ nhật"}.get(
                d.weekday(), ""
            )
            return f"{weekday_vn}, ngày {d.strftime('%d/%m/%Y')}"
    except Exception:
        return str(iso_or_str)


class BookingLookupService:
    def __init__(self):
        self.session_factory = get_session_factory()

    async def cancel_patient_request(
        self, code: str, user_id: str | UUID | None = None, guest_token: str | None = None
    ) -> dict[str, Any]:
        """Bệnh nhân tự hủy yêu cầu đặt lịch (mã YC-xxxx) qua chat.

        Chỉ tìm trong các yêu cầu thuộc chính tài khoản / phiên khách (cùng phạm vi với tra cứu lịch).
        Yêu cầu còn "new" (chưa ai xử lý, chưa chốt lịch) → hủy luôn. Đã có điều phối viên xử lý hoặc đã
        chốt lịch → không tự hủy, chỉ ghi nhận để điều phối viên liên hệ (tránh lệch giữ chỗ / đặt cọc).
        Trả về {"result": "cancelled" | "handoff" | "not_found", "code": ...}.
        """
        import hashlib

        from src.services.workbench import bump, event

        suffix = code.upper().removeprefix("YC-").lower()
        owners = []
        if user_id:
            owners.append(Case.patient_id == UUID(str(user_id)))
            owners.append(Case.owner_key == f"user:{user_id}")
        if guest_token:
            owners.append(Case.owner_key == "guest:" + hashlib.sha256(guest_token.encode()).hexdigest())
        if not owners or not re.fullmatch(r"[0-9a-f]{8}", suffix):
            return {"result": "not_found", "code": code}

        async with self.session_factory() as db, db.begin():
            rows = (
                (
                    await db.execute(
                        select(Case)
                        .where(or_(*owners), Case.status.notin_(["cancelled", "completed"]))
                        .order_by(Case.created_at.desc())
                        .limit(20)
                        .with_for_update()
                    )
                )
                .scalars()
                .all()
            )
            case = next((c for c in rows if str(c.id).startswith(suffix)), None)
            if case is None:
                return {"result": "not_found", "code": code}
            if case.status == "new" and not case.booking_id and not case.assigned_to:
                case.status = "cancelled"
                case.follow_up_at = None
                event(db, case, None, "patient_cancelled", "Bệnh nhân tự hủy yêu cầu qua chat")
                bump(case)
                return {"result": "cancelled", "code": code}
            event(db, case, None, "patient_cancel_requested", "Bệnh nhân yêu cầu hủy lịch qua chat")
            bump(case)
            return {"result": "handoff", "code": code}

    async def reschedule_patient_request(
        self,
        code: str,
        new_date: str | None,
        new_period: str | None,
        user_id: str | UUID | None = None,
        guest_token: str | None = None,
    ) -> dict[str, Any]:
        """Bệnh nhân xin đổi ngày/buổi khám cho yêu cầu YC-xxxx (cùng phạm vi sở hữu như hủy).

        Yêu cầu còn "new" → cập nhật ngày/buổi mong muốn ngay. Đã có người xử lý / đã chốt lịch → chỉ ghi
        nhận để điều phối viên đổi lịch (đổi lịch đã chốt cần giữ chỗ mới, không tự làm được).
        """
        import hashlib

        from src.services.workbench import bump, event

        suffix = code.upper().removeprefix("YC-").lower()
        owners = []
        if user_id:
            owners.append(Case.patient_id == UUID(str(user_id)))
            owners.append(Case.owner_key == f"user:{user_id}")
        if guest_token:
            owners.append(Case.owner_key == "guest:" + hashlib.sha256(guest_token.encode()).hexdigest())
        if not owners or not re.fullmatch(r"[0-9a-f]{8}", suffix):
            return {"result": "not_found", "code": code}

        async with self.session_factory() as db, db.begin():
            rows = (
                (
                    await db.execute(
                        select(Case)
                        .where(or_(*owners), Case.status.notin_(["cancelled", "completed"]))
                        .order_by(Case.created_at.desc())
                        .limit(20)
                        .with_for_update()
                    )
                )
                .scalars()
                .all()
            )
            case = next((c for c in rows if str(c.id).startswith(suffix)), None)
            if case is None:
                return {"result": "not_found", "code": code}
            details = {"preferred_date": new_date, "preferred_period": new_period}
            if case.status == "new" and not case.booking_id and not case.assigned_to:
                patient = dict(case.patient or {})
                if new_date:
                    patient["preferred_date"] = new_date
                if new_period:
                    patient["preferred_period"] = new_period
                case.patient = patient
                event(db, case, None, "patient_rescheduled", "Bệnh nhân đổi ngày khám mong muốn qua chat", details)
                bump(case)
                return {"result": "updated", "code": code}
            event(db, case, None, "patient_reschedule_requested", "Bệnh nhân xin đổi lịch qua chat", details)
            bump(case)
            return {"result": "handoff", "code": code}

    async def lookup_patient_appointments(
        self,
        user_id: str | UUID | None = None,
        phone: str | None = None,
        guest_token: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Look up all active appointments (bookings and intake cases) for the patient."""
        u_id = UUID(str(user_id)) if user_id else None
        clean_phone = re.sub(r"\D", "", phone or "")
        records: list[dict[str, Any]] = []

        async with self.session_factory() as db:
            # 1. Lookup Bookings from bookings table
            if u_id:
                stmt_bookings = (
                    select(Booking)
                    .where(Booking.user_id == u_id, Booking.status.notin_(["cancelled", "rejected"]))
                    .order_by(Booking.starts_at.desc())
                    .limit(10)
                )
                b_rows = (await db.execute(stmt_bookings)).scalars().all()
                for b in b_rows:
                    doc = await db.get(Doctor, b.doctor_id)
                    fac = await db.get(Facility, b.facility_id)
                    spec = await db.get(Specialty, b.specialty_id)
                    code = "BK-" + str(b.id).split("-")[0].upper()
                    status_text = "Đã xác nhận" if b.status == "confirmed" else "Đang chờ duyệt"
                    records.append(
                        {
                            "type": "booking",
                            "id": str(b.id),
                            "code": code,
                            "status": b.status,
                            "status_display": status_text,
                            "facility_name": fac.name if fac else "Vinmec",
                            "specialty_name": spec.name if spec else "Khám chuyên khoa",
                            "doctor_name": doc.full_name if doc else "Bác sĩ chuyên khoa",
                            "starts_at": b.starts_at.isoformat() if b.starts_at else None,
                            "datetime_display": _format_vn_date_str(b.starts_at.isoformat() if b.starts_at else None),
                            "reason": b.reason,
                        }
                    )

            # 2. Lookup Cases from coordination_cases table
            conditions = []
            if u_id:
                conditions.append(Case.patient_id == u_id)
                conditions.append(Case.owner_key == f"user:{u_id}")
            if guest_token:
                import hashlib

                guest_key = "guest:" + hashlib.sha256(guest_token.encode()).hexdigest()
                conditions.append(Case.owner_key == guest_key)

            if conditions:
                stmt_cases = (
                    select(Case)
                    .where(
                        or_(*conditions),
                        Case.status.notin_(["cancelled", "completed", "observing"]),
                        Case.booking_id.is_(None),  # Don't duplicate if already converted to booking
                    )
                    .order_by(Case.created_at.desc())
                    .limit(10)
                )
                c_rows = (await db.execute(stmt_cases)).scalars().all()
                for c in c_rows:
                    p = c.patient or {}
                    ai = c.ai_snapshot or {}
                    pref_date = p.get("preferred_date")
                    pref_period = p.get("preferred_period")
                    period_vn = (
                        "Buổi sáng (08:00 - 12:00)"
                        if pref_period == "morning"
                        else ("Buổi chiều (13:00 - 17:00)" if pref_period == "afternoon" else "Linh hoạt")
                    )
                    date_display = _format_vn_date_str(pref_date) + (f" • {period_vn}" if pref_date else "")

                    fac_name = p.get("facility_preference") or "Bệnh viện ĐKQT Vinmec"
                    spec_name = (
                        ai.get("suggested_department_name") or c.plan.get("specialty_name") or "Chuyên khoa phù hợp"
                    )
                    doc_name = p.get("doctor_name") or "Điều phối viên y tế sắp xếp bác sĩ phù hợp nhất"
                    code = "YC-" + str(c.id).split("-")[0].upper()
                    records.append(
                        {
                            "type": "case",
                            "id": str(c.id),
                            "code": code,
                            "status": c.status,
                            "status_display": "Đang chờ điều phối viên liên hệ xác nhận",
                            "facility_name": fac_name,
                            "specialty_name": spec_name,
                            "doctor_name": doc_name,
                            "patient_name": p.get("name") or name or "Quý khách",
                            "patient_phone": p.get("phone") or clean_phone,
                            "starts_at": pref_date,
                            "datetime_display": date_display,
                            "reason": p.get("notes") or "Đăng ký khám chuyên khoa",
                        }
                    )

        # Format output message
        if not records:
            msg = (
                "Dạ thưa bác, em đã tra cứu thông tin trên hệ thống nhưng hiện tại **chưa ghi nhận lịch khám hoặc phiếu đăng ký nào đang chờ xử lý** dưới tài khoản của bác.\n\n"
                "💡 Bác có thể kiểm tra lại số điện thoại đăng ký hoặc để em hỗ trợ bác kết nối đặt lịch khám mới tại Vinmec ngay bây giờ nhé ạ!"
            )
            return {"found": False, "records": [], "formatted_response": msg}

        lines = ["Dạ, em đã tra cứu thấy thông tin lịch hẹn / phiếu đăng ký khám của bác trên hệ thống như sau:\n"]
        for idx, r in enumerate(records, 1):
            p_name = r.get("patient_name") or name or "Bệnh nhân"
            p_phone = r.get("patient_phone") or clean_phone
            lines.append(
                f"📋 **Lịch hẹn #{idx} (Mã: `{r['code']}`):**\n"
                f"• 👤 **Bệnh nhân:** {p_name}\n"
                + (f"• 📞 **Số điện thoại:** {p_phone}\n" if p_phone else "")
                + f"• 🏥 **Cơ sở khám:** {r['facility_name']}\n"
                f"• 🩺 **Chuyên khoa:** {r['specialty_name']}\n"
                f"• 👨‍⚕️ **Bác sĩ:** {r['doctor_name']}\n"
                f"• 📅 **Thời gian khám:** {r['datetime_display']}\n"
                f"• 🔖 **Trạng thái:** {r['status_display']}\n"
                + (f"• 📝 **Lý do khám:** {r['reason']}\n" if r.get("reason") else "")
            )

        lines.append(
            "💡 Bác cũng có thể xem chi tiết và theo dõi tiến độ cập nhật bất kỳ lúc nào tại mục **Tiến trình điều trị** trên thanh menu nhé ạ!"
        )

        return {
            "found": True,
            "records": records,
            "formatted_response": "\n".join(lines),
        }

    async def auto_commit_conversational_booking(
        self,
        intake_data: dict[str, Any],
        user: Any | None = None,
        session_id: str = "",
        guest_token: str = "",
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Automatically commit the booking intake to coordination_cases when the patient confirms in chat."""
        from types import SimpleNamespace

        from src.services.workbench import intake

        state = state or {}
        p_name = (
            intake_data.get("patient_name") or state.get("patient_name") or (user.full_name if user else "Bệnh nhân")
        )
        p_phone = intake_data.get("patient_phone") or state.get("patient_phone") or (user.phone if user else "")
        p_dob_str = (
            intake_data.get("date_of_birth")
            or state.get("patient_dob")
            or (str(user.date_of_birth) if user and user.date_of_birth else "1990-01-01")
        )
        try:
            p_dob = date.fromisoformat(p_dob_str)
        except Exception:
            p_dob = date(1990, 1, 1)

        p_gender = intake_data.get("gender") or state.get("patient_gender") or (user.gender if user else "other")
        pref_date_str = intake_data.get("preferred_date")
        pref_date = None
        if pref_date_str:
            try:
                pref_date = date.fromisoformat(pref_date_str)
            except Exception:
                pref_date = None

        p_email = (
            intake_data.get("patient_email")
            or state.get("patient_email")
            or (getattr(user, "email", None) if user else None)
        )

        req = SimpleNamespace(
            session_id=session_id,
            patient_name=p_name.strip(),
            patient_phone=p_phone.strip(),
            patient_email=p_email,
            date_of_birth=p_dob,
            gender=p_gender,
            guardian_name=None,
            guardian_phone=None,
            consent_to_contact=True,
            preferred_date=pref_date,
            preferred_period=intake_data.get("preferred_period") or "morning",
            facility_preference=intake_data.get("facility_preference")
            or "Chưa chọn cơ sở (điều phối viên tư vấn cơ sở phù hợp)",
            contact_time_preference=None,
            patient_notes=intake_data.get("patient_notes")
            or intake_data.get("clinical_summary")
            or "Đăng ký khám qua Trợ lý AI",
            specialty_name=intake_data.get("specialty_name")
            or state.get("suggested_department_name")
            or "Chưa xác định chuyên khoa (điều phối viên tư vấn)",
            specialty_code=intake_data.get("specialty_code") or state.get("suggested_department_code") or "",
        )

        maker = self.session_factory
        try:
            session_ctx = maker()
        except TypeError:
            session_ctx = maker
        if callable(session_ctx) and not hasattr(session_ctx, "__aenter__"):
            session_ctx = session_ctx()

        async with session_ctx as db, db.begin():
            effective_user = user
            if effective_user is None and state.get("user_id"):
                try:
                    effective_user = await db.get(User, UUID(str(state["user_id"])))
                except Exception:
                    effective_user = None
            case = await intake(db, req, effective_user, guest_token, state)
            request_id = str(case.id)
            request_code = "YC-" + request_id.split("-")[0].upper()

        logger.info(
            "Conversational booking auto-committed", extra={"case_id": request_id, "request_code": request_code}
        )
        return {
            "saved": True,
            "request_id": request_id,
            "request_code": request_code,
            "status": "PENDING_CONTACT",
        }


_lookup_service: BookingLookupService | None = None


def get_booking_lookup_service() -> BookingLookupService:
    global _lookup_service
    if _lookup_service is None:
        _lookup_service = BookingLookupService()
    return _lookup_service
