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
    # Ocean Park
    "ocean park 2": "Bệnh viện ĐKQT Vinmec Ocean Park 2 (Hưng Yên)",
    "ocean park ii": "Bệnh viện ĐKQT Vinmec Ocean Park 2 (Hưng Yên)",
    "ocean city": "Bệnh viện ĐKQT Vinmec Ocean Park 2 (Hưng Yên)",
    "ocean park": "Phòng khám ĐKQT Vinmec Ocean Park (Hà Nội)",
    "oceanpark": "Phòng khám ĐKQT Vinmec Ocean Park (Hà Nội)",
    "gia lâm": "Phòng khám ĐKQT Vinmec Ocean Park (Hà Nội)",
    "gia lam": "Phòng khám ĐKQT Vinmec Ocean Park (Hà Nội)",
    # Royal City
    "royal city": "Phòng khám ĐKQT Vinmec Royal City (Hà Nội)",
    "royalcity": "Phòng khám ĐKQT Vinmec Royal City (Hà Nội)",
    "nguyễn trãi": "Phòng khám ĐKQT Vinmec Royal City (Hà Nội)",
    # Riverside
    "riverside": "Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)",
    "phúc lợi": "Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)",
    "long biên": "Bệnh viện ĐKQT Vinmec Riverside (Hà Nội)",
    # Times City
    "times city": "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)",
    "timescity": "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)",
    "hai bà trưng": "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)",
    "minh khai": "Bệnh viện ĐKQT Vinmec Times City (Hà Nội)",
    # Central Park
    "central park": "Bệnh viện ĐKQT Vinmec Central Park (TP.HCM)",
    "centralpark": "Bệnh viện ĐKQT Vinmec Central Park (TP.HCM)",
    "bình thạnh": "Bệnh viện ĐKQT Vinmec Central Park (TP.HCM)",
    "nguyễn hữu cảnh": "Bệnh viện ĐKQT Vinmec Central Park (TP.HCM)",
    # Smart City
    "smart city": "Phòng khám ĐKQT Vinmec Smart City (Hà Nội)",
    "smartcity": "Phòng khám ĐKQT Vinmec Smart City (Hà Nội)",
    "tây mỗ": "Phòng khám ĐKQT Vinmec Smart City (Hà Nội)",
    # Other cities
    "hải phòng": "Bệnh viện ĐKQT Vinmec Hải Phòng",
    "hai phong": "Bệnh viện ĐKQT Vinmec Hải Phòng",
    "đà nẵng": "Bệnh viện ĐKQT Vinmec Đà Nẵng",
    "da nang": "Bệnh viện ĐKQT Vinmec Đà Nẵng",
    "nha trang": "Bệnh viện ĐKQT Vinmec Nha Trang",
    "phú quốc": "Bệnh viện ĐKQT Vinmec Phú Quốc",
    "phu quoc": "Bệnh viện ĐKQT Vinmec Phú Quốc",
    "hạ long": "Bệnh viện ĐKQT Vinmec Hạ Long",
    "ha long": "Bệnh viện ĐKQT Vinmec Hạ Long",
    "cần thơ": "Bệnh viện ĐKQT Vinmec Cần Thơ",
    "can tho": "Bệnh viện ĐKQT Vinmec Cần Thơ",
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


