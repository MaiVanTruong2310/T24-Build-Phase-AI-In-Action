"""
Zero-Token Semantic & Policy FAQ Cache Service
Tiết kiệm 100% token LLM cho các câu hỏi thường gặp:
- Bảng giá khám & dịch vụ chung
- Địa chỉ, giờ làm việc & Hotline cơ sở
- Hướng dẫn chuẩn bị trước khi khám (nhịn ăn, giấy tờ tùy thân)
- Quy trình đặt lịch, đổi/hủy lịch hẹn
- Chào hỏi và hướng dẫn sử dụng bot ban đầu
"""

import re
import unicodedata

from src.medical_assistant.domain.language_service import detect_language


def _normalize_text(text: str) -> str:
    """Loại bỏ dấu tiếng Việt và chuẩn hóa chữ thường để so khớp cực nhanh"""
    # U+FFFD commonly appears when a legacy client decodes Vietnamese text
    # with the wrong charset. In greeting phrases it most often replaces "à".
    text = text.replace("\ufffd", "a").lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "d")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class FAQEntry:
    def __init__(
        self,
        key: str,
        patterns: list[str],
        response_vi: str,
        response_en: str,
        quick_replies_vi: list[str] | None = None,
        quick_replies_en: list[str] | None = None,
    ):
        self.key = key
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.response_vi = response_vi
        self.response_en = response_en
        self.quick_replies_vi = quick_replies_vi or []
        self.quick_replies_en = quick_replies_en or []

    def matches(self, text: str, normalized_text: str) -> bool:
        for p in self.patterns:
            if p.search(text) or p.search(normalized_text):
                return True
        return False

    def get_response(self, language: str = "vi") -> tuple[str, list[str]]:
        if language == "en":
            return self.response_en, self.quick_replies_en
        return self.response_vi, self.quick_replies_vi


