"""Booking slot and patient intake entity extraction service.

Provides robust Vietnamese entity extraction for booking forms:
- Full Name
- Phone Number
- Date of Birth / Age / Year of Birth
- Gender
- Preferred Facility
- Preferred Date & Period
- Booking Intent & Missing Fields Analysis
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

FACILITY_MAPPING = {
    "times city": "Bệnh viện ĐKQT Vinmec Times City",
    "timescity": "Bệnh viện ĐKQT Vinmec Times City",
    "hai bà trưng": "Bệnh viện ĐKQT Vinmec Times City",
    "minh khai": "Bệnh viện ĐKQT Vinmec Times City",
    "central park": "Bệnh viện ĐKQT Vinmec Central Park",
    "centralpark": "Bệnh viện ĐKQT Vinmec Central Park",
    "bình thạnh": "Bệnh viện ĐKQT Vinmec Central Park",
    "nguyễn hữu cảnh": "Bệnh viện ĐKQT Vinmec Central Park",
    "smart city": "Phòng khám ĐKQT Vinmec Smart City",
    "smartcity": "Phòng khám ĐKQT Vinmec Smart City",
    "tây mỗ": "Phòng khám ĐKQT Vinmec Smart City",
    "hải phòng": "Bệnh viện ĐKQT Vinmec Hải Phòng",
    "hai phong": "Bệnh viện ĐKQT Vinmec Hải Phòng",
    "đà nẵng": "Bệnh viện ĐKQT Vinmec Đà Nẵng",
    "da nang": "Bệnh viện ĐKQT Vinmec Đà Nẵng",
    "nha trang": "Bệnh viện ĐKQT Vinmec Nha Trang",
    "phú quốc": "Bệnh viện ĐKQT Vinmec Phú Quốc",
    "phu quoc": "Bệnh viện ĐKQT Vinmec Phú Quốc",
    "hạ long": "Bệnh viện ĐKQT Vinmec Hạ Long",
    "ha long": "Bệnh viện ĐKQT Vinmec Hạ Long",
}

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _get_vn_today() -> date:
    from datetime import datetime
    return datetime.now(VN_TZ).date()


def clean_name(raw: str) -> str:
    """Clean extracted Vietnamese name."""
    cleaned = raw.strip()
    # Remove common trailing particles with strict word boundaries
    cleaned = re.sub(
        r"\s+\b(?:nhé|nhe|ạ|nha|với|voi|nhé\s+ạ|giúp\s+tôi|giúp\s+em|vào|lúc|ngày|sđt|số\s+điện\s+thoại|năm\s+sinh)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Remove unwanted punctuation
    cleaned = re.sub(r"^[,\-:\s]+|[,\-:\s]+$", "", cleaned)
    # Capitalize words properly
    words = [w.capitalize() for w in cleaned.split() if w]
    return " ".join(words)


def extract_booking_entities(text: str, current_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract patient booking details from conversation text."""
    current_state = current_state or {}
    text_clean = text.strip()
    lower_text = text_clean.lower()
    entities: dict[str, Any] = {}

    # 1. Booking intent detection
    booking_intent_keywords = [
        "đặt lịch", "dat lich", "hẹn khám", "hen kham", "đăng ký khám", "dang ky kham",
        "muốn khám", "muon kham", "gặp bác sĩ", "gap bac si", "book lịch", "book lich",
        "phiếu khám", "phieu kham", "đặt hẹn", "dat hen", "khám bệnh", "kham benh"
    ]
    is_booking_intent = any(kw in lower_text for kw in booking_intent_keywords)
    entities["is_booking_intent"] = is_booking_intent

    # 2. Extract Phone Number
    # Match VN 10-digit phone with various separators (spaces, dots, hyphens)
    phone_match = re.search(
        r"(?:\b|\D)(?:\+?84|0)(3[2-9]|5[689]|7[06-9]|8[1-9]|9[0-9])[\s.-]?(\d{3})[\s.-]?(\d{3,4})\b",
        text_clean
    )
    if phone_match:
        raw_digits = re.sub(r"\D", "", phone_match.group(0))
        if raw_digits.startswith("84"):
            raw_digits = "0" + raw_digits[2:]
        if len(raw_digits) == 10:
            entities["patient_phone"] = raw_digits

    # 3. Extract Full Name
    name_patterns = [
        r"(?:tôi|toi|mình|minh|em|anh|chị|chi)\s+tên(?:\s+là)?\s+([A-Za-zÀ-ỹ\s]{2,40})",
        r"tên\s+(?:của\s+)?(?:tôi|mình|em|bệnh\s+nhân|người\s+khám)(?:\s+là)?\s+([A-Za-zÀ-ỹ\s]{2,40})",
        r"(?:bệnh\s+nhân|người\s+khám)(?:\s+tên)?(?:\s+là)?\s*[:\-]?\s*([A-Za-zÀ-ỹ\s]{2,40})",
        r"(?:họ\s+và\s+tên|họ\s+tên)\s*[:\-]?\s*([A-Za-zÀ-ỹ\s]{2,40})",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            candidate = clean_name(match.group(1))
            # Validate plausible name: 2 to 5 words, not matching stopwords
            words = candidate.split()
            if 2 <= len(words) <= 5 and not any(w.lower() in {"đặt", "lịch", "khám", "bác", "sĩ", "ở", "tại", "vinmec"} for w in words):
                entities["patient_name"] = candidate
                break

    # 4. Extract Date of Birth / Year / Age
    today = _get_vn_today()
    dob_match = re.search(r"sinh\s+ngày\s+(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", text_clean, re.IGNORECASE)
    if dob_match:
        day, month, year = int(dob_match.group(1)), int(dob_match.group(2)), int(dob_match.group(3))
        try:
            entities["date_of_birth"] = date(year, month, day).isoformat()
        except ValueError:
            pass
    if "date_of_birth" not in entities:
        # Year of birth: sinh năm 1990 / năm sinh 1990
        year_match = re.search(r"(?:sinh\s+năm|năm\s+sinh)\s*[:\-]?\s*(19\d{2}|20[0-2]\d)", text_clean, re.IGNORECASE)
        if year_match:
            year = int(year_match.group(1))
            if 1920 <= year <= today.year:
                entities["date_of_birth"] = f"{year}-01-01"
    if "date_of_birth" not in entities:
        # Age: 35 tuổi
        age_match = re.search(r"\b(\d{1,2})\s+tuổi\b", text_clean, re.IGNORECASE)
        if age_match:
            age = int(age_match.group(1))
            if 1 <= age <= 100:
                est_year = today.year - age
                entities["date_of_birth"] = f"{est_year}-01-01"

    # 5. Extract Gender
    if re.search(r"\b(nam|male|con trai|anh|ông)\b", lower_text):
        entities["gender"] = "male"
    elif re.search(r"\b(nữ|nu|female|con gái|chị|bà)\b", lower_text):
        entities["gender"] = "female"

    # 6. Extract Facility Preference
    for key, facility_name in FACILITY_MAPPING.items():
        if key in lower_text:
            entities["facility_preference"] = facility_name
            break

    # 7. Extract Preferred Date
    if "hôm nay" in lower_text:
        entities["preferred_date"] = today.isoformat()
    elif "ngày mai" in lower_text or "mai" in lower_text.split():
        entities["preferred_date"] = (today + timedelta(days=1)).isoformat()
    elif "ngày mốt" in lower_text or "ngày kia" in lower_text:
        entities["preferred_date"] = (today + timedelta(days=2)).isoformat()
    else:
        date_pattern = re.search(r"(?:ngày|vào\s+ngày)\s+(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{4}))?", text_clean, re.IGNORECASE)
        if date_pattern:
            d = int(date_pattern.group(1))
            m = int(date_pattern.group(2))
            y = int(date_pattern.group(3)) if date_pattern.group(3) else today.year
            try:
                entities["preferred_date"] = date(y, m, d).isoformat()
            except ValueError:
                pass

    # 8. Extract Preferred Period (buổi khám)
    if any(w in lower_text for w in ["buổi sáng", "sáng mai", "sáng nay", "buoi sang"]):
        entities["preferred_period"] = "morning"
    elif any(w in lower_text for w in ["buổi chiều", "chiều mai", "chiều nay", "buoi chieu"]):
        entities["preferred_period"] = "afternoon"
    elif any(w in lower_text for w in ["buổi tối", "tối nay", "buoi toi"]):
        entities["preferred_period"] = "evening"

    # 9. Extract Package Inquiry
    entities["is_package_inquiry"] = detect_package_inquiry(text_clean)

    return entities


def detect_package_inquiry(text: str) -> bool:
    """Detect if the patient is inquiring about health checkup packages / service packages."""
    if not text:
        return False
    lower = text.lower()
    package_keywords = [
        "gói khám", "goi kham",
        "gói dịch vụ", "goi dich vu",
        "khám tổng quát", "kham tong quat",
        "khám sức khỏe tổng quát", "kham suc khoe tong quat",
        "khám định kỳ", "kham dinh ky",
        "tầm soát", "tam soat",
        "gói tầm soát", "goi tam soat",
        "gói sinh", "goi sinh",
        "gói thai sản", "goi thai san",
        "gói tiêm chủng", "goi tiem chung",
        "gói tiền hôn nhân", "goi tien hon nhan",
        "gói tim mạch", "goi tim mach",
        "gói ung thư", "goi ung thu",
        "bảng giá gói", "danh mục gói", "các gói khám"
    ]
    return any(kw in lower for kw in package_keywords)


def extract_clinical_details(
    text: str,
    clinical_facts: dict[str, Any] | None = None,
    history_texts: list[str] | None = None,
) -> dict[str, Any]:
    """Extract clinical details (location, severity, duration, associated, negatives) from text and facts."""
    all_texts = list(history_texts or [])
    if text and text not in all_texts:
        all_texts.append(text)
    combined = " ".join(all_texts).strip()
    lower_comb = combined.lower()
    facts = clinical_facts or {}

    # 1. Location extraction
    locations = []
    location_map = [
        # Extremities & Specific joints (prioritize specific digits/joints first)
        (r"\b(ngón tay cái|ngón cái|ngon tay cai|ngon cai)\b", "Khớp ngón tay cái"),
        (r"\b(ngón trỏ|ngón giữa|ngón áp út|ngón út)\b", "Khớp ngón tay"),
        (r"\b(khớp ngón tay|khớp ngón|ngón tay|ngon tay|khop ngon)\b", "Khớp ngón tay"),
        (r"\b(cổ tay|mu bàn tay|lòng bàn tay|bàn tay)\b", "Cổ tay / Bàn tay"),
        (r"\b(khớp khuỷu|khuỷu tay|cùi chỏ)\b", "Khớp khuỷu tay"),
        (r"\b(cánh tay|bắp tay|cẳng tay)\b", "Vùng cánh tay"),
        (r"\b(ngón chân cái|ngón cái chân)\b", "Khớp ngón chân cái"),
        (r"\b(ngón chân|khớp ngón chân)\b", "Khớp ngón chân"),
        (r"\b(cổ chân|mắt cá chân|mắt cá|mu bàn chân|lòng bàn chân|gót chân|bàn chân)\b", "Cổ chân / Bàn chân"),
        (r"\b(khớp gối|đầu gối)\b", "Khớp gối"),
        (r"\b(khớp vai|bả vai|khớp bả vai)\b", "Khớp vai"),
        (r"\b(khớp háng|vùng háng)\b", "Khớp háng"),
        (r"\b(khớp thái dương hàm|quai hàm)\b", "Khớp thái dương hàm"),
        # Spine & Neck
        (r"\b(đốt sống cổ|cột sống cổ|vùng cổ gáy|cổ gáy)\b", "Cột sống cổ / Vùng sau gáy"),
        (r"\b(thắt lưng|vùng lưng dưới|cột sống thắt lưng|lưng dưới)\b", "Vùng thắt lưng / Cột sống"),
        (r"\b(cột sống|xương sống|đốt sống)\b", "Cột sống"),
        (r"\b(sau gáy|vùng chẩm)\b", "Vùng sau gáy"),
        # Head & Throat
        (r"\b(nửa đầu bên trái|nửa đầu trái)\b", "Nửa đầu trái"),
        (r"\b(nửa đầu bên phải|nửa đầu phải)\b", "Nửa đầu phải"),
        (r"\b(thái dương|hai bên thái dương)\b", "Vùng thái dương"),
        (r"\b(vùng trán|trán|đỉnh đầu)\b", "Vùng trán / Đỉnh đầu"),
        (r"\b(quanh mắt|hốc mắt)\b", "Vùng quanh mắt"),
        (r"\b(cổ họng|vòm họng|họng|thanh quản)\b", "Vùng họng / thanh quản"),
        # Chest & Abdomen
        (r"\b(ngực trái|ngực bên trái)\b", "Vùng ngực trái"),
        (r"\b(ngực phải|ngực bên phải)\b", "Vùng ngực phải"),
        (r"\b(sau xương ức|giữa ngực)\b", "Sau xương ức"),
        (r"\b(thượng vị|vùng trên rốn)\b", "Vùng thượng vị"),
        (r"\b(hạ sườn phải|sườn phải)\b", "Hạ sườn phải"),
        (r"\b(hạ sườn trái|sườn trái)\b", "Hạ sườn trái"),
        (r"\b(quanh rốn|vùng rốn)\b", "Quanh rốn"),
        (r"\b(hố chậu phải|bụng dưới bên phải|ruột thừa)\b", "Hố chậu phải / Bụng dưới phải"),
        (r"\b(hố chậu trái|bụng dưới bên trái)\b", "Hố chậu trái / Bụng dưới trái"),
        (r"\b(bụng dưới|hạ vị)\b", "Vùng hạ vị / Bụng dưới"),
    ]
    for pattern, loc_name in location_map:
        if re.search(pattern, lower_comb):
            locations.append(loc_name)
    if not locations and facts.get("location"):
        locations.append(str(facts["location"]))
    primary_location = locations[0] if locations else ""

    # 2. Pain Severity & Score (0-10 or descriptive)
    severity = ""
    pain_score = None
    score_match = re.search(r"\b(?:đau|mức độ|thang điểm|khoảng)\s*(\d{1,2})\s*(?:/|trên|\/)\s*10\b", lower_comb)
    if not score_match:
        score_match = re.search(r"\b(\d{1,2})\s*(?:/|trên|\/)\s*10\b", lower_comb)
    if not score_match:
        score_match = re.search(r"\b(?:thang điểm|điểm đau|đau mức)\s*(\d{1,2})\b", lower_comb)

    if score_match:
        val = int(score_match.group(1))
        if 0 <= val <= 10:
            pain_score = val
            if val >= 8:
                severity = f"{val}/10 (Đau dữ dội / Mức độ nặng)"
            elif val >= 5:
                severity = f"{val}/10 (Đau vừa / Trung bình)"
            else:
                severity = f"{val}/10 (Đau nhẹ)"

    if not severity:
        if any(w in lower_comb for w in ["dữ dội", "quặn thắt", "quặn từng cơn", "nhói buốt", "không chịu nổi", "như dao đâm"]):
            severity = "Mức độ nặng (Dữ dội / Đau quặn)"
        elif any(w in lower_comb for w in ["âm ỉ", "tức nặng", "nóng rát", "nhức nhối", "khó chịu nhiều"]):
            severity = "Mức độ trung bình (Âm ỉ / Tức nặng)"
        elif any(w in lower_comb for w in ["nhẹ", "hơi đau", "châm chích", "thoang thoảng"]):
            severity = "Mức độ nhẹ"

    # 3. Duration & Onset
    duration = ""
    dur_match = re.search(r"\b(\d{1,2})\s*(ngày|ngay|tuần|tuan|tháng|thang|giờ|gio|tiếng)\s*(?:nay|rồi|qua|trước)?\b", lower_comb)
    if dur_match:
        duration = f"{dur_match.group(1)} {dur_match.group(2)} nay"
    elif "sáng nay" in lower_comb:
        duration = "Từ sáng nay"
    elif "hôm qua" in lower_comb:
        duration = "Từ hôm qua"
    elif "mới bị" in lower_comb or "đột ngột" in lower_comb:
        duration = "Khởi phát đột ngột gần đây"
    elif facts.get("duration_days"):
        duration = f"{facts['duration_days']} ngày nay"

    # 4. Associated Symptoms
    associated = []
    assoc_patterns = [
        (r"\b(buồn nôn|nôn nao)\b", "Buồn nôn"),
        (r"\b(nôn mửa|đã nôn|nôn ra)\b", "Nôn"),
        (r"\b(sốt nhẹ|sốt cao|nóng sốt|phát sốt)\b", "Sốt"),
        (r"\b(chóng mặt|hoa mắt|choáng váng)\b", "Chóng mặt"),
        (r"\b(ợ chua|ợ nóng|trào ngược)\b", "Ợ chua, trào ngược"),
        (r"\b(khó thở|hụt hơi|thở dốc)\b", "Khó thở nhẹ/vừa"),
        (r"\b(vã mồ hôi|toát mồ hôi)\b", "Vã mồ hôi"),
        (r"\b(tiêu chảy|đi ngoài lỏng)\b", "Tiêu chảy"),
        (r"\b(ho đờm|ho khan|ho nhiều)\b", "Ho"),
        (r"\b(mệt mỏi|suy nhược|chán ăn)\b", "Mệt mỏi, chán ăn"),
    ]
    for pattern, name in assoc_patterns:
        if re.search(pattern, lower_comb) and not re.search(rf"không\s+{pattern}", lower_comb):
            associated.append(name)

    # 5. Negative Findings / Exclusions
    negatives = []
    neg_patterns = [
        (r"không\s+(?:bị\s+)?sốt", "Không sốt"),
        (r"không\s+(?:bị\s+)?khó\s+thở", "Không khó thở"),
        (r"không\s+(?:bị\s+)?nôn", "Không nôn"),
        (r"không\s+(?:bị\s+)?đau\s+ngực", "Không đau ngực"),
        (r"không\s+(?:bị\s+)?chóng\s+mặt", "Không chóng mặt"),
        (r"không\s+(?:bị\s+)?tiêu\s+chảy", "Không tiêu chảy"),
        (r"không\s+lan", "Đau không lan"),
    ]
    for pattern, label in neg_patterns:
        if re.search(pattern, lower_comb):
            negatives.append(label)

    # 6. Primary Complaint description
    complaint = ""
    if any(w in lower_comb for w in ["đau bụng", "đau dạ dày", "đau thượng vị"]):
        complaint = "Đau bụng"
    elif any(w in lower_comb for w in ["đau ngực", "tức ngực", "nặng ngực"]):
        complaint = "Đau tức ngực"
    elif any(w in lower_comb for w in ["đau đầu", "nhức đầu"]):
        complaint = "Đau đầu"
    elif any(w in lower_comb for w in ["đau họng", "rát họng", "viêm họng"]):
        complaint = "Đau rát họng"
    elif any(w in lower_comb for w in ["đau lưng", "đau mỏi thắt lưng"]):
        complaint = "Đau mỏi thắt lưng"
    elif any(w in lower_comb for w in ["đau khớp", "mỏi khớp", "nhức khớp", "viêm khớp", "sưng khớp", "đau ngón", "sưng ngón", "cứng khớp", "khớp ngón", "trật khớp"]):
        complaint = "Đau nhức khớp"
    elif any(w in lower_comb for w in ["đau cơ", "mỏi cơ", "chuột rút"]):
        complaint = "Đau mỏi cơ"
    elif any(w in lower_comb for w in ["chóng mặt", "choáng váng"]):
        complaint = "Chóng mặt / Choáng váng"
    elif any(w in lower_comb for w in ["khó thở", "hụt hơi"]):
        complaint = "Khó thở"
    elif any(w in lower_comb for w in ["sốt cao", "sốt nhẹ", "phát sốt"]):
        complaint = "Sốt"
    elif any(w in lower_comb for w in ["ho khan", "ho đờm", "ho dai dẳng"]):
        complaint = "Ho kéo dài"
    else:
        # Fallback to symptoms list from facts
        active_codes = facts.get("active_complaint_codes") or []
        if active_codes:
            complaint = active_codes[0].replace("_", " ").capitalize()

    return {
        "primary_complaint": complaint,
        "location": primary_location,
        "severity": severity,
        "pain_score": pain_score,
        "duration": duration,
        "associated": associated,
        "negatives": negatives,
    }


def generate_clinical_summary(state: dict[str, Any], current_text: str = "") -> dict[str, Any]:
    """Synthesize structured clinical notes formatted for medical reception & triage."""
    details = extract_clinical_details(
        text=current_text,
        clinical_facts=state.get("clinical_facts"),
        history_texts=state.get("collected_details"),
    )

    parts = []
    # 1. Main complaint & location
    comp = details.get("primary_complaint") or "Khó chịu / Triệu chứng bất thường"
    loc = details.get("location")
    sev = details.get("severity")
    dur = details.get("duration")

    lead = f"Bệnh nhân có triệu chứng {comp.lower()}"
    if loc:
        lead += f" ({loc})"
    if sev:
        lead += f", {sev}"
    if dur:
        lead += f", diễn tiến {dur}"
    lead += "."
    parts.append(lead)

    # 2. Associated symptoms
    assoc = details.get("associated") or []
    if assoc:
        parts.append(f"Triệu chứng đi kèm: {', '.join(assoc)}.")

    # 3. Negatives
    negs = details.get("negatives") or []
    if negs:
        parts.append(f"Dấu hiệu loại trừ: {', '.join(negs)}.")

    summary_text = " ".join(parts).strip()
    return {
        "summary": summary_text,
        "details": details,
    }


def evaluate_missing_fields(
    patient_name: str | None,
    patient_phone: str | None,
    date_of_birth: str | None,
    facility_preference: str | None = None,
    preferred_date: str | None = None,
) -> list[str]:
    """Identify which required or recommended fields are still missing."""
    missing = []
    if not patient_name or len(patient_name.strip()) < 2:
        missing.append("patient_name")
    if not patient_phone or len(re.sub(r"\D", "", patient_phone)) < 9:
        missing.append("patient_phone")
    if not date_of_birth:
        missing.append("date_of_birth")
    return missing


def build_booking_guidance_text(
    is_authenticated: bool,
    missing_fields: list[str],
    current_intake: dict[str, Any],
    specialty_name: str,
    lang: str = "vi",
) -> str:
    """Generate friendly, clinical guidance prompting for missing fields or confirming live fill."""
    name = current_intake.get("patient_name") or ""
    phone = current_intake.get("patient_phone") or ""
    facility = current_intake.get("facility_preference") or ""
    date_str = current_intake.get("preferred_date") or ""

    if is_authenticated:
        # Authenticated user flow
        if lang == "en":
            return (
                f"I have pre-filled the **Appointment Request Form** on the right with your verified profile:\n"
                f"- **Patient:** {name}\n"
                f"- **Phone:** {phone}\n"
                f"- **Specialty:** {specialty_name}\n\n"
                "Please review your preferred date and facility on the live form, then click **'Confirm & Submit'**."
            )
        return (
            f"Dạ, em đã điền sẵn thông tin từ tài khoản của bác vào **Phiếu Đăng Ký Khám** ở khung bên cạnh:\n"
            f"- **Bệnh nhân:** {name}\n"
            f"- **Số điện thoại:** {phone}\n"
            f"- **Chuyên khoa:** {specialty_name}\n\n"
            "Bác vui lòng kiểm tra lại ngày và cơ sở mong muốn trên phiếu bên cạnh rồi bấm **'Xác nhận gửi thông tin đặt khám'** nhé ạ!"
        )

    # Guest user flow (Slot-Filling)
    if not missing_fields:
        # Fully filled by conversational extraction
        if lang == "en":
            return (
                f"I have automatically filled the **Appointment Request Form** on the right with your provided details:\n"
                f"- **Patient:** {name}\n"
                f"- **Phone:** {phone}\n"
                f"- **Specialty:** {specialty_name}\n"
                + (f"- **Facility:** {facility}\n" if facility else "")
                + "\nPlease review the details on the right panel and click **'Confirm & Submit'** to finalize."
            )
        return (
            f"Dạ, em đã tự động điền các thông tin của bác vào **Phiếu Đăng Ký Khám** ở khung bên cạnh:\n"
            f"- **Họ và tên:** {name}\n"
            f"- **Số điện thoại:** {phone}\n"
            f"- **Chuyên khoa:** {specialty_name}\n"
            + (f"- **Cơ sở khám:** {facility}\n" if facility else "")
            + "\nBác vui lòng kiểm tra lại thông tin trên form bên cạnh (hoặc chỉnh sửa nếu cần) và bấm **'Xác nhận gửi thông tin đặt khám'** nhé ạ!"
        )

    # Missing some fields
    missing_labels = []
    if "patient_name" in missing_fields:
        missing_labels.append("1. **Họ và tên đầy đủ** của người khám" if lang == "vi" else "1. Full name")
    if "patient_phone" in missing_fields:
        missing_labels.append("2. **Số điện thoại liên hệ**" if lang == "vi" else "2. Contact phone number")
    if "date_of_birth" in missing_fields:
        missing_labels.append("3. **Ngày sinh** (hoặc Năm sinh / Số tuổi)" if lang == "vi" else "3. Date of birth / Age")

    bullet_list = "\n".join(missing_labels)

    if name:
        greeting = f"Dạ {name}, " if lang == "vi" else f"Dear {name}, "
    else:
        greeting = "Dạ, " if lang == "vi" else ""

    if lang == "en":
        return (
            f"{greeting}to help you prepare the appointment booking for **{specialty_name}** (hold requests are not verified until confirmed), "
            "please provide the following details so I can auto-fill the form for you:\n"
            f"{bullet_list}\n\n"
            "*(You can also type directly into the live form on the right at any time.)*"
        )

    return (
        f"{greeting}để em tự động điền phiếu hẹn khám **Khoa {specialty_name}** giúp bác (yêu cầu giữ chỗ chưa được database xác minh cho đến khi điền đủ thông tin), "
        "bác vui lòng cho em biết thêm các thông tin còn thiếu sau nhé ạ:\n"
        f"{bullet_list}\n\n"
        "*(Bác cũng có thể trực tiếp gõ hoặc chỉnh sửa vào Phiếu Khám ở khung bên cạnh bất cứ lúc nào ạ!)*"
    )
