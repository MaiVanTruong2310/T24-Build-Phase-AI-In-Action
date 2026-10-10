"""
Language Detection & Bilingual Translation Utility for Medical Assistant (P-124).
Provides:
1. Fast heuristic language detection (Vietnamese 'vi' vs English 'en').
2. Standard bilingual specialty names for Vinmec International Hospital.
3. Bilingual clinical disclaimers and emergency headers.
"""

import re
import unicodedata

# Bộ từ điển chuyên khoa chuẩn song ngữ Vinmec
SPECIALTY_BILINGUAL_MAP: dict[str, dict[str, str]] = {
    "TIM_MACH": {"vi": "Trung tâm Tim mạch", "en": "Cardiology Center"},
    "NOI_TIM_MACH": {"vi": "Trung tâm Tim mạch", "en": "Cardiology Center"},
    "HO_HAP": {"vi": "Nội hô hấp", "en": "Pulmonology & Respiratory Medicine"},
    "NOI_HO_HAP": {"vi": "Nội hô hấp", "en": "Pulmonology & Respiratory Medicine"},
    "TIEU_HOA": {"vi": "Tiêu hóa - Gan mật", "en": "Gastroenterology & Hepatology"},
    "TIEU_HOA_GAN_MAT": {"vi": "Tiêu hóa - Gan mật", "en": "Gastroenterology & Hepatology"},
    "TAI_MUI_HONG": {"vi": "Tai - Mũi - Họng", "en": "Otorhinolaryngology (ENT)"},
    "THAN_KINH": {"vi": "Thần kinh", "en": "Neurology"},
    "NOI_THAN_KINH": {"vi": "Thần kinh", "en": "Neurology"},
    "XUONG_KHOP": {"vi": "Chấn thương chỉnh hình & Cột sống", "en": "Orthopedics & Sports Medicine"},
    "DI_UNG": {"vi": "Miễn dịch - Dị ứng", "en": "Clinical Immunology & Allergy"},
    "MIEN_DICH": {"vi": "Miễn dịch - Dị ứng", "en": "Clinical Immunology & Allergy"},
    "TRUYEN_NHIEM": {"vi": "Truyền nhiễm", "en": "Infectious Diseases"},
    "TAM_THAN": {"vi": "Trung tâm chăm sóc sức khỏe tinh thần", "en": "Mental Health Care Center"},
    "DA_LIEU": {"vi": "Da liễu", "en": "Dermatology"},
    "NHI_KHOA": {"vi": "Nhi khoa", "en": "Pediatrics"},
    "SAN_PHU_KHOA": {"vi": "Sản phụ khoa", "en": "Obstetrics & Gynecology"},
    "UNG_BUOU": {"vi": "Ung bướu", "en": "Oncology"},
    "MAT": {"vi": "Mắt (Nhãn khoa)", "en": "Ophthalmology"},
    "THAN_TIET_NIEU": {"vi": "Thận - Tiết niệu", "en": "Nephrology & Urology"},
    "RANG_HAM_MAT": {"vi": "Răng Hàm Mặt", "en": "Dentistry & Maxillofacial"},
    "NOI_TIET": {"vi": "Nội tiết", "en": "Endocrinology"},
    "HUYET_HOC": {"vi": "Huyết học", "en": "Hematology"},
    "NAM_KHOA": {"vi": "Nam khoa", "en": "Andrology"},
    "NHAN_KHOA": {"vi": "Mắt (Nhãn khoa)", "en": "Ophthalmology"},
    "DA_KHOA": {"vi": "Sức khỏe tổng quát", "en": "General Internal Medicine"},
    "TONG_QUAT": {"vi": "Sức khỏe tổng quát", "en": "General Internal Medicine"},
    "CAP_CUU": {"vi": "Cấp cứu", "en": "Emergency Department"},
}

# Reverse lookup từ tên tiếng Việt sang mã chuyên khoa
_VI_NAME_TO_CODE = {}
for code, names in SPECIALTY_BILINGUAL_MAP.items():
    _VI_NAME_TO_CODE[names["vi"].lower()] = code
    _VI_NAME_TO_CODE[code.lower()] = code


# Regex phát hiện dấu tiếng Việt
VIETNAMESE_ACCENTS_REGEX = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", re.IGNORECASE
)

# Từ khóa đặc trưng tiếng Việt không dấu
VI_COMMON_WORDS = {
    "toi",
    "dau",
    "nguc",
    "sot",
    "bac",
    "kham",
    "khong",
    "em",
    "khoa",
    "thuoc",
    "dat",
    "hen",
    "lich",
    "cho",
    "biet",
    "bi",
    "sao",
    "gi",
    "uong",
    "tiem",
    "bung",
    "co",
    "va",
    "nhung",
    "nguoi",
    "thay",
    "kho",
    "tho",
    "chong",
    "mat",
    "muon",
    "nhe",
}

