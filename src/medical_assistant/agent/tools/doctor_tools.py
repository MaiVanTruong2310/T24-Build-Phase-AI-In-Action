"""Read-only tools for discovering doctors, details, and schedules."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.medical_assistant.agent.tools.base import (
    VN_TZ,
    ToolExecutionError,
    format_utc_to_vn_time,
    normalize_fold,
)
from src.medical_assistant.domain.doctor_schedule_service import (
    _experience_years,
    _load_crawled_doctors,
    _specialty_terms,
    get_doctor_schedule_service,
)
from src.medical_assistant.domain.facility_linking import facility_key

logger = logging.getLogger(__name__)


class SearchDoctorsInput(BaseModel):
    name: str | None = Field(
        default=None,
        description="Tên bác sĩ cần tìm (VD: 'Thành', 'Nguyễn Văn A', 'Lê Thị Mai')",
    )
    specialty: str | None = Field(
        default=None,
        description="Chuyên khoa khám bệnh (VD: 'Tim mạch', 'Tiêu hóa', 'Thần kinh', 'Nhi')",
    )
    facility: str | None = Field(
        default=None,
        description="Tên hoặc khu vực cơ sở bệnh viện (VD: 'Times City', 'Central Park', 'Đà Nẵng')",
    )
    min_experience_years: int | None = Field(
        default=None,
        ge=0,
        description="Số năm kinh nghiệm tối thiểu của bác sĩ (VD: 10, 15)",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Số lượng bác sĩ tối đa cần hiển thị (tối đa 5 bác sĩ)",
    )


class GetDoctorDetailInput(BaseModel):
    doctor_id: str = Field(
        ...,
        description="Mã định danh (ID) của bác sĩ từ Supabase (UUID) hoặc từ crawl (bắt đầu bằng 'crawl-')",
    )


class GetDoctorSlotsInput(BaseModel):
    doctor_id: str = Field(
        ...,
        description="Mã định danh của bác sĩ (UUID từ Supabase)",
    )
    from_date: str | None = Field(
        default=None,
        description="Ngày bắt đầu tra cứu theo định dạng YYYY-MM-DD (mặc định là ngày hôm nay)",
    )
    days: int = Field(
        default=7,
        ge=1,
        le=14,
        description="Số ngày tra cứu lịch khám (từ 1 đến 14 ngày)",
    )
    period: str | None = Field(
        default=None,
        description="Buổi khám mong muốn: 'morning' (sáng), 'afternoon' (chiều), hoặc 'evening' (tối)",
    )


@tool("search_doctors", args_schema=SearchDoctorsInput)
def search_doctors(
    name: str | None = None,
    specialty: str | None = None,
    facility: str | None = None,
    min_experience_years: int | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Tìm kiếm danh sách bác sĩ chuyên khoa thực tế từ cơ sở dữ liệu và hồ sơ Vinmec.

    Sử dụng khi người dùng hỏi về danh sách bác sĩ, bác sĩ giỏi/giàu kinh nghiệm,
    tìm bác sĩ theo tên, chuyên khoa hoặc cơ sở y tế cụ thể.
    """
    try:
        limit = max(1, min(limit, 5))
        doctor_service = get_doctor_schedule_service()

        name_query = normalize_fold(name) if name else None
        specialty_terms = _specialty_terms(specialty) if specialty else []
        req_fac_key = facility_key(facility) if facility else None

        matched_doctors: list[dict[str, Any]] = []
        db_unavailable = False
        db_error_message = ""

        # 1. Tra cứu trước trong Supabase database nếu có cấu hình
        if hasattr(doctor_service, "client") and doctor_service.client is not None:
            try:
                # 1.1 Tìm các chuyên khoa khớp trong DB nếu người dùng lọc theo specialty
                target_doc_ids: set[str] | None = None
                if specialty_terms:
                    all_db_specs = (
                        doctor_service.client.select(
                            "specialties",
                            params={"select": "id,name", "limit": 300},
                        )
                        or []
                    )
                    matched_spec_ids = [
                        str(s["id"])
                        for s in all_db_specs
                        if any(term in normalize_fold(str(s.get("name") or "")) for term in specialty_terms)
                    ]
                    if matched_spec_ids:
                        ds_rows = (
                            doctor_service.client.select(
                                "doctor_specialties",
                                params={
                                    "select": "doctor_id",
                                    "specialty_id": f"in.({','.join(matched_spec_ids)})",
                                    "limit": 100,
                                },
                            )
                            or []
                        )
                        target_doc_ids = {str(r["doctor_id"]) for r in ds_rows if r.get("doctor_id")}
                    else:
                        target_doc_ids = set()

                # 1.2 Hỗ trợ tìm kiếm theo tên (có dấu và không dấu)
                names_to_query = [name.strip()] if name else []
                if name_query:
                    crawled_all = _load_crawled_doctors()
                    for rec in crawled_all:
                        r_name = str(rec.get("name") or "")
                        if name_query in normalize_fold(r_name) and r_name not in names_to_query:
                            names_to_query.append(r_name)

                sb_params: dict[str, Any] = {
                    "select": "id,full_name,title,years_of_experience,position,source_url,doctor_specialties(specialties(name)),doctor_facilities(department,facilities(name))",
                    "limit": 50,
                }
                if target_doc_ids is not None:
                    if not target_doc_ids:
                        sb_rows = []
                    else:
                        sb_params["id"] = f"in.({','.join(list(target_doc_ids)[:50])})"
                        sb_rows = doctor_service.client.select("doctors", params=sb_params) or []
                elif names_to_query:
                    sb_rows = []
                    for n_candidate in names_to_query[:3]:
                        sb_params["full_name"] = f"ilike.*{n_candidate}*"
                        found_rows = doctor_service.client.select("doctors", params=sb_params) or []
                        for fr in found_rows:
                            if not any(r.get("id") == fr.get("id") for r in sb_rows):
                                sb_rows.append(fr)
                        if sb_rows:
                            break
                else:
                    sb_rows = doctor_service.client.select("doctors", params=sb_params) or []

                if sb_rows:
                    for doc in sb_rows:
                        doc_name = str(doc.get("full_name") or "")
                        # Kiểm tra lọc theo tên không dấu
                        if name_query and name_query not in normalize_fold(doc_name):
                            continue

                        years = doc.get("years_of_experience")
                        years_val = int(years) if years is not None and str(years).isdigit() else 0
                        if min_experience_years is not None and years_val < min_experience_years:
                            continue

                        # Trích xuất chuyên khoa THẬT từ quan hệ doctor_specialties -> specialties
                        doc_specialties = []
                        for ds in doc.get("doctor_specialties") or []:
                            if isinstance(ds, dict) and ds.get("specialties"):
                                s_name = ds["specialties"].get("name")
                                if s_name and s_name not in doc_specialties:
                                    doc_specialties.append(s_name)

                        # Bắt buộc lọc lại ở Python: Tuyệt đối không gán nhãn chuyên khoa suy ra!
                        if specialty_terms:
                            norm_doc_specs = normalize_fold(" ".join(doc_specialties))
                            if not any(term in norm_doc_specs for term in specialty_terms):
                                continue

                        # Trích xuất danh sách cơ sở từ quan hệ doctor_facilities
                        doc_facilities = []
                        for df in doc.get("doctor_facilities") or []:
                            if isinstance(df, dict) and df.get("facilities"):
                                f_name = df["facilities"].get("name")
                                if f_name and f_name not in doc_facilities:
                                    doc_facilities.append(f_name)
                        doc_workplace = ", ".join(doc_facilities) if doc_facilities else "Hệ thống Y tế Vinmec"

                        # Kiểm tra facility nếu người dùng có yêu cầu
                        if req_fac_key and not any(facility_key(f) == req_fac_key for f in doc_facilities):
                            continue

                        exp_display = (
                            f"{years_val} năm kinh nghiệm" if years_val > 0 else "Bác sĩ Chuyên khoa giàu kinh nghiệm"
                        )
                        matched_doctors.append(
                            {
                                "id": str(doc["id"]),
                                "full_name": doc_name or "Bác sĩ Chuyên khoa",
                                "title": doc.get("title") or "Bác sĩ chuyên khoa",
                                "specialties": doc_specialties,  # Chuyên khoa thật từ DB, không gán suy diễn!
                                "workplace": doc_workplace,
                                "years_of_experience": years_val if years_val > 0 else None,
                                "experience_display": exp_display,
                                "source": doc.get("source_url") or "supabase.doctors",
                                "data_source": "supabase",
                                "schedule_verified": True,
                            }
                        )
            except Exception as exc:
                db_unavailable = True
                db_error_message = str(exc)
                logger.warning(
                    "Supabase doctors search failed: %s; falling back to crawl data with data_unavailable flag.", exc
                )
        else:
            db_unavailable = True
            db_error_message = "Cơ sở dữ liệu Supabase chưa được cấu hình hoặc tạm thời ngắt kết nối."

        # 2. Bổ sung hoặc fallback từ nguồn dữ liệu hồ sơ Vinmec (992 bác sĩ)
        crawled_records = _load_crawled_doctors()
        scored_crawled: list[tuple[int, int, dict[str, Any]]] = []

        for record in crawled_records:
            full_name = str(record.get("name") or "")
            norm_name = normalize_fold(full_name)
            if name_query and name_query not in norm_name:
                continue

            specialties = record.get("specialties") or []
            positions = record.get("positions") or []
            sections = record.get("sections") or {}
            workplaces = record.get("workplace") or sections.get("Nơi làm việc") or []
            if isinstance(workplaces, str):
                workplaces = [workplaces]

            if req_fac_key and not any(facility_key(w) == req_fac_key for w in workplaces):
                continue

            years = _experience_years(record.get("years_of_experience"))
            if min_experience_years is not None and years < min_experience_years:
                continue

            # Tính điểm tương đồng chuyên khoa
            score = 1
            if specialty_terms:
                searchable = normalize_fold(" ".join([*specialties, *positions, str(record.get("overview") or "")]))
                spec_text = normalize_fold(" ".join(specialties))
                matched_term_count = sum(
                    4 if term in spec_text else 1 for term in specialty_terms if term in searchable
                )
                if matched_term_count == 0:
                    continue
                score = matched_term_count

            scored_crawled.append((score, years, record))

        # Sắp xếp theo độ phù hợp và số năm kinh nghiệm
        scored_crawled.sort(key=lambda item: (item[0], item[1]), reverse=True)

        for _, years, record in scored_crawled:
            if len(matched_doctors) >= limit:
                break
            credentials = record.get("credentials") or []
            positions = record.get("positions") or []
            title = ", ".join(credentials) or (positions[0] if positions else "Bác sĩ chuyên khoa")
            identifier = str(record.get("profile_id") or record.get("source_url"))
            sections = record.get("sections") or {}
            workplaces = record.get("workplace") or sections.get("Nơi làm việc") or []
            if isinstance(workplaces, str):
                workplaces = [workplaces]

            # Kiểm tra trùng tên với doctors đã có
            rec_name = record.get("name") or "Bác sĩ Chuyên khoa"
            if any(d["full_name"] == rec_name for d in matched_doctors):
                continue

            exp_display = f"{years} năm kinh nghiệm" if years > 0 else "Bác sĩ Chuyên khoa giàu kinh nghiệm"
            matched_doctors.append(
                {
                    "id": f"crawl-{identifier}",
                    "full_name": rec_name,
                    "title": title,
                    "specialties": record.get("specialties") or [],
                    "workplace": workplaces[0] if workplaces else "Hệ thống Y tế Vinmec",
                    "years_of_experience": years if years > 0 else None,
                    "experience_display": exp_display,
                    "source": record.get("source_url") or "vinmec_crawl",
                    "data_source": "vinmec_crawl",
                    "schedule_verified": False,
                }
            )

        matched_doctors = matched_doctors[:limit]

        # Xác định nguồn dữ liệu thực tế và cờ source_mixed
        has_supabase = any(d.get("data_source") == "supabase" for d in matched_doctors)
        has_crawl = any(d.get("data_source") == "vinmec_crawl" for d in matched_doctors)
        source_mixed = has_supabase and has_crawl
        primary_source = (
            "supabase.doctors"
            if has_supabase and not has_crawl
            else ("vinmec_crawl" if has_crawl and not has_supabase else "hybrid (supabase + crawl)")
        )

        if not matched_doctors:
            criteria_parts = []
            if name:
                criteria_parts.append(f"tên '{name}'")
            if specialty:
                criteria_parts.append(f"chuyên khoa '{specialty}'")
            if facility:
                criteria_parts.append(f"cơ sở '{facility}'")
            if min_experience_years:
                criteria_parts.append(f"kinh nghiệm từ {min_experience_years} năm")
            criteria_str = ", ".join(criteria_parts) or "tiêu chí đã chọn"

            resp: dict[str, Any] = {
                "found": False,
                "count": 0,
                "doctors": [],
                "reason": f"Không tìm thấy bác sĩ nào phù hợp với {criteria_str}.",
                "source": primary_source,
                "source_mixed": False,
                "data_unavailable": db_unavailable,
            }
            if db_unavailable:
                resp["warning"] = f"Cơ sở dữ liệu Supabase tạm thời gián đoạn ({db_error_message})."
            return resp

        resp_data: dict[str, Any] = {
            "found": True,
            "count": len(matched_doctors),
            "doctors": matched_doctors,
            "source": primary_source,
            "source_mixed": source_mixed,
            "data_unavailable": db_unavailable,
        }
        if db_unavailable:
            resp_data["warning"] = (
                "Cơ sở dữ liệu lịch khám Supabase gián đoạn; kết quả dựa trên hồ sơ lưu trữ và chưa xác thực lịch khám."
            )
        return resp_data
    except Exception as exc:
        logger.error("Error in search_doctors tool: %s", exc, exc_info=True)
        raise ToolExecutionError(f"Lỗi khi tìm kiếm bác sĩ: {exc}") from exc


