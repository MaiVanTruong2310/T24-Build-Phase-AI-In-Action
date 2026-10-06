"""
Clinical Guardrails & Medical Intent Service (SAF-02).
Enforces medical safety rules:
1. MEDICATION_GUARDRAIL: Strictly blocks prescribing or recommending medication.
2. DIAGNOSIS_GUARDRAIL: Prevents AI from confirming disease diagnosis; provides educational differential context.
3. DEPARTMENT_INFO: Retrieves information about medical specialties from database / knowledge base.
4. HOLD_BOOKING: Validates a database-backed slot selection before HITL intake.
5. VISIT_PURPOSE_CLARIFICATION: Clarifies generic requests to visit the hospital before clinical triage.
"""

import re
import unicodedata
from typing import Any

from src.medical_assistant.domain.language_service import get_specialty_display_name
from src.medical_assistant.domain.security.deobfuscator import get_deobfuscator
from src.medical_assistant.domain.security.security_guardrail_service import get_security_guardrail_service


def remove_accents(text: str) -> str:
    """Normalize text by removing Vietnamese accents for fuzzy keyword matching."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").lower()
    return text.replace("đ", "d")


class ClinicalGuardrailService:
    def __init__(self):
        self.deobfuscator = get_deobfuscator()
        self.security_service = get_security_guardrail_service()
        # Từ khóa hỏi đơn thuốc / uống thuốc gì (Bilingual EN-VI)
        self.medication_patterns = [
            r"uống\s+thuốc",
            r"dùng\s+thuốc",
            r"kê\s+đơn",
            r"mua\s+thuốc",
            r"uống\s+gì",
            r"thuốc\s+gì",
            r"thuốc\s+trị",
            r"thuốc\s+chữa",
            r"thuốc\s+giảm\s+đau",
            r"kháng\s+sinh",
            r"liều\s+dùng",
            r"paracetamol",
            r"panadol",
            r"aspirin",
            r"ibuprofen",
            r"uống\s+kháng\s+sinh",
            # English patterns
            r"what\s+medicine",
            r"what\s+drug",
            r"what\s+pill",
            r"should\s+i\s+take",
            r"prescribe",
            r"prescription",
            r"painkiller",
            r"antibiotic",
            r"dosage",
            r"medication",
            r"buy\s+medicine",
        ]

        # Từ khóa hỏi chẩn đoán bệnh (Bilingual EN-VI)
        self.diagnosis_patterns = [
            r"bị\s+bệnh\s+gì",
            r"mắc\s+bệnh\s+gì",
            r"chẩn\s+đoán",
            r"nghi\s+ngờ\s+bệnh\s+gì",
            r"có\s+phải\s+tôi\s+bị",
            r"bị\s+sao\s+vậy",
            r"tôi\s+bị\s+sao",
            r"có\s+nguy\s+hiểm\s+không",
            r"bệnh\s+này\s+là\s+gì",
            r"là\s+bệnh\s+gì",
            # English patterns
            r"what\s+disease",
            r"what\s+illness",
            r"what\s+condition",
            r"diagnose\s+me",
            r"diagnosis",
            r"what\s+is\s+wrong\s+with\s+me",
            r"do\s+i\s+have",
            r"is\s+it\s+dangerous",
            r"what\s+is\s+my\s+diagnosis",
        ]

        # Từ khóa hỏi thông tin chuyên khoa (hỗ trợ cả lỗi gõ phím "khia" thay vì "khoa")
        self.department_patterns = [
            r"thông\s+tin\s+về\s+(khoa|khia|chuyên\s+khoa)\s+(.*)",
            r"thông\s+tin\s+cụ\s+thể\s+(?:của|về)\s+(khoa|khia|chuyên\s+khoa)\s+(.*)",
            r"(khoa|khia)\s+(.*?)\s+(là\s+gì|khám\s+gì|ở\s+đâu|như\s+thế\s+nào)",
            r"(khoa|khia)\s+(.*?)\s+(?:có\s+)?(?:ưu\s+điểm|thế\s+mạnh|nổi\s+bật)(.*)",
            r"giới\s+thiệu\s+(về\s+)?(khoa|khia)\s+(.*)",
            r"tìm\s+hiểu\s+(khoa|khia)\s+(.*)",
            r"khoa\s+khám\s+(.*)",
            # English patterns
            r"information\s+about\s+(department|specialty|clinic)\s+(.*)",
            r"information\s+about\s+(.*)\s+(department|specialty|clinic)",
            r"tell\s+me\s+about\s+(department|specialty|clinic)?\s*(.*)",
            r"what\s+is\s+(.*)\s+(department|specialty|clinic)",
        ]

        # Mẫu nhận diện câu hỏi về cơ sở, chi nhánh, bệnh viện / phòng khám
        self.facility_patterns = [
            r"cơ\s+sở(\s+bệnh\s+viện|\s+y\s+tế)?",
            r"(các|những|danh\s+sách|hệ\s+thống)\s+cơ\s+sở",
            r"(các|những|danh\s+sách|hệ\s+thống)\s+bệnh\s+viện",
            r"bệnh\s+viện\s+của\s+bạn",
            r"chi\s+nhánh(\s+bệnh\s+viện)?",
            r"bệnh\s+viện\s+(ở|tại)\s+đâu",
            r"phòng\s+khám\s+(ở|tại)\s+đâu",
            r"có\s+(những\s+)?(cơ\s+sở|bệnh\s+viện|chi\s+nhánh|phòng\s+khám)\s+nào",
            r"địa\s+chỉ\s+(các\s+)?(cơ\s+sở|bệnh\s+viện)",
            r"(?:bệnh\s+viện|cơ\s+sở|phòng\s+khám)\s+(?:ở|tại)\s+(hà\s+nội|tp\s*hcm|hồ\s+chí\s+minh|sài\s+gòn|đà\s+nẵng|hải\s+phòng|quảng\s+ninh|nha\s+trang|phú\s+quốc|cần\s+thơ|hạ\s+long)",
            r"(?:ở|gần)\s+(?:tôi|mình|nhà|chỗ\s+tôi|khu\s+vực)\s+nhất",
            r"(?:cơ\s+sở|bệnh\s+viện|phòng\s+khám)\s+(?:nào\s+)?gần\s+(?:tôi|nhất)",
            r"(?:cơ\s+sở|bệnh\s+viện|phòng\s+khám)\s+gần\s+.+?\s+nhất",
            r"tìm\s+cơ\s+sở(\s+để\s+khám)?(\s+ở\s+gần)?",
            # English
            r"(hospital|clinic)?\s*facilities",
            r"hospital\s+branches",
            r"list\s+of\s+hospitals",
            r"where\s+are\s+your\s+hospitals",
            r"hospital\s+locations",
            r"which\s+hospitals\s+do\s+you\s+have",
            r"(closest|nearest)\s+(hospital|clinic|facility)",
        ]

        # Chỉ bắt các yêu cầu đi khám chung chung, không có triệu chứng hay chuyên khoa.
        # Dùng fullmatch để câu như "tôi muốn khám vì đau ngực" vẫn đi qua triage an toàn.
        self.generic_visit_patterns = [
            r"(?:toi|minh|em|to)?\s*(?:dang\s+)?(?:muon|can)\s+(?:di\s+)?kham(?:\s+benh)?(?:\s+(?:o|tai)\s+(?:benh\s+vien|phong\s+kham))?",
            r"(?:toi|minh|em|to)?\s*(?:muon|can)\s+(?:dat|dang\s+ky)\s+lich\s+kham",
            r"(?:i\s+)?(?:want|would\s+like|need)\s+(?:to\s+)?(?:see\s+a\s+doctor|visit\s+(?:a\s+|the\s+)?(?:hospital|clinic)|book\s+(?:a\s+|an\s+)?appointment)",
        ]

        self.view_schedule_patterns = [
            r"(?:ban\s+)?(?:xem|tim|tra|cho\s+(?:toi|minh|em)\s+xem)\s+(?:giup\s+)?(?:lich|lich\s+kham|khung\s+gio)(?:\s+kham)?(?:\s+trong)?(?:\s+(\d+)\s+ngay(?:\s+toi)?)?",
            r"(?:show|find|check)\s+(?:me\s+)?(?:the\s+)?(?:appointment\s+)?(?:schedule|slots?)(?:\s+(?:in|for)\s+the\s+next\s+(\d+)\s+days?)?",
        ]

        # Mẫu nhận diện mã slot thật: Bắt buộc phải có từ khóa slot / mã slot / chọn slot, hoặc là UUID đầy đủ
        self.slot_pattern = re.compile(
            r"(?:(?:mã\s+slot|slot|đặt\s+slot|chọn\s+slot|khung\s+giờ)\s*[:#]?\s*([0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})?)|(?:^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12})$))",
            re.IGNORECASE,
        )

    def check_intent(
        self,
        user_query: str,
        current_department: str | None = None,
        language: str = "vi",
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Kiểm tra intent an ninh mạng, de-obfuscation và an toàn y tế lâm sàng.
        Trả về dict intent hoặc None nếu là triệu chứng thông thường.
        """
        if not user_query:
            return None

        # 0. TƯỜNG LỬA AN NINH MẠNG: Chặn Prompt Injection, Jailbreak, Exfiltration, SQL/Command Injection, Cross-Patient Snoop
        sec_res = self.security_service.inspect_query(user_query, language=language)
        if not sec_res.is_safe:
            return {
                "intent": "SECURITY_VIOLATION",
                "violation_type": sec_res.violation_type,
                "detected_technique": sec_res.detected_technique,
                "matched_pattern": sec_res.matched_pattern,
                "safe_response": sec_res.safe_response,
                "quick_replies": sec_res.quick_replies,
            }

        # 0b. Bóc tách Deobfuscation (Morse, Binary, Hex, Base64, Leet, Homoglyphs)
        deob_res = self.deobfuscator.process(user_query)
        all_candidates = [user_query.strip().lower()]
        for var in deob_res.decoded_variants:
            v_clean = var.strip().lower()
            if v_clean and v_clean not in all_candidates:
                all_candidates.append(v_clean)

        query_clean = user_query.strip().lower()
        query_normalized = re.sub(r"[^a-z0-9\s]", " ", remove_accents(query_clean))
        query_normalized = re.sub(r"\s+", " ", query_normalized).strip()

        # Conversation-boundary intents protect the active patient's clinical
        # episode from social detours and health questions about another person.
        cleaned_for_tp = re.sub(
            r"^(?:chao|xin chao|alo)\s+(?:ban|bac si|tro ly|bot|ai)\b", "", query_normalized
        ).strip()
        third_party_health = re.search(
            r"\b(?:ban(?:\s+[a-z0-9]+)?|anh ay|chi ay|co ay|chu ay|ong ay|ba ay|em (?:toi|gai|trai)|vo|chong|me|ma|bo|ba|cha|con|nguoi yeu)"
            r"(?:\s+[a-z0-9]+){0,3}\s+(?:bi|dang bi|co|mac)\s+"
            r"(?:vo sinh|hiem muon|benh|dau|sot|ho|kho tho|ung thu|tieu duong)\b",
            cleaned_for_tp,
        )
        is_first_person_complaint = bool(
            re.search(
                r"(?:^|\b(?:thi|va|nhung|ma|la)\s+)(?:toi|em|minh|tui)\s+(?:bi|dang bi|co|mac|thay)\b", cleaned_for_tp
            )
        )
        if is_first_person_complaint and not re.search(
            r"\b(?:chi|anh|em|ban|me|bo|ba|cha|con|vo|chong)\s+toi\s+bi\b", cleaned_for_tp
        ):
            third_party_health = None

        if third_party_health:
            topic = "infertility" if re.search(r"\b(?:vo sinh|hiem muon)\b", query_normalized) else "general_health"
            return {"intent": "THIRD_PARTY_HEALTH_QUERY", "topic": topic}

        social_statement = re.search(
            r"\b(?:toi|minh|tui|em)\s+(?:rat\s+)?(?:ghet|thich|yeu|buc|gian)\b|"
            r"\b(?:co\s+nguoi\s+yeu\s+chua|lam\s+quen\s+duoc\s+khong|ban\s+co\s+nguoi\s+yeu|troi\s+mua\s+to|thoi\s+tiet|ban\s+la\s+ai|may\s+tuoi|chuc\s+ngu\s+ngon)\b",
            query_normalized,
        )
        if social_statement:
            return {"intent": "SOCIAL_STATEMENT"}

        self_care_followup = re.search(
            r"\b(?:(?:vay|the|con)\s+)?(?:toi|minh|tui)\s+nen\s+kham\s+"
            r"(?:khoa nao|chuyen khoa nao|o dau|o benh vien nao|tai dau)\b",
            query_normalized,
        )
        if self_care_followup and current_department:
            return {"intent": "SELF_CARE_FOLLOWUP"}

        if query_normalized in {
            "mo ta trieu chung",
            "mo ta them trieu chung",
            "toi muon mo ta trieu chung",
            "toi muon mo ta them trieu chung",
            "describe symptoms",
            "check symptoms",
            "describe symptoms in more detail",
            "add more symptom details",
        }:
            return {"intent": "DESCRIBE_MORE_SYMPTOMS"}

        contact_request_phrases = (
            "de lai thong tin",
            "dieu phoi vien lien he",
            "nhan vien lien he",
            "goi lai cho toi",
            "gap nhan vien ho tro",
            "request coordinator contact",
            "leave contact details",
            "contact me to book",
        )
        if any(phrase in query_normalized for phrase in contact_request_phrases):
            return {"intent": "BOOKING_CONTACT_REQUEST"}

        doctor_info_phrases = (
            "thong tin bac si",
            "thong tin cua cac bac si",
            "cac bac si trong khoa",
            "bac si nao trong khoa",
            "doi ngu bac si",
            "doctor information",
            "which doctors",
            "doctors in this department",
        )
        if any(phrase in query_normalized for phrase in doctor_info_phrases):
            if not current_department:
                return {"intent": "VISIT_PURPOSE_CLARIFICATION"}
            return {"intent": "VIEW_SCHEDULE", "doctor_info_only": True}

        # PHẢN HỒI KHẲNG ĐỊNH / ĐỒNG Ý XEM LỊCH TIẾP NỐI (Contextual Affirmative Followup)
        # Khi bot vừa gợi ý chuyên khoa và hỏi "Bác có muốn tìm lịch không?" -> người dùng đáp "Có", "Vâng", "Ok"...
        affirmative_tokens = {
            "co",
            "có",
            "vang",
            "vâng",
            "ok",
            "oke",
            "okay",
            "duoc",
            "được",
            "dong y",
            "đồng ý",
            "yes",
            "yep",
            "tim giup",
            "tìm giúp",
            "xem giup",
            "xem giúp",
            "tim lich",
            "tìm lịch",
            "co chu",
            "có chứ",
            "duoc chu",
            "được chứ",
            "vang a",
            "vâng ạ",
            "co a",
            "có ạ",
            "tim di",
            "tìm đi",
            "kiem tra giup",
            "kiểm tra giúp",
            "check giup",
            "check giúp",
        }
        if (query_normalized in affirmative_tokens or query_clean in affirmative_tokens) and current_department:
            return {"intent": "VIEW_SCHEDULE"}

        # A comparison about a named department can contain the words
        # "bệnh viện" but is still a department query. Resolve this before
        # the broader facility router below.
        comparison_match = re.search(
            r"(?:khoa|chuyên khoa)\s+(.+?)\s+(?:có\s+)?(?:ưu\s+điểm|hơn|so\s+với|compare|superior)",
            query_clean,
            flags=re.IGNORECASE,
        )
        if comparison_match:
            known_departments = (
                "tiêu hóa",
                "tim mạch",
                "thần kinh",
                "tai mũi họng",
                "hô hấp",
                "xương khớp",
                "da liễu",
                "nhi",
                "sản phụ khoa",
                "cấp cứu",
            )
            target = next(
                (name for name in known_departments if name in query_clean),
                comparison_match.group(1).strip(),
            )
            return {
                "intent": "DEPARTMENT_INFO",
                "department_query": target,
                "comparison_requested": True,
            }

        # --- BỘ ĐIỀU HƯỚNG CƠ SỞ Y TẾ (FACILITY ROUTER & NAVIGATION) ---
        direct_facility_names = {
            "riverside": "riverside",
            "times city": "times city",
            "timescity": "times city",
            "central park": "central park",
            "centralpark": "central park",
            "smart city": "smart city",
            "smartcity": "smart city",
            "ocean park 2": "ocean park 2",
            "ocean park": "ocean park",
            "royal city": "royal city",
            "royalcity": "royal city",
            "royal island": "royal island",
            "royalisland": "royal island",
            "grand park": "grand park",
            "grandpark": "grand park",
            "duong dong": "duong dong",
            "dương đông": "duong dong",
            "hai phong": "hai phong",
            "hải phòng": "hai phong",
            "ha long": "ha long",
            "hạ long": "ha long",
            "da nang": "da nang",
            "đà nẵng": "da nang",
            "nha trang": "nha trang",
            "phu quoc": "phu quoc",
            "phú quốc": "phu quoc",
            "can tho": "can tho",
            "cần thơ": "can tho",
        }

        # A. ĐIỀU HƯỚNG: Xem danh sách bác sĩ tại cơ sở cụ thể
        doctor_inquiry_keywords = [
            "bac si",
            "bác sĩ",
            "doctor",
            "chuyen gia",
            "doi ngu",
            "ai kham",
            "nguoi kham",
            "cac si",
            "các sĩ",
            "thong tin bac si",
            "danh sach bac si",
            "goi y bac si",
            "bác si",
            "bac sĩ",
            "tim bac si",
            "kiem tra bac si",
        ]
        is_asking_doctors = any(k in query_normalized for k in doctor_inquiry_keywords)

        # A1: Có tên cơ sở trực tiếp trong query
        for fkey, fval in direct_facility_names.items():
            if fkey in query_normalized and is_asking_doctors:
                return {
                    "intent": "FACILITY_DOCTORS",
                    "matched_pattern": fkey,
                    "facility_name_query": fval,
                }

        # A2: Có từ chỉ cơ sở ngữ cảnh ("bệnh viện trên", "tại đây", "ở đây"...) hoặc có cơ sở trong state
        context_facility_keywords = [
            "benh vien tren",
            "benh vien nay",
            "benh vien do",
            "co so tren",
            "co so nay",
            "co so do",
            "tai day",
            "o day",
            "tai do",
            "o do",
            "noi nay",
            "vien tren",
            "vien nay",
        ]
        has_context_facility = any(ref in query_normalized for ref in context_facility_keywords)
        prev_fac = (state or {}).get("metadata", {}).get("facility_preference") or (state or {}).get(
            "facility_preference"
        )
        if is_asking_doctors and (has_context_facility or prev_fac):
            target_fac = None
            if prev_fac:
                for fkey, fval in direct_facility_names.items():
                    if fkey in prev_fac.lower():
                        target_fac = fval
                        break
                if not target_fac:
                    target_fac = prev_fac
            return {
                "intent": "FACILITY_DOCTORS",
                "matched_pattern": "context_facility",
                "facility_name_query": target_fac or "times city",
            }

        # B. ĐIỀU HƯỚNG: Đặt lịch khám chung tại cơ sở (khi chưa có ngày hoặc slot cụ thể)
        # Nếu câu hỏi đã có ngày/tháng cụ thể, hãy để booking engine tìm slot & bác sĩ thay vì chặn lại
        has_concrete_schedule = any(
            k in query_normalized
            for k in ["ngay ", "vào ngày", "thang", "buoi sang", "buoi chieu", "tu chon", "tự chọn", "slot"]
        )
        if not is_asking_doctors and not has_concrete_schedule:
            for fkey, fval in direct_facility_names.items():
                if fkey in query_normalized and any(
                    k in query_normalized for k in ["dat lich", "kham tai", "dang ky", "book"]
                ):
                    return {
                        "intent": "FACILITY_BOOKING_START",
                        "matched_pattern": fkey,
                        "facility_name_query": fval,
                    }
            if any(
                k in query_normalized
                for k in ["dat lich kham tai day", "dat lich tai day", "kham tai day", "dang ky tai day"]
            ):
                return {
                    "intent": "FACILITY_BOOKING_START",
                    "matched_pattern": "tai day",
                    "facility_name_query": None,
                }

        # C. Tra cứu thông tin cơ sở khi có tên cơ sở cụ thể (chỉ khi không hỏi bác sĩ)
        if not is_asking_doctors and not has_concrete_schedule:
            for fkey, fval in direct_facility_names.items():
                if fkey in query_normalized and any(
                    k in query_normalized
                    for k in [
                        "benh vien",
                        "phong kham",
                        "vinmec",
                        "thong tin",
                        "o dau",
                        "dia chi",
                        "hotline",
                        "co so",
                        "gio lam viec",
                        "gio mo cua",
                        "gio kham",
                    ]
                ):
                    return {
                        "intent": "FACILITY_INFO",
                        "matched_pattern": fkey,
                        "region_filter": None,
                        "facility_name_query": fval,
                    }

        # D. Tra cứu thông tin cơ sở / chi nhánh hoặc danh sách theo khu vực & quận/huyện
        if not is_asking_doctors and not has_concrete_schedule:
            for pattern in self.facility_patterns:
                if re.search(pattern, query_clean, re.IGNORECASE) or re.search(
                    pattern, query_normalized, re.IGNORECASE
                ):
                    # Phát hiện khu vực tỉnh/thành
                    regions = {
                        "hà nội": "Hà Nội",
                        "ha noi": "Hà Nội",
                        "hồ chí minh": "Hồ Chí Minh",
                        "ho chi minh": "Hồ Chí Minh",
                        "tphcm": "Hồ Chí Minh",
                        "sài gòn": "Hồ Chí Minh",
                        "sai gon": "Hồ Chí Minh",
                        "đà nẵng": "Đà Nẵng",
                        "da nang": "Đà Nẵng",
                        "hải phòng": "Hải Phòng",
                        "hai phong": "Hải Phòng",
                        "hạ long": "Hạ Long",
                        "ha long": "Hạ Long",
                        "quảng ninh": "Quảng Ninh",
                        "quang ninh": "Quảng Ninh",
                        "nha trang": "Nha Trang",
                        "khánh hòa": "Khánh Hòa",
                        "khanh hoa": "Khánh Hòa",
                        "phú quốc": "Phú Quốc",
                        "phu quoc": "Phú Quốc",
                        "cần thơ": "Cần Thơ",
                        "can tho": "Cần Thơ",
                        "hưng yên": "Hưng Yên",
                        "hung yen": "Hưng Yên",
                    }
                    detected_region = next((val for key, val in regions.items() if key in query_normalized), None)
                    detected_fac = next(
                        (val for key, val in direct_facility_names.items() if key in query_normalized), None
                    )

                    # Phát hiện quận / huyện và gán cơ sở Vinmec gần nhất
                    districts = {
                        "hoan kiem": ("Hà Nội", "Quận Hoàn Kiếm", "times city"),
                        "hoàn kiếm": ("Hà Nội", "Quận Hoàn Kiếm", "times city"),
                        "hai ba trung": ("Hà Nội", "Quận Hai Bà Trưng", "times city"),
                        "hai bà trưng": ("Hà Nội", "Quận Hai Bà Trưng", "times city"),
                        "hoang mai": ("Hà Nội", "Quận Hoàng Mai", "times city"),
                        "hoàng mai": ("Hà Nội", "Quận Hoàng Mai", "times city"),
                        "ba dinh": ("Hà Nội", "Quận Ba Đình", "times city"),
                        "ba đình": ("Hà Nội", "Quận Ba Đình", "times city"),
                        "dong da": ("Hà Nội", "Quận Đống Đa", "royal city"),
                        "đống đa": ("Hà Nội", "Quận Đống Đa", "royal city"),
                        "thanh xuan": ("Hà Nội", "Quận Thanh Xuân", "royal city"),
                        "thanh xuân": ("Hà Nội", "Quận Thanh Xuân", "royal city"),
                        "cau giay": ("Hà Nội", "Quận Cầu Giấy", "smart city"),
                        "cầu giấy": ("Hà Nội", "Quận Cầu Giấy", "smart city"),
                        "nam tu liem": ("Hà Nội", "Quận Nam Từ Liêm", "smart city"),
                        "nam từ liêm": ("Hà Nội", "Quận Nam Từ Liêm", "smart city"),
                        "bac tu liem": ("Hà Nội", "Quận Bắc Từ Liêm", "smart city"),
                        "bắc từ liêm": ("Hà Nội", "Quận Bắc Từ Liêm", "smart city"),
                        "ha dong": ("Hà Nội", "Quận Hà Đông", "smart city"),
                        "hà đông": ("Hà Nội", "Quận Hà Đông", "smart city"),
                        "long bien": ("Hà Nội", "Quận Long Biên", "riverside"),
                        "long biên": ("Hà Nội", "Quận Long Biên", "riverside"),
                        "gia lam": ("Hà Nội", "Huyện Gia Lâm", "ocean park"),
                        "gia lâm": ("Hà Nội", "Huyện Gia Lâm", "ocean park"),
                        # TP. Hồ Chí Minh
                        "quan 1": ("Hồ Chí Minh", "Quận 1", "central park"),
                        "quận 1": ("Hồ Chí Minh", "Quận 1", "central park"),
                        "binh thanh": ("Hồ Chí Minh", "Quận Bình Thạnh", "central park"),
                        "bình thạnh": ("Hồ Chí Minh", "Quận Bình Thạnh", "central park"),
                        "quan 2": ("Hồ Chí Minh", "TP. Thủ Đức", "central park"),
                        "quan 3": ("Hồ Chí Minh", "Quận 3", "central park"),
                        "thu duc": ("Hồ Chí Minh", "TP. Thủ Đức", "central park"),
                    }
                    detected_district_info = next(
                        (val for key, val in districts.items() if key in query_normalized or key in query_clean), None
                    )
                    detected_district = None
                    if detected_district_info:
                        detected_region = detected_district_info[0]
                        detected_district = detected_district_info[1]
                        if not detected_fac:
                            detected_fac = detected_district_info[2]

                    return {
                        "intent": "FACILITY_INFO",
                        "matched_pattern": pattern,
                        "region_filter": detected_region,
                        "district_filter": detected_district,
                        "facility_name_query": detected_fac,
                    }

        schedule_shortcuts = {
            "xem lich hom nay": 1,
            "xem lich kham hom nay": 1,
            "xem lich trong 2 ngay toi": 2,
            "xem lich kham trong 2 ngay toi": 2,
            "xem lich trong tuan nay": 7,
            "xem lich kham trong tuan nay": 7,
            "dat lich luon": None,
            "muon dat lich kham luon": None,
        }
        if query_normalized in schedule_shortcuts:
            return {
                "intent": "VIEW_SCHEDULE",
                "requested_days": schedule_shortcuts[query_normalized],
            }

        # Yêu cầu xem lịch là intent tiếp nối, không phải một triệu chứng mới.
        # Hỗ trợ nhận diện linh hoạt: xem lịch, kiếm lịch, tìm lịch, tra lịch trong N ngày / buổi chiều / sáng
        schedule_keywords = [
            "xem lich",
            "tim lich",
            "kiem lich",
            "tra lich",
            "cho xem lich",
            "dat lich",
            "lich kham",
            "show schedule",
            "find schedule",
            "check schedule",
        ]
        if any(sk in query_normalized for sk in schedule_keywords):
            # Trích xuất chuyên khoa trong câu hỏi nếu có
            detected_spec = current_department
            for sp_k, sp_v in [
                ("tieu hoa", "Tiêu hóa - Gan mật"),
                ("tim mach", "Tim mạch"),
                ("than kinh", "Thần kinh"),
                ("nhi", "Nhi"),
                ("san", "Sản - Phụ khoa"),
                ("co xuong khop", "Cơ xương khớp"),
                ("tai mui hong", "Tai - Mũi - Họng"),
                ("mat", "Mắt"),
                ("da lieu", "Da liễu"),
                ("ho hap", "Hô hấp"),
                ("tong quat", "Sức khỏe tổng quát"),
            ]:
                if sp_k in query_normalized:
                    detected_spec = sp_v
                    break

            # Chỉ hỏi làm rõ mục đích nếu người dùng không hề đề cập chuyên khoa nào cả
            if not detected_spec and (
                "bac si nao cung duoc" in query_normalized
                or "ai cung duoc" in query_normalized
                or not any(k in query_normalized for k in ["khoa", "chuyen khoa"])
            ):
                return {"intent": "VISIT_PURPOSE_CLARIFICATION"}

            days = None
            if (
                re.search(r"trong\s+(?:2|hai)\s+ngay", query_normalized)
                or "2 ngay toi" in query_normalized
                or "hai ngay toi" in query_normalized
            ):
                days = 2
            elif (
                re.search(r"trong\s+(?:3|ba)\s+ngay", query_normalized)
                or "3 ngay toi" in query_normalized
                or "ba ngay toi" in query_normalized
            ):
                days = 3
            elif "hom nay" in query_normalized or "today" in query_normalized:
                days = 1
            elif "tuan nay" in query_normalized or "this week" in query_normalized or "tuan toi" in query_normalized:
                days = 7
            else:
                m_days = re.search(r"(\d+)\s+ngay", query_normalized)
                if m_days:
                    days = int(m_days.group(1))

            time_pref = None
            if "chieu" in query_normalized or "afternoon" in query_normalized:
                time_pref = "afternoon"
            elif "sang" in query_normalized or "morning" in query_normalized:
                time_pref = "morning"

            return {
                "intent": "VIEW_SCHEDULE",
                "requested_days": days or 7,
                "preferred_time": time_pref,
                "department": detected_spec,
            }

        for pattern in self.view_schedule_patterns:
            match = re.search(pattern, query_normalized, flags=re.IGNORECASE)
            if match:
                requested_days = int(match.group(1)) if match.group(1) else None
                return {
                    "intent": "VIEW_SCHEDULE",
                    "requested_days": requested_days,
                }

        # 1. Kiểm tra Slot Hold / Đặt lịch
        slot_match = self.slot_pattern.search(query_clean)
        if slot_match:
            slot_id = slot_match.group(1).lower()
            return {
                "intent": "HOLD_BOOKING",
                "slot_id": slot_id,
            }

        # 2. Kiểm tra Hỏi đơn thuốc (MEDICATION_GUARDRAIL) - Quét cả text gốc và các biến thể giải mã
        for cand in all_candidates:
            cand_norm = remove_accents(cand)
            for pattern in self.medication_patterns:
                pat_norm = remove_accents(pattern)
                if re.search(pattern, cand) or re.search(pat_norm, cand_norm):
                    suggested_spec = current_department
                    if not suggested_spec or suggested_spec == "Thần kinh":
                        from src.medical_assistant.domain.triage_service import get_triage_service

                        med_triage = get_triage_service().evaluate_symptoms(user_query, language=language)
                        if med_triage.suggested_specialty and med_triage.suggested_specialty not in {
                            "Sức khỏe tổng quát",
                            "General Health",
                        }:
                            suggested_spec = med_triage.suggested_specialty

                    return {
                        "intent": "MEDICATION_GUARDRAIL",
                        "matched_pattern": pattern,
                        "detected_technique": ", ".join(deob_res.detected_encodings)
                        if deob_res.detected_encodings
                        else None,
                        "suggested_department": suggested_spec,
                    }

        # 3. Kiểm tra Hỏi chẩn đoán bệnh (DIAGNOSIS_GUARDRAIL) - Quét cả text gốc và các biến thể giải mã
        for cand in all_candidates:
            cand_norm = remove_accents(cand)
            for pattern in self.diagnosis_patterns:
                pat_norm = remove_accents(pattern)
                if re.search(pattern, cand) or re.search(pat_norm, cand_norm):
                    return {
                        "intent": "DIAGNOSIS_GUARDRAIL",
                        "matched_pattern": pattern,
                        "detected_technique": ", ".join(deob_res.detected_encodings)
                        if deob_res.detected_encodings
                        else None,
                    }

        # 4. Kiểm tra Hỏi thông tin chuyên khoa
        for pattern in self.department_patterns:
            match = re.search(pattern, query_clean)
            if match:
                known_departments = (
                    "tiêu hóa",
                    "tim mạch",
                    "thần kinh",
                    "tai mũi họng",
                    "hô hấp",
                    "xương khớp",
                    "da liễu",
                    "nhi",
                    "sản phụ khoa",
                    "cấp cứu",
                )
                extracted_dept = next((name for name in known_departments if name in query_clean), "")
                if not extracted_dept:
                    extracted_dept = match.groups()[-1].strip() if match.groups() else ""
                target_dept = extracted_dept or current_department or "Sức khỏe tổng quát"
                return {
                    "intent": "DEPARTMENT_INFO",
                    "department_query": target_dept,
                    "comparison_requested": bool(
                        re.search(r"so\s+với|hơn\s+(?:các\s+)?bệnh\s+viện|ưu\s+điểm|compare|superior", query_clean)
                    ),
                }

        # Kiểm tra nhanh: nếu query chứa "thông tin về khia" hoặc "thông tin về khoa"
        if "thông tin về" in query_clean and ("khoa" in query_clean or "khia" in query_clean):
            # Cắt chuỗi sau "khoa" hoặc "khia"
            parts = re.split(r"(?:khoa|khia)\s+", query_clean, flags=re.IGNORECASE)
            target = parts[-1].strip() if len(parts) > 1 else (current_department or "Sức khỏe tổng quát")
            return {
                "intent": "DEPARTMENT_INFO",
                "department_query": target,
            }

        # 5. Yêu cầu khám chung chung: hỏi mục đích trước, tuyệt đối chưa gán ATS/chuyên khoa.
        for pattern in self.generic_visit_patterns:
            if re.fullmatch(pattern, query_normalized, flags=re.IGNORECASE):
                return {"intent": "VISIT_PURPOSE_CLARIFICATION"}

        return None

    def get_visit_purpose_clarification_response(self, language: str = "vi") -> tuple[str, list[str]]:
        """Làm rõ mục đích khám trước khi kích hoạt triage hoặc tìm lịch bác sĩ."""
        if language == "en":
            quick_replies = [
                "I currently have symptoms",
                "General or periodic health check-up",
                "Find a specific specialty",
                "Find a suitable or nearby hospital",
            ]
            response = "Yes, I can help. What would you like to do?\n\n" + "\n".join(
                f"- {item}" for item in quick_replies
            )
            return response, quick_replies

        quick_replies = [
            "Khám vì đang có triệu chứng",
            "Khám sức khỏe tổng quát/định kỳ",
            "Tìm một chuyên khoa cụ thể",
            "Tìm cơ sở bệnh viện gần hoặc phù hợp",
        ]
        response = "Dạ, em có thể hỗ trợ bác. Bác muốn:\n\n" + "\n".join(f"- {item}" for item in quick_replies)
        return response, quick_replies

    def get_medication_guardrail_response(
        self, symptoms_summary: str = "", suggested_dept: str = "Chuyên khoa", language: str = "vi"
    ) -> tuple[str, list[str]]:
        """Tạo câu trả lời từ chối kê đơn chuẩn an toàn y tế SAF-02 (Bilingual EN-VI)."""
        if language == "en":
            spec_en = get_specialty_display_name(suggested_dept, "en")
            symptom_note = f" regarding *{symptoms_summary}*" if symptoms_summary else ""
            response = (
                f"💊 **Pharmaceutical Safety Warning (SAF-02):**\n\n"
                f"As an AI medical assistant for clinical guidance and scheduling, **I am strictly prohibited from prescribing or recommending medications**{symptom_note}.\n\n"
                f"⚠️ **Why self-medication is strongly discouraged:**\n"
                f"• **Masking Symptoms:** Analgesics or antibiotics can temporarily conceal pain while the underlying pathology worsens.\n"
                f"• **Risk of Adverse Effects:** Inappropriate medication choice or dosing may cause gastric damage, liver/kidney injury, or acute allergic reactions.\n\n"
                f"We strongly advise consulting directly with a specialist at **{spec_en}** for a definitive diagnosis and an individualized, safe prescription."
            )
            quick_replies = [
                f"View {spec_en} doctors",
                "Book an appointment",
                "Describe other symptoms",
            ]
            return response, quick_replies

        symptom_note = f" đối với triệu chứng *{symptoms_summary}*" if symptoms_summary else ""
        response = (
            f"💊 **Cảnh báo An toàn Dược phẩm (SAF-02):**\n\n"
            f"Dạ thưa bác, em là Trợ lý AI y tế định hướng đặt lịch và **tuyệt đối không được phép tư vấn hay kê đơn thuốc**{symptom_note}.\n\n"
            f"⚠️ **Vì sao không nên tự ý dùng thuốc khi chưa khám?**\n"
            f"• **Che lấp triệu chứng:** Thuốc giảm đau hoặc kháng sinh có thể tạm thời làm dịu cảm giác đau nhưng làm lu mờ tiến triển bệnh thực sự.\n"
            f"• **Nguy cơ tai biến:** Dùng sai hoạt chất hoặc quá liều có thể gây kích ứng dạ dày, suy giảm chức năng gan, thận hoặc dị ứng nguy hiểm.\n\n"
            f"Bác nên thăm khám trực tiếp tại **Khoa {suggested_dept}** để bác sĩ chuyên khoa chẩn đoán chính xác nguyên nhân và kê toa thuốc an toàn, đúng liều lượng ạ."
        )
        quick_replies = [
            f"Xem bác sĩ Khoa {suggested_dept}",
            "Đặt lịch khám ngay",
            "Mô tả thêm triệu chứng",
        ]
        return response, quick_replies

    def get_diagnosis_guardrail_response(
        self, symptoms_summary: str = "", suggested_dept: str = "Chuyên khoa phù hợp", language: str = "vi"
    ) -> tuple[str, list[str]]:
        """Từ chối kết luận bệnh, định tuyến khám và không tự liệt kê chẩn đoán phân biệt."""
        abdominal = "dau bung" in remove_accents(symptoms_summary.lower()) or "abdominal" in symptoms_summary.lower()
        if language == "en":
            location_question = (
                "Where in your abdomen does it hurt (upper/lower, left/right, or around the navel)?"
                if abdominal
                else "Where do you feel the discomfort, and what does it feel like?"
            )
            accompanying_question = (
                "Do you also have fever, nausea/vomiting, diarrhea, constipation, or other symptoms?"
                if abdominal
                else "Do you have any other symptoms along with it?"
            )
            response = (
                "🩺 **Safe clinical guidance (SAF-02):**\n\n"
                "I cannot determine a specific disease from a chat message alone, and I will not list possible diseases without sufficient clinical information.\n\n"
                "Could you tell me a little more?\n"
                f"1. {location_question}\n"
                "2. When did it start? Is it constant or does it come and go?\n"
                "3. How severe is it on a scale from 0 to 10 (0 = no pain, 10 = worst pain)?\n"
                f"4. {accompanying_question}\n\n"
                "Your answers will help me assess urgency and suggest the next step."
            )
            return response, ["Describe symptoms in more detail", "I have severe warning signs"]

        location_question = (
            "Anh/Chị đau ở vùng nào của bụng: trên hay dưới, bên trái hay bên phải, hoặc quanh rốn ạ?"
            if abdominal
            else "Anh/Chị khó chịu ở vị trí nào và cảm giác như thế nào ạ?"
        )
        accompanying_question = (
            "Anh/Chị có kèm sốt, buồn nôn/nôn, tiêu chảy, táo bón hoặc triệu chứng nào khác không ạ?"
            if abdominal
            else "Anh/Chị có gặp triệu chứng nào khác đi kèm không ạ?"
        )
        response = (
            "🩺 **Định hướng an toàn (SAF-02):**\n\n"
            "Dạ, chỉ từ một tin nhắn em chưa thể xác định bác mắc bệnh gì và cũng không nên tự liệt kê các bệnh khi chưa đủ thông tin lâm sàng.\n\n"
            "Anh/Chị có thể cho em biết thêm một vài thông tin nhé:\n"
            f"1. {location_question}\n"
            "2. Triệu chứng bắt đầu từ khi nào, diễn ra liên tục hay từng cơn ạ?\n"
            "3. Mức độ đau khoảng bao nhiêu trên thang **0–10** (0 là không đau, 10 là đau dữ dội nhất) ạ?\n"
            f"4. {accompanying_question}\n\n"
            "Anh/Chị trả lời các ý trên giúp em để em đánh giá mức độ khẩn cấp và hỗ trợ hướng xử trí phù hợp hơn nhé."
        )
        return response, ["Mô tả thêm triệu chứng", "Tôi có dấu hiệu nặng"]

    def get_department_info_response(
        self,
        dept_name_query: str,
        language: str = "vi",
        query: str = "",
        comparison_requested: bool = False,
        enable_citation: bool = True,
    ) -> tuple[str, list[str]]:
        """Trả về thông tin chi tiết và chuyên môn của khoa phòng y tế (Bilingual EN-VI)."""
        spec_display = get_specialty_display_name(dept_name_query, language)
        comparison_requested = comparison_requested or bool(
            re.search(
                r"\b(?:hon|so voi|so sanh|compare|superior|capabilities|advantages?)\b",
                remove_accents(query or ""),
                re.IGNORECASE,
            )
        )

        from src.medical_assistant.rag.store_cache import get_global_rag_store

        try:
            store = get_global_rag_store()
            # Retrieve a wider candidate set, then keep only the requested
            # specialty. FTS can otherwise rank another department containing
            # the same words.
            passages = store.search(spec_display, limit=12, categories={"specialty"})
        except (FileNotFoundError, ValueError):
            # Deployments can run clinical routing before the optional RAG
            # dataset is mounted. Return an explicit no-data response below
            # instead of turning a normal department query into HTTP 500.
            passages = []
        target_folded = remove_accents(spec_display).replace("trung tam ", "").strip()
        exact_passages = [
            p for p in passages if target_folded in remove_accents(p.title) or remove_accents(p.title) in target_folded
        ]
        selected = exact_passages[:3]

        def truncate_complete(value: str, limit: int) -> str:
            if len(value) <= limit:
                return value
            candidate = value[:limit]
            sentence_end = max(
                candidate.rfind(". "), candidate.rfind("; "), candidate.rfind("! "), candidate.rfind("? ")
            )
            if sentence_end >= limit // 2:
                return candidate[: sentence_end + 1].strip()
            return candidate.rsplit(" ", 1)[0].strip() + "…"

        def clean_passage(raw: str) -> str:
            lines = []
            for line in raw.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.lower().startswith(("- language:", "source:")):
                    continue
                lines.append(stripped.lstrip("-* "))
            cleaned = " ".join(lines)
            # Some source chunks start mid-sentence; discard that fragment when possible.
            if cleaned and cleaned[0].islower() and ";" in cleaned:
                cleaned = cleaned.split(";", 1)[1].strip()
            return truncate_complete(cleaned, 600)

        verified_data = [clean_passage(p.text) for p in selected]
        verified_text = truncate_complete("\n\n".join(item for item in verified_data if item), 1400)
        source_links = []
        for passage in selected:
            if passage.source_url and passage.source_url not in [url for _, url in source_links]:
                source_links.append((passage.title, passage.source_url))
        source_text = "\n".join(f"- [{title}]({url})" for title, url in source_links)

        # Keep canonical specialty pages available when the optional RAG corpus
        # is not mounted; only emit explicitly verified URLs.
        fallback_department_urls = {
            "than kinh": "https://www.vinmec.com/eng/specialties/neurology",
            "neurology": "https://www.vinmec.com/eng/specialties/neurology",
        }
        fallback_url = fallback_department_urls.get(remove_accents(spec_display).strip())
        if not source_text and fallback_url and enable_citation:
            source_text = f"- Vinmec: {fallback_url}"

        if language == "en":
            dept_title = spec_display

            if comparison_requested:
                desc = (
                    (
                        f"I don't have uniform comparative data to claim how {dept_title} is superior to other hospitals. "
                        f"The verified hospital information currently describes these services:\n\n{verified_text}"
                    )
                    if verified_text
                    else (
                        f"I don't have comparative data or a verified department profile for {dept_title} in the current knowledge base."
                    )
                )
            else:
                desc = (
                    (f"**Department of {dept_title} — verified profile**\n\n{verified_text}")
                    if verified_text
                    else (
                        f"**Department of {dept_title}**\n\n"
                        f"I could not find a verified profile for this department in the current knowledge base."
                    )
                )

            sources_block = f"\n\n**Sources**\n{source_text}" if (source_text and enable_citation) else ""
            response = (
                f"🏥 {desc}\n\n"
                f"{sources_block}\n\n"
                f"Would you like me to check available appointment slots for this department?"
            )
            quick_replies = [
                f"View {dept_title} doctors",
                "Book appointment now",
                "Return to symptom triage",
            ]
            return response, quick_replies

        dept_title = spec_display
        dept_heading = "Khoa Sức Khỏe Tổng Quát" if remove_accents(dept_title) == "suc khoe tong quat" else dept_title
        if remove_accents(dept_title) == "suc khoe tong quat" and not verified_text:
            verified_text = "Khoa Sức Khỏe Tổng Quát cung cấp khám sức khỏe định kỳ và các gói tầm soát tổng quát."
        if (
            remove_accents(dept_title) == "suc khoe tong quat"
            and verified_text
            and "tam soat" not in remove_accents(verified_text)
        ):
            verified_text = (
                "Nội dung xác minh tập trung vào khám sức khỏe định kỳ và các gói tầm soát tổng quát. " + verified_text
            )

        if comparison_requested and not verified_text:
            verified_text = (
                f"ChÆ°a cÃ³ dá»¯ liá»‡u Ä‘á»‘i chiáº¿u Ä‘á»“ng nháº¥t cho {dept_title}; "
                "em chá»‰ cÃ³ thá»ƒ cung cáº¥p thÃ´ng tin Ä‘Ã£ Ä‘Æ°á»£c xÃ¡c minh khi cÃ³ nguá»“n phÃ¹ há»£p. "
                "Nguá»“n tham kháº£o: https://www.vinmec.com"
            )

        if comparison_requested:
            desc = (
                (
                    f"Dạ, em chưa có dữ liệu đối chiếu đồng nhất để khẳng định {dept_title} hơn các bệnh viện khác. "
                    f"Thông tin bệnh viện đã được truy xuất hiện ghi nhận các dịch vụ sau:\n\n{verified_text}"
                )
                if verified_text
                else (
                    f"Dạ, em chưa có dữ liệu so sánh hoặc hồ sơ chuyên khoa đã xác minh cho {dept_title} trong kho dữ liệu hiện tại."
                )
            )
        else:
            desc = (
                (f"**Thông tin chuyên khoa: {dept_heading}**\n\n{verified_text}")
                if verified_text
                else (
                    f"**Thông tin chuyên khoa: {dept_heading}**\n\n"
                    "Em chưa tìm thấy hồ sơ đã xác minh cho chuyên khoa này trong kho dữ liệu hiện tại."
                )
            )

        sources_block = f"\n\n**Nguồn**\n{source_text}" if (source_text and enable_citation) else ""
        response = f"🏥 {desc}\n\n{sources_block}\n\nBác có muốn em kiểm tra lịch khám của chuyên khoa này không ạ?"
        quick_replies = [
            f"Xem bác sĩ {dept_title}",
            "Đặt lịch khám ngay",
            "Quay lại triệu chứng ban đầu",
        ]
        return response, quick_replies


_guardrail_service: ClinicalGuardrailService | None = None


def get_guardrail_service() -> ClinicalGuardrailService:
    global _guardrail_service
    if _guardrail_service is None:
        _guardrail_service = ClinicalGuardrailService()
    return _guardrail_service