def parse_vietnamese_date(text: str, reference_date: date | None = None) -> date | None:
    """Parse relative and explicit Vietnamese date expressions into a date object.

    Handles:
    - 'hôm nay', 'ngày mai', 'ngày mốt', 'ngày kia', 'ngày kìa'
    - 'thứ 2 tuần sau', 'thứ hai tuần tới', 'thứ 3 tới', 'thứ 4 tuần này', 'thứ 6', 'chủ nhật'
    - 'đầu tuần sau', 'cuối tuần này', 'cuối tuần sau'
    - 'ngày 05/10/2026', '05/10', 'ngày 5 tháng 10 năm 2026', 'ngày 5 tháng 10'
    """
    if not text:
        return None
    ref = reference_date or _get_vn_today()
    t = text.lower().strip()

    # 1. Exact date: DD/MM/YYYY or DD/MM
    dm_match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{4}))?\b", t)
    if dm_match:
        d, m = int(dm_match.group(1)), int(dm_match.group(2))
        y = int(dm_match.group(3)) if dm_match.group(3) else ref.year
        try:
            res = date(y, m, d)
            if not dm_match.group(3) and res < ref:
                res = date(y + 1, m, d)
            return res
        except ValueError:
            pass

    # 2. Words: (ngày) D tháng M (năm Y)
    dt_match = re.search(r"(?:ngày\s+)?(\d{1,2})\s+tháng\s+(\d{1,2})(?:\s+năm\s+(\d{4}))?", t)
    if dt_match:
        d, m = int(dt_match.group(1)), int(dt_match.group(2))
        y = int(dt_match.group(3)) if dt_match.group(3) else ref.year
        try:
            res = date(y, m, d)
            if not dt_match.group(3) and res < ref:
                res = date(y + 1, m, d)
            return res
        except ValueError:
            pass

    # 3. Relative today/tomorrow/after tomorrow
    if "hôm nay" in t:
        return ref
    if any(k in t for k in ["ngày mai", "sáng mai", "chiều mai", "tối mai"]) or "mai" in t.split():
        return ref + timedelta(days=1)
    if "ngày mốt" in t or "ngày kia" in t:
        return ref + timedelta(days=2)
    if "ngày kìa" in t:
        return ref + timedelta(days=3)

    # 4. Weekdays mapping (Monday = 0, Sunday = 6)
    weekday_map = {
        "thứ 2": 0, "thứ hai": 0, "thu 2": 0, "thu hai": 0, "t2": 0,
        "thứ 3": 1, "thứ ba": 1, "thu 3": 1, "thu ba": 1, "t3": 1,
        "thứ 4": 2, "thứ tư": 2, "thứ bốn": 2, "thu 4": 2, "thu tu": 2, "t4": 2,
        "thứ 5": 3, "thứ năm": 3, "thu 5": 3, "thu nam": 3, "t5": 3,
        "thứ 6": 4, "thứ sáu": 4, "thu 6": 4, "thu sau": 4, "t6": 4,
        "thứ 7": 5, "thứ bảy": 5, "thu 7": 5, "thu bay": 5, "t7": 5,
        "chủ nhật": 6, "chu nhat": 6, "cn": 6,
    }

    found_weekday = None
    for wk_name in sorted(weekday_map.keys(), key=len, reverse=True):
        if re.search(r"\b" + re.escape(wk_name) + r"\b", t):
            found_weekday = weekday_map[wk_name]
            break

    is_next_week = any(k in t for k in ["tuần sau", "tuan sau", "tuần tới", "tuan toi", "tuần kế", "kế tiếp"])
    is_this_week = any(k in t for k in ["tuần này", "tuan nay"])

    if found_weekday is not None:
        ref_weekday = ref.weekday()  # 0..6
        if is_next_week:
            days_to_next_monday = (7 - ref_weekday) if ref_weekday != 0 else 7
            next_monday = ref + timedelta(days=days_to_next_monday)
            return next_monday + timedelta(days=found_weekday)
        elif is_this_week:
            days_from_monday = ref_weekday
            this_monday = ref - timedelta(days=days_from_monday)
            return this_monday + timedelta(days=found_weekday)
        else:
            diff = found_weekday - ref_weekday
            if diff <= 0:
                diff += 7
            return ref + timedelta(days=diff)

    if "đầu tuần sau" in t or "đầu tuần tới" in t:
        days_to_next_monday = (7 - ref.weekday()) if ref.weekday() != 0 else 7
        return ref + timedelta(days=days_to_next_monday)
    if "cuối tuần này" in t:
        diff = 5 - ref.weekday()
        return ref + timedelta(days=max(0, diff))
    if "cuối tuần sau" in t:
        days_to_next_monday = (7 - ref.weekday()) if ref.weekday() != 0 else 7
        return ref + timedelta(days=days_to_next_monday + 5)

    return None