@tool("get_doctor_detail", args_schema=GetDoctorDetailInput)
def get_doctor_detail(doctor_id: str) -> dict[str, Any]:
    """Xem hồ sơ chi tiết, quá trình đào tạo, kinh nghiệm công tác của một bác sĩ cụ thể theo mã ID."""
    try:
        doctor_id = str(doctor_id or "").strip()
        if not doctor_id:
            return {
                "found": False,
                "doctor_id": "",
                "reason": "Mã định danh bác sĩ không được để trống.",
                "source": "doctors",
            }

        # 1. Nếu là bác sĩ từ nguồn crawled dataset
        if doctor_id.startswith("crawl-"):
            clean_id = doctor_id.removeprefix("crawl-")
            for record in _load_crawled_doctors():
                rec_id = str(record.get("profile_id") or record.get("source_url"))
                if rec_id == clean_id or str(record.get("source_url")) == clean_id:
                    sections = record.get("sections") or {}
                    years = _experience_years(record.get("years_of_experience"))
                    workplaces = record.get("workplace") or sections.get("Nơi làm việc") or []
                    if isinstance(workplaces, str):
                        workplaces = [workplaces]

                    credentials = record.get("credentials") or []
                    positions = record.get("positions") or []
                    title = ", ".join(credentials) or (positions[0] if positions else "Bác sĩ chuyên khoa")

                    exp_display = f"{years} năm kinh nghiệm" if years > 0 else "Bác sĩ Chuyên khoa giàu kinh nghiệm"

                    return {
                        "found": True,
                        "doctor_id": doctor_id,
                        "full_name": record.get("name") or "Bác sĩ chuyên khoa",
                        "title": title,
                        "specialties": record.get("specialties") or [],
                        "positions": positions,
                        "workplace": workplaces[0] if workplaces else "Hệ thống Y tế Vinmec",
                        "years_of_experience": years if years > 0 else None,
                        "experience_display": exp_display,
                        "training_process": sections.get("Quá trình đào tạo") or [],
                        "work_experience": sections.get("Kinh nghiệm công tác") or [],
                        "overview": str(record.get("overview") or "").strip(),
                        "source": record.get("source_url") or "https://www.vinmec.com",
                        "data_source": "vinmec_crawl",
                    }

        # 2. Nếu là ID từ Supabase database (UUID)
        doctor_service = get_doctor_schedule_service()
        if hasattr(doctor_service, "client") and doctor_service.client is not None:
            try:
                UUID(doctor_id)
                rows = doctor_service.client.select(
                    "doctors",
                    params={
                        "select": "id,full_name,title,years_of_experience,position,bio,source_url,doctor_facilities(department,facilities(name))",
                        "id": f"eq.{doctor_id}",
                        "limit": 1,
                    },
                )
                if rows:
                    doc = rows[0]
                    years = doc.get("years_of_experience")
                    years_val = int(years) if years is not None and str(years).isdigit() else 0
                    exp_display = (
                        f"{years_val} năm kinh nghiệm" if years_val > 0 else "Bác sĩ Chuyên khoa giàu kinh nghiệm"
                    )

                    doc_facilities = []
                    for df in doc.get("doctor_facilities") or []:
                        if isinstance(df, dict) and df.get("facilities"):
                            f_name = df["facilities"].get("name")
                            if f_name and f_name not in doc_facilities:
                                doc_facilities.append(f_name)
                    doc_workplace = ", ".join(doc_facilities) if doc_facilities else "Hệ thống Y tế Vinmec"

                    return {
                        "found": True,
                        "doctor_id": doctor_id,
                        "full_name": doc.get("full_name") or "Bác sĩ chuyên khoa",
                        "title": doc.get("title") or "Bác sĩ chuyên khoa",
                        "specialties": doc.get("specialties") or [],
                        "workplace": doc_workplace,
                        "years_of_experience": years_val if years_val > 0 else None,
                        "experience_display": exp_display,
                        "overview": str(doc.get("bio") or doc.get("overview") or "").strip(),
                        "source": doc.get("source_url") or "supabase.doctors",
                        "data_source": "supabase",
                        "schedule_verified": True,
                    }
            except ValueError:
                pass
            except Exception as exc:
                logger.warning("Supabase doctor detail lookup failed for id %s: %s", doctor_id, exc)
                return {
                    "found": False,
                    "doctor_id": doctor_id,
                    "reason": f"Không thể tra cứu hồ sơ bác sĩ do cơ sở dữ liệu gián đoạn ({exc}).",
                    "data_unavailable": True,
                    "source": "supabase.doctors",
                }

        return {
            "found": False,
            "doctor_id": doctor_id,
            "reason": f"Không tìm thấy hồ sơ chi tiết cho bác sĩ với mã '{doctor_id}'.",
            "source": "doctors",
        }
    except Exception as exc:
        logger.error("Error in get_doctor_detail tool: %s", exc, exc_info=True)
        return {
            "found": False,
            "doctor_id": str(doctor_id or "").strip() if "doctor_id" in locals() else "",
            "data_unavailable": True,
            "reason": f"Lỗi kết nối hoặc không thể tra cứu chi tiết bác sĩ: {exc}",
            "source": "doctors",
        }