# Từ khóa đặc trưng tiếng Anh (Clinical & General English)
EN_COMMON_WORDS = {
    "i",
    "my",
    "me",
    "you",
    "your",
    "he",
    "she",
    "it",
    "we",
    "they",
    "them",
    "have",
    "has",
    "had",
    "pain",
    "chest",
    "fever",
    "cough",
    "doctor",
    "appointment",
    "help",
    "hello",
    "hi",
    "am",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "with",
    "for",
    "severe",
    "headache",
    "shortness",
    "breath",
    "breathing",
    "dizzy",
    "stomach",
    "booking",
    "slot",
    "schedule",
    "please",
    "and",
    "or",
    "the",
    "a",
    "an",
    "in",
    "on",
    "at",
    "to",
    "of",
    "from",
    "patient",
    "collapsed",
    "unresponsive",
    "unconscious",
    "stopped",
    "stroke",
    "bleed",
    "bleeding",
    "blood",
    "vomit",
    "vomiting",
    "spasm",
    "face",
    "facial",
    "arm",
    "leg",
    "heart",
    "rate",
    "attack",
    "can",
    "cannot",
    "could",
    "should",
    "would",
    "do",
    "does",
    "did",
    "not",
    "no",
    "yes",
    "what",
    "where",
    "when",
    "why",
    "how",
    "who",
    "which",
    "disease",
    "illness",
    "feeling",
    "feel",
    "felt",
    "days",
    "hours",
}


def detect_language(text: str) -> str:
    """
    Phát hiện ngôn ngữ của người dùng: 'vi' (Tiếng Việt) hoặc 'en' (Tiếng Anh).
    Ưu tiên:
    1. Có dấu tiếng Việt -> 'vi'
    2. Tần suất từ vựng tiếng Việt không dấu vs từ vựng tiếng Anh
    3. Mặc định 'vi' nếu không rõ
    """
    if not text:
        return "vi"

    # 1. Kiểm tra dấu tiếng Việt
    if VIETNAMESE_ACCENTS_REGEX.search(text):
        return "vi"

    # 2. Đếm từ vựng
    tokens = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    if not tokens:
        return "vi"

    vi_count = sum(1 for t in tokens if t in VI_COMMON_WORDS)
    en_count = sum(1 for t in tokens if t in EN_COMMON_WORDS)

    if en_count > vi_count:
        return "en"
    if vi_count > en_count:
        return "vi"

    return "vi"