FAQ_KNOWLEDGE_BASE: list[FAQEntry] = [
    # 1. Chào hỏi ban đầu
    FAQEntry(
        key="GREETING",
        patterns=[
            r"^(xin ch[aà]o|ch[aà]o (b[aạ]n|em|bot|b[aá]c)|b[aắ]t đ[aầ]u|alo)$",
            r"^(t[oô]i mu[oố]n kh[aá]m|mu[oố]n đ[aặ]t l[iị]ch|đ[aặ]t l[iị]ch kh[aá]m|đ[aặ]t h[eẹ]n|dat hen|dat lich|bat dau|alo)$",
            r"^(xin chao|chao ban|chao em|chao bot)$",
            r"^xin chao(?: tro ly| bot| ban| em)?$",
            # English
            r"^(hello|hi|good morning|good afternoon|good evening|hey|start)$",
            r"^(?:hello|hi|hey)(?:\s+.*(?:book|appointment|doctor).*)?$",
            r"^(book appointment|make appointment|i want to see a doctor)$",
        ],
        response_vi=(
            "👋 **Xin chào bác! Em là Trợ lý Y tế Thông minh (P-124).**\n\n"
            "Em có thể hỗ trợ bác:\n"
            "1. 🩺 **Định hướng chuyên khoa:** Phân tích triệu chứng và đề xuất khoa khám phù hợp.\n"
            "2. 👨‍⚕️ **Tra cứu bác sĩ & Khung giờ:** Tìm bác sĩ chuyên khoa giỏi và ca khám còn trống.\n"
            "3. 📅 **Giữ chỗ đặt lịch hẹn (Hold 15 phút):** Giữ slot khám và gửi Lễ tân phê duyệt.\n\n"
            "Bác vui lòng chia sẻ: **Hiện tại bác đang cảm thấy khó chịu hoặc có triệu chứng gì ở đâu ạ?**"
        ),
        response_en=(
            "👋 **Hello and welcome! I am the Vinmec Smart Medical Assistant (P-124).**\n\n"
            "I can assist you with:\n"
            "1. 🩺 **Specialty Guidance:** Analyze your symptoms and recommend the appropriate clinical department.\n"
            "2. 👨‍⚕️ **Doctor & Schedule Lookup:** Search available appointment slots with experienced specialists.\n"
            "3. 📅 **Slot Reservation (15-min Hold):** Temporarily reserve your preferred slot and notify reception.\n\n"
            "Please share: **What symptoms or health concerns are you experiencing today?**"
        ),
        quick_replies_vi=["Đau tức ngực / khó thở", "Đau đầu / chóng mặt", "Đau bụng / khó tiêu", "Đau mỏi vai gáy / lưng", "Khám sức khỏe tổng quát"],
        quick_replies_en=["Chest discomfort / shortness of breath", "Headache / dizziness", "Abdominal pain / indigestion", "Neck / back / joint pain", "General health checkup"]
    ),

    # 2. Hướng dẫn nhịn ăn / chuẩn bị trước khám
    FAQEntry(
        key="FASTING_PREPARATION",
        patterns=[
            r"nhin an.*(xet nghiem|kham|mau)",
            r"co duoc an (sang|truoc khi|gi khong)",
            r"chuan bi gi truoc khi (kham|xet nghiem)",
            r"co can nhin an",
            # English
            r"fast(ing)?.*(test|exam|blood|appointment)",
            r"can i eat.*(before|morning)",
            r"how to prepare.*(exam|test)",
            r"do i need to fast",
        ],
        response_vi=(
            "📋 **Hướng dẫn chuẩn bị trước khi đi khám & làm xét nghiệm:**\n\n"
            "1. **Nhịn ăn:** Quý khách cần **nhịn ăn sáng từ 6 - 8 tiếng** trước khi lấy máu xét nghiệm đường huyết, mỡ máu, chức năng gan/thận hoặc nội soi tiêu hóa. Được uống nước lọc lượng vừa phải.\n"
            "2. **Đồ uống:** Tuyệt đối không uống nước ngọt có ga, sữa chua, cà phê, nước tăng lực hoặc rượu bia trong vòng 24 giờ trước khi khám.\n"
            "3. **Thuốc đang dùng:** Thuốc huyết áp vẫn uống bình thường vào buổi sáng với ít nước lọc. Thuốc tiểu đường nên tạm ngưng và mang theo đến bệnh viện để uống sau khi đã lấy máu xét nghiệm.\n"
            "4. **Giấy tờ:** Mang theo CCCD/Hộ chiếu, thẻ BHYT và các kết quả khám cũ (nếu có)."
        ),
        response_en=(
            "📋 **Preparation Guidelines Before Clinical Examination & Laboratory Tests:**\n\n"
            "1. **Fasting:** You must **fast for 6 to 8 hours** prior to blood tests (glucose, lipid panel, liver/kidney function) or gastrointestinal endoscopy. Plain water is permitted in moderation.\n"
            "2. **Beverages:** Strictly avoid carbonated drinks, dairy, coffee, energy drinks, and alcohol for 24 hours prior to testing.\n"
            "3. **Current Medications:** Blood pressure medications should be taken as usual in the morning with a sip of water. Diabetes medications should be temporarily withheld and brought to the clinic to take after blood sampling.\n"
            "4. **Documents:** Please bring your Passport/National ID, health insurance cards, and any prior medical records."
        ),
        quick_replies_vi=["Đặt lịch khám tổng quát", "Bảng giá gói khám", "Quay lại mô tả triệu chứng"],
        quick_replies_en=["Book health screening", "Pricing & package fees", "Describe current symptoms"]
    ),

    # 3. Bảng giá dịch vụ chung
    FAQEntry(
        key="PRICING_INFO",
        patterns=[
            r"bang gia|chi phi kham|gia kham|gia dich vu|bao nhieu tien|kham mat bao nhieu|kham het bao nhieu",
            # English
            r"(price|pricing|cost|fee|how much).*(consultation|exam|doctor|clinic|package)",
            r"how much does it cost",
            r"consultation fee",
        ],
        response_vi=(
            "💳 **Bảng giá tham khảo dịch vụ khám chữa bệnh:**\n\n"
            "• **Khám Nội đa khoa (có hẹn):** 440.000 VNĐ / lượt\n"
            "• **Khám Chuyên khoa (có hẹn trước):** 690.000 VNĐ / lượt\n"
            "• **Khám Chuyên gia / Trưởng phó khoa:** 1.800.000 VNĐ / lượt\n"
            "• **Khám Nhi / Sơ sinh (có hẹn):** 550.000 VNĐ / lượt\n"
            "• **Gói Sức khỏe tổng quát Cơ bản:** từ 5.000.000 VNĐ\n"
            "• **Gói Sức khỏe tổng quát Nâng cao:** từ 18.000.000 VNĐ\n\n"
            "*Lưu ý: Đặt lịch hẹn trước qua hệ thống giúp quý khách tiết kiệm chi phí so với khám không hẹn (1.100.000 VNĐ). Bệnh viện có áp dụng thanh toán BHYT & Bảo hiểm bảo lãnh tư nhân.*"
        ),
        response_en=(
            "💳 **Vinmec Outpatient Examination Fee Schedule:**\n\n"
            "• **General Internal Medicine (Scheduled):** 440,000 VND / visit\n"
            "• **Specialist Consultation (Scheduled):** 690,000 VND / visit\n"
            "• **Department Head / Senior Specialist:** 1,800,000 VND / visit\n"
            "• **Pediatric Examination (Scheduled):** 550,000 VND / visit\n"
            "• **Standard Health Screening Package:** from 5,000,000 VND\n"
            "• **Comprehensive Health Screening Package:** from 18,000,000 VND\n\n"
            "*Note: Booking an appointment in advance secures preferential rates compared to walk-in consultations (1,100,000 VND). Vinmec accepts international private health insurance direct billing and national health insurance (BHYT).* "
        ),
        quick_replies_vi=["Đặt lịch khám chuyên khoa", "Xem gói tổng quát", "Tư vấn bảo hiểm"],
        quick_replies_en=["Book specialist consultation", "View screening packages", "Insurance inquiries"]
    ),

    # 4. Giờ làm việc & Hotline các cơ sở
    FAQEntry(
        key="WORKING_HOURS_HOTLINE",
        patterns=[
            r"gio lam viec|gio mo cua|lam viec den may gio|may gio lam viec|mo cua den may gio|dong cua luc may gio|kham thu 7|kham chu nhat|hotline|so dien thoai tong dai|dia chi benh vien",
            # English
            r"(working|operating|opening)\s+hours",
            r"(what\s+time|when)\s+do\s+you\s+(open|close)",
            r"open\s+on\s+(saturday|sunday|weekend)",
            r"hospital\s+(hotline|phone|address)",
        ],
        response_vi=(
            "🏥 **Thời gian làm việc & Hotline Bệnh viện:**\n\n"
            "⏰ **Giờ làm việc khu Khám bệnh:**\n"
            "• **Thứ 2 đến Thứ 6:** Sáng 08:00 - 12:00 | Chiều 13:00 - 17:00\n"
            "• **Thứ 7:** Sáng 08:00 - 12:00 (Nghỉ chiều Thứ 7 & Chủ Nhật)\n"
            "• **Khoa Cấp cứu & Phòng Lưu bệnh:** Trực cấp cứu **24/7** liên tục tất cả các ngày trong năm.\n\n"
            "📞 **Hotline các cơ sở chính:**\n"
            "• Times City (Hà Nội): `024 3974 3556`\n"
            "• Central Park (TP.HCM): `028 3622 1166`\n"
            "• Đà Nẵng: `023 6371 1111` | Hải Phòng: `022 5730 9888`"
        ),
        response_en=(
            "🏥 **Operating Hours & Hospital Hotlines:**\n\n"
            "⏰ **Outpatient Clinic Hours:**\n"
            "• **Monday to Friday:** Morning 08:00 - 12:00 | Afternoon 13:00 - 17:00\n"
            "• **Saturday:** Morning 08:00 - 12:00 (Closed Saturday afternoon & Sunday)\n"
            "• **Emergency Department & Inpatient Units:** Operating **24/7** year-round.\n\n"
            "📞 **Key Hospital Hotlines:**\n"
            "• Times City (Hanoi): `+84 24 3974 3556`\n"
            "• Central Park (HCMC): `+84 28 3622 1166`\n"
            "• Danang: `+84 23 6371 1111` | Hai Phong: `+84 22 5730 9888`"
        ),
        quick_replies_vi=["Đặt lịch khám ngay", "Đăng ký cấp cứu 115", "Tư vấn triệu chứng"],
        quick_replies_en=["Book an appointment", "Emergency 115 contact", "Consult symptoms"]
    ),

    # 5. Chính sách đổi / hủy lịch hẹn
    FAQEntry(
        key="CANCEL_RESCHEDULE_POLICY",
        patterns=[
            r"doi lich|huy lich|doi gio kham|huy hen|doi ngay kham|hoan tien|chinh sach huy",
            # English
            r"cancel.*(appointment|booking)",
            r"reschedule.*(appointment|booking|time)",
            r"change.*(time|date).*appointment",
            r"cancellation\s+policy",
        ],
        response_vi=(
            "🔄 **Chính sách Đổi & Hủy lịch khám:**\n\n"
            "1. **Thời gian đổi/hủy:** Quý khách có thể đổi hoặc hủy lịch hẹn hoàn toàn miễn phí **trước giờ khám ít nhất 2 tiếng**.\n"
            "2. **Cách thực hiện:**\n"
            "   • Nhắn trực tiếp cho em: *'Tôi muốn hủy lịch mã [Mã đặt lịch]'*.\n"
            "   • Hoặc liên hệ Tổng đài CSKH để nhân viên Lễ tân hỗ trợ giải phóng khung giờ cho bệnh nhân khác.\n"
            "3. **Hoàn tiền / Slot trống:** Khi quý khách hủy hẹn, slot khám sẽ tự động được hoàn trả về trạng thái khả dụng cho cộng đồng."
        ),
        response_en=(
            "🔄 **Appointment Rescheduling & Cancellation Policy:**\n\n"
            "1. **Notice Window:** You may reschedule or cancel your appointment free of charge **at least 2 hours before the scheduled time**.\n"
            "2. **How to Cancel:**\n"
            "   • Message me directly: *'Cancel booking [Booking Code]'*.\n"
            "   • Or contact our Customer Care Center so our reception staff can release the slot for other patients.\n"
            "3. **Slot Availability:** Upon cancellation, the slot is immediately returned to the active schedule."
        ),
        quick_replies_vi=["Quay lại đặt lịch khám", "Kiểm tra mã đặt lịch", "Gặp lễ tân"],
        quick_replies_en=["Return to booking", "Check booking status", "Contact receptionist"]
    )
]