DOCTOR_STOPWORDS = {
    "chuyên", "khoa", "nào", "giỏi", "vinmec", "gặp", "điều", "phối", "viên",
    "rảnh", "trực", "trống", "lịch", "trong", "khám", "ở", "tại", "cho", "giúp",
    "xem", "liệt", "kê", "danh", "sách", "tự", "chọn", "tư", "vấn", "có", "tốt",
    "chữa", "trị", "gì", "đó", "đấy", "hôm", "nay", "mai", "tuần", "sau", "tới",
    "sáng", "chiều", "tối", "biết", "với", "được", "không", "ạ", "nhé", "tôi", "em",
    "ai", "tìm", "hỏi", "chỉ", "định", "sắp", "xếp", "này", "kia"
}


def detect_doctor_inquiry(text: str) -> bool:
    """Detect if user is asking to list / choose / inquire about available doctors."""
    if not text:
        return False
    lower = text.lower()
    inquiry_keywords = [
        "tự chọn bác sĩ", "tu chon bac si",
        "chọn bác sĩ", "chon bac si",
        "liệt kê tên bác sĩ", "liet ke ten bac si",
        "liệt kê bác sĩ", "liet ke bac si",
        "danh sách bác sĩ", "danh sach bac si",
        "bác sĩ rảnh", "bac si ranh",
        "bác sĩ trống", "bac si trong",
        "bác sĩ trực", "bac si truc",
        "bác sĩ nào rảnh", "bac si nao ranh",
        "bác sĩ nào khám", "bac si nao kham",
        "bác sĩ nào giỏi", "bac si nao gioi",
        "có bác sĩ nào", "co bac si nao",
        "tên bác sĩ", "ten bac si",
    ]
    return any(kw in lower for kw in inquiry_keywords)


def detect_booking_confirmation(text: str) -> bool:
    """Detect if the user gives direct conversational confirmation to submit/book the appointment."""
    if not text:
        return False
    lower = text.lower().strip()
    confirm_patterns = [
        r"\b(?:tôi\s+)?xác\s+nhận(?:\s+đặt\s+lịch|\s+đặt\s+hẹn|\s+đặt\s+khám)?\b",
        r"\b(?:tôi\s+thấy\s+)?lịch\s+(?:này\s+)?ổn[,\s]+đặt\s+(?:cho\s+tôi|giúp\s+tôi|hộ\s+tôi)\b",
        r"\bđặt\s+lịch(?:\s+cho\s+tôi|\s+giúp\s+tôi|\s+đi|\s+luôn|\s+nhé)\b",
        r"\bchốt\s+lịch(?:\s+này|\s+giúp\s+tôi|\s+cho\s+tôi|\s+đi|\s+nhé)\b",
        r"\bđồng\s+ý\s+(?:đặt\s+lịch|lịch\s+này|thông\s+tin\s+này)\b",
        r"\bđặt\s+khám(?:\s+luôn|\s+đi|\s+cho\s+tôi|\s+nhé)\b",
        r"\bok[,\s]+đặt(?:\s+lịch)?\b",
    ]
    for pat in confirm_patterns:
        if re.search(pat, lower):
            return True
    exact_phrases = [
        "đặt lịch đi", "dat lich di",
        "tôi xác nhận đặt lịch", "toi xac nhan dat lich",
        "xác nhận đặt lịch", "xac nhan dat lich",
        "tôi thấy lịch này ổn, đặt cho tôi", "toi thay lich nay on, dat cho toi",
        "tôi thấy lịch này ổn đặt cho tôi", "toi thay lich nay on dat cho toi",
        "đặt cho tôi đi", "dat cho toi di",
        "chốt lịch đi", "chot lich di",
        "xác nhận giúp tôi", "xac nhan giup toi"
    ]
    return any(p in lower for p in exact_phrases)