def get_specialty_display_name(specialty_input: str, language: str = "vi") -> str:
    """
    Trả về tên chuyên khoa chuẩn theo ngôn ngữ được yêu cầu ('vi' hoặc 'en').
    """
    clean_input = specialty_input.strip()
    clean_lower = clean_input.lower()
    clean_normalized = clean_lower.replace("_", " ").replace("-", " ")

    # Thử chuẩn hóa loại bỏ tiền tố thường gặp
    prefix_stripped = re.sub(r"^(khám|khoa|phòng khám|trung tâm)\s+", "", clean_normalized).strip()

    # Tìm mã chuyên khoa
    code = (
        _VI_NAME_TO_CODE.get(clean_lower)
        or _VI_NAME_TO_CODE.get(clean_normalized)
        or _VI_NAME_TO_CODE.get(prefix_stripped)
    )
    if not code:
        for k, names in SPECIALTY_BILINGUAL_MAP.items():
            vi_name = names["vi"].lower()
            en_name = names["en"].lower()
            if (
                clean_lower == vi_name
                or clean_normalized == vi_name
                or prefix_stripped == vi_name
                or vi_name in clean_normalized
                or clean_normalized in vi_name
                or clean_normalized in en_name
            ):
                code = k
                break

    if not code:
        if any(w in clean_normalized for w in ["tổng quát", "tong quat", "đa khoa", "da khoa", "general internal"]):
            code = "TONG_QUAT"
        elif any(w in clean_normalized for w in ["thần kinh", "than kinh", "neurology"]):
            code = "THAN_KINH"
        elif any(w in clean_normalized for w in ["tiêu hóa", "tieu hoa", "gan mật", "gastroenterology"]):
            code = "TIEU_HOA"
        elif any(w in clean_normalized for w in ["hô hấp", "ho hap", "phổi", "pulmonology"]):
            code = "HO_HAP"
        elif any(w in clean_normalized for w in ["tim mạch", "tim mach", "cardiology"]):
            code = "TIM_MACH"
        elif any(w in clean_normalized for w in ["tai mũi họng", "tai mui hong", "ent"]):
            code = "TAI_MUI_HONG"
        elif any(w in clean_normalized for w in ["xương khớp", "xuong khop", "chấn thương", "cột sống", "orthopedics"]):
            code = "XUONG_KHOP"
        elif any(w in clean_normalized for w in ["nhi", "trẻ em", "pediatric"]):
            code = "NHI_KHOA"
        elif any(w in clean_normalized for w in ["sản", "phụ khoa", "obstetrics", "gynecology"]):
            code = "SAN_PHU_KHOA"
        elif any(w in clean_normalized for w in ["ung bướu", "ung buou", "ung thư", "oncology"]):
            code = "UNG_BUOU"
        elif any(w in clean_normalized for w in ["da liễu", "da lieu", "dermatology"]):
            code = "DA_LIEU"
        elif any(w in clean_normalized for w in ["mắt", "mat", "nhãn khoa", "nhan khoa", "ophthalmology", "eye"]):
            code = "MAT"
        elif any(w in clean_normalized for w in ["cấp cứu", "cap cuu", "emergency"]):
            code = "CAP_CUU"

    if code and code in SPECIALTY_BILINGUAL_MAP:
        return SPECIALTY_BILINGUAL_MAP[code].get(language, SPECIALTY_BILINGUAL_MAP[code]["vi"])

    # Fallback nếu không map được
    if language == "en":
        if "tim" in clean_lower:
            return "Cardiology Center"
        if "hô hấp" in clean_lower or "ho hap" in clean_lower:
            return "Pulmonology & Respiratory Medicine"
        if "tiêu hóa" in clean_lower or "tieu hoa" in clean_lower:
            return "Gastroenterology & Hepatology"
        if "thần kinh" in clean_lower or "than kinh" in clean_lower:
            return "Neurology"
        if "cấp cứu" in clean_lower or "cap cuu" in clean_lower:
            return "Emergency Department"
        if "tai mũi họng" in clean_lower or "tai - mũi - họng" in clean_lower:
            return "Otorhinolaryngology (ENT)"
        if "xương khớp" in clean_lower or "xuong khop" in clean_lower:
            return "Orthopedics & Sports Medicine"
        return "General Internal Medicine"

    return clean_input


def canonicalize_specialty_code(specialty_input: str) -> str:
    """
    Chuẩn hóa tên hoặc mã chuyên khoa về mã chuẩn Vinmec/DDXPlus:
    HO_HAP, TIM_MACH, TIEU_HOA, TAI_MUI_HONG, THAN_KINH, MIEN_DICH,
    TRUYEN_NHIEM, TAM_THAN, XUONG_KHOP, DA_LIEU, THAN_TIET_NIEU,
    SAN_PHU_KHOA, NHI_KHOA, MAT, RANG_HAM_MAT, TONG_QUAT.
    """
    if not specialty_input:
        return "TONG_QUAT"

    text = unicodedata.normalize("NFD", specialty_input)
    text = re.sub(r"[\u0300-\u036f]", "", text)
    text = text.replace("đ", "d").replace("Đ", "D")
    clean = re.sub(r"[\s\-_/]+", "", text.lower())

    if any(k in clean for k in ["hohap", "noihohap", "pulmon", "respir"]):
        return "HO_HAP"
    if any(k in clean for k in ["timmach", "trungtamtimmach", "noitimmach", "cardio"]):
        return "TIM_MACH"
    if any(k in clean for k in ["tieuhoa", "tieuhoaganmat", "gastro", "hepato"]):
        return "TIEU_HOA"
    # "ent" phải là từ riêng: substring khớp nhầm "Center" (Women's Health Center → TMH).
    if any(k in clean for k in ["taimuihong", "otorhino"]) or re.search(r"\bent\b", text.lower()):
        return "TAI_MUI_HONG"
    if any(k in clean for k in ["thankinh", "noithankinh", "neuro"]):
        return "THAN_KINH"
    if any(k in clean for k in ["miendich", "diung", "miendichdiung", "immuno", "allergy"]):
        return "MIEN_DICH"
    if any(k in clean for k in ["truyennhiem", "nhiemtrung", "infectio"]):
        return "TRUYEN_NHIEM"
    if any(k in clean for k in ["tamthan", "suckhoetinhthan", "psychiat"]):
        return "TAM_THAN"
    if any(k in clean for k in ["xuongkhop", "chanthuongchinhhinh", "coxuongkhop", "ortho", "musculo"]):
        return "XUONG_KHOP"
    if any(k in clean for k in ["dalieu", "dermato"]):
        return "DA_LIEU"
    # Trước đây các khoa dưới rơi về TONG_QUAT → hiển thị và tìm lịch nhầm "Sức khỏe tổng quát".
    if any(k in clean for k in ["tietnieu", "urolog", "nephro"]):
        return "THAN_TIET_NIEU"
    if any(k in clean for k in ["sanphukhoa", "phukhoa", "khoasan", "suckhoephunu", "obstet", "gyneco", "women"]):
        return "SAN_PHU_KHOA"
    if any(k in clean for k in ["nhikhoa", "trungtamnhi", "noinhi", "pediatr"]):
        return "NHI_KHOA"
    if any(k in clean for k in ["nhankhoa", "khoamat", "khammat", "ophthalm"]) or clean in {"mat", "mat(nhankhoa)"}:
        return "MAT"
    if any(k in clean for k in ["ranghammat", "nhakhoa", "dentist", "dental"]):
        return "RANG_HAM_MAT"
    if any(k in clean for k in ["ungbuou", "ungthu", "oncolog"]):
        return "UNG_BUOU"
    if any(k in clean for k in ["noitiet", "endocrin", "daithaoduong", "tieuduong"]):
        return "NOI_TIET"
    if any(k in clean for k in ["huyethoc", "hematolog", "truyenmau"]):
        return "HUYET_HOC"
    if any(k in clean for k in ["namkhoa", "androlog"]):
        return "NAM_KHOA"
    if any(k in clean for k in ["capcuu", "emergency", "hoisuc"]):
        return "CAP_CUU"
    if any(k in clean for k in ["dakhoa", "noikhoa", "suckhoetongquat", "tongquat", "general", "kham"]):
        return "TONG_QUAT"

    return "TONG_QUAT"


