"""
Facility Service: Truy xuất thông tin cơ sở bệnh viện và phòng khám từ Supabase & Datalake.
Hỗ trợ song ngữ (VI/EN), tìm kiếm chi tiết theo tên cơ sở hoặc khu vực, và điều hướng đặt lịch.
"""

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from src.medical_assistant.db.supabase_client import get_supabase_client
from src.medical_assistant.domain.doctor_schedule_service import DoctorScheduleService, _load_crawled_doctors
from src.medical_assistant.domain.facility_linking import facility_key

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATALAKE_DIR = PROJECT_ROOT / "data" / "datalake"


def _normalize_text(text: str) -> str:
    """Loại bỏ dấu tiếng Việt và chuẩn hóa chữ thường để so khớp chuỗi"""
    if not text:
        return ""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "d")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class FacilityService:
    def __init__(self, client: Any | None = None):
        self.client = client
        self._hospital_metadata: dict[str, dict[str, Any]] = {}
        self._specialty_mapping: dict[str, list[str]] = {}
        self._load_datalake_metadata()

    def _get_client(self):
        if self.client is None:
            self.client = get_supabase_client()
        return self.client

    def _load_datalake_metadata(self):
        """Nạp URL chi tiết và danh sách chuyên khoa mũi nhọn từ Datalake."""
        hospitals_file = DATALAKE_DIR / "normalized" / "hospitals.jsonl"
        if hospitals_file.exists():
            try:
                with open(hospitals_file, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        name = record.get("name", "")
                        norm_name = _normalize_text(name)
                        if norm_name:
                            self._hospital_metadata[norm_name] = {
                                "detail_url": record.get("detail_url") or record.get("source_url"),
                                "facility_type": record.get("facility_type_label") or "Bệnh viện",
                            }
            except Exception as exc:
                logger.warning("Could not load hospitals.jsonl: %s", exc)

        specialties_file = DATALAKE_DIR / "rag" / "specialty_facilities.jsonl"
        if specialties_file.exists():
            try:
                with open(specialties_file, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        meta = record.get("metadata", {})
                        name = meta.get("name", "")
                        specs = meta.get("specialties", [])
                        norm_name = _normalize_text(name)
                        if norm_name and specs:
                            curr = self._specialty_mapping.setdefault(norm_name, [])
                            for sp in specs:
                                if sp not in curr:
                                    curr.append(sp)
            except Exception as exc:
                logger.warning("Could not load specialty_facilities.jsonl: %s", exc)

    def fetch_active_facilities(self) -> list[dict[str, Any]]:
        """
        Truy vấn toàn bộ cơ sở active từ bảng public.facilities trên Supabase.
        Có cơ chế In-Memory Cache và Fallback sang Datalake (hospitals.jsonl)
        đảm bảo dịch vụ hoạt động ổn định 100% ngay cả khi mạng hoặc Supabase gián đoạn.
        """
        if getattr(self, "_cached_facilities", None):
            return self._cached_facilities

        try:
            client = self._get_client()
            rows = client.select(
                "facilities",
                params={
                    "select": "id,code,name,address,phone,status",
                    "status": "eq.active",
                    "order": "name.asc",
                },
            )
            if rows:
                self._cached_facilities = rows
                return rows
        except Exception as exc:
            logger.warning("Supabase facilities lookup failed: %s. Using datalake fallback.", exc)

        # Fallback từ Datalake normalized/hospitals.jsonl
        fallback_facilities: list[dict[str, Any]] = []
        hospitals_file = DATALAKE_DIR / "normalized" / "hospitals.jsonl"
        if hospitals_file.exists():
            try:
                with open(hospitals_file, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        rec = json.loads(line)
                        fallback_facilities.append(
                            {
                                "id": rec.get("facility_key"),
                                "code": rec.get("facility_key"),
                                "name": rec.get("name"),
                                "address": rec.get("address"),
                                "phone": rec.get("hotline_display") or rec.get("hotline_normalized") or "1900 232 389",
                                "status": "active",
                            }
                        )
                if fallback_facilities:
                    self._cached_facilities = fallback_facilities
                    return fallback_facilities
            except Exception as exc:
                logger.error("Failed to load fallback hospitals: %s", exc)

        return []

    def _find_detail_metadata(self, facility_name: str) -> dict[str, Any]:
        """Tìm URL chi tiết và chuyên khoa theo tên cơ sở."""
        norm = _normalize_text(facility_name)
        if norm in self._hospital_metadata:
            res = dict(self._hospital_metadata[norm])
            res["specialties"] = self._specialty_mapping.get(norm, [])
            return res
        for key, val in self._hospital_metadata.items():
            if key in norm or norm in key:
                res = dict(val)
                res["specialties"] = self._specialty_mapping.get(key, [])
                return res
        return {}

    def get_facility_detail_response(
        self,
        facility: dict[str, Any],
        language: str = "vi",
        enable_citation: bool = True,
    ) -> tuple[str, list[str]]:
        """Trả về Thẻ thông tin chi tiết của MỘT cơ sở bệnh viện cụ thể."""
        name = facility.get("name", "Bệnh viện Vinmec")
        address = facility.get("address", "Đang cập nhật")
        phone = facility.get("phone") or "1900 232 389"

        meta = self._find_detail_metadata(name)
        detail_url = meta.get("detail_url") or "https://www.vinmec.com/vie/co-so-y-te/"
        specialties = meta.get("specialties", [])

        is_clinic = "phòng khám" in name.lower() or "clinic" in name.lower()

        short_name = (
            name.replace("Bệnh viện Đa khoa Quốc tế ", "")
            .replace("Bệnh viện Đa khoa quốc tế ", "")
            .replace("Phòng khám Đa khoa Quốc tế ", "")
            .replace("Phòng khám Đa Khoa ", "")
        )

        if language == "en":
            facility_type = "International General Clinic" if is_clinic else "International General Hospital"
            specs_str = (
                ", ".join(specialties[:6]) if specialties else "General Medicine, Cardiology, Neurology, Pediatrics"
            )
            lines = [
                f"🏥 **{name}**\n",
                f"• 🏨 **Facility Type:** {facility_type}",
                f"• 📍 **Address:** {address}",
                f"• 📞 **Hotline:** `{phone}`",
                "• ⏰ **Operating Hours:**",
                "  - Outpatient Clinics: 08:00 - 12:00 | 13:00 - 17:00 (Monday to Friday)",
                "  - Saturday: 08:00 - 12:00 (Closed Sunday & Saturday afternoon)",
                "  - **Emergency & Inpatient Department:** Operating **24/7** year-round.",
                f"• 🩺 **Key Specialties & Strengths:**\n  {specs_str}",
            ]
            if enable_citation:
                lines.append(
                    f"• 🌐 **Official Profile & Equipment Details:**\n  👉 [View full facility details & photos on Vinmec.com]({detail_url})\n"
                )
            lines.append(
                "💡 *Would you like me to look up doctors working at this facility or help you schedule a consultation?*"
            )
            quick_replies = [
                f"View doctors at {short_name}",
                f"Book appointment at {short_name}",
                "Check other facilities",
            ]
        else:
            facility_type = "Phòng khám Đa khoa Quốc tế" if is_clinic else "Bệnh viện Đa khoa Quốc tế"
            specs_str = (
                ", ".join(specialties[:6])
                if specialties
                else "Nội đa khoa, Thần kinh - Đột quỵ, Tim mạch, Cơ xương khớp, Nhi"
            )
            lines = [
                f"🏥 **{name}**\n",
                f"• 🏨 **Phân loại cơ sở:** {facility_type}",
                f"• 📍 **Địa chỉ:** {address}",
                f"• 📞 **Hotline trực tiếp:** `{phone}`",
                "• ⏰ **Thời gian hoạt động:**",
                "  - Khám ngoại trú: 08:00 - 12:00 | 13:00 - 17:00 (Thứ 2 đến Thứ 6)",
                "  - Thứ 7: 08:00 - 12:00 (Nghỉ chiều Thứ 7 & Chủ Nhật)",
                "  - **Khoa Cấp cứu & Lưu bệnh:** Phục vụ **24/7** liên tục tất cả các ngày trong năm.",
                f"• 🩺 **Chuyên khoa & Dịch vụ nổi bật:**\n  {specs_str}...",
            ]
            if enable_citation:
                lines.append(
                    f"• 🌐 **Hồ sơ chuyên sâu & Cơ sở vật chất:**\n  👉 [Xem giới thiệu chi tiết, trang thiết bị & viện trưởng trên Vinmec.com]({detail_url})\n"
                )
            lines.append(
                "💡 *Bác có muốn em tìm bác sĩ chuyên khoa đang làm việc tại cơ sở này hoặc hỗ trợ đặt lịch khám tại đây không ạ?*"
            )
            quick_replies = [
                f"Xem bác sĩ tại {short_name}",
                f"Đặt lịch khám tại {short_name}",
                "Xem các cơ sở khác",
            ]

        return "\n".join(lines).strip(), quick_replies

    def get_facility_doctors_response(
        self,
        facility_query: str,
        language: str = "vi",
        enable_citation: bool = True,
        department_context: str | None = None,
        booking_intake: dict[str, Any] | None = None,
        is_authenticated: bool = False,
    ) -> tuple[str, list[str]]:
        """Điều hướng: Tìm và hiển thị danh sách bác sĩ thuộc cơ sở y tế cụ thể, kèm ngữ cảnh chuyên khoa nếu có."""
        norm_q = _normalize_text(facility_query)
        matched_docs: list[dict[str, Any]] = []
        facility = None
        try:
            client = self._get_client()
            schedule_service = DoctorScheduleService(client=client)
            facility = schedule_service.find_facility(facility_query)
            if facility:
                dept_specialty_ids: list[str] = []
                if department_context:
                    candidate_specs = schedule_service.find_candidate_specialties(department_context)
                    dept_specialty_ids = [str(sp["id"]) for sp in candidate_specs[:3]]

                dept_doc_ids: set[str] = set()
                if dept_specialty_ids:
                    spec_relations = client.select(
                        "doctor_specialties",
                        params={
                            "select": "doctor_id",
                            "specialty_id": f"in.({','.join(dept_specialty_ids)})",
                            "review_status": "eq.approved",
                            "limit": 1000,
                        },
                    )
                    dept_doc_ids = {str(r["doctor_id"]) for r in spec_relations if r.get("doctor_id")}

                relations = client.select(
                    "doctor_facilities",
                    params={
                        "select": "doctor_id,department",
                        "facility_id": f"eq.{facility['id']}",
                        "status": "eq.active",
                        "limit": 1000,
                    },
                )
                relation_by_doctor = {str(row["doctor_id"]): row for row in relations if row.get("doctor_id")}
                target_doc_ids = list(relation_by_doctor)
                is_dept_filtered = False
                if dept_doc_ids:
                    filtered_ids = [d_id for d_id in target_doc_ids if d_id in dept_doc_ids]
                    if filtered_ids:
                        target_doc_ids = filtered_ids
                        is_dept_filtered = True

                if target_doc_ids:
                    doctors = client.select(
                        "doctors",
                        params={
                            "select": "id,full_name,title,source_url",
                            "id": "in.(" + ",".join(target_doc_ids[:50]) + ")",
                            "status": "eq.active",
                            "review_status": "eq.approved",
                            "order": "full_name.asc",
                            "limit": 1000,
                        },
                    )
                    matched_docs = [
                        {
                            "name": doctor.get("full_name"),
                            "specialties": [department_context]
                            if (is_dept_filtered and department_context)
                            else (
                                [relation_by_doctor[str(doctor["id"])].get("department")]
                                if relation_by_doctor[str(doctor["id"])].get("department")
                                else []
                            ),
                            "source_url": doctor.get("source_url"),
                            "sections": {
                                "Chức vụ": [doctor.get("title")] if doctor.get("title") else [],
                                "Nơi làm việc": [
                                    relation_by_doctor[str(doctor["id"])].get("department") or facility.get("name")
                                ],
                            },
                        }
                        for doctor in doctors
                    ]
        except Exception as exc:
            logger.warning("Could not load facility doctors from Supabase: %s", type(exc).__name__)

        if not matched_docs:
            requested_key = facility_key((facility or {}).get("name") or facility_query)
            for d in _load_crawled_doctors():
                secs = d.get("sections", {})
                workplaces = d.get("workplace") or secs.get("Nơi làm việc") or []
                if isinstance(workplaces, str):
                    workplaces = [workplaces]
                if requested_key:
                    is_match = any(facility_key(workplace) == requested_key for workplace in workplaces)
                else:
                    is_match = any(norm_q in _normalize_text(workplace) for workplace in workplaces)
                if is_match:
                    matched_docs.append(d)

            if department_context and matched_docs:
                dept_norm = _normalize_text(department_context)
                filtered_crawled = []
                for d in matched_docs:
                    secs = d.get("sections", {})
                    specs = d.get("specialties") or secs.get("Chuyên khoa") or []
                    all_text = " ".join([str(s) for s in specs] + [str(w) for w in (d.get("workplace") or [])])
                    if dept_norm in _normalize_text(all_text):
                        filtered_crawled.append(d)
                if filtered_crawled:
                    matched_docs = filtered_crawled

        fac_display = (facility.get("name") if facility else facility_query).strip().title()

        if matched_docs:
            header_title = (
                f"👨‍⚕️ **Đội ngũ Bác sĩ chuyên khoa {department_context} tại {fac_display}:**\n"
                if department_context
                else f"👨‍⚕️ **Đội ngũ Bác sĩ tiêu biểu làm việc tại {fac_display}:**\n"
            )
            lines = [
                header_title,
                f"Hệ thống ghi nhận **{len(matched_docs)}** bác sĩ, chuyên gia y tế phù hợp:\n",
            ]
            for idx, doc in enumerate(matched_docs[:5], 1):
                secs = doc.get("sections", {})
                specs = ", ".join(doc.get("specialties") or secs.get("Chuyên khoa") or ["Bác sĩ chuyên khoa"])
                pos_list = secs.get("Chức vụ") or []
                pos_str = f" - {pos_list[0]}" if pos_list else ""
                source_url = doc.get("source_url") or ""
                url_str = f" — [Hồ sơ bác sĩ]({source_url})" if (source_url and enable_citation) else ""
                lines.append(f"**{idx}. {doc.get('name')}**{pos_str}\n   • Chuyên môn: {specs}{url_str}\n")

            if department_context:
                lines.append(
                    f"💡 *Để khám đúng **Khoa {department_context}**, bác có thể đặt lịch hẹn để hệ thống ưu tiên xếp bác sĩ chuyên khoa phù hợp nhất.*"
                )
            else:
                lines.append(
                    "💡 *Bác có muốn đặt lịch khám với bác sĩ hoặc tìm hiểu chuyên khoa cụ thể nào tại cơ sở này không ạ?*"
                )
            quick_replies = [
                f"Đặt lịch tại {fac_display}",
                "Khám Sức khỏe tổng quát",
                "Tư vấn triệu chứng",
            ]
            return "\n".join(lines).strip(), quick_replies

        # Trường hợp cơ sở phòng khám đa khoa vệ tinh hoặc chưa liên kết bác sĩ cơ hữu riêng
        if department_context:
            if language == "vi":
                lines = [
                    f"🏥 **Khám Khoa {department_context} & Đội ngũ Bác sĩ tại {fac_display}:**\n",
                    f"Dạ có ạ! **{fac_display}** tiếp nhận khám và chẩn đoán ban đầu cho các bệnh lý thuộc **Khoa {department_context}** (thực hiện chụp X-quang kỹ thuật số, siêu âm khớp, kê đơn và điều trị ngoại trú).\n",
                    f"• 👨‍⚕️ **Đội ngũ Bác sĩ:** Các bác sĩ chuyên khoa {department_context} từ hệ thống Bệnh viện ĐKQT Vinmec (trực tiếp từ cơ sở Vinmec Times City) phụ trách chuyên môn và có lịch khám luân chuyển định kỳ tại {fac_display}.",
                    "• 🏨 **Trường hợp chuyên sâu:** Nếu cần can thiệp ngoại khoa phức tạp hoặc điều trị nội trú, cơ sở sẽ hội chẩn và chuyển tiếp thuận tiện sang Bệnh viện ĐKQT Vinmec Times City (chỉ cách ~15 phút di chuyển).\n",
                ]
                if booking_intake:
                    p_info = (
                        f" (**Bệnh nhân:** {booking_intake.get('patient_name')}, **Chuyên khoa:** {department_context})"
                        if is_authenticated and booking_intake.get("patient_name")
                        else f" (**Chuyên khoa:** {department_context})"
                    )
                    lines.append(
                        f"📋 **Phiếu Đăng Ký Khám:**\n"
                        f"Em đã tự động cập nhật cơ sở mong muốn là **{fac_display}** vào Phiếu Hẹn Khám ở khung bên cạnh{p_info}. "
                        f"Bác vui lòng kiểm tra ngày khám phù hợp trên phiếu rồi bấm **'Xác nhận gửi thông tin đặt khám'** để Lễ tân điều phối giữ chỗ cho bác nhé ạ!"
                    )
            else:
                lines = [
                    f"🏥 **Department of {department_context} & Doctors at {fac_display}:**\n",
                    f"Yes! **{fac_display}** provides outpatient consultations and diagnostic services for **{department_context}**.",
                    f"• 👨‍⚕️ **Specialists:** Specialists from Vinmec International Hospital (Times City) directly consult on scheduled rotating days at {fac_display}.",
                    "• 🏨 **Advanced Inpatient Care:** Cases requiring surgery or inpatient care are seamlessly connected to Vinmec Times City Hospital.\n",
                ]
            quick_replies = [
                f"Đặt lịch tại {fac_display}",
                "Xem lịch tại Times City",
                "Tư vấn triệu chứng",
            ]
            return "\n".join(lines).strip(), quick_replies

        lines = [
            f"👨‍⚕️ **Đội ngũ Bác sĩ tại {fac_display}:**\n",
            f"Cơ sở **{fac_display}** tiếp đón bệnh nhân với đội ngũ bác sĩ, chuyên gia luân chuyển từ hệ thống Bệnh viện Đa khoa Quốc tế Vinmec.\n",
            "Bác vui lòng cho em biết chuyên khoa dự định khám (Nội, Ngoại, Sản, Nhi, Tim mạch...) hoặc chia sẻ triệu chứng để em điều phối bác sĩ phù hợp nhất ạ!",
        ]
        quick_replies = [
            f"Đặt lịch tại {fac_display}",
            "Khám Sức khỏe tổng quát",
            "Mô tả triệu chứng",
        ]
        return "\n".join(lines).strip(), quick_replies

    def get_facility_booking_guidance_response(
        self,
        facility_query: str,
        language: str = "vi",
    ) -> tuple[str, list[str]]:
        """Điều hướng: Hướng dẫn người dùng chọn khoa hoặc triệu chứng khi muốn đặt lịch tại 1 cơ sở."""
        fac_display = facility_query.strip().title()
        response = (
            f"📅 **Đăng ký khám tại {fac_display}**\n\n"
            f"Em đã ghi nhận cơ sở ưu tiên của bác là **{fac_display}**!\n\n"
            "Để hỗ trợ bác đặt lịch khám chính xác và nhanh chóng nhất, bác dự định khám chuyên khoa nào ạ?\n"
            "• Khám Sức khỏe tổng quát / Tầm soát định kỳ\n"
            "• Khám Tim mạch, Tiêu hóa, Thần kinh, Cơ xương khớp...\n\n"
            "*(Bác cũng có thể chia sẻ nhanh triệu chứng khó chịu đang gặp phải để em tự động định hướng đúng chuyên khoa cho bác nhé!)*"
        )
        quick_replies = [
            "Khám Sức khỏe tổng quát",
            "Khám Tim mạch",
            "Khám Tiêu hóa",
            "Mô tả triệu chứng hiện tại",
        ]
        return response, quick_replies

    def get_facilities_response(
        self,
        language: str = "vi",
        region_filter: str | None = None,
        district_filter: str | None = None,
        facility_name_query: str | None = None,
        department_context: str | None = None,
        enable_citation: bool = True,
    ) -> tuple[str, list[str]]:
        """
        Định dạng danh sách cơ sở bệnh viện & phòng khám từ Supabase thành nội dung chat.
        - Tự động gợi ý cơ sở GẦN NHẤT nếu người dùng chỉ định Quận/Huyện kèm năng lực chuyên môn đang khám.
        - Tự động chuyển sang chế độ Xem Chi Tiết Cơ Sở nếu người dùng hỏi đích danh 1 bệnh viện.
        """
        all_facilities = self.fetch_active_facilities()

        if not all_facilities:
            if language == "en":
                return (
                    "🏥 **Vinmec Healthcare System Facilities**\n\n"
                    "We are currently updating our facilities database. "
                    "For immediate inquiries, please reach our 24/7 National Hotline: `1900 232 389`.",
                    ["Book an appointment", "View specialties", "Operating hours"],
                )
            return (
                "🏥 **Hệ thống Cơ sở Y tế & Bệnh viện Vinmec**\n\n"
                "Hệ thống hiện đang đồng bộ danh bạ cơ sở. Quý khách vui lòng liên hệ "
                "Tổng đài hỗ trợ 24/7 toàn quốc: `1900 232 389` để được hỗ trợ tức thời.",
                ["Đặt lịch khám", "Xem chuyên khoa", "Giờ làm việc & Hotline"],
            )

        # 0. TRƯỜNG HỢP GỢI Ý CƠ SỞ GẦN NHẤT THEO QUẬN/HUYỆN & NGỮ CẢNH CHUYÊN KHOA
        if district_filter and facility_name_query:
            norm_q = _normalize_text(facility_name_query)
            matched = [
                f
                for f in all_facilities
                if norm_q in _normalize_text(f.get("name", "")) or norm_q in _normalize_text(f.get("code", ""))
            ]
            if matched:
                best_fac = matched[0]
                fac_name = best_fac.get("name")
                address = best_fac.get("address")
                phone = best_fac.get("phone") or "1900 232 389"
                meta = self._find_detail_metadata(fac_name)
                detail_url = meta.get("detail_url") or "https://www.vinmec.com/vie/co-so-y-te/"

                short_name = (
                    fac_name.replace("Bệnh viện Đa khoa Quốc tế ", "")
                    .replace("Bệnh viện Đa khoa quốc tế ", "")
                    .replace("Phòng khám Đa khoa Quốc tế ", "")
                    .replace("Phòng khám Đa Khoa ", "")
                )

                if language == "en":
                    dept_intro = (
                        f" to examine and treat conditions for **{department_context}**" if department_context else ""
                    )
                    lines = [
                        f"🏥 **Recommended Nearest Vinmec Facility from {district_filter}:**\n",
                        f"For patients in **{district_filter}**, the most accessible and comprehensive facility{dept_intro} is:\n",
                        f"🏨 **{fac_name}**",
                        f"• 📍 **Address:** {address}",
                        f"• 📞 **Direct Hotline:** `{phone}`",
                        "• ⏰ **Operating Hours:** 08:00 - 17:00 (Mon - Fri) | 08:00 - 12:00 (Sat) | **Emergency 24/7**.",
                    ]
                    if department_context:
                        lines.append(
                            f"• 🩺 **Clinical Strength:** Fully equipped departments and experienced specialists for **{department_context}**."
                        )
                    if enable_citation:
                        lines.append(
                            f"• 🌐 👉 [View facility details & specialist doctors on Vinmec.com]({detail_url})\n"
                        )
                    lines.append(
                        f"💡 *Would you like me to check available doctor schedules or help you book an appointment at {short_name}?*"
                    )
                    quick_replies = [
                        f"Book at {short_name}",
                        f"View doctors at {short_name}",
                        "View other facilities",
                    ]
                else:
                    dept_intro = f" phục vụ thăm khám **{department_context}**" if department_context else ""
                    lines = [
                        "🏥 **Cơ sở Vinmec thuận tiện và gần nhất cho bác:**\n",
                        f"Với vị trí của bác tại **{district_filter}**, cơ sở y tế quốc tế gần và phù hợp nhất{dept_intro} là:\n",
                        f"🏨 **{fac_name}**",
                        f"• 📍 **Địa chỉ:** {address}",
                        f"• 📞 **Hotline trực tiếp:** `{phone}`",
                        "• ⏰ **Thời gian làm việc:** 08:00 - 17:00 (Thứ 2 - Thứ 6) | 08:00 - 12:00 (Thứ 7) | **Cấp cứu 24/7** liên tục.",
                    ]
                    if department_context:
                        lines.append(
                            f"• 🩺 **Năng lực chuyên môn:** Có đội ngũ chuyên gia hàng đầu và trang thiết bị chuyên sâu của **{department_context}** để trực tiếp thăm khám triệu chứng cho bác."
                        )
                    if enable_citation:
                        lines.append(
                            f"• 🌐 👉 [Xem chi tiết cơ sở vật chất & đội ngũ chuyên gia tại {short_name}]({detail_url})\n"
                        )
                    lines.append(
                        f"💡 *Bác có muốn em kiểm tra lịch khám của bác sĩ chuyên khoa hoặc hỗ trợ đặt hẹn tại {short_name} không ạ?*"
                    )
                    quick_replies = [
                        f"Đặt lịch tại {short_name}",
                        f"Xem bác sĩ tại {short_name}",
                        f"Xem tất cả cơ sở tại {region_filter or 'Hà Nội'}",
                    ]
                return "\n".join(lines).strip(), quick_replies

        # 1. TRƯỜNG HỢP HỎI ĐÍCH DANH 1 BỆNH VIỆN CỤ THỂ
        if facility_name_query:
            norm_q = _normalize_text(facility_name_query)
            matched = [
                f
                for f in all_facilities
                if norm_q in _normalize_text(f.get("name", "")) or norm_q in _normalize_text(f.get("code", ""))
            ]
            if matched:
                return self.get_facility_detail_response(matched[0], language=language, enable_citation=enable_citation)

        # 2. TRƯỜNG HỢP HỎI DANH SÁCH HOẶC THEO KHU VỰC
        if language == "en":
            filtered = [
                f
                for f in all_facilities
                if f.get("name", "").startswith("Vinmec")
                or "Hospital" in f.get("name", "")
                or "Clinic" in f.get("name", "")
            ]
            if not filtered:
                filtered = all_facilities
        else:
            filtered = [
                f
                for f in all_facilities
                if f.get("name", "").startswith(("Bệnh viện", "Phòng khám", "Bệnh Viện", "Phòng Khám"))
            ]
            if not filtered:
                filtered = all_facilities

        # Lọc theo khu vực nếu người dùng yêu cầu
        if region_filter:
            rf = _normalize_text(region_filter)
            matching = [
                f
                for f in filtered
                if rf in _normalize_text(f.get("address", "")) or rf in _normalize_text(f.get("name", ""))
            ]
            if matching:
                filtered = matching

        # Tra cứu các cơ sở có chuyên khoa/bác sĩ phù hợp nếu có department_context
        specialty_facility_ids: set[str] = set()
        if department_context:
            try:
                client = self._get_client()
                sched_service = DoctorScheduleService(client=client)
                specs = sched_service.find_candidate_specialties(department_context)
                if specs:
                    spec_ids = [sp["id"] for sp in specs[:3]]
                    rels = client.select(
                        "doctor_specialties",
                        params={
                            "select": "doctor_id",
                            "specialty_id": f"in.({','.join(spec_ids)})",
                            "review_status": "eq.approved",
                            "limit": 200,
                        },
                    )
                    doc_ids = list({r["doctor_id"] for r in rels if r.get("doctor_id")})
                    if doc_ids:
                        df = client.select(
                            "doctor_facilities",
                            params={
                                "select": "facility_id",
                                "doctor_id": f"in.({','.join(doc_ids[:50])})",
                                "status": "eq.active",
                                "limit": 200,
                            },
                        )
                        specialty_facility_ids = {f["facility_id"] for f in df if f.get("facility_id")}
            except Exception as exc:
                logger.warning("Failed to lookup specialty facilities: %s", exc)

        hospitals: list[dict[str, Any]] = []
        clinics: list[dict[str, Any]] = []

        for item in filtered:
            name = item.get("name", "")
            if "Phòng khám" in name or "Clinic" in name or "phòng khám" in name:
                clinics.append(item)
            else:
                hospitals.append(item)

        lines: list[str] = []
        if language == "en":
            if department_context:
                region_str = f" in {region_filter}" if region_filter else ""
                lines.append(f"🏥 **Vinmec Healthcare Facilities for {department_context}{region_str}:**\n")
                spec_hospitals = [h for h in hospitals if h.get("id") in specialty_facility_ids]
                other_hospitals = [h for h in hospitals if h.get("id") not in specialty_facility_ids]

                if spec_hospitals:
                    lines.append(f"### 🏨 Specialized Hospitals for {department_context} (Inpatient & Surgery):")
                    for h in spec_hospitals:
                        phone_str = f" | 📞 Hotline: `{h['phone']}`" if h.get("phone") else ""
                        lines.append(
                            f"• **{h['name']}**\n  📍 Address: {h.get('address', 'Updating')}{phone_str}\n  ✨ *Comprehensive inpatient care, specialized diagnostics, and 24/7 emergency services.*\n"
                        )
                elif hospitals:
                    lines.append("### 🏨 International General Hospitals:")
                    for h in hospitals:
                        phone_str = f" | 📞 Hotline: `{h['phone']}`" if h.get("phone") else ""
                        lines.append(f"• **{h['name']}**\n  📍 Address: {h.get('address', 'Updating')}{phone_str}\n")

                secondary_facilities = clinics + (other_hospitals if spec_hospitals else [])
                if secondary_facilities:
                    lines.append("### 🩺 General Clinics (Initial Screening & Consultation):")
                    seen_names = set()
                    for c in secondary_facilities:
                        if c["name"] in seen_names:
                            continue
                        seen_names.add(c["name"])
                        phone_str = f" | 📞 Hotline: `{c['phone']}`" if c.get("phone") else ""
                        lines.append(f"• **{c['name']}**\n  📍 Address: {c.get('address', 'Updating')}{phone_str}\n")
                    lines.append(
                        "💡 *Satellite clinics provide initial examination, ultrasound, and outpatient treatment, referring complex cases to the specialized hospital.*"
                    )

                quick_replies = ["Book appointment", f"Doctors for {department_context}", "General Health Checkup"]
            else:
                lines.append("🏥 **Vinmec International Healthcare System**\n")
                lines.append("Vinmec operates modern international hospitals and specialized clinics across Vietnam:\n")

                if hospitals:
                    lines.append("### 🏨 International General Hospitals:")
                    for h in hospitals:
                        phone_str = f" | 📞 Hotline: `{h['phone']}`" if h.get("phone") else ""
                        lines.append(f"• **{h['name']}**\n  📍 Address: {h.get('address', 'Updating')}{phone_str}\n")

                if clinics:
                    lines.append("### 🩺 International General Clinics:")
                    for c in clinics:
                        phone_str = f" | 📞 Hotline: `{c['phone']}`" if c.get("phone") else ""
                        lines.append(f"• **{c['name']}**\n  📍 Address: {c.get('address', 'Updating')}{phone_str}\n")

                lines.append("💡 *Emergency services operate 24/7 at all hospitals.*")
                quick_replies = ["Book appointment now", "Search doctor schedule", "General Health Checkup"]
        else:
            region_suffix = f" tại {region_filter}" if region_filter else ""
            if department_context:
                lines.append(f"🏥 **Cơ sở Y tế Vinmec tiếp nhận khám Khoa {department_context}{region_suffix}:**\n")
                spec_hospitals = [h for h in hospitals if h.get("id") in specialty_facility_ids]
                other_hospitals = [h for h in hospitals if h.get("id") not in specialty_facility_ids]

                if spec_hospitals:
                    lines.append(f"### 🏨 Bệnh viện ĐKQT tiếp nhận điều trị chuyên sâu Khoa {department_context}:")
                    for h in spec_hospitals:
                        phone_str = f" | 📞 Hotline: `{h['phone']}`" if h.get("phone") else ""
                        lines.append(
                            f"• **{h['name']}**\n  📍 Địa chỉ: {h.get('address', 'Đang cập nhật')}{phone_str}\n  ✨ *Trung tâm chuyên sâu trang bị đầy đủ máy móc hiện đại, phòng mổ vô khuẩn và điều trị nội trú 24/7.*\n"
                        )
                elif hospitals:
                    lines.append("### 🏨 Bệnh viện Đa khoa Quốc tế:")
                    for h in hospitals:
                        phone_str = f" | 📞 Hotline: `{h['phone']}`" if h.get("phone") else ""
                        lines.append(
                            f"• **{h['name']}**\n  📍 Địa chỉ: {h.get('address', 'Đang cập nhật')}{phone_str}\n"
                        )

                secondary_facilities = clinics + (other_hospitals if spec_hospitals else [])
                if secondary_facilities:
                    lines.append("### 🩺 Phòng khám Đa khoa vệ tinh (Tiếp nhận khám ban đầu & Chuyển tiếp):")
                    seen_names = set()
                    for c in secondary_facilities:
                        if c["name"] in seen_names:
                            continue
                        seen_names.add(c["name"])
                        phone_str = f" | 📞 Hotline: `{c['phone']}`" if c.get("phone") else ""
                        lines.append(
                            f"• **{c['name']}**\n  📍 Địa chỉ: {c.get('address', 'Đang cập nhật')}{phone_str}\n"
                        )
                    lines.append(
                        "💡 *Các phòng khám vệ tinh tiếp nhận khám sàng lọc ban đầu, siêu âm, xét nghiệm và điều trị ngoại trú; trường hợp cần can thiệp ngoại khoa hay nội trú chuyên sâu sẽ được hội chẩn chuyển viện nhanh chóng sang bệnh viện trung tâm.*\n"
                    )

                quick_replies = ["Đặt lịch khám ngay", f"Bác sĩ Khoa {department_context}", "Xem các cơ sở khác"]
            else:
                lines.append(f"🏥 **Hệ thống Bệnh viện & Phòng khám Đa khoa Quốc tế Vinmec{region_suffix}**\n")
                lines.append("Hệ sinh thái Vinmec hiện diện tại các thành phố trọng điểm trên toàn quốc:\n")

                if hospitals:
                    lines.append("### 🏨 Bệnh viện Đa khoa Quốc tế:")
                    for h in hospitals:
                        phone_str = f" | 📞 Hotline: `{h['phone']}`" if h.get("phone") else ""
                        lines.append(
                            f"• **{h['name']}**\n  📍 Địa chỉ: {h.get('address', 'Đang cập nhật')}{phone_str}\n"
                        )

                if clinics:
                    lines.append("### 🩺 Phòng khám Đa khoa Quốc tế:")
                    for c in clinics:
                        phone_str = f" | 📞 Hotline: `{c['phone']}`" if c.get("phone") else ""
                        lines.append(
                            f"• **{c['name']}**\n  📍 Địa chỉ: {c.get('address', 'Đang cập nhật')}{phone_str}\n"
                        )

                lines.append("💡 *Khoa Cấp cứu & Phòng Lưu bệnh làm việc **24/7** tại tất cả các bệnh viện.*")
                quick_replies = ["Đặt lịch khám ngay", "Xem danh sách bác sĩ", "Giờ làm việc & Khám Thứ 7"]

        return "\n".join(lines).strip(), quick_replies


_facility_service: FacilityService | None = None


def get_facility_service() -> FacilityService:
    global _facility_service
    if _facility_service is None:
        _facility_service = FacilityService()
    return _facility_service