def detect_appointment_query(text: str) -> bool:
    """Detect if the patient is querying/checking their existing appointment or booking status."""
    if not text:
        return False
    lower = text.lower().strip()
    query_phrases = [
        "tôi có lịch khám", "toi co lich kham",
        "xem lại thông tin", "xem lai thong tin",
        "cho tôi xem lại", "cho toi xem lai",
        "xem lại lịch", "xem lai lich",
        "kiểm tra lịch hẹn", "kiem tra lich hen",
        "kiểm tra lịch khám", "kiem tra lich kham",
        "thông tin lịch khám", "thong tin lich kham",
        "tra cứu lịch", "tra cuu lich",
        "lịch đã đặt", "lich da dat",
        "tôi đã đặt lịch", "toi da dat lich",
        "lịch hẹn của tôi", "lich hen cua toi",
    ]
    return any(p in lower for p in query_phrases)


def extract_booking_entities(text: str, current_state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract patient booking details from conversation text."""
    current_state = current_state or {}
    text_clean = text.strip()
    lower_text = text_clean.lower()
    entities: dict[str, Any] = {}

    # 1. Booking intent detection
    booking_intent_keywords = [
        "đặt lịch", "dat lich", "hẹn khám", "hen kham", "đăng ký khám", "dang ky kham",
        "muốn khám", "muon kham", "muốn đi khám", "muon di kham", "đi khám", "di kham",
        "gặp bác sĩ", "gap bac si", "book lịch", "book lich",
        "phiếu khám", "phieu kham", "đặt hẹn", "dat hen", "lên lịch", "len lich",
        "lịch hẹn", "lich hen", "khám bệnh", "kham benh"
    ]
    is_booking_intent = any(kw in lower_text for kw in booking_intent_keywords)
    entities["is_booking_intent"] = is_booking_intent
    entities["is_doctor_inquiry"] = detect_doctor_inquiry(text_clean)
    entities["is_booking_confirmation"] = detect_booking_confirmation(text_clean)
    entities["is_appointment_query"] = detect_appointment_query(text_clean)

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
        r"(?:tôi|toi|mình|minh|em|anh|chị|chi)\s+tên(?:\s+là)?\s+([A-Za-zÀ-ỹ\s]+?)(?:[,.\n]|(?:\s+(?:tôi|toi|em|mình|minh|bị|bi|đang|dang|năm|nam|sinh|muốn|muon|khám|kham))|$)",
        r"tên\s+(?:của\s+)?(?:tôi|mình|em|bệnh\s+nhân|người\s+khám)(?:\s+là)?\s+([A-Za-zÀ-ỹ\s]+?)(?:[,.\n]|(?:\s+(?:tôi|toi|em|mình|minh|bị|bi|đang|dang|năm|nam|sinh|muốn|muon|khám|kham))|$)",
        r"(?:bệnh\s+nhân|người\s+khám)(?:\s+tên)?(?:\s+là)?\s*[:\-]?\s*([A-Za-zÀ-ỹ\s]+?)(?:[,.\n]|(?:\s+(?:tôi|toi|em|mình|minh|bị|bi|đang|dang|năm|nam|sinh|muốn|muon|khám|kham))|$)",
        r"(?:họ\s+và\s+tên|họ\s+tên)\s*[:\-]?\s*([A-Za-zÀ-ỹ\s]+?)(?:[,.\n]|(?:\s+(?:tôi|toi|em|mình|minh|bị|bi|đang|dang|năm|nam|sinh|muốn|muon|khám|kham))|$)",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text_clean, re.IGNORECASE)
        if match:
            candidate = clean_name(match.group(1))
            # Validate plausible name: 1 to 5 words, not matching stopwords
            words = candidate.split()
            if 1 <= len(words) <= 5 and not any(w.lower() in {"đặt", "lịch", "khám", "bác", "sĩ", "ở", "tại", "vinmec", "bị", "đang", "là"} for w in words):
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
    # Sort keys by length descending so longer keys match before shorter substrings
    for key in sorted(FACILITY_MAPPING.keys(), key=len, reverse=True):
        if key in lower_text:
            entities["facility_preference"] = FACILITY_MAPPING[key]
            break

    # 7. Extract Preferred Date using Vietnamese date parser
    parsed_date = parse_vietnamese_date(text_clean, reference_date=today)
    if parsed_date:
        entities["preferred_date"] = parsed_date.isoformat()

    # 8. Extract Preferred Period (buổi khám)
    if re.search(r"\b(ca\s+sáng|buổi\s+sáng|buoi\s+sang|sáng\s+mai|sáng\s+nay|buổi\s+sớm|ban\s+sáng)\b", lower_text) or "ca sáng" in lower_text or "buổi sáng" in lower_text:
        entities["preferred_period"] = "morning"
    elif re.search(r"\b(ca\s+chiều|buổi\s+chiều|buoi\s+chieu|chiều\s+mai|chiều\s+nay|ban\s+chiều)\b", lower_text) or "ca chiều" in lower_text or "buổi chiều" in lower_text:
        entities["preferred_period"] = "afternoon"
    elif re.search(r"\b(ca\s+tối|buổi\s+tối|buoi\s+toi|tối\s+nay|tối\s+mai|ban\s+đêm)\b", lower_text) or "ca tối" in lower_text or "buổi tối" in lower_text:
        entities["preferred_period"] = "evening"

    # 9. Extract Explicit Specialty Preference
    specialty_lookup = {
        "xương khớp": "Cơ xương khớp",
        "cơ xương khớp": "Cơ xương khớp",
        "chấn thương chỉnh hình": "Chấn thương chỉnh hình & Cột sống",
        "thần kinh": "Thần kinh",
        "tim mạch": "Tim mạch",
        "tiêu hóa": "Tiêu hóa",
        "tai mũi họng": "Tai Mũi Họng",
        "hô hấp": "Hô hấp",
        "phổi": "Hô hấp",
        "da liễu": "Da liễu",
        "nhi": "Nhi",
        "mắt": "Mắt",
        "sản phụ khoa": "Sản phụ khoa",
        "ung bướu": "Ung bướu",
    }
    for skw, sval in specialty_lookup.items():
        if re.search(rf"\b(?:khoa|chuyên\s+khoa)\s+{re.escape(skw)}\b", lower_text) or skw in lower_text:
            entities["specialty_preference"] = sval
            break

    # 10. Extract Doctor Preference / Coordinator arrangement
    if entities.get("is_doctor_inquiry"):
        # User is inquiring about doctors or asking to list/choose, not assigning a name
        entities["doctor_inquiry"] = True
    elif any(kw in lower_text for kw in ["điều phối viên", "dieu phoi vien", "bệnh viện sắp xếp", "tự sắp xếp", "chỉ định giúp", "sắp xếp theo điều phối viên", "điều phối viên sắp xếp"]):
        entities["doctor_preference"] = "coordinator"
        entities["doctor_name"] = "Điều phối viên y tế sắp xếp bác sĩ phù hợp nhất"
    else:
        doc_match = re.search(r"\b(?:bác\s+sĩ|bs\.?)\s+([A-Za-zÀ-ỹ\s]+?)(?:[,.\n]|(?:\s+(?:ở|tại|ngày|vào|buổi|khám))|$)", text_clean, re.IGNORECASE)
        if doc_match:
            candidate_doc = clean_name(doc_match.group(1))
            cand_words = [w.lower() for w in candidate_doc.split()]
            if 1 <= len(cand_words) <= 4 and not any(w in DOCTOR_STOPWORDS for w in cand_words):
                entities["doctor_name"] = f"BS. {candidate_doc}"
                entities["doctor_preference"] = candidate_doc

    # 11. Extract Package Inquiry
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
        (r"\b(khớp gối\s+(?:ở\s+)?(?:chân\s+)?phải|đầu gối\s+(?:ở\s+)?(?:chân\s+)?phải|gối phải|gối chân phải|đầu gối chân phải)\b", "Khớp gối phải"),
        (r"\b(khớp gối\s+(?:ở\s+)?(?:chân\s+)?trái|đầu gối\s+(?:ở\s+)?(?:chân\s+)?trái|gối trái|gối chân trái|đầu gối chân trái)\b", "Khớp gối trái"),
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
        (r"\b(bụng\s+(?:dữ\s+dội\s+)?(?:ở\s+)?(?:bên\s+)?phải|hố chậu phải|bụng dưới bên phải|bụng phải|ở bên phải|bên phải bụng|ruột thừa)\b", "Hố chậu phải / Bụng dưới phải"),
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
    # Avoid matching appointment days like 'thứ 2 tuần sau' as duration
    dur_match = re.search(
        r"(?<!thứ\s)(?<!thu\s)\b(\d{1,2})\s*(ngày|ngay|tuần|tuan|tháng|thang|giờ|gio|tiếng)\s*(nay|rồi|qua|trước|nay\s+trở\s+lại)\b(?!(\s+(?:sau|tới|toi|này)))",
        lower_comb,
    )
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
        (r"\b(gặp vấn đề về đi lại|vấn đề về đi lại|khó đi lại|đi lại khó khăn|khó khăn khi đi lại|đi khập khiễng|hạn chế vận động)\b", "Hạn chế vận động, khó đi lại"),
        (r"\b(buồn nôn|nôn nao)\b", "Buồn nôn"),
        (r"\b(nôn ói|nôn mửa|nôn nhiều|đã nôn|nôn ra|nôn)\b", "Nôn ói"),
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


def format_vietnamese_date_display(date_str: str | None) -> str:
    """Format ISO date YYYY-MM-DD to friendly Vietnamese date representation."""
    if not date_str:
        return "Chưa chọn ngày"
    try:
        d = date.fromisoformat(date_str)
        weekday_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
        return f"{weekday_names[d.weekday()]}, ngày {d.strftime('%d/%m/%Y')}"
    except Exception:
        return date_str


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
    if not facility_preference:
        missing.append("facility_preference")
    if not preferred_date:
        missing.append("preferred_date")
    return missing


def build_booking_guidance_text(
    is_authenticated: bool,
    missing_fields: list[str],
    current_intake: dict[str, Any],
    specialty_name: str,
    lang: str = "vi",
) -> str:
    """Generate friendly, clinical guidance displaying all pre-filled fields and prompting for missing fields."""
    name = current_intake.get("patient_name") or ""
    phone = current_intake.get("patient_phone") or ""
    dob = current_intake.get("date_of_birth") or ""
    facility = current_intake.get("facility_preference") or ""
    date_str = current_intake.get("preferred_date") or ""
    period = current_intake.get("preferred_period") or "any"
    doc_name = (
        current_intake.get("doctor_name")
        or current_intake.get("preferred_doctor_name")
        or (current_intake.get("doctors", [{}])[0].get("name") if current_intake.get("selected_doctor_id") else "")
        or ""
    )
    clinical_notes = current_intake.get("clinical_summary") or current_intake.get("patient_notes") or ""

    period_display_map = {
        "morning": "Buổi sáng (08:00 - 12:00)",
        "afternoon": "Buổi chiều (13:30 - 17:00)",
        "evening": "Buổi tối",
        "any": "Cả ngày / Giờ linh hoạt",
    }
    period_display = period_display_map.get(period, "Cả ngày / Giờ linh hoạt")
    doc_display = doc_name if doc_name else "Điều phối viên y tế sắp xếp bác sĩ phù hợp nhất"
    date_display = format_vietnamese_date_display(date_str)

    # Missing check: evaluate which core fields are still needed
    missing_items = []
    if not name or len(name.strip()) < 2:
        missing_items.append("Họ và tên bệnh nhân" if lang == "vi" else "Patient full name")
    if not phone or len(re.sub(r"\D", "", phone)) < 9:
        missing_items.append("Số điện thoại liên hệ" if lang == "vi" else "Contact phone number")
    if not is_authenticated and not dob:
        missing_items.append("Ngày sinh (hoặc Năm sinh / Tuổi)" if lang == "vi" else "Date of birth")
    if not facility:
        missing_items.append("Cơ sở Vinmec tiếp nhận" if lang == "vi" else "Preferred Vinmec facility")
    if not date_str:
        missing_items.append("Ngày khám mong muốn" if lang == "vi" else "Preferred appointment date")

    has_missing = len(missing_items) > 0

    if lang == "en":
        summary_lines = [
            f"• 👤 **Patient:** {name if name else '*(Not provided)*'}",
            f"• 📞 **Phone:** {phone if phone else '*(Not provided)*'}",
            f"• 🩺 **Specialty:** {specialty_name}",
            f"• 👨‍⚕️ **Doctor:** {doc_display}",
            f"• 🏥 **Facility:** {facility if facility else '*(Not selected)*'}",
            f"• 📅 **Date:** {date_display}",
            f"• ⏰ **Session:** {period_display}",
        ]
        if clinical_notes:
            summary_lines.append(f"• 📝 **Clinical Summary & Symptoms:** {clinical_notes}")
        summary_block = "\n".join(summary_lines)

        if has_missing:
            missing_prompt = ", ".join(f"**{item}**" for item in missing_items)
            return (
                f"I have pre-filled your details on the **Appointment Request Form** on the right panel:\n\n"
                f"📋 **Recorded Appointment Information:**\n"
                f"{summary_block}\n\n"
                f"👉 To complete your appointment request, please let me know: {missing_prompt} "
                f"(or select directly on the form on the right panel)."
            )
        return (
            f"I have prepared all details on the **Appointment Request Form** on the right panel:\n\n"
            f"📋 **Prepared Appointment Information:**\n"
            f"{summary_block}\n\n"
            f"Please verify your details and click **'Confirm & Submit'** on the form to send your appointment request!"
        )

    # Vietnamese
    summary_lines = [
        f"• 👤 **Bệnh nhân:** {name if name else '*(Chưa có thông tin)*'}",
        f"• 📞 **Số điện thoại:** {phone if phone else '*(Chưa có thông tin)*'}",
        f"• 🩺 **Chuyên khoa:** {specialty_name}",
        f"• 👨‍⚕️ **Bác sĩ:** {doc_display}",
        f"• 🏥 **Cơ sở khám:** {facility if facility else '*(Chưa chọn cơ sở)*'}",
        f"• 📅 **Ngày khám:** {date_display}",
        f"• ⏰ **Buổi khám:** {period_display}",
    ]
    if clinical_notes:
        summary_lines.append(f"• 📝 **Lý do & Triệu chứng:** {clinical_notes}")
    summary_block = "\n".join(summary_lines)

    lead_in = (
        "Dạ, em đã điền thông tin từ tài khoản của bác vào **Phiếu Đăng Ký Khám** ở khung bên cạnh:\n\n"
        if is_authenticated
        else "Dạ, em đã tự động điền các thông tin của bác vào **Phiếu Đăng Ký Khám** ở khung bên cạnh:\n\n"
    )

    if has_missing:
        missing_prompt = ", ".join(f"**{item}**" for item in missing_items)
        return (
            f"{lead_in}"
            f"📋 **Thông tin lịch hẹn ghi nhận:**\n"
            f"{summary_block}\n\n"
            f"👉 Để hoàn thiện phiếu hẹn giúp bác, bác vui lòng cho em biết thêm: {missing_prompt} "
            f"(hoặc bác có thể nhấn chọn trực tiếp trên phiếu bên cạnh nhé ạ)!"
        )

    return (
        f"{lead_in}"
        f"📋 **Thông tin lịch hẹn đã chuẩn bị:**\n"
        f"{summary_block}\n\n"
        f"Bác vui lòng kiểm tra lại xem các thông tin trên đã chính xác chưa và bấm nút **'Xác nhận gửi thông tin đặt khám'** trên phiếu ở khung bên cạnh để hệ thống tiếp nhận lịch hẹn ngay nhé ạ!"
    )