def get_same_day_safety_net(language: str = "vi") -> str:
    """Dặn dò an toàn cho ca ưu tiên khám trong ngày (ATS 3): dấu hiệu nặng lên thì gọi cấp cứu."""
    if language == "en":
        return (
            "\n\n⚠️ While waiting for your appointment, if you develop shortness of breath, chest pain, drowsiness, "
            "seizures or rapidly worsening symptoms, call 115 or go to the nearest emergency department."
        )
    return (
        "\n\n⚠️ Trong lúc chờ khám, nếu xuất hiện khó thở, đau ngực, lơ mơ, co giật hoặc triệu chứng nặng lên nhanh, "
        "hãy gọi 115 hoặc đến cơ sở cấp cứu gần nhất."
    )


def get_medical_disclaimer(language: str = "vi") -> str:
    """Trả về tuyên bố miễn trừ trách nhiệm y tế song ngữ."""
    if language == "en":
        return (
            "\n\n---\n*Medical Disclaimer: This information is for clinical guidance and booking assistance only, "
            "and does not replace the diagnosis or treatment prescription of a specialist physician.*"
        )
    return (
        "\n\n---\n*Khuyến cáo y tế: Thông tin chỉ mang tính chất định hướng và hỗ trợ đặt lịch khám, "
        "không thay thế cho chẩn đoán hoặc chỉ định điều trị của bác sĩ chuyên khoa.*"
    )


def get_emergency_guidance(flag_name: str, specialty: str, ats_level: int = 1, language: str = "vi") -> str:
    """Trả về hướng dẫn cấp cứu khẩn cấp (ATS 1/2) song ngữ."""
    spec_display = get_specialty_display_name(specialty, language)
    if language == "en":
        if ats_level == 1:
            return (
                f"🚨 **CRITICAL MEDICAL EMERGENCY (ATS Level 1):** Your reported symptoms indicate a life-threatening "
                f"emergency ({flag_name}). Please call emergency services (115 or +84 24 3974 3556 for Vinmec Emergency) "
                f"or proceed immediately to the nearest Emergency Department. **Do not wait for a scheduled appointment!**"
            )
        else:
            return (
                f"🚨 **ACUTE MEDICAL ALERT (ATS Level 2 - {flag_name}):** Your condition requires urgent evaluation "
                f"by {spec_display}. Please call emergency services (115 in Vietnam) or proceed directly to the Emergency Department for immediate intervention. "
                f"**Do not wait for a routine appointment.**"
            )
    else:
        if ats_level == 1:
            return (
                f"🚨 CẢNH BÁO NGUY HIỂM: Triệu chứng của bạn có dấu hiệu cấp cứu khẩn cấp ({flag_name}). "
                "Vui lòng gọi 115 hoặc đến ngay phòng Cấp cứu của bệnh viện gần nhất, "
                "tuyệt đối không chờ đợi lịch khám hẹn trước!"
            )
        else:
            return (
                f"🚨 CẢNH BÁO CẤP TÍNH ({flag_name}): Tình trạng của bạn có dấu hiệu cấp cứu chuyên khoa {spec_display}. "
                "Vui lòng gọi 115 hoặc đến ngay phòng Cấp cứu để được xử trí khẩn cấp, không chờ đợi lịch khám hẹn trước!"
            )


