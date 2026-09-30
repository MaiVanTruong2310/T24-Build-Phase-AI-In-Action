"""
Security Guardrail Service.
Enforces defense against:
1. Prompt Injections & Jailbreaks (DAN, Developer Mode, Roleplay Bypass)
2. System Prompt Exfiltration
3. Tool Abuse & Unauthorized Commands (SQL Injection, DB Alteration, Shell)
4. Cross-Patient Privacy Violations (Multi-Tenant PHI/PII Snoop Attempts)
5. Out-of-domain Dangerous Content (Explosives, Bio-weapons, Self-harm)
"""

import re
import unicodedata
from dataclasses import dataclass

from src.medical_assistant.domain.security.deobfuscator import Deobfuscator, get_deobfuscator


@dataclass
class SecurityCheckResult:
    is_safe: bool
    violation_type: str | None = None  # PROMPT_INJECTION | SYSTEM_EXFILTRATION | PRIVILEGE_ESCALATION | CROSS_PATIENT_SNOOP | DANGEROUS_CONTENT
    detected_technique: str | None = None
    matched_pattern: str | None = None
    safe_response: str | None = None
    quick_replies: list[str] | None = None


class SecurityGuardrailService:
    def __init__(self, deobfuscator: Deobfuscator | None = None):
        self.deobfuscator = deobfuscator or get_deobfuscator()

        # 1. Prompt Injection & Jailbreak Patterns
        self.injection_patterns = [
            r"ignore\s+(all\s+)?(previous|prior|system)\s+(instructions|prompts|rules)",
            r"bỏ\s+qua\s+(hết\s+|tất\s+cả\s+)?(chỉ\s+thị|quy\s+tắc|hướng\s+dẫn|lời\s+nhắc)\s+(trước|hệ\s+thống)",
            r"quên\s+(đi\s+)?(toàn\s+bộ\s+|tất\s+cả\s+)?(quy\s+định|chỉ\s+thị|luật)",
            r"you\s+are\s+now\s+(in\s+)?(developer\s+mode|dan|unrestricted|jailbreak)",
            r"(chuyển\s+sang|kích\s+hoạt)\s+chế\s+độ\s+(nhà\s+phát\s+triển|developer|dan|không\s+giới\s+hạn)",
            r"act\s+as\s+an?\s+(unrestricted|unfiltered|jailbroken|evil)\s+ai",
            r"hãy\s+đóng\s+vai\s+(ai|bác\s+sĩ)\s+không\s+bị\s+ràng\s+buộc",
            r"disregard\s+(the\s+above|all\s+rules|safety\s+guidelines)",
            r"override\s+system\s+(prompt|settings|guardrails)",
            r"new\s+system\s+directive",
            r"system\s*:\s*you\s+are",
            r"bạn\s+không\s+còn\s+là\s+trợ\s+lý\s+y\s+tế",
            r"pretend\s+you\s+have\s+no\s+(rules|limits|safety)",
            r"bỏ\s+(?:hết|toàn\s+bộ|tất\s+cả)\s+(?:luật|lệnh|quy\s+tắc|hướng\s+dẫn)(?:\s+trước\s+đó)?",
            r"(?:giả\s+sử|coi\s+như|hãy\s+tin)\s+(?:tôi|tao|mình)\s+là\s+(?:quản\s+trị\s+viên|admin|developer)",
            r"(?:chuyển|bật|vào)\s+(?:sang\s+)?chế\s+độ\s+(?:nội\s+bộ|quản\s+trị|admin)",
        ]

        # 2. System Prompt & Secret Exfiltration Patterns
        self.exfiltration_patterns = [
            r"(repeat|show|print|reveal|output|display)\s+(the\s+|your\s+)?(system\s+prompt|initial\s+instructions|system\s+message)",
            r"(in|hiển\s+thị|cho\s+xem|xuất|đọc)\s+(toàn\s+bộ\s+)?(system\s+prompt|lời\s+nhắc\s+hệ\s+thống|chỉ\s+thị\s+ban\s+đầu|cấu\s+hình\s+prompt)",
            r"what\s+are\s+your\s+(exact\s+)?(instructions|system\s+rules|directives)",
            r"hướng\s+dẫn\s+hệ\s+thống\s+của\s+bạn\s+là\s+gì",
            r"output\s+your\s+(prompt|instructions)\s+as\s+(json|markdown|yaml|text)",
            r"what\s+did\s+the\s+developer\s+tell\s+you",
            r"lời\s+nhắc\s+của\s+nhà\s+phát\s+triển\s+cho\s+bạn",
            r"(give|show|dump)\s+me\s+your\s+(api\s+key|token|secrets|database\s+password)",
            r"(cho\s+tôi|in\s+ra|lấy)\s+(api\s+key|mật\s+khẩu|chuỗi\s+kết\s+nối|token\s+supabase)",
            r"(?:chép|đưa|gửi|tiết\s+lộ).{0,40}(?:chỉ\s+dẫn|chỉ\s+thị|cấu\s+hình).{0,30}(?:hệ\s+thống|nội\s+bộ)",
            r"(?:khóa|mã\s+khóa|bí\s+mật|secret|credential).{0,30}(?:đang\s+dùng|nội\s+bộ|hệ\s+thống)",
        ]

        # 3. Privilege Escalation & SQL/Shell Command Patterns
        self.privilege_patterns = [
            r"\b(drop|alter|truncate)\s+table\b",
            r"\bdelete\s+from\s+[a-zA-Z0-9_]+",
            r"\bunion\s+select\b",
            r"\bselect\s+.*\s+from\s+(information_schema|pg_|users|patients|auth\.)",
            r"\b(exec|execute_sql|eval|os\.system|subprocess)\b",
            r"\b(rm\s+-rf|chmod\s+777|cat\s+/etc/passwd)\b",
            r"\binsert\s+into\s+.*(admin|users|roles)",
        ]

        # 4. Cross-Patient Privacy Violations (Multi-Tenant Snoop)
        self.cross_patient_patterns = [
            r"(cho\s+xem|ai\s+đã\s+đặt|danh\s+sách|thông\s+tin)\s+(bệnh\s+nhân|khách\s+hàng|người\s+khác)",
            r"(xem|đọc|tìm)\s+hồ\s+sơ\s+(bệnh\s+án\s+)?của\s+(người\s+khác|bệnh\s+nhân\s+khác)",
            r"who\s+(else\s+)?booked\s+slot",
            r"(show|list|get)\s+(other|all)\s+patients?",
            r"(read|view)\s+(medical\s+records?|history)\s+of\s+another\s+patient",
            r"tra\s+cứu\s+(sđt|số\s+điện\s+thoại|cccd|cmnd|bhyt)\s+của\s+(người\s+khác|bệnh\s+nhân)",
        ]

        # 5. Out-of-Domain Dangerous / Harmful Content
        self.harmful_patterns = [
            r"(chế\s+tạo|cách\s+làm)\s+(bom|thuốc\s+nổ|chất\s+độc|vũ\s+khí\s+hóa\s+học)",
            r"(how\s+to|instructions\s+to)\s+(make|synthesize|build)\s+(a\s+bomb|poison|explosive|bio-weapon)",
            r"(hướng\s+dẫn|cách)\s+(tự\s+tử|tự\s+hại|kết\s+liễu\s+đời)",
            r"(how\s+to|methods\s+of)\s+(commit\s+suicide|self-harm|kill\s+myself)",
        ]

    @staticmethod
    def _fold_security_text(text: str) -> str:
        """Accent/case/punctuation tolerant form used only for security signals."""
        folded = unicodedata.normalize("NFKD", text.casefold())
        folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
        folded = re.sub(r"[^a-z0-9]+", " ", folded)
        return re.sub(r"\s+", " ", folded).strip()

    @staticmethod
    def _edit_distance_at_most_one(left: str, right: str) -> bool:
        """Small bounded typo check; only used for long security-specific words."""
        if left == right:
            return True
        if abs(len(left) - len(right)) > 1:
            return False
        if len(left) == len(right):
            mismatches = [i for i, (a, b) in enumerate(zip(left, right)) if a != b]
            if len(mismatches) <= 1:
                return True
            # Common human typo: two adjacent characters are transposed.
            if len(mismatches) == 2:
                first, second = mismatches
                return (
                    second == first + 1
                    and left[first] == right[second]
                    and left[second] == right[first]
                )
            return False
        short, long = (left, right) if len(left) < len(right) else (right, left)
        i = j = edits = 0
        while i < len(short) and j < len(long):
            if short[i] == long[j]:
                i += 1
                j += 1
            else:
                edits += 1
                j += 1
                if edits > 1:
                    return False
        return True

    def _has_security_keyword(self, folded_text: str, keywords: tuple[str, ...]) -> bool:
        tokens = folded_text.split()
        for keyword in keywords:
            if " " in keyword and keyword in folded_text:
                return True
            if len(keyword) >= 5 and any(
                len(token) >= 4 and self._edit_distance_at_most_one(token, keyword)
                for token in tokens
            ):
                return True
            if keyword in tokens:
                return True
        return False

    def _extract_embedded_symptom(self, query: str) -> str | None:
        """Trích xuất triệu chứng y tế hợp lệ nếu người dùng gửi prompt lai ghép (vừa có triệu chứng vừa có injection)."""
        query_lower = query.lower()
        symptom_keywords = [
            ("đau thắt ngực", "đau ngực"),
            ("đau ngực", "đau ngực"),
            ("đau bụng", "đau bụng"),
            ("đau dạ dày", "đau dạ dày"),
            ("đau đầu", "đau đầu"),
            ("đau nửa đầu", "đau nửa đầu"),
            ("đau vai gáy", "đau vai gáy"),
            ("đau lưng", "đau lưng"),
            ("buồn nôn", "buồn nôn"),
            ("chóng mặt", "chóng mặt"),
            ("khó thở", "khó thở"),
            ("sốt cao", "sốt"),
            ("sốt", "sốt"),
            ("táo bón", "táo bón"),
            ("tiêu chảy", "tiêu chảy"),
            ("abdominal pain", "abdominal pain"),
            ("stomach ache", "stomach ache"),
            ("chest pain", "chest pain"),
            ("headache", "headache"),
            ("dizziness", "dizziness"),
            ("shortness of breath", "shortness of breath"),
            ("back pain", "back pain"),
        ]
        for kw, label in symptom_keywords:
            if kw in query_lower:
                return label
        return None

    def inspect_query(self, user_query: str, language: str = "vi") -> SecurityCheckResult:
        """
        Kiểm tra toàn diện an ninh đầu vào.
        Sử dụng Deobfuscator để quét cả text gốc và các biến thể giải mã (Morse, Hex, Binary, Base64, Leet).
        """
        if not user_query or not user_query.strip():
            return SecurityCheckResult(is_safe=True)

        embedded_symptom = self._extract_embedded_symptom(user_query)

        # 1. Bóc tách Deobfuscation
        deob_res = self.deobfuscator.process(user_query)
        text_variants = deob_res.all_text_representations
        detected_enc = ", ".join(deob_res.detected_encodings) if deob_res.detected_encodings else None

        for variant in text_variants:
            var_lower = variant.lower().strip()
            folded = self._fold_security_text(var_lower)

            # Phát hiện theo tổ hợp ý định để bắt cách nói tự nhiên mà không phụ thuộc
            # một câu regex cố định. Chỉ chặn khi có ít nhất hai nhóm tín hiệu độc lập.
            override_signal = bool(re.search(
                r"(?:bỏ|quên|ghi\s+đè|phớt\s+lờ|ignore|override).{0,35}(?:luật|quy\s+tắc|chỉ\s+thị|hướng\s+dẫn|instruction|rule)",
                var_lower,
            )) or (
                self._has_security_keyword(folded, ("ignore", "override", "bo qua", "quen"))
                and self._has_security_keyword(folded, ("instruction", "instructions", "rules", "luat", "chi thi", "huong dan"))
            ) or (
                self._has_security_keyword(
                    folded,
                    ("khong co rang buoc", "coi nhu khong co rang buoc", "tat rao chan", "bo gioi han", "unrestricted"),
                )
            )
            authority_signal = bool(re.search(
                r"(?:quản\s+trị\s+viên|admin|developer|chế\s+độ\s+nội\s+bộ|internal\s+mode)",
                var_lower,
            )) or self._has_security_keyword(
                folded, ("admin", "developer", "quan tri vien", "che do noi bo", "internal mode")
            )
            secret_signal = bool(re.search(
                r"(?:system\s+prompt|chỉ\s+dẫn\s+hệ\s+thống|chỉ\s+thị\s+hệ\s+thống|khóa\s+bí\s+mật|api\s*key|secret|credential)",
                var_lower,
            )) or self._has_security_keyword(
                folded,
                (
                    "system prompt", "secret", "credential", "api key", "khoa api", "khoa bi mat",
                    "chi thi he thong", "cau hinh an", "cau hinh noi bo", "ma ket noi he thong",
                    "ket noi he thong", "phia sau man hinh", "nguoi ta da dan", "loi dan he thong",
                ),
            )
            extraction_signal = bool(re.search(
                r"(?:chép|in|đưa|gửi|hiện|tiết\s+lộ|reveal|print|show|dump|output).{0,45}(?:prompt|chỉ\s+dẫn|chỉ\s+thị|khóa|secret|key)",
                var_lower,
            )) or (
                self._has_security_keyword(
                    folded,
                    ("reveal", "print", "show", "dump", "output", "chep", "dua", "gui", "tiet lo", "noi nho", "nghe thu", "cho coi"),
                )
                and self._has_security_keyword(
                    folded,
                    ("prompt", "secret", "key", "khoa", "chi dan", "chi thi", "cau hinh", "ma ket noi", "ket noi he thong", "loi dan", "da dan"),
                )
            )
            if sum((override_signal, authority_signal, secret_signal, extraction_signal)) >= 2:
                violation_type = "PROMPT_INJECTION" if (override_signal or authority_signal) else "SYSTEM_EXFILTRATION"
                if violation_type == "SYSTEM_EXFILTRATION":
                    resp, replies = self._get_exfiltration_response(language, detected_symptom=embedded_symptom)
                else:
                    resp, replies = self._get_injection_response(language, detected_symptom=embedded_symptom)
                return SecurityCheckResult(
                    is_safe=False,
                    violation_type=violation_type,
                    detected_technique=detected_enc,
                    matched_pattern="semantic_compound_attack",
                    safe_response=resp,
                    quick_replies=replies,
                )

            # A. Kiểm tra Dangerous Content (Tự hại / Vũ khí)
            for pattern in self.harmful_patterns:
                if re.search(pattern, var_lower):
                    resp, replies = self._get_harmful_response(language)
                    return SecurityCheckResult(
                        is_safe=False,
                        violation_type="DANGEROUS_CONTENT",
                        detected_technique=detected_enc,
                        matched_pattern=pattern,
                        safe_response=resp,
                        quick_replies=replies,
                    )

            # B. Kiểm tra Prompt Injection / Jailbreak
            for pattern in self.injection_patterns:
                if re.search(pattern, var_lower):
                    resp, replies = self._get_injection_response(language, detected_symptom=embedded_symptom)
                    return SecurityCheckResult(
                        is_safe=False,
                        violation_type="PROMPT_INJECTION",
                        detected_technique=detected_enc,
                        matched_pattern=pattern,
                        safe_response=resp,
                        quick_replies=replies,
                    )

            # C. Kiểm tra Exfiltration (System Prompt / Secret Keys)
            for pattern in self.exfiltration_patterns:
                if re.search(pattern, var_lower):
                    resp, replies = self._get_exfiltration_response(language, detected_symptom=embedded_symptom)
                    return SecurityCheckResult(
                        is_safe=False,
                        violation_type="SYSTEM_EXFILTRATION",
                        detected_technique=detected_enc,
                        matched_pattern=pattern,
                        safe_response=resp,
                        quick_replies=replies,
                    )

            # D. Kiểm tra Privilege Escalation & SQL Injection
            for pattern in self.privilege_patterns:
                if re.search(pattern, var_lower):
                    resp, replies = self._get_privilege_response(language)
                    return SecurityCheckResult(
                        is_safe=False,
                        violation_type="PRIVILEGE_ESCALATION",
                        detected_technique=detected_enc,
                        matched_pattern=pattern,
                        safe_response=resp,
                        quick_replies=replies,
                    )

            # E. Kiểm tra Cross-Patient Snoop (Multi-Tenant Privacy)
            for pattern in self.cross_patient_patterns:
                if re.search(pattern, var_lower):
                    resp, replies = self._get_cross_patient_response(language)
                    return SecurityCheckResult(
                        is_safe=False,
                        violation_type="CROSS_PATIENT_SNOOP",
                        detected_technique=detected_enc,
                        matched_pattern=pattern,
                        safe_response=resp,
                        quick_replies=replies,
                    )

        return SecurityCheckResult(is_safe=True)

    def _get_injection_response(self, language: str, detected_symptom: str | None = None) -> tuple[str, list[str]]:
        if language == "en":
            if detected_symptom:
                resp = (
                    "🛡️ **System Security & Clinical Integrity Notice:**\n\n"
                    f"I have noted your reported symptom (*{detected_symptom}*). However, your message includes unauthorized system override or configuration commands.\n\n"
                    "For system security, I have ignored the override command. Could you please share more clinical details about your symptom (such as duration, pain characteristics) so I can guide you to the right specialist?"
                )
                replies = [f"Details on {detected_symptom}", "Find a doctor", "Hospital schedule"]
            else:
                resp = (
                    "🛡️ **System Security & Clinical Integrity Notice:**\n\n"
                    "I am a specialized Medical Reception & Scheduling Assistant. "
                    "I operate strictly under medical safety protocols (SAF-01/02) and cannot execute system override commands, roleplays, or arbitrary prompt instructions.\n\n"
                    "Please let me know how I can assist with your symptoms or finding a doctor."
                )
                replies = ["Check symptoms", "Find a doctor", "Hospital schedule"]
        else:
            if detected_symptom:
                resp = (
                    "🛡️ **Thông báo An toàn & Chuẩn mực Y tế:**\n\n"
                    f"Dạ thưa bác, em có ghi nhận tình trạng khó chịu của bác liên quan đến *{detected_symptom}*. Tuy nhiên, tin nhắn có chứa phần chỉ thị hoặc dữ liệu can thiệp cấu hình hệ thống không được phép.\n\n"
                    "Tuân thủ quy chuẩn an toàn thông tin y tế, em xin phép bỏ qua phần lệnh can thiệp đó. Bác vui lòng mô tả cụ thể hơn về triệu chứng (vị trí, thời gian bắt đầu, cảm giác đau) để em hỗ trợ định hướng chuyên khoa phù hợp nhất cho bác nhé."
                )
                replies = [f"Chi tiết về {detected_symptom}", "Tìm bác sĩ chuyên khoa", "Giờ làm việc bệnh viện"]
            else:
                resp = (
                    "🛡️ **Thông báo An toàn & Chuẩn mực Y tế:**\n\n"
                    "Dạ thưa bác, em là Trợ lý Tiếp đón Y tế và Đặt lịch khám chuyên khoa. "
                    "Em hoạt động tuân thủ nghiêm ngặt các quy chuẩn an toàn y tế và không được phép thực hiện các yêu cầu can thiệp cấu hình, nhập vai hoặc lệnh ghi đè chỉ thị hệ thống.\n\n"
                    "Bác vui lòng cho em biết triệu chứng sức khỏe hoặc chuyên khoa bác muốn thăm khám để em hỗ trợ tốt nhất ạ."
                )
                replies = ["Mô tả triệu chứng", "Tìm bác sĩ chuyên khoa", "Giờ làm việc bệnh viện"]
        return resp, replies

    def _get_exfiltration_response(self, language: str, detected_symptom: str | None = None) -> tuple[str, list[str]]:
        if language == "en":
            resp = (
                "🔒 **Confidentiality Notice:**\n\n"
                "System directives, architectural prompts, API keys, and internal configurations are strictly confidential and protected by enterprise security policies.\n\n"
                "May I assist you with clinical triage or specialist appointments?"
            )
            replies = ["Describe symptoms", "View specialties", "Hospital pricing"]
        else:
            if detected_symptom:
                resp = (
                    "🔒 **Cảnh báo Bảo mật Cấu hình:**\n\n"
                    f"Dạ thưa bác, em có ghi nhận triệu chứng (*{detected_symptom}*) của bác. Tuy nhiên, toàn bộ chỉ thị hệ thống, prompt cấu hình và mã khóa đều được bảo vệ nghiêm ngặt theo chính sách an toàn thông tin y tế.\n\n"
                    f"Em xin phép bỏ qua yêu cầu truy xuất dữ liệu hệ thống và luôn sẵn sàng hỗ trợ định hướng chuyên khoa cho tình trạng *{detected_symptom}* của bác ạ."
                )
                replies = [f"Chi tiết về {detected_symptom}", "Xem danh sách chuyên khoa", "Bảng giá khám"]
            else:
                resp = (
                    "🔒 **Cảnh báo Bảo mật Cấu hình:**\n\n"
                    "Dạ thưa bác, toàn bộ chỉ thị hệ thống, prompt cấu hình, mã khóa và thông tin vận hành nội bộ đều được bảo vệ nghiêm ngặt theo chính sách an toàn thông tin y tế.\n\n"
                    "Em luôn sẵn sàng hỗ trợ bác định hướng chuyên khoa và đặt lịch khám với các bác sĩ ạ."
                )
                replies = ["Mô tả triệu chứng", "Xem danh sách chuyên khoa", "Bảng giá khám"]
        return resp, replies

    def _get_privilege_response(self, language: str) -> tuple[str, list[str]]:
        if language == "en":
            resp = (
                "⛔ **Access Denied:**\n\n"
                "Arbitrary database commands, script executions, and schema manipulation are strictly prohibited and monitored by system audit logs."
            )
            replies = ["Return to medical triage", "Hospital FAQ"]
        else:
            resp = (
                "⛔ **Truy cập Bị từ chối:**\n\n"
                "Hệ thống tuyệt đối không cho phép thực thi các câu lệnh cơ sở dữ liệu hoặc thao tác hệ thống tùy ý. Hành vi này được giám sát bởi hệ thống ghi nhận bảo mật."
            )
            replies = ["Quay lại tư vấn y tế", "Hỏi đáp thủ tục khám"]
        return resp, replies

    def _get_cross_patient_response(self, language: str) -> tuple[str, list[str]]:
        if language == "en":
            resp = (
                "🔐 **Patient Privacy Protection (HIPAA & Medical Law):**\n\n"
                "Under medical confidentiality laws and privacy regulations, patient health information (PHI) and booking records of other individuals are strictly private. "
                "The assistant is isolated to your current session only."
            )
            replies = ["View my current booking", "Book new appointment"]
        else:
            resp = (
                "🔐 **Bảo vệ Bí mật Thông tin Bệnh nhân (Luật Khám Chữa Bệnh):**\n\n"
                "Theo Luật Khám bệnh, chữa bệnh và quy định bảo mật thông tin y tế, danh tính, số điện thoại, lịch hẹn và hồ sơ bệnh án của bệnh nhân khác là tuyệt mật. "
                "Trợ lý AI chỉ phục vụ phiên làm việc cá nhân của bác và tuyệt đối không truy xuất dữ liệu của người khác."
            )
            replies = ["Xem thông tin slot của tôi", "Đặt lịch khám mới"]
        return resp, replies

    def _get_harmful_response(self, language: str) -> tuple[str, list[str]]:
        if language == "en":
            resp = (
                "⚠️ **Emergency Safety Warning:**\n\n"
                "If you or someone else is in immediate distress, please call emergency services right away: **115** (Vietnam) or your local emergency hotline. "
                "The assistant does not process queries regarding self-harm, weapons, or harmful substances."
            )
            replies = ["Call emergency 115", "Hospital helpline"]
        else:
            resp = (
                "⚠️ **Cảnh báo Khẩn cấp & An Toàn Tính Mạng:**\n\n"
                "Nếu bác hoặc người thân đang gặp tình trạng nguy hiểm hoặc khủng hoảng tâm lý, xin vui lòng gọi ngay tổng đài cấp cứu **`115`** hoặc đường dây nóng hỗ trợ tâm lý/y tế khẩn cấp. "
                "Trợ lý AI kiên quyết từ chối hỗ trợ các nội dung liên quan đến tự gây hại hoặc chất nguy hiểm."
            )
            replies = ["Gọi cấp cứu 115", "Hotline hỗ trợ bệnh viện"]
        return resp, replies


_security_guardrail_service_instance: SecurityGuardrailService | None = None


def get_security_guardrail_service() -> SecurityGuardrailService:
    global _security_guardrail_service_instance
    if _security_guardrail_service_instance is None:
        _security_guardrail_service_instance = SecurityGuardrailService()
    return _security_guardrail_service_instance