class ZeroTokenCacheService:
    """Service đối soát câu hỏi thường gặp với tốc độ < 0.1ms và 0 token LLM (Bilingual EN-VI)"""

    def __init__(self):
        self.entries = FAQ_KNOWLEDGE_BASE

    def has_clinical_symptom(self, text: str) -> bool:
        """Kiểm tra xem câu hỏi có chứa triệu chứng bệnh hay không để không chặn nhầm vào cache."""
        norm = _normalize_text(text)
        indicators = [
            "dau", "sot", "ho", "met", "kho tho", "non", "chong mat", "tuc nguc",
            "tao bon", "tieu chay", "phat ban", "di ung", "o chua", "ngua", "chay mau",
            "co giat", "bat tinh", "mo mat", "day bung", "kho tieu", "buon non", "te bi",
            "pain", "ache", "fever", "cough", "breath", "vomit", "nausea", "dizzy",
            "bleed", "rash", "cramp", "seizure", "swelling", "numb"
        ]
        tokens = set(norm.split())
        for ind in indicators:
            if " " in ind:
                if ind in norm:
                    return True
            elif ind in tokens:
                return True
        return False

    def check_cache(self, user_query: str, language: str | None = None) -> tuple[str, list[str], str] | None:
        """
        Kiểm tra xem câu hỏi có thuộc nhóm FAQ chính sách/giờ làm việc/chuẩn bị khám không.
        Trả về: (response_text, quick_replies, faq_key) hoặc None.
        QUY TẮC AN TOÀN: Nếu câu hỏi có kèm triệu chứng y tế, TUYỆT ĐỐI không trả lời bằng Greeting cache!
        """
        text = user_query.strip()
        if not text:
            return None

        lang = language if language in ["vi", "en"] else detect_language(user_query)
        norm_text = _normalize_text(text)
        has_symptoms = self.has_clinical_symptom(text)

        for entry in self.entries:
            # Nếu người dùng có triệu chứng y tế thực sự, không được chặn bằng GREETING
            if entry.key == "GREETING" and has_symptoms:
                continue

            if entry.matches(text, norm_text):
                resp, replies = entry.get_response(lang)
                return resp, replies, entry.key

        return None


_cache_service: ZeroTokenCacheService | None = None


def get_cache_service() -> ZeroTokenCacheService:
    global _cache_service
    if _cache_service is None:
        _cache_service = ZeroTokenCacheService()
    return _cache_service