def get_triage_guidance(
    specialty: str, disease_name: str = "", ats_level: int = 4, max_days: int = 7, language: str = "vi"
) -> str:
    """Trả về hướng dẫn điều phối chuyên khoa song ngữ."""
    spec_display = get_specialty_display_name(specialty, language)
    if language == "en":
        if ats_level in [1, 2]:
            disease_note = f" ({disease_name})" if disease_name else ""
            return (
                f"⚠️ Your symptoms may be related to an acute condition{disease_note}. "
                f"We strongly recommend visiting the Emergency Department or consulting a specialist at **{spec_display}** immediately."
            )
        elif ats_level == 3:
            return (
                f"Your symptoms are best evaluated by **{spec_display}**. "
                "Due to the acute nature of your condition, priority same-day or next-morning appointments are available."
            )
        else:
            return (
                f"Based on your symptoms, we recommend scheduling a consultation with **{spec_display}**. "
                f"You may select a convenient appointment within the next {max_days} days."
            )
    else:
        if ats_level in [1, 2]:
            disease_note = f" ({disease_name})" if disease_name else ""
            return (
                f"⚠️ Triệu chứng có thể liên quan đến vấn đề cấp tính{disease_note}. "
                f"Khuyến cáo bạn nên đến Khoa Cấp cứu hoặc chuyên khoa {spec_display} để được bác sĩ kiểm tra ngay lập tức."
            )
        elif ats_level == 3:
            return (
                f"Triệu chứng của bạn phù hợp thăm khám tại chuyên khoa {spec_display}. "
                "Do tình trạng cấp tính, hệ thống chỉ hỗ trợ đặt lịch khám trong ngày hôm nay hoặc sáng mai."
            )
        else:
            return (
                f"Triệu chứng của bạn phù hợp thăm khám tại chuyên khoa {spec_display}. "
                f"Bạn có thể chọn bác sĩ và lịch khám thuận tiện trong {max_days} ngày tới."
            )


def get_hold_booking_response(slot_id: str, specialty: str, language: str = "vi") -> tuple[str, list[str]]:
    """Trả về thông báo tiếp nhận yêu cầu đặt khám song ngữ."""
    spec_display = get_specialty_display_name(specialty, language)
    req_code = f"REQ-{slot_id[:8].upper()}"
    if language == "en":
        response = (
            f"✅ **Appointment Request Submitted! (Reference Code: `{req_code}`)**\n\n"
            f"📋 **Request Details:**\n"
            f"• **Department:** {spec_display}\n"
            f"• **Slot ID:** `{slot_id}`\n"
            f"• **Status:** Forwarded to Vinmec Medical Coordinator for review\n\n"
            f"📞 Our medical coordinator will contact you shortly to verify your details and finalize the appointment. "
            f"Please keep your phone accessible.\n\n"
            f"💡 *Would you like preparation instructions or pricing details before your visit?*"
        )
        quick_replies = [
            "Fasting instructions before exam",
            "Consultation fees & pricing",
            "Book for another symptom",
        ]
    else:
        response = (
            f"✅ **Yêu cầu đặt hẹn đã được ghi nhận! (Mã yêu cầu: `{req_code}`)**\n\n"
            f"📋 **Thông tin yêu cầu khám:**\n"
            f"• **Chuyên khoa:** {spec_display}\n"
            f"• **Mã slot:** `{slot_id}`\n"
            f"• **Trạng thái:** Đang chuyển thông tin đến Điều phối viên y tế phòng khám\n\n"
            f"📞 Điều phối viên y tế sẽ gọi điện thoại cho bác trong thời gian sớm nhất để kiểm tra và xác nhận lịch hẹn chính thức. Bác vui lòng để ý chuông điện thoại nhé!\n\n"
            f"💡 *Bác có cần chuẩn bị hay hỏi thêm thông tin gì trước buổi khám không ạ?*"
        )
        quick_replies = [
            "Hướng dẫn nhịn ăn trước khám",
            "Bảng giá dịch vụ khám",
            "Đăng ký khám triệu chứng khác",
        ]
    return response, quick_replies