@tool("get_doctor_slots", args_schema=GetDoctorSlotsInput)
def get_doctor_slots(
    doctor_id: str,
    from_date: str | None = None,
    days: int = 7,
    period: str | None = None,
) -> dict[str, Any]:
    """Tra cứu các khung giờ khám trống (appointment slots) có thể đặt lịch của bác sĩ theo múi giờ GMT+7."""
    try:
        doctor_id = str(doctor_id or "").strip()
        days = max(1, min(days, 14))

        if not doctor_id:
            return {
                "found": False,
                "doctor_id": "",
                "slots": [],
                "reason": "Mã định danh bác sĩ không được để trống.",
                "source": "supabase.doctor_schedules",
            }

        # Nếu là hồ sơ từ web crawl chưa nạp vào hệ thống xếp lịch vận hành
        if doctor_id.startswith("crawl-"):
            return {
                "found": False,
                "doctor_id": doctor_id,
                "slots": [],
                "reason": (
                    "Bác sĩ từ nguồn hồ sơ chuyên gia chưa tích hợp mở slot trực tuyến trên hệ thống. "
                    "Bác có thể để lại thông tin liên hệ để điều phối viên y tế hỗ trợ sắp xếp lịch trực tiếp."
                ),
                "source": "vinmec_crawl",
            }

        # Tính thời gian bắt đầu tra cứu (mặc định hiện tại theo múi giờ Việt Nam GMT+7)
        now_vn = datetime.now(VN_TZ)
        if from_date:
            try:
                parsed_date = datetime.strptime(from_date.strip(), "%Y-%m-%d").date()
                start_dt = datetime.combine(parsed_date, datetime.min.time(), tzinfo=VN_TZ)
            except ValueError:
                start_dt = now_vn
        else:
            start_dt = now_vn

        end_dt = start_dt + timedelta(days=days)

        doctor_service = get_doctor_schedule_service()
        if not hasattr(doctor_service, "client") or doctor_service.client is None:
            return {
                "found": False,
                "doctor_id": doctor_id,
                "slots": [],
                "data_unavailable": True,
                "reason": "Cơ sở dữ liệu lịch khám (Supabase) chưa được kết nối hoặc đang gián đoạn.",
                "source": "supabase.doctor_schedules",
            }

        schedule_params: dict[str, Any] = {
            "doctor_id": f"eq.{doctor_id}",
            "status": "eq.available",
            "starts_at": f"gte.{start_dt.isoformat()}",
            "order": "starts_at.asc",
            "limit": 50,
        }

        try:
            raw_slots = doctor_service.client.select("doctor_schedules", params=schedule_params)
        except Exception as exc:
            logger.error("Failed to select doctor_schedules: %s", exc)
            return {
                "found": False,
                "doctor_id": doctor_id,
                "slots": [],
                "data_unavailable": True,
                "reason": f"Lỗi kết nối cơ sở dữ liệu khi tra cứu lịch trống: {exc}",
                "source": "supabase.doctor_schedules",
            }

        formatted_slots: list[dict[str, Any]] = []
        for slot in raw_slots or []:
            raw_start = str(slot.get("starts_at") or "")
            try:
                starts_at = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
            except ValueError:
                continue

            if starts_at > end_dt:
                continue

            local_hour = starts_at.astimezone(VN_TZ).hour
            if period == "morning" and local_hour >= 12:
                continue
            if period in {"afternoon", "evening"} and local_hour < 12:
                continue

            formatted_slots.append(
                {
                    "slot_id": str(slot.get("id")),
                    "starts_at": format_utc_to_vn_time(raw_start),
                    "starts_at_iso": raw_start,
                    "ends_at": str(slot.get("ends_at") or ""),
                    "status": "available",
                    "facility_id": str(slot.get("facility_id") or ""),
                    "verified": True,
                }
            )

        if not formatted_slots:
            return {
                "found": False,
                "doctor_id": doctor_id,
                "slots": [],
                "reason": f"Không có lịch khám trống khả dụng trong vòng {days} ngày tới.",
                "source": "supabase.doctor_schedules",
            }

        return {
            "found": True,
            "doctor_id": doctor_id,
            "count": len(formatted_slots),
            "slots": formatted_slots,
            "source": "supabase.doctor_schedules",
        }
    except Exception as exc:
        logger.error("Error in get_doctor_slots tool: %s", exc, exc_info=True)
        return {
            "found": False,
            "doctor_id": str(doctor_id or "").strip() if "doctor_id" in locals() else "",
            "slots": [],
            "data_unavailable": True,
            "reason": f"Lỗi khi tra cứu lịch khám: {exc}",
            "source": "supabase.doctor_schedules",
        }
