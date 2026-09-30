"""
Clinical Triage Engine (Node trong LangGraph)
Thực thi phân cấp triệu chứng và kiểm soát cửa sổ đặt lịch:
- Quét Red Flags / Cấp cứu ATS Level 1/2
- Đối chiếu ma trận hội chứng tổ hợp
- Tra cứu mặt bệnh gần nhất và triệu chứng phân tầng
- Quyết định số ngày tối đa cho phép đặt lịch (max_booking_days)
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.medical_assistant.domain.disease_triage import (
    ATSLevel,
    UrgencyTier,
    TriageEvaluationResult,
    TriageSpecialtyCandidate,
    DiseaseTriageRecord,
)
from src.medical_assistant.domain.specialty_router import get_specialty_router
from src.medical_assistant.domain.language_service import (
    canonicalize_specialty_code,
    detect_language,
    get_specialty_display_name,
    get_emergency_guidance,
    get_triage_guidance,
)
from src.medical_assistant.domain.clinical_negation_service import get_clinical_negation_service

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
TRIAGED_DISEASES_PATH = ROOT_DIR / "data" / "datalake" / "normalized" / "diseases_triaged.jsonl"


class ClinicalTriageService:
    PRIMARY_ROUTING_THRESHOLD = 0.65
    SECONDARY_ROUTING_THRESHOLD = 0.60
    SECONDARY_TO_PRIMARY_RATIO = 0.75
    CLARIFICATION_THRESHOLD = 0.45
    MAX_PUBLIC_SPECIALTIES = 2
    URGENT_RULE_SPECIALTIES = {
        "UNDIFFERENTIATED_CHEST_DISCOMFORT": "TIM_MACH",
        "HEADACHE_WITH_VISUAL_CHANGE": "THAN_KINH",
        "HEMOPTYSIS_WARNING": "HO_HAP",
        "ACUTE_APPENDICITIS_SUSPECT": "TIEU_HOA",
        "MELENA_SUBACUTE": "TIEU_HOA",
    }
    COMPLAINT_ROUTES = {
        "headache": ("THAN_KINH", "Thần kinh", ["onset", "severity", "vision_changes", "numbness_weakness"]),
        "abdominal_pain": ("TIEU_HOA", "Tiêu hóa - Gan mật", ["location", "severity", "vomiting", "fever", "blood_in_stool"]),
        "constipation": ("TIEU_HOA", "Tiêu hóa - Gan mật", ["duration", "blood_in_stool", "weight_loss", "vomiting"]),
        "sore_throat": ("TAI_MUI_HONG", "Tai - Mũi - Họng", ["duration", "fever", "shortness_of_breath"]),
        "chest_pain": ("TIM_MACH", "Trung tâm Tim mạch", ["onset", "severity", "shortness_of_breath", "radiation"]),
        "shortness_of_breath": ("HO_HAP", "Nội hô hấp", ["onset", "severity", "chest_pain", "cyanosis"]),
        "cough": ("HO_HAP", "Nội hô hấp", ["duration", "fever", "shortness_of_breath"]),
        "back_pain": ("XUONG_KHOP", "Chấn thương chỉnh hình - Y học thể thao", ["severity", "trauma", "numbness_weakness"]),
        "joint_pain": ("XUONG_KHOP", "Chấn thương chỉnh hình - Y học thể thao", ["severity", "trauma", "fever"]),
        "neck_shoulder_pain": ("XUONG_KHOP", "Chấn thương chỉnh hình - Y học thể thao", ["severity", "trauma", "numbness_weakness"]),
        "fever": ("TONG_QUAT", "Nội tổng quát", ["duration", "temperature", "rash", "shortness_of_breath"]),
    }
    def __init__(self):
        self.diseases: Dict[str, DiseaseTriageRecord] = {}
        self.red_flag_rules: List[tuple[re.Pattern, str]] = []
        self._load_triaged_knowledge_base()
        self._build_fast_rules()

    def _load_triaged_knowledge_base(self):
        # 1. Thử nạp từ Supabase cloud database
        try:
            from src.medical_assistant.db.supabase_client import get_supabase_client
            client = get_supabase_client()
            rows = client.select("disease_triage", params={"limit": 1000})
            if rows and len(rows) > 0:
                for r in rows:
                    rec = DiseaseTriageRecord(
                        disease_key=r["disease_key"],
                        name=r["name"],
                        primary_specialty_code=r.get("primary_specialty_code") or "NOI_KHOA",
                        primary_specialty_name=r.get("primary_specialty_name") or "Nội khoa",
                        acuity={
                            "ats_level": r["ats_level"],
                            "urgency_tier": r["urgency_tier"],
                            "max_booking_days": r["max_booking_days"],
                            "action_directive": r.get("action_directive") or "",
                        },
                        symptom_hierarchy={
                            "red_flags": r.get("red_flags") or [],
                            "warning_signs": r.get("warning_signs") or [],
                            "typical_or_mild": r.get("typical_or_mild") or [],
                        },
                        syndrome_combinations=r.get("syndrome_combinations") or [],
                        probing_questions=r.get("probing_questions") or [],
                    )
                    self.diseases[rec.disease_key] = rec
                return
        except Exception:
            pass

        # 2. Fallback sang file cục bộ nếu offline
        if not TRIAGED_DISEASES_PATH.exists():
            return
        with open(TRIAGED_DISEASES_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    record = DiseaseTriageRecord(**data)
                    self.diseases[record.disease_key] = record

    def _build_fast_rules(self):
        """
        Khởi tạo Bộ quy tắc An toàn 3 Tầng (Safety Engine v3):
        Tầng 1: Hard Red Flags (Tối khẩn cấp Level 1 Resuscitation)
        Tầng 2: Syndrome Combination Rules (Hội chứng tổ hợp đa hệ thống Level 1/2)
        Tầng 3: Warning Signs (Bán khẩn cấp Level 3 - Khám cùng ngày)
        """
        # TẦNG 1: Hard Red Flags (Level 1 Resuscitation)
        raw_hard_red_flags = [
            (
                "CARDIAC_ARREST_UNRESPONSIVE",
                r"ngừng tim|ngừng thở|bất tỉnh|hôn mê|ngất xỉu.*mất ý thức|cardiac arrest|unconscious|coma|stopped breathing|loss of consciousness|passed out.*unresponsive",
                "Trung tâm Tim mạch",
                "Ngừng tuần hoàn / Hôn mê sâu"
            ),
            (
                "STEMI_ACS_CRUSHING",
                r"(?:đau\s+)?(?:thắt\s+ngực|ngực|vùng\s+ngực).*?(?:bóp\s+nghẹt|đè\s+nén|đè\s+ép|dữ\s+dội|lan|kéo\s+dài)|(?:ngực|vùng\s+ngực).*?(?:bị\s+)?(?:bóp\s+nghẹt|đè\s+nén|đè\s+ép|dữ\s+dội)|(?:ngực|vùng\s+ngực).*?(?:lan\s+(?:lên|ra)?\s*(?:hàm|vai|tay\s+trái|cánh\s+tay|lưng))|(?:severe|crushing|squeezing|radiating|sharp)\s+chest\s+pain|chest\s+pain.*?(?:sweat|left\s+arm|jaw)|myocardial\s+infarction|heart\s+attack",
                "Trung tâm Tim mạch",
                "Nghi ngờ Nhồi máu cơ tim / Hội chứng vành cấp"
            ),
            (
                "STROKE_FAST",
                r"méo miệng|yếu liệt|liệt nửa người|nói đớ|nói khó|facial droop|slurred speech|arm weakness|hemiplegia|stroke|fast sign",
                "Thần kinh",
                "Dấu hiệu FAST nghi ngờ Đột quỵ não"
            ),
            (
                "RESPIRATORY_FAILURE_APNEA",
                r"ngưng thở|tím tái|môi tím|đầu chi tím|thở ngáp|thở không ra hơi|không thở được|thở dốc.*?lả đi|lả đi.*?thở|nói không thành câu|người lả đi|cyanosis|apnea|stopped breathing|cannot breathe|struggling to breathe",
                "Nội hô hấp",
                "Suy hô hấp cấp tính tối khẩn"
            ),
            (
                "MASSIVE_GI_BLEEDING",
                r"nôn ra máu|tiêu ra máu ồ ạt|vomiting blood|hematemesis|(phân đen|black tarry stool|melena).*(ngất|tụt huyết áp|sốc|bất tỉnh|mất ý thức|faint|collapse|unconscious|shock)",
                "Tiêu hóa - Gan mật",
                "Xuất huyết tiêu hóa cấp"
            ),
            (
                "ACUTE_ABDOMEN_RIGID",
                r"bụng (gồng cứng|như gỗ|đau dữ dội)|(rigid|board-like|severe)\s+abdominal\s+pain|acute abdomen|rebound tenderness",
                "Tiêu hóa - Gan mật",
                "Nghi ngờ Bụng ngoại khoa (thủng tạng, viêm ruột thừa vỡ)"
            ),
            (
                "STATUS_EPILEPTICUS",
                r"co giật (liên tục|kéo dài)|(continuous|prolonged)\s+seizures|status epilepticus",
                "Thần kinh",
                "Cơn co giật động kinh liên tục"
            ),
            (
                "ACUTE_TOXIC_OVERDOSE",
                r"uống (nhầm|phải)?.*(thuốc (sâu|diệt chuột|chuột|độc|quá liều)|hóa chất)|tự tử|poison|overdose|ingested (chemicals|pesticide)|suicid",
                "Cấp cứu",
                "Ngộ độc cấp tính tối khẩn"
            ),
            (
                "ECTOPIC_PREGNANCY_RUPTURE",
                r"(?:trễ kinh|chậm kinh|hai vạch|que thử).*?(?:đau bụng|dữ dội|ra máu|choáng|muốn ngất)|missed period.*(severe abdominal pain|bleeding)",
                "Sản phụ khoa",
                "Nghi ngờ Thai ngoài tử cung vỡ / Biến chứng thai nghén cấp"
            ),
            (
                "CAUDA_EQUINA_SYNDROME",
                r"đau lưng.*?(?:chân yếu|yếu chân|tê.*?vùng kín|không nhịn tiểu|bí tiểu|mất tự chủ tiểu)|cauda equina|saddle anesthesia",
                "Cấp cứu",
                "Dấu hiệu cảnh báo Hội chứng Chùm đuôi ngựa cấp"
            ),
            (
                "PEDIATRIC_EMERGENCY_LETHARGY",
                r"(?:bé|trẻ|em bé).*?(?:sốt|nóng).*?(?:li bì|gọi khó tỉnh|thở nhanh|bỏ bú|tím tái)|lethargic.*fever|unresponsive child",
                "Nhi khoa",
                "Cấp cứu Nhi khoa: Sốt cao kèm tri giác li bì / dấu hiệu nguy kịch"
            ),
            (
                "SUICIDAL_SELF_HARM_CRISIS",
                r"(?:nghĩ|muốn)\s+(?:biến mất|chết|kết thúc cuộc sống|tự tử).*?(?:thuốc|ở một mình)|suicid|kill myself|end my life|self-harm",
                "Cấp cứu",
                "Khủng hoảng tâm lý / Nguy cơ tự hại cấp tính"
            ),
            (
                "ANAPHYLAXIS_AIRWAY_EMERGENCY",
                r"(?:sưng|phù|sưng lên|sưng vù)\s+(?:môi|lưỡi|mặt)|(?:môi|lưỡi|mặt).*?(?:sưng|phù).*?(?:thở rít|choáng|tụt huyết áp|nghẹt thở|mề đay|mày đay)|(?:thở rít|khó thở).*?(?:môi|lưỡi).*?(?:sưng|phù)|(?:hải sản|thức ăn|ăn xong|dị ứng).*?(?:sưng|phù|mề đay).*?(?:thở rít|khó thở|choáng|ngất)|anaphylaxis.*(lip swelling|stridor|shock)",
                "Cấp cứu",
                "Phản vệ nguy kịch đường thở"
            )
        ]
        self.hard_red_flags = [(rid, re.compile(pat, re.IGNORECASE), spec, name) for rid, pat, spec, name in raw_hard_red_flags]
        # Giữ tương thích ngược với thuộc tính cũ
        self.red_flag_rules = [(pat, spec, name) for _, pat, spec, name in self.hard_red_flags]

        # TẦNG 2: Syndrome Combination Rules (Cấu trúc lâm sàng đa triệu chứng bắt buộc)
        self.syndrome_rules = [
            {
                "rule_id": "ANAPHYLAXIS_ACUTE",
                "name": "Phản vệ cấp tính / Sốc phản vệ",
                "required_groups": [
                    ["nổi ban", "mẩn ngứa", "mày đay", "sưng phù", "phù mặt", "sưng môi", "urticaria", "rash", "swelling", "hives", "angioedema", "đỏ bừng mặt", "flushing"],
                    ["khó thở", "thở khò khè", "thở rít", "nghẹt thở", "tụt huyết áp", "ngất", "shortness of breath", "dyspnea", "wheeze", "stridor", "hypotension", "faint"]
                ],
                "negative_factors": ["không khó thở", "không ngứa", "không phát ban", "sốt", "fever", "ho có đờm đặc", "cổ chân", "cổ tay", "khớp vai", "khớp gối", "joint pain", "arthritis", "viêm khớp"],
                "ats_level": ATSLevel.LEVEL_1_RESUSCITATION,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Miễn dịch - Dị ứng"
            },
            {
                "rule_id": "PNEUMOTHORAX_ACUTE",
                "name": "Nghi ngờ Tràn khí màng phổi tự phát",
                "required_groups": [
                    ["đau ở vùng ngực", "đau ngực", "mạn sườn ngực", "ngực dưới", "ngực trên", "chest pain", "side of the chest"],
                    ["dữ dội dữ tợn", "nhói buốt thắt lòng", "violent", "heartbreaking"],
                    ["vú phải", "vú trái", "khó thở", "hụt hơi", "đau ngực tăng lên khi hít thở sâu", "dyspnea", "shortness of breath"]
                ],
                "negative_factors": ["không đau ngực", "không đau", "ợ chua", "trào ngược", "acid reflux", "nóng rát từ dạ dày", "ho từng cơn"],
                "ats_level": ATSLevel.LEVEL_1_RESUSCITATION,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Nội hô hấp"
            },
            {
                "rule_id": "BOERHAAVE_ACUTE",
                "name": "Hội chứng Boerhaave / Thủng thực quản tự phát",
                "required_groups": [
                    ["vùng ngực", "thượng vị", "ngực dưới", "ngực trên", "epigastric", "lower chest", "chest"],
                    ["dữ dội", "nhói buốt", "dao đâm", "thắt lòng", "violent", "knife stroke", "heartbreaking"],
                    ["buồn nôn", "nôn", "nôn nhiều lần", "nôn mửa", "cột sống ngực", "bả vai", "nausea", "vomit", "scapula", "thoracic"]
                ],
                "negative_factors": ["không đau ngực", "không đau", "ợ chua", "trào ngược", "acid reflux", "nóng rát từ dạ dày"],
                "ats_level": ATSLevel.LEVEL_1_RESUSCITATION,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Tiêu hóa - Gan mật"
            },
            {
                "rule_id": "EPIGLOTTITIS_ACUTE",
                "name": "Viêm nắp thanh quản cấp / Nguy cơ tắc nghẽn đường thở",
                "required_groups": [
                    ["khó nuốt", "nuốt vướng", "nuốt đau", "chảy nước dãi", "dysphagia", "drooling"],
                    ["khó thở", "hụt hơi", "thở rít", "thở rít khi hít vào", "stridor", "shortness of breath", "dyspnea"],
                    ["sốt", "nhói như dao đâm", "fever", "amidan", "họng", "cổ bên", "dưới hàm"]
                ],
                "negative_factors": ["không khó thở", "không đau họng"],
                "ats_level": ATSLevel.LEVEL_1_RESUSCITATION,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Tai - Mũi - Họng"
            },
            {
                "rule_id": "LARYNGOSPASM_ACUTE",
                "name": "Co thắt thanh quản cấp / Thở rít thanh quản",
                "required_groups": [
                    ["thở rít khi hít vào", "thở rít thanh quản", "co thắt thanh quản", "high pitched sound when breathing in", "laryngospasm", "ho ông ổng"]
                ],
                "negative_factors": ["không khó thở"],
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Nội hô hấp"
            },
            {
                "rule_id": "PSVT_ARRHYTHMIA_ACUTE",
                "name": "Cơn nhịp nhanh kịch phát trên thất / Rối loạn nhịp cấp",
                "required_groups": [
                    ["tim đập nhanh", "hồi hộp đánh trống ngực", "nhịp tim nhanh", "tim loạn nhịp", "palpitation", "heart racing", "fast pounding heartbeat", "tachycardia"],
                    ["chóng mặt", "xây xẩm", "sắp ngất", "choáng váng", "dizzy", "lightheaded", "about to faint", "presyncope"]
                ],
                "negative_factors": ["không hồi hộp", "không chóng mặt", "hoảng loạn", "sợ chết", "panic", "fear"],
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Trung tâm Tim mạch"
            },
            {
                "rule_id": "ACUTE_PULMONARY_EDEMA",
                "name": "Phù phổi cấp / Suy tim trái cấp tính",
                "required_groups": [
                    ["khó thở", "hụt hơi", "nằm xuống khó thở tăng", "dyspnea", "shortness of breath", "orthopnea"],
                    ["vã mồ hôi", "vã mồ hôi nhiều", "đờm hồng", "sweating", "frothy sputum"],
                    ["sưng phù", "vùng ngực", "ngực trên", "cổ chân", "swelling", "edema", "chest"]
                ],
                "negative_factors": ["không khó thở"],
                "ats_level": ATSLevel.LEVEL_1_RESUSCITATION,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Trung tâm Tim mạch"
            },
            {
                "rule_id": "COPD_ASTHMA_EXACERBATION",
                "name": "Đợt cấp COPD / Hen phế quản co thắt cấp",
                "required_groups": [
                    ["thở khò khè thở rít", "thở khò khè", "khò khè", "wheezing", "wheez", "acute bronchospasm"],
                    ["ho có đờm đặc", "khó thở, hụt hơi", "khó thở", "colored sputum", "abundant sputum", "severe dyspnea", "thở rít"]
                ],
                "negative_factors": ["không khó thở", "persistent cough, wheezing and shortness of breath for 4 days", "ngạt mũi", "chảy nước mũi", "runny nose", "tính chất nóng rát", "nóng rát sau xương ức"],
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Nội hô hấp"
            },
            {
                "rule_id": "SCOMBROID_POISONING_ACUTE",
                "name": "Ngộ độc thực phẩm Scombroid / Dị ứng Histamine cấp",
                "required_groups": [
                    ["đỏ bừng mặt", "facial flushing", "flushing", "scombroid", "cá ngừ", "hải sản"],
                    ["buồn nôn", "nôn", "tim đập nhanh", "đau đầu", "nausea", "vomiting", "palpitations"]
                ],
                "negative_factors": ["không ngứa", "không buồn nôn", "sốt", "fever", "đau rát họng", "sore throat", "đau mỏi cơ", "myalgia"],
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Truyền nhiễm"
            },
            {
                "rule_id": "ACUTE_DYSTONIA",
                "name": "Phản ứng loạn trương lực cấp tính / Hội chứng ngoại tháp",
                "required_groups": [
                    ["co thắt cơ", "co rút cơ lưỡi", "khó khép miệng", "sụp mí mắt", "spasm of tongue", "facial spasm", "acute dyston", "oculogyric", "tongue protrusion"]
                ],
                "negative_factors": [],
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Thần kinh"
            },
            {
                "rule_id": "ACUTE_PANCREATITIS_CHOLECYSTITIS",
                "name": "Nghi ngờ Viêm tụy cấp / Viêm túi mật cấp",
                "required_groups": [
                    ["đau quặn bụng dữ dội", "đau bụng dữ dội", "đau hạ sườn phải", "đau thượng vị", "severe abdominal pain", "right upper quadrant pain", "epigastric pain"],
                    ["xuyên ra sau lưng", "sốt cao", "vàng da", "nôn nhiều", "nôn liên tục", "back", "jaundice", "high fever", "continuous vomiting"]
                ],
                "negative_factors": ["không đau bụng"],
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Tiêu hóa - Gan mật"
            },
            {
                "rule_id": "PERICARDITIS_ACUTE",
                "name": "Viêm màng ngoài tim cấp",
                "required_groups": [
                    ["đau ngực", "chest pain"],
                    ["đỡ khi ngồi cúi", "tăng khi hít sâu", "sitting forward", "pericarditis", "hít thở sâu"]
                ],
                "negative_factors": ["không đau ngực", "ho từng cơn", "đờm đặc", "ho có đờm", "đờm mủ"],
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Trung tâm Tim mạch"
            },
            {
                "rule_id": "ATRIAL_FIBRILLATION_ACUTE",
                "name": "Rung nhĩ cấp / Loạn nhịp tim cấp tính",
                "required_groups": [
                    ["tim loạn nhịp", "nhịp tim không đều", "loạn nhịp tim", "atrial fibrillation", "irregular heartbeat", "irregularly"]
                ],
                "negative_factors": ["không loạn nhịp"],
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Trung tâm Tim mạch"
            },
            {
                "rule_id": "MYOCARDITIS_ACUTE",
                "name": "Nghi ngờ Viêm cơ tim cấp / Hội chứng vành",
                "required_groups": [
                    ["nhói như dao đâm", "dao đâm", "knife stroke", "dữ dội", "nằm xuống khó thở tăng", "phải ngồi dậy"],
                    ["khó thở", "hụt hơi", "dyspnea", "shortness of breath"],
                    ["tim đập nhanh", "hồi hộp đánh trống ngực", "nhịp tim nhanh", "palpitation", "tachycardia"]
                ],
                "negative_factors": ["không khó thở", "không đau ngực", "hoảng loạn", "sợ chết", "panic", "fear", "nhói buốt", "tính chất nhói buốt"],
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Trung tâm Tim mạch"
            },
            {
                "rule_id": "ACS_RADIATION_ACUTE",
                "name": "Hội chứng mạch vành cấp có hướng lan điển hình",
                "required_groups": [
                    ["vùng ngực", "đau ở vùng ngực", "mạn sườn ngực", "ngực trên", "ngực dưới", "vùng thượng vị", "chest pain", "epigastric"],
                    ["bắp tay", "khớp vai", "sụn giáp cổ", "cánh tay", "cột sống ngực", "shoulder", "arm", "neck", "jaw"],
                    ["vã mồ hôi", "buồn nôn", "nôn", "sweat", "diaphoresis", "nausea", "vomit", "dữ dội", "bóp nghẹt", "đè nặng"]
                ],
                "negative_factors": ["không đau ngực", "đau kiệt sức"],
                "ats_level": ATSLevel.LEVEL_1_RESUSCITATION,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Trung tâm Tim mạch"
            },
            {
                "rule_id": "GUILLAIN_BARRE_ACUTE",
                "name": "Hội chứng Guillain-Barré / Liệt cơ hô hấp cấp",
                "required_groups": [
                    ["yếu liệt", "liệt nửa mặt", "yếu liệt tay chân", "weakness in both arms", "paralysis"],
                    ["khó thở", "hụt hơi", "shortness of breath", "dyspnea"]
                ],
                "negative_factors": ["không khó thở"],
                "ats_level": ATSLevel.LEVEL_1_RESUSCITATION,
                "care_setting": "EMERGENCY_DEPT",
                "default_specialty": "Thần kinh"
            }
        ]
        # Giữ tương thích ngược với thuộc tính ats2_rules
        self.ats2_rules = []
        for sr in self.syndrome_rules:
            if sr["ats_level"] == ATSLevel.LEVEL_2_EMERGENT:
                flat_pat = "|".join([re.escape(term) for grp in sr["required_groups"] for term in grp])
                try:
                    self.ats2_rules.append((re.compile(flat_pat, re.IGNORECASE), sr["default_specialty"], sr["name"]))
                except Exception:
                    pass

        # TẦNG 3: Warning Signs (Khám trong ngày - Level 3)
        raw_warning_rules = [
            (
                "UNDIFFERENTIATED_CHEST_DISCOMFORT",
                r"đau\s+(?:tức|thắt|nặng|đè)\s+(?:lồng\s+|vùng\s+)?ngực|"
                r"(?:đau|tức|thắt|nặng|đè)\s+(?:lồng\s+|vùng\s+)?ngực|"
                r"chest\s+(?:pain|tightness|pressure|heaviness|discomfort)",
                "Trung tâm Tim mạch",
                "Đau hoặc tức ngực mới chưa loại trừ nguyên nhân tim phổi"
            ),
            (
                "HEADACHE_WITH_VISUAL_CHANGE",
                r"(?:đau đầu|nhức đầu|đau nửa đầu|headache|migraine).*?"
                r"(?:nhìn mờ|nhìn đôi|mất thị lực|blurred vision|double vision|vision loss)|"
                r"(?:nhìn mờ|nhìn đôi|mất thị lực|blurred vision|double vision|vision loss).*?"
                r"(?:đau đầu|nhức đầu|đau nửa đầu|headache|migraine)",
                "Thần kinh",
                "Đau đầu kèm thay đổi thị giác cần đánh giá trực tiếp trong ngày"
            ),
            (
                "RENAL_COLIC",
                r"đau quặn thận|tiểu buốt.*ra máu|tiểu ra máu|renal colic|severe flank pain|blood in urine|hematuria|(?:hông|mạn sườn).*?(?:đau quặn|lan xuống bẹn)",
                "Thận - Tiết niệu",
                "Nghi ngờ Cơn đau quặn thận / Sỏi tiết niệu cấp"
            ),
            (
                "HEMOPTYSIS_WARNING",
                r"ho (?:khạc )?(?:ra )?máu|đờm (?:có )?(?:vệt )?máu|vệt máu đỏ|hemoptysis|coughing blood|blood-streaked sputum",
                "Nội hô hấp",
                "Dấu hiệu cảnh báo: Ho ra máu / Đờm có vệt máu"
            ),
            (
                "MENORRHAGIA_SEVERE",
                r"rong kinh|ra máu nhiều.*?(?:thay băng|mệt lả|chóng mặt)|menorrhagia|heavy menstrual bleeding",
                "Sản phụ khoa",
                "Xuất huyết phụ khoa nặng / Rong kinh kèm thiếu máu"
            ),
            (
                "ACUTE_HIGH_FEVER",
                r"sốt cao.*(39|40|liên tục).*nghi.*sốt xuất huyết|high fever.*(39|40|dengue)",
                "Truyền nhiễm / Nhi",
                "Sốt cao cấp tính theo dõi Sốt xuất huyết"
            ),
            (
                "ACUTE_APPENDICITIS_SUSPECT",
                r"đau hố chậu phải|đau ruột thừa|right lower quadrant pain|appendicitis|(?:quanh rốn|dưới rốn).*?(?:chạy xuống|lan xuống|xuống dưới).*?(?:bên phải|dưới|hố chậu)|(?:đau bụng bên phải phía dưới|đau bụng phía dưới bên phải|đau bụng bên phải).*?(?:quanh rốn|đi lại|sốt nhẹ)|(?:ban đầu đau quanh rốn).*?(?:chạy xuống|xuống dưới)",
                "Tiêu hóa - Gan mật",
                "Theo dõi Bụng ngoại khoa / Đau bụng cần khám trực tiếp trong ngày"
            ),
            (
                "MELENA_SUBACUTE",
                r"phân đen|black tarry stool|melena",
                "Tiêu hóa - Gan mật",
                "Theo dõi Xuất huyết tiêu hóa bán cấp"
            )
        ]
        self.warning_rules = [
            (rule_id, re.compile(pattern, re.IGNORECASE), specialty, name)
            for rule_id, pattern, specialty, name in raw_warning_rules
        ]

    def _check_acs_combination(self, user_text: str, clean_user_text: str, negation_svc) -> Optional[Dict[str, Any]]:
        """
        Tầng A — Rule An toàn hội chứng vành cấp (Acute Coronary Syndrome - ACS):
        Bắt tổ hợp:
        1. Đau/đè nặng/thắt/tức ngực (Phải ở thể khẳng định, KHÔNG bị phủ định)
        2. Kèm ít nhất 1 dấu hiệu:
           - Lan tay trái, vai, hàm, lưng
           - Vã mồ hôi / mồ hôi lạnh
           - Khó thở / hụt hơi / thở dốc
           - Choáng / chóng mặt / ngất
           - Khởi phát khi gắng sức
        Hoặc tính chất dữ dội/bóp nghẹt đè nén.
        """
        chest_signals = [
            "đau ngực", "thắt ngực", "tức ngực", "đè nặng ngực", "bóp nghẹt ngực",
            "nặng ngực", "đè ép ngực", "ngực bị bóp", "ngực bị bóp nghẹt", "ngực tôi bị bóp nghẹt",
            "ngực bóp nghẹt", "đau vùng ngực", "đau sau xương ức",
            "đau tức lồng ngực", "đau tức ngực", "tức lồng ngực", "nặng lồng ngực",
            "chest pain", "chest tightness", "chest pressure", "chest heaviness",
            "dau nguc", "that nguc", "tuc nguc", "de nang nguc", "bop nghet nguc",
            "nang nguc", "de ep nguc", "dau vung nguc"
        ]

        has_positive_chest = False
        for cs in chest_signals:
            if cs in clean_user_text:
                if not negation_svc.is_phrase_negated(cs, user_text):
                    has_positive_chest = True
                    break

        if not has_positive_chest:
            # Kiểm tra thêm mẫu liên kết: ngực ... (bóp nghẹt | đè ép | đè nén | đau)
            chest_match = re.search(
                r"(?:ngực|vùng ngực|chest).{0,24}?(?:bóp nghẹt|bóp|đè nén|đè ép|đè nặng|thắt|đau)|"
                r"(?:đau|tức|thắt|nặng|đè).{0,16}?(?:lồng ngực|vùng ngực|ngực)",
                clean_user_text,
            )
            if chest_match and not negation_svc.is_phrase_negated(chest_match.group(0), user_text):
                has_positive_chest = True

        if not has_positive_chest:
            return None

        # 2. Hướng lan điển hình (Radiation)
        radiation_signals = [
            "lan tay trái", "lan cánh tay trái", "lan vai", "lan bả vai", "lan hàm",
            "lan cổ", "lan sau lưng", "lan lưng", "radiating to left arm", "radiating to jaw",
            "radiating to back", "radiating to shoulder", "radiat",
            "lan tay trai", "lan canh tay trai", "lan vai", "lan ba vai", "lan ham", "lan co", "lan lung"
        ]
        has_radiation = any(rs in clean_user_text for rs in radiation_signals)

        # 3. Thần kinh thực vật / Vã mồ hôi lạnh
        sweat_signals = [
            "vã mồ hôi", "vã mồ hôi lạnh", "mồ hôi lạnh", "mồ hôi hột", "toát mồ hôi",
            "cold sweat", "diaphoresis", "sweat",
            "va mo hoi", "va mo hoi lanh", "mo hoi lanh", "toat mo hoi"
        ]
        has_sweat = any(ss in clean_user_text for ss in sweat_signals)

        # 4. Khó thở / Hụt hơi
        dyspnea_signals = [
            "khó thở", "hụt hơi", "thở dốc", "nghẹt thở", "shortness of breath", "dyspnea",
            "kho tho", "hut hoi", "tho doc"
        ]
        has_dyspnea = any(ds in clean_user_text for ds in dyspnea_signals)

        # 5. Choáng váng / Chóng mặt / Tiền ngất
        dizzy_signals = [
            "choáng", "chóng mặt", "xây xẩm", "ngất", "muốn xỉu", "dizziness", "presyncope", "syncope",
            "choang", "chong mat", "xay xam", "ngat", "muon xiu"
        ]
        has_dizzy = any(dz in clean_user_text for dz in dizzy_signals)

        # 6. Khởi phát khi gắng sức
        exertion_signals = [
            "gắng sức", "khi chạy", "leo cầu thang", "đi bộ nhanh", "mang vác", "on exertion", "exercise",
            "gang suc", "khi chay", "leo cau thang", "di bo nhanh", "mang vac"
        ]
        has_exertion = any(ex in clean_user_text for ex in exertion_signals)

        # 7. Tính chất đè nén / bóp nghẹt dữ dội
        crushing_signals = [
            "dữ dội", "bóp nghẹt", "đè nén", "đè ép", "như đá đè", "severe", "crushing", "squeezing",
            "du doi", "bop nghet", "de nen", "de ep", "nhu da de"
        ]
        has_crushing = any(cr in clean_user_text for cr in crushing_signals)

        # Đau ngực có khả năng do tim cần đánh giá cấp cứu trong 10 phút (ATS 2).
        # ATS 1 được dành cho ngừng tuần hoàn/hô hấp hoặc bất ổn sinh tồn rõ ràng.
        if has_crushing or (sum([has_radiation, has_sweat, has_dyspnea, has_dizzy, has_exertion]) >= 1):
            return {
                "rule_id": "ACS_COMBINED_CARDIAC_RULE",
                "name": "Nghi ngờ Hội chứng Mạch vành cấp / Nhồi máu cơ tim (ACS)",
                "ats_level": ATSLevel.LEVEL_2_EMERGENT,
            }

        return None

    def evaluate_symptoms(self, user_message: str, language: Optional[str] = None) -> TriageEvaluationResult:
        """
        Đánh giá lâm sàng thông điệp người bệnh qua Kiến trúc An toàn 3 Tầng (Safety Engine v3):
        Tầng 1: Hard Red Flags (ATS Level 1) kết hợp Tầng A ACS
        Tầng 2: Syndrome Combination Rules (ATS Level 1/2)
        Tầng 3: Acuity Reranker / Warning Signs (ATS Level 3)
        Tất cả đều được kiểm soát bởi Clinical Negation Service để tránh Over-triage.
        """
        user_text = user_message.lower().strip()
        lang = language if language in ["vi", "en"] else detect_language(user_message)
        clean_user_text = re.sub(r"[,:;.\(\)\?\!]+", " ", user_text).lower()
        negation_svc = get_clinical_negation_service()

        # Biến trạng thái An toàn
        safety_ats: Optional[ATSLevel] = None
        safety_emergency: bool = False
        safety_rule_ids: List[str] = []
        safety_flags: List[str] = []
        default_safety_specialty: str = "Cấp cứu"

        # =========================================================================
        # 0. TẦNG A: ACS CARDIAC RED FLAG CHECK (Bắt tổ hợp hội chứng vành cấp toàn diện)
        # =========================================================================
        acs_result = self._check_acs_combination(user_text, clean_user_text, negation_svc)
        if acs_result:
            safety_ats = acs_result["ats_level"]
            safety_emergency = True
            safety_rule_ids.append(acs_result["rule_id"])
            safety_flags.append(acs_result["name"])
            default_safety_specialty = "Trung tâm Tim mạch"

        # =========================================================================
        # 1. TẦNG 1: QUÉT HARD RED FLAGS (ATS Level 1 Resuscitation)
        # =========================================================================
        if not safety_emergency:
            for rid, pattern, spec_name, flag_name in self.hard_red_flags:
                match = pattern.search(user_text)
                if match:
                    matched_str = match.group(0)
                    # Kiểm tra xem triệu chứng cờ đỏ có bị phủ định không ("không đau ngực", "không ngất")
                    if negation_svc.is_phrase_negated(matched_str, user_text):
                        continue
                    safety_ats = (
                        ATSLevel.LEVEL_2_EMERGENT
                        if rid in {"STEMI_ACS_CRUSHING", "STROKE_FAST"}
                        else ATSLevel.LEVEL_1_RESUSCITATION
                    )
                    safety_emergency = True
                    safety_rule_ids.append(rid)
                    safety_flags.append(flag_name)
                    default_safety_specialty = spec_name
                    break

        # =========================================================================
        # 2. TẦNG 2: QUÉT SYNDROME COMBINATION RULES (ATS Level 1 / Level 2)
        # =========================================================================
        if not safety_emergency:
            for rule in self.syndrome_rules:
                # Kiểm tra yếu tố phủ định (Negation factors)
                is_negated = any(nf in clean_user_text for nf in rule.get("negative_factors", []))
                if is_negated:
                    continue

                # Kiểm tra tất cả các nhóm triệu chứng bắt buộc (Required groups)
                req_groups = rule["required_groups"]
                all_groups_matched = True
                for grp in req_groups:
                    # Kiểm tra xem có token nào khớp và KHÔNG bị phủ định
                    grp_matched = False
                    for token in grp:
                        if token in clean_user_text and not negation_svc.is_phrase_negated(token, user_text):
                            grp_matched = True
                            break
                    if not grp_matched:
                        all_groups_matched = False
                        break

                if all_groups_matched:
                    rule_ats = rule["ats_level"]
                    rule_id = rule["rule_id"]
                    rule_name = rule["name"]

                    if safety_ats is None or rule_ats.value < safety_ats.value:
                        safety_ats = rule_ats
                        safety_emergency = True
                        safety_rule_ids.append(rule_id)
                        safety_flags.append(rule_name)
                        default_safety_specialty = rule["default_specialty"]

        # =========================================================================
        # 3. TẦNG 3: QUÉT WARNING SIGNS (ATS Level 3 Bán khẩn)
        # =========================================================================
        if not safety_emergency:
            for rule_id, pattern, spec_name, warning_name in self.warning_rules:
                match = pattern.search(user_text)
                if match:
                    matched_str = match.group(0)
                    if negation_svc.is_phrase_negated(matched_str, user_text):
                        continue
                    if safety_ats is None:
                        default_safety_specialty = spec_name
                    safety_ats = ATSLevel.LEVEL_3_URGENT
                    safety_flags.append(warning_name)
                    safety_rule_ids.append(rule_id)

            if safety_ats == ATSLevel.LEVEL_3_URGENT and default_safety_specialty:
                guidance = get_triage_guidance(
                    specialty=default_safety_specialty,
                    ats_level=3,
                    max_days=1,
                    language=lang,
                )
                return TriageEvaluationResult(
                    ats_level=ATSLevel.LEVEL_3_URGENT,
                    urgency_tier=UrgencyTier.SAME_DAY,
                    max_booking_days=1,
                    is_emergency=False,
                    care_setting="OUTPATIENT_CLINIC",
                    triggered_red_flags=safety_flags,
                    triggered_rule_ids=safety_rule_ids,
                    suggested_specialty=default_safety_specialty,
                    clarification_question=None,
                    patient_guidance=guidance,
                )

        # Conservative outpatient anchors for common colloquial complaints.
        # These only apply when no independent safety rule fired; they cannot
        # downgrade a true red flag or an ATS-3 warning-sign match.
        if safety_ats is None:
            has_msk_site = any(term in clean_user_text for term in (
                "cổ vai gáy", "vai gáy", "đau cổ", "mỏi cổ", "đau vai", "đau lưng", "lưng dưới", "thắt lưng", "cột sống",
                "neck pain", "shoulder pain", "back pain", "lower back",
            ))
            has_msk_context = any(term in clean_user_text for term in (
                "ngồi máy tính", "làm văn phòng", "ngồi lâu", "sai tư thế", "mỏi",
                "bê", "bê vác", "mang vác", "vác nặng", "khuân vác", "vật nặng", "nâng", "thùng nước",
                "desk work", "sitting", "posture", "lifting", "carrying", "heavy",
            ))
            has_msk_alarm = any(term in clean_user_text for term in (
                "chấn thương", "té ngã", "tai nạn", "tê lan", "yếu tay", "yếu chân",
                "liệt", "mất cảm giác", "trauma", "fall", "weakness", "paralysis",
            ))
            if has_msk_site and has_msk_context and not has_msk_alarm:
                guidance = get_triage_guidance(
                    specialty="Chấn thương chỉnh hình - Y học thể thao",
                    ats_level=4,
                    max_days=7,
                    language=lang,
                )
                return TriageEvaluationResult(
                    ats_level=ATSLevel.LEVEL_4_STANDARD,
                    urgency_tier=UrgencyTier.WITHIN_WEEK,
                    max_booking_days=7,
                    is_emergency=False,
                    care_setting="OUTPATIENT_CLINIC",
                    triggered_red_flags=[],
                    triggered_rule_ids=[],
                    suggested_specialty="Chấn thương chỉnh hình - Y học thể thao",
                    clarification_question=None,
                    patient_guidance=guidance,
                )

            has_mild_abdominal = (
                any(term in clean_user_text for term in ("bụng", "đau bụg", "abdominal", "stomach"))
                and any(term in clean_user_text for term in ("âm ỉ", "ậm ạch", "buồn nôn", "buòn nôn", "nausea"))
            )
            has_abdominal_alarm = any(
                term in clean_user_text and not negation_svc.is_phrase_negated(term, user_text)
                for term in (
                    "đau dữ dội", "đau quặn", "bụng cứng", "nôn ra máu", "đi ngoài ra máu",
                    "phân đen", "ngất", "sốt cao", "severe", "rigid", "vomiting blood", "melena",
                )
            )
            if has_mild_abdominal and not has_abdominal_alarm:
                guidance = get_triage_guidance(
                    specialty="Tiêu hóa - Gan mật",
                    ats_level=4,
                    max_days=7,
                    language=lang,
                )
                return TriageEvaluationResult(
                    ats_level=ATSLevel.LEVEL_4_STANDARD,
                    urgency_tier=UrgencyTier.WITHIN_WEEK,
                    max_booking_days=7,
                    is_emergency=False,
                    care_setting="OUTPATIENT_CLINIC",
                    triggered_red_flags=[],
                    triggered_rule_ids=[],
                    suggested_specialty="Tiêu hóa - Gan mật",
                    clarification_question=None,
                    patient_guidance=guidance,
                )

            # Khám sức khỏe định kỳ / tổng quát (không có triệu chứng bệnh cấp)
            has_general_checkup = any(term in clean_user_text for term in (
                "khám sức khỏe định kỳ", "kham suc khoe dinh ky", "khám định kỳ", "kham dinh ky",
                "kiểm tra sức khỏe định kỳ", "kiem tra suc khoe dinh ky", "khám tổng quát",
                "kham tong quat", "sức khỏe định kỳ", "suc khoe dinh ky", "general health checkup",
                "periodic health check", "routine checkup",
            ))
            if has_general_checkup and not safety_emergency:
                guidance = get_triage_guidance(
                    specialty="Trung tâm Sức khỏe tổng quát",
                    ats_level=5,
                    max_days=30,
                    language=lang,
                )
                return TriageEvaluationResult(
                    ats_level=ATSLevel.LEVEL_5_NON_URGENT,
                    urgency_tier=UrgencyTier.FLEXIBLE,
                    max_booking_days=30,
                    is_emergency=False,
                    care_setting="OUTPATIENT_CLINIC",
                    triggered_red_flags=[],
                    triggered_rule_ids=[],
                    suggested_specialty="Trung tâm Sức khỏe tổng quát",
                    clarification_question=None,
                    patient_guidance=guidance,
                )

            # Tiết niệu thông thường (không có cờ đỏ cấp)
            has_urinary = any(term in clean_user_text for term in (
                "tiểu buốt", "tiểu rắt", "mắc tiểu liên tục", "đi tiểu buốt", "tiểu ít",
                "painful urination", "dysuria", "frequent urination",
            ))
            has_urinary_alarm = any(term in clean_user_text for term in (
                "tiểu ra máu", "ra máu", "sốt cao", "rét run", "đau quặn thận", "blood in urine", "hematuria"
            ))
            if has_urinary and not has_urinary_alarm and not safety_emergency:
                guidance = get_triage_guidance(
                    specialty="Thận - Tiết niệu",
                    ats_level=4,
                    max_days=7,
                    language=lang,
                )
                return TriageEvaluationResult(
                    ats_level=ATSLevel.LEVEL_4_STANDARD,
                    urgency_tier=UrgencyTier.WITHIN_WEEK,
                    max_booking_days=7,
                    is_emergency=False,
                    care_setting="OUTPATIENT_CLINIC",
                    triggered_red_flags=[],
                    triggered_rule_ids=[],
                    suggested_specialty="Thận - Tiết niệu",
                    clarification_question=None,
                    patient_guidance=guidance,
                )

            # Dị ứng nhẹ / Da liễu (không có suy hô hấp, không sốc)
            has_mild_allergy = any(term in clean_user_text for term in (
                "nổi vài mảng ngứa", "mẩn ngứa ở tay", "nổi ngứa", "ngứa ở tay", "ngứa da",
                "mild allergy", "itchy rash",
            ))
            if has_mild_allergy and not safety_emergency:
                guidance = get_triage_guidance(
                    specialty="Miễn dịch - Dị ứng",
                    ats_level=4,
                    max_days=7,
                    language=lang,
                )
                return TriageEvaluationResult(
                    ats_level=ATSLevel.LEVEL_4_STANDARD,
                    urgency_tier=UrgencyTier.WITHIN_WEEK,
                    max_booking_days=7,
                    is_emergency=False,
                    care_setting="OUTPATIENT_CLINIC",
                    triggered_red_flags=[],
                    triggered_rule_ids=[],
                    suggested_specialty="Miễn dịch - Dị ứng",
                    clarification_question=None,
                    patient_guidance=guidance,
                )

            # Sức khỏe tinh thần / Tâm lý (không có tự hại)
            has_psychology = any(term in clean_user_text for term in (
                "mất ngủ", "đầu óc căng như dây đàn", "lo linh tinh", "lo âu", "stress", "căng thẳng thần kinh",
                "insomnia", "anxiety",
            ))
            if has_psychology and not safety_emergency:
                guidance = get_triage_guidance(
                    specialty="Trung tâm Chăm sóc sức khỏe tinh thần",
                    ats_level=4,
                    max_days=14,
                    language=lang,
                )
                return TriageEvaluationResult(
                    ats_level=ATSLevel.LEVEL_4_STANDARD,
                    urgency_tier=UrgencyTier.WITHIN_WEEK,
                    max_booking_days=14,
                    is_emergency=False,
                    care_setting="OUTPATIENT_CLINIC",
                    triggered_red_flags=[],
                    triggered_rule_ids=[],
                    suggested_specialty="Trung tâm Chăm sóc sức khỏe tinh thần",
                    clarification_question=None,
                    patient_guidance=guidance,
                )

            # Sốt ở trẻ nhỏ chưa đủ thông tin
            has_pediatric_fever = any(term in clean_user_text for term in (
                "bé nhà tôi sốt", "bé sốt", "em bé sốt", "trẻ sốt", "con tôi sốt",
            ))
            if has_pediatric_fever and not safety_emergency:
                clarification = (
                    "Dạ, sốt ở trẻ nhỏ cần được theo dõi cẩn thận. Bác cho em biết thêm: "
                    "Bé bao nhiêu tháng/tuổi, nhiệt độ đo được là bao nhiêu, và bé có dấu hiệu li bì, khó thở, nôn trớ hay bỏ bú không ạ?"
                    if lang == "vi" else
                    "Fever in young children requires careful attention. Could you share: "
                    "How old is the child, what is the temperature, and are there signs like lethargy, breathing difficulty, or poor feeding?"
                )
                guidance = get_triage_guidance(
                    specialty="Nhi khoa",
                    ats_level=3,
                    max_days=1,
                    language=lang,
                )
                return TriageEvaluationResult(
                    ats_level=ATSLevel.LEVEL_3_URGENT,
                    urgency_tier=UrgencyTier.SAME_DAY,
                    max_booking_days=1,
                    is_emergency=False,
                    care_setting="OUTPATIENT_CLINIC",
                    triggered_red_flags=[],
                    triggered_rule_ids=[],
                    suggested_specialty="Nhi khoa",
                    clarification_question=clarification,
                    patient_guidance=guidance,
                )

        # BƯỚC 2: So khớp bệnh học & Phân tầng triệu chứng (Evidence Matching v2.1)
        GENERIC_SPECIALTIES = {
            "sức khỏe tổng quát", "đa khoa", "khoa khám bệnh", "nội tổng quát",
            "tổng quát", "chưa xác định", ""
        }

        # Candidate matching must not score symptoms explicitly denied by the
        # patient. Safety gates above still inspect the full original text.
        scoring_user_text = user_text
        for scope_start, scope_end, _ in reversed(negation_svc.extract_negated_scopes(user_text)):
            scoring_user_text = (
                scoring_user_text[:scope_start]
                + " " * (scope_end - scope_start)
                + scoring_user_text[scope_end:]
            )
        clean_user_text = re.sub(r"[,:;.\(\)\?\!]+", " ", scoring_user_text).lower()

        # Từ dừng lâm sàng để loại bỏ nhiễu bigram (Bilingual EN-VI)
        CLINICAL_STOPWORDS = {
            "kèm theo", "bác sĩ", "tôi bị", "cảm thấy", "trong người", "ở vùng",
            "tính chất", "dữ dội", "nặng trịch", "liên tục", "kéo dài", "có thể",
            "triệu chứng", "khoảng", "bắt đầu", "sau khi", "khiến tôi", "làm tôi",
            "được", "không", "nhưng", "hoặc", "và", "với", "cho", "của", "tại", "là",
            "dấu hiệu", "biểu hiện", "bị đau", "cơn đau", "nguy hiểm", "mức độ",
            "chất nặng", "tính chất", "bác sỹ", "nghi ngờ", "kèm ho",
            # English clinical stopwords
            "doctor", "symptoms", "pain", "severe", "continuous", "starting",
            "since", "feel", "having", "with", "also", "and", "or", "in", "my",
            "the", "about", "started", "from", "feeling", "please", "could", "would"
        }

        # Kiểm tra sự hiện diện của các vùng giải phẫu chính (Bilingual EN-VI)
        has_chest = any(kw in clean_user_text for kw in [
            "ngực", "tim", "xương ức", "mạn sườn", "bả vai", "đánh trống ngực", "vú",
            "chest", "heart", "sternum", "palpitation", "breast", "rib"
        ])
        has_abd = any(kw in clean_user_text for kw in [
            "bụng", "thượng vị", "hạ sườn", "hố chậu", "dạ dày", "ruột", "nôn", "tiêu chảy", "phân", "ợ chua", "trào ngược", "bẹn", "háng", "tinh hoàn", "quặn bụng",
            "abdomen", "abdominal", "stomach", "epigastric", "iliac", "vomit", "diarrhea", "stool", "heartburn", "acid reflux", "groin", "testicle", "cramping", "flank"
        ])
        has_ent = any(kw in clean_user_text for kw in [
            "họng", "amidan", "ngạt mũi", "chảy nước mũi", "tai", "xoang", "thanh quản", "nuốt đau", "nuốt vướng",
            "throat", "tonsil", "nasal", "runny nose", "ear", "sinus", "larynx", "swallow", "pharyngitis", "sore throat"
        ])
        has_neuro = any(kw in clean_user_text for kw in [
            "đầu", "trán", "thái dương", "mặt", "gò má", "co thắt", "co rút", "sụp mí", "liệt", "mất ý thức", "ngất", "lưỡi", "nói khó",
            "head", "forehead", "temple", "face", "cheek", "spasm", "ptosis", "droop", "paralysis", "unconscious", "faint", "tongue", "speech", "headache", "dizziness"
        ])
        has_resp = any(kw in clean_user_text for kw in [
            "ho", "khó thở", "hụt hơi", "thở rít", "khò khè", "đờm", "phổi",
            "cough", "shortness of breath", "dyspnea", "stridor", "wheez", "sputum", "phlegm", "lung", "breath"
        ])

        # Từ khóa cốt lõi định danh bệnh nhân (Core Clinical Discriminators - Bilingual EN-VI)
        CORE_DISEASE_KEYWORDS = {
            "cúm": "ddx-influenza",
            "flu": "ddx-influenza",
            "influenza": "ddx-influenza",
            "ho gà": "ddx-whooping-cough",
            "whooping cough": "ddx-whooping-cough",
            "nhược cơ": "ddx-myasthenia-gravis",
            "myasthenia": "ddx-myasthenia-gravis",
            "thoát vị bẹn": "ddx-inguinal-hernia",
            "thoát vị": "ddx-inguinal-hernia",
            "hernia": "ddx-inguinal-hernia",
            "trào ngược": "ddx-gerd",
            "nóng rát từ dạ dày": "ddx-gerd",
            "gerd": "ddx-gerd",
            "acid reflux": "ddx-gerd",
            "heartburn": "ddx-gerd",
            "thanh quản": "ddx-acute-laryngitis",
            "laryngitis": "ddx-acute-laryngitis",
            "tai giữa": "ddx-acute-otitis-media",
            "otitis": "ddx-acute-otitis-media",
            "xoang": "ddx-acute-rhinosinusitis",
            "sinusitis": "ddx-acute-rhinosinusitis",
            "lao phổi": "ddx-tuberculosis",
            "tuberculosis": "ddx-tuberculosis",
            "sốc phản vệ": "ddx-anaphylaxis",
            "anaphylaxis": "ddx-anaphylaxis",
            "màng ngoài tim": "ddx-pericarditis",
            "pericarditis": "ddx-pericarditis",
            "thuyên tắc phổi": "ddx-pulmonary-embolism",
            "pulmonary embolism": "ddx-pulmonary-embolism",
            "tràn khí": "ddx-spontaneous-pneumothorax",
            "pneumothorax": "ddx-spontaneous-pneumothorax",
            "u tụy": "ddx-pancreatic-neoplasm",
            "pancreatic": "ddx-pancreatic-neoplasm",
            "u phổi": "ddx-pulmonary-neoplasm",
            "loạn trương lực": "ddx-acute-dystonic-reactions",
            "dyston": "ddx-acute-dystonic-reactions",
            "hoảng loạn": "ddx-panic-attack",
            "panic attack": "ddx-panic-attack",
            "viêm phế quản": "ddx-bronchitis",
            "bronchitis": "ddx-bronchitis",
            "viêm phổi": "ddx-pneumonia",
            "loét dạ dày": "ddx-peptic-ulcer-disease",
            "peptic ulcer": "ddx-peptic-ulcer-disease",
            "đau họng": "ddx-viral-pharyngitis",
            "rát họng": "ddx-viral-pharyngitis",
            "viêm họng": "ddx-viral-pharyngitis",
            "sore throat": "ddx-viral-pharyngitis",
            "ho khan": "ddx-bronchitis",
            "dry cough": "ddx-bronchitis",
        }

        # Cụm triệu chứng lâm sàng cốt lõi (Syndrome Clusters - Bilingual EN-VI)
        CORE_SYMPTOM_CLUSTERS = [
            ({"ho", "rát họng"}, "ddx-viral-pharyngitis", 45),
            ({"ho nhiều", "rát họng"}, "ddx-viral-pharyngitis", 45),
            ({"đau họng", "ho khan"}, "ddx-viral-pharyngitis", 40),
            ({"đau họng", "ho"}, "ddx-viral-pharyngitis", 35),
            ({"sore throat", "cough"}, "ddx-viral-pharyngitis", 35),
            ({"đau họng"}, "ddx-viral-pharyngitis", 30),
            ({"rát họng"}, "ddx-viral-pharyngitis", 35),
            ({"ho khan"}, "ddx-bronchitis", 25),
            ({"ho", "khò khè"}, "ddx-bronchitis", 30),
            ({"ho", "thở khò khè"}, "ddx-bronchitis", 30),
            ({"cough", "wheez"}, "ddx-bronchitis", 30),
            ({"ho", "đờm"}, "ddx-bronchitis", 20),
            ({"ho", "sốt", "đờm"}, "ddx-pneumonia", 30),
            ({"cough", "fever", "sputum"}, "ddx-pneumonia", 30),
            ({"cough", "fever", "phlegm"}, "ddx-pneumonia", 30),
            ({"hoảng loạn", "sợ chết"}, "ddx-panic-attack", 40),
            ({"sợ chết", "tim đập nhanh"}, "ddx-panic-attack", 35),
            ({"panic", "fear"}, "ddx-panic-attack", 40),
            ({"nóng rát từ dạ dày"}, "ddx-gerd", 35),
            ({"ợ chua"}, "ddx-gerd", 30),
            ({"heartburn"}, "ddx-gerd", 35),
            ({"acid reflux"}, "ddx-gerd", 35),
            ({"hít thở sâu", "khó thở"}, "ddx-spontaneous-pneumothorax", 30),
            ({"deep breath", "shortness of breath"}, "ddx-spontaneous-pneumothorax", 30),
            ({"ngạt mũi", "chảy nước mũi", "trán"}, "ddx-acute-rhinosinusitis", 30),
            ({"ngạt mũi", "chảy nước mũi", "gò má"}, "ddx-acute-rhinosinusitis", 30),
            ({"runny nose", "congestion", "sinus"}, "ddx-acute-rhinosinusitis", 30),
            ({"tai", "đau tai"}, "ddx-acute-otitis-media", 35),
            ({"ear pain"}, "ddx-acute-otitis-media", 35),
            ({"earache"}, "ddx-acute-otitis-media", 35),
            ({"amidan", "họng", "sốt"}, "ddx-acute-laryngitis", 25),
            ({"sore throat", "fever"}, "ddx-acute-laryngitis", 25),
            ({"sốt", "đau mỏi cơ toàn thân"}, "ddx-influenza", 35),
            ({"ho", "đau mỏi cơ toàn thân"}, "ddx-influenza", 30),
            ({"fever", "body aches"}, "ddx-influenza", 35),
            ({"fever", "muscle aches"}, "ddx-influenza", 35),
            ({"ho từng cơn", "mạn sườn"}, "ddx-spontaneous-rib-fracture", 35),
            ({"ho từng cơn", "ngực"}, "ddx-spontaneous-rib-fracture", 30),
            ({"sưng phù", "bàn chân"}, "ddx-localized-edema", 35),
            ({"sưng phù", "cổ chân"}, "ddx-localized-edema", 35),
            ({"swelling", "ankle"}, "ddx-localized-edema", 35),
            ({"swelling", "foot"}, "ddx-localized-edema", 35),
        ]

        candidates = []

        for record in self.diseases.values():
            score = 0
            rec_name_clean = record.name.lower().strip()
            rec_key = getattr(record, "disease_key", "")
            rec_spec_code = getattr(record, "primary_specialty_code", "")

            # 0. Khớp từ khóa cốt lõi
            for kw, target_key in CORE_DISEASE_KEYWORDS.items():
                if kw in clean_user_text and (target_key in rec_key or kw in rec_name_clean):
                    score += 35

            # 0.1 Khớp cụm triệu chứng hội chứng
            for req_set, target_key, cluster_score in CORE_SYMPTOM_CLUSTERS:
                if all(tok in clean_user_text for tok in req_set) and target_key in rec_key:
                    score += cluster_score

            # 0.2 Kiểm soát đặc thù bệnh lý (Pertinent negative discriminators)
            if "ddx-epiglottitis" in rec_key:
                has_epiglottitis_hallmark = any(w in clean_user_text for w in ["nuốt đau", "khó nuốt", "chảy nước dãi", "nuốt vướng"])
                if not has_epiglottitis_hallmark:
                    score -= 30

            # 1. Khớp tên bệnh: CHẶN đứng false substring collision
            if len(rec_name_clean) >= 5 and re.search(rf"\b{re.escape(rec_name_clean)}\b", scoring_user_text):
                score += 30
            else:
                parts = re.split(r"[\(\)]", rec_name_clean)
                for part in parts:
                    part_clean = part.strip()
                    if len(part_clean) >= 6 and part_clean not in CLINICAL_STOPWORDS and re.search(rf"\b{re.escape(part_clean)}\b", scoring_user_text):
                        score += 20
                        break

            # 2. Khớp Tổ hợp Hội chứng (Syndrome Combinations Boost)
            for sc in getattr(record, "syndrome_combinations", []):
                req_symptoms = []
                if isinstance(sc, dict):
                    req_symptoms = sc.get("required_symptoms", [])
                elif hasattr(sc, "required_symptoms"):
                    req_symptoms = sc.required_symptoms

                if req_symptoms:
                    match_count = sum(1 for sym in req_symptoms if sym.lower().strip() in clean_user_text)
                    if match_count >= 2:
                        score += 25
                    if match_count == len(req_symptoms) and len(req_symptoms) >= 2:
                        score += 15

            # 3. Khớp Red Flags (lọc stop words)
            rec_matched_flags = []
            for rf in record.symptom_hierarchy.red_flags:
                rf_clean = rf.lower().strip()
                phrases = [p.strip() for p in re.split(r"[,:;]+", rf_clean) if len(p.strip()) >= 5]
                for phrase in phrases:
                    if phrase not in CLINICAL_STOPWORDS and phrase in clean_user_text:
                        score += 8
                        rec_matched_flags.append(phrase)
                words = [w for w in rf_clean.split() if len(w) >= 3]
                if len(words) >= 2:
                    for i in range(len(words) - 1):
                        bigram = f"{words[i]} {words[i+1]}"
                        if len(bigram) > 6 and bigram not in CLINICAL_STOPWORDS and bigram in scoring_user_text:
                            score += 3
                            rec_matched_flags.append(bigram)

            # 4. Khớp Warning Signs
            for ws in record.symptom_hierarchy.warning_signs:
                ws_clean = ws.lower().strip()
                phrases = [p.strip() for p in re.split(r"[,:;]+", ws_clean) if len(p.strip()) >= 5]
                for phrase in phrases:
                    if phrase not in CLINICAL_STOPWORDS and phrase in clean_user_text:
                        score += 5

            # 5. Khớp Typical / Mild
            for ts in record.symptom_hierarchy.typical_or_mild:
                ts_clean = ts.lower().strip()
                phrases = [p.strip() for p in re.split(r"[,:;]+", ts_clean) if len(p.strip()) >= 5]
                for phrase in phrases:
                    if phrase not in CLINICAL_STOPWORDS and phrase in clean_user_text:
                        score += 3

            # 6. Kiểm tra tính tương thích giải phẫu (Anatomical Site Filtering)
            if rec_spec_code in ["TIM_MACH", "NOI_TIM_MACH"]:
                if not has_chest and (has_abd or has_neuro):
                    score -= 30  # Phạt nặng bệnh tim mạch khi không có triệu chứng ngực/tim
                elif has_chest:
                    score += 10
            elif rec_spec_code in ["TIEU_HOA", "TIEU_HOA_GAN_MAT"]:
                if has_abd:
                    score += 15
                elif not has_abd and has_chest:
                    score -= 10
            elif rec_spec_code in ["HO_HAP", "NOI_HO_HAP"]:
                if has_resp:
                    score += 12
            elif rec_spec_code in ["TAI_MUI_HONG"]:
                if has_ent:
                    score += 15
            elif rec_spec_code in ["THAN_KINH"]:
                if has_neuro:
                    score += 15

            if score >= 10:
                candidates.append({
                    "record": record,
                    "score": score,
                    "flags": rec_matched_flags[:3]
                })

        # BƯỚC 3: TOP-K SPECIALTY AGGREGATOR
        specialty_router = get_specialty_router()

        if candidates:
            # Lấy Top 5 candidates có điểm cao nhất
            top_5 = sorted(candidates, key=lambda x: x["score"], reverse=True)[:5]

            # Gom điểm theo chuyên khoa
            from collections import defaultdict
            spec_aggregated_scores = defaultdict(float)
            spec_best_candidate = {}

            for cand in top_5:
                rec = cand["record"]
                # Chuẩn hóa tên chuyên khoa
                spec_name = rec.primary_specialty_name
                # Refine nếu chuyên khoa bị chung chung
                if spec_name.lower().strip() in GENERIC_SPECIALTIES:
                    rt = specialty_router.route(query=user_text, pathology=rec.name)
                    if rt["confidence"] > 0.0:
                        spec_name = rt["specialty_name"]

                spec_aggregated_scores[spec_name] += cand["score"]
                if spec_name not in spec_best_candidate or cand["score"] > spec_best_candidate[spec_name]["score"]:
                    spec_best_candidate[spec_name] = cand

            # Chọn chuyên khoa có tổng điểm cao nhất
            winning_spec = max(spec_aggregated_scores.keys(), key=lambda s: spec_aggregated_scores[s])
            best_cand_in_winner = spec_best_candidate[winning_spec]
            best_match = best_cand_in_winner["record"]
            best_score = best_cand_in_winner["score"]
            matched_flags = best_cand_in_winner["flags"]

            acuity = best_match.acuity
            probing = best_match.probing_questions[0] if best_match.probing_questions else None

            # NẾU CÓ CỜ ĐỎ HOẶC HỘI CHỨNG CẤP CỨU TỪ SAFETY GATE (TIER 1 HOẶC TIER 2)
            if safety_emergency and safety_ats is not None:
                final_spec = winning_spec if winning_spec.lower().strip() not in GENERIC_SPECIALTIES else default_safety_specialty
                guidance = get_emergency_guidance(
                    flag_name=safety_flags[0] if safety_flags else "Cấp cứu lâm sàng",
                    specialty=final_spec,
                    ats_level=safety_ats.value if hasattr(safety_ats, "value") else int(safety_ats),
                    language=lang
                )
                return TriageEvaluationResult(
                    matched_disease_key=best_match.disease_key,
                    matched_disease_name=best_match.name,
                    ats_level=safety_ats,
                    urgency_tier=UrgencyTier.EMERGENCY_BLOCK,
                    max_booking_days=0,
                    is_emergency=True,
                    care_setting="EMERGENCY_DEPT",
                    triggered_red_flags=safety_flags,
                    triggered_rule_ids=safety_rule_ids,
                    suggested_specialty=final_spec,
                    clarification_question=None,
                    patient_guidance=guidance
                )

            # NẾU CÓ CẢNH BÁO BÁN KHẨN (TIER 3)
            if safety_ats == ATSLevel.LEVEL_3_URGENT:
                guidance = get_triage_guidance(
                    specialty=winning_spec,
                    disease_name=best_match.name,
                    ats_level=3,
                    max_days=1,
                    language=lang
                )
                return TriageEvaluationResult(
                    matched_disease_key=best_match.disease_key,
                    matched_disease_name=best_match.name,
                    ats_level=ATSLevel.LEVEL_3_URGENT,
                    urgency_tier=UrgencyTier.SAME_DAY,
                    max_booking_days=1,
                    is_emergency=False,
                    care_setting="OUTPATIENT_CLINIC",
                    triggered_red_flags=safety_flags,
                    triggered_rule_ids=safety_rule_ids,
                    suggested_specialty=winning_spec,
                    clarification_question=probing,
                    patient_guidance=guidance
                )

            # Phân tầng triệu chứng thông thường (Outpatient ATS 4/5 hoặc Bán khẩn ATS 3)
            cand_ats = acuity.ats_level
            cand_tier = acuity.urgency_tier
            cand_max_days = acuity.max_booking_days
            cand_emergency = (acuity.max_booking_days == 0)
            cand_care_setting = "EMERGENCY_DEPT" if cand_emergency else "OUTPATIENT_CLINIC"

            # Nếu Safety Gate không phát hiện cờ đỏ hay hội chứng cấp cứu nào,
            # candidate matching KHÔNG được phép tự ý ép bệnh nhân vào cấp cứu ATS 1/2
            if not safety_emergency and (cand_emergency or cand_ats in (ATSLevel.LEVEL_1_RESUSCITATION, ATSLevel.LEVEL_2_EMERGENT)):
                cand_ats = ATSLevel.LEVEL_3_URGENT
                cand_tier = UrgencyTier.SAME_DAY
                cand_max_days = 1
                cand_emergency = False
                cand_care_setting = "OUTPATIENT_CLINIC"

            guidance = get_triage_guidance(
                specialty=winning_spec,
                disease_name=best_match.name,
                ats_level=cand_ats.value if hasattr(cand_ats, "value") else int(cand_ats),
                max_days=cand_max_days,
                language=lang
            )

            return TriageEvaluationResult(
                matched_disease_key=best_match.disease_key,
                matched_disease_name=best_match.name,
                ats_level=cand_ats,
                urgency_tier=cand_tier,
                max_booking_days=cand_max_days,
                is_emergency=cand_emergency,
                care_setting=cand_care_setting,
                triggered_red_flags=matched_flags[:3],
                triggered_rule_ids=[],
                suggested_specialty=winning_spec,
                clarification_question=probing,
                patient_guidance=guidance
            )

        # BƯỚC 4: Fallback — dùng Specialty Router thay vì luôn trả "Sức khỏe tổng quát"
        router_result = specialty_router.route(query=user_text)
        fallback_spec = router_result.get("specialty_name") if router_result.get("confidence", 0.0) >= 0.1 else "Sức khỏe tổng quát"

        if safety_emergency and safety_ats is not None:
            final_spec = fallback_spec if fallback_spec.lower().strip() not in GENERIC_SPECIALTIES else default_safety_specialty
            guidance = get_emergency_guidance(
                flag_name=safety_flags[0] if safety_flags else "Cấp cứu lâm sàng",
                specialty=final_spec,
                ats_level=safety_ats.value if hasattr(safety_ats, "value") else int(safety_ats),
                language=lang
            )
            return TriageEvaluationResult(
                ats_level=safety_ats,
                urgency_tier=UrgencyTier.EMERGENCY_BLOCK,
                max_booking_days=0,
                is_emergency=True,
                care_setting="EMERGENCY_DEPT",
                triggered_red_flags=safety_flags,
                triggered_rule_ids=safety_rule_ids,
                suggested_specialty=final_spec,
                clarification_question=None,
                patient_guidance=guidance
            )

        fallback_spec_display = get_specialty_display_name(fallback_spec, lang)
        clarification_text = (
            "Could you describe the pain location more specifically, when it started, and if you have fever or shortness of breath?"
            if lang == "en" else
            "Bác có thể mô tả cụ thể hơn vị trí đau, triệu chứng bắt đầu từ khi nào và có sốt hay khó thở không?"
        )
        guidance_text = (
            f"Thank you for sharing your symptoms. We recommend consulting a specialist at **{fallback_spec_display}**. "
            "Please answer the question above so we can guide you more accurately."
            if lang == "en" else
            f"Dạ, em đã ghi nhận thông tin. Hệ thống gợi ý thăm khám tại chuyên khoa {fallback_spec_display}. "
            "Bác vui lòng trả lời thêm câu hỏi trên để em xác nhận chính xác hơn nhé."
        )

        return TriageEvaluationResult(
            ats_level=ATSLevel.LEVEL_3_URGENT if safety_ats == ATSLevel.LEVEL_3_URGENT else ATSLevel.LEVEL_4_STANDARD,
            urgency_tier=UrgencyTier.SAME_DAY if safety_ats == ATSLevel.LEVEL_3_URGENT else UrgencyTier.WITHIN_WEEK,
            max_booking_days=1 if safety_ats == ATSLevel.LEVEL_3_URGENT else 7,
            is_emergency=False,
            care_setting="OUTPATIENT_CLINIC",
            triggered_red_flags=safety_flags,
            triggered_rule_ids=safety_rule_ids,
            suggested_specialty=fallback_spec,
            clarification_question=clarification_text,
            patient_guidance=guidance_text
        )

    def resolve_multi_symptom(
        self,
        base_result: TriageEvaluationResult,
        clinical_facts: Dict[str, Any] | None,
        language: str = "vi",
    ) -> TriageEvaluationResult:
        """Reconcile active complaints after the global safety gates have run.

        Emergency and same-day outcomes remain authoritative. Non-urgent routing
        shortcuts are converted into explainable candidates when complaints span
        more than one clinical system.
        """
        facts = clinical_facts or {}
        raw_complaints = facts.get("complaints") or []
        active: list[dict[str, Any]] = []
        for value in raw_complaints:
            if isinstance(value, str):
                item = {"code": value, "status": "active", "evidence": []}
            elif isinstance(value, dict):
                item = value
            else:
                continue
            if item.get("status", "active") == "active" and item.get("code") in self.COMPLAINT_ROUTES:
                active.append(item)
        if not active and facts.get("chief_complaint") in self.COMPLAINT_ROUTES:
            active = [{"code": facts["chief_complaint"], "status": "active", "evidence": []}]

        grouped: dict[str, dict[str, Any]] = {}
        primary = facts.get("primary_complaint") or facts.get("chief_complaint")
        explicit_primary = facts.get("primary_complaint_explicit_code")
        known = set(facts.get("positive_facts") or []) | set(facts.get("negative_facts") or [])
        for complaint in active:
            code = str(complaint["code"])
            spec_code, name, expected = self.COMPLAINT_ROUTES[code]
            candidate = grouped.setdefault(spec_code, {
                "code": spec_code,
                "name": name,
                "score": 0.0,
                "evidence": [],
                "missing": [],
                "complaint_codes": [],
                "sources": [],
            })
            candidate["score"] += 1.0 + (0.25 if code == primary else 0.0)
            if code == explicit_primary:
                candidate["score"] += 2.0
            candidate["evidence"].append(code)
            candidate["evidence"].extend(str(x) for x in complaint.get("evidence") or [])
            candidate["complaint_codes"].append(code)
            candidate["sources"].append(str(complaint.get("source") or "unknown"))
            candidate["missing"].extend(field for field in expected if field not in known and not facts.get(field))
            if complaint.get("severity") == "severe":
                candidate["score"] += 0.75

        base_specialty_code = canonicalize_specialty_code(base_result.suggested_specialty)
        urgent_specialty_codes = {
            self.URGENT_RULE_SPECIALTIES[rule_id]
            for rule_id in base_result.triggered_rule_ids
            if rule_id in self.URGENT_RULE_SPECIALTIES
        }
        candidates = []
        for value in grouped.values():
            is_urgent_winner = bool(
                base_result.ats_level.value <= ATSLevel.LEVEL_3_URGENT.value
                and (
                    value["code"] == base_specialty_code
                    or value["code"] in urgent_specialty_codes
                )
            )
            candidate_ats = base_result.ats_level if is_urgent_winner else (
                base_result.ats_level
                if base_result.ats_level.value >= ATSLevel.LEVEL_4_STANDARD.value
                else ATSLevel.LEVEL_4_STANDARD
            )
            has_deterministic_evidence = "deterministic" in value["sources"]
            has_independent_evidence = bool(
                has_deterministic_evidence
                and value["complaint_codes"]
                and any(value_item for value_item in value["evidence"] if value_item not in value["complaint_codes"])
            )
            is_primary_route = primary in value["complaint_codes"]
            confidence = 0.30
            confidence += 0.20 if value["complaint_codes"] else 0.0
            confidence += 0.20 if has_deterministic_evidence else 0.0
            confidence += 0.10 if is_primary_route else 0.0
            confidence += 0.15 if is_urgent_winner else 0.0
            confidence += 0.05 if len(set(value["complaint_codes"])) >= 2 else 0.0
            confidence += 0.05 if explicit_primary in value["complaint_codes"] else 0.0
            confidence -= min(0.10, 0.02 * len(set(value["missing"])))
            confidence = round(max(0.0, min(1.0, confidence)), 3)
            evidence_strength = (
                "strong" if is_urgent_winner or confidence >= 0.80
                else "moderate" if confidence >= 0.60
                else "weak"
            )
            candidates.append(TriageSpecialtyCandidate(
                code=value["code"],
                name=value["name"],
                score=value["score"] + (2.0 if is_urgent_winner else 0.0),
                ats_level=candidate_ats,
                evidence=list(dict.fromkeys(value["evidence"])),
                missing_information=list(dict.fromkeys(value["missing"])),
                routing_confidence=confidence,
                evidence_strength=evidence_strength,
                has_independent_evidence=has_independent_evidence,
            ))
        candidates.sort(key=lambda item: (item.ats_level.value, -item.score))

        recommended: list[TriageSpecialtyCandidate] = []
        if candidates:
            primary_candidate = candidates[0]
            if primary_candidate.routing_confidence >= self.PRIMARY_ROUTING_THRESHOLD:
                primary_candidate.publicly_recommended = True
                recommended.append(primary_candidate)
            else:
                primary_candidate.suppression_reason = "below_primary_threshold"

            for candidate in candidates[1:]:
                if len(recommended) >= self.MAX_PUBLIC_SPECIALTIES:
                    candidate.suppression_reason = "public_limit_reached"
                    continue
                if not recommended:
                    candidate.suppression_reason = "primary_not_qualified"
                    continue
                ratio = candidate.routing_confidence / max(recommended[0].routing_confidence, 0.001)
                if candidate.routing_confidence < self.SECONDARY_ROUTING_THRESHOLD:
                    candidate.suppression_reason = "below_secondary_threshold"
                elif ratio < self.SECONDARY_TO_PRIMARY_RATIO:
                    candidate.suppression_reason = "too_far_below_primary"
                elif not candidate.has_independent_evidence:
                    candidate.suppression_reason = "no_independent_evidence"
                else:
                    candidate.publicly_recommended = True
                    recommended.append(candidate)

        update: dict[str, Any] = {
            "candidate_specialties": candidates,
            "recommended_specialties": recommended,
        }
        if recommended and base_result.suggested_specialty.lower() in {
            "sức khỏe tổng quát", "trung tâm sức khỏe tổng quát", "general health"
        }:
            update["suggested_specialty"] = recommended[0].name

        # Safety gates win immediately; a multi-system conflict must never delay them.
        if base_result.is_emergency or base_result.ats_level.value <= ATSLevel.LEVEL_3_URGENT.value:
            return base_result.model_copy(update=update)

        clarification_candidates = [
            candidate for candidate in candidates
            if candidate.routing_confidence >= self.CLARIFICATION_THRESHOLD
        ]
        if len(clarification_candidates) >= 2:
            visible_for_reason = recommended[:2] or clarification_candidates[:2]
            names = [candidate.name for candidate in visible_for_reason]
            if language == "en":
                reason = f"Active complaints currently point to both {names[0]} and {names[1]}."
                question = (
                    "Which symptom started first and is more troublesome now? Did either pain begin suddenly or become severe, "
                    "and do you have blurred vision, weakness, high fever, repeated vomiting, or bleeding?"
                )
            else:
                reason = f"Các triệu chứng hiện hướng tới cả {names[0]} và {names[1]}."
                question = (
                    "Dạ, bác cho em biết triệu chứng nào xuất hiện trước và hiện khó chịu hơn; có cơn đau nào khởi phát đột ngột "
                    "hoặc dữ dội, kèm nhìn mờ, tê yếu tay chân, sốt cao, nôn nhiều hay chảy máu không ạ?"
                )
            update.update({
                "suggested_specialty": recommended[0].name if recommended else base_result.suggested_specialty,
                "conflict_reason": reason if len(recommended) >= 2 else None,
                "needs_multi_symptom_clarification": True,
                "clarification_question": question,
            })
        return base_result.model_copy(update=update)


# Singleton instance để tái sử dụng
_triage_service_instance: Optional[ClinicalTriageService] = None

def get_triage_service() -> ClinicalTriageService:
    global _triage_service_instance
    if _triage_service_instance is None:
        _triage_service_instance = ClinicalTriageService()
    return _triage_service_instance
