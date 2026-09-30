"""
Specialty Router — Bộ Điều Phối Chuyên Khoa 3 Tầng.

Tầng 1: DDXPlus Pathology → Vinmec Specialty (Lookup cứng, <1ms)
Tầng 2: Semantic Symptom Router (TF-IDF + cosine similarity, <50ms)
Tầng 3: LLM-based Router (GPT-4o-mini structured output, ~500ms)

Triết lý thiết kế:
- Chạy tuần tự từ rẻ→đắt, nhanh→chậm.
- Tầng trước có kết quả tin cậy → dừng sớm, không gọi tầng sau.
- Tầng 3 (LLM) chỉ kích hoạt khi hai tầng trước không đủ confident.
"""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# TẦNG 1: LOOKUP TABLE — DDXPlus Pathology → Vinmec Specialty
# ────────────────────────────────────────────────────────────────

# 49 pathologies trong DDXPlus dataset mapped tới specialty code + tên chuyên khoa Vinmec
DDXPLUS_PATHOLOGY_SPECIALTY_MAP: dict[str, dict[str, str]] = {
    # Tim mạch
    "Myocardial infarction": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "Unstable angina": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "Stable angina": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "Atrial fibrillation": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "Pulmonary embolism": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "Pericarditis": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "Myocarditis": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "PSVT": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "Possible NSTEMI / STEMI": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "Acute pulmonary edema": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "Anemia": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "SLE": {"code": "TIM_MACH", "name": "Miễn dịch - Dị ứng"},

    # Hô hấp
    "Pneumonia": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Bronchitis": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "URTI": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Influenza": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Tuberculosis": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Bronchiolitis": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Acute laryngitis": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Croup": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Whooping cough": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Acute COPD exacerbation / Infection": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Pneumothorax": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Pulmonary neoplasm": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Bronchiectasis": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Sarcoidosis": {"code": "HO_HAP", "name": "Nội hô hấp"},

    # Tiêu hóa - Gan mật
    "GERD": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "Boerhaave": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "Pancreatic neoplasm": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "Acute pancreatitis": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "Peptic ulcer disease": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},

    # Tai mũi họng
    "Viral pharyngitis": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},
    "Epiglottitis": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},
    "Acute otitis media": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},
    "Chronic rhinosinusitis": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},
    "Acute rhinosinusitis": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},

    # Truyền nhiễm
    "HIV (initial infection)": {"code": "TRUYEN_NHIEM", "name": "Truyền nhiễm"},
    "Ebola": {"code": "TRUYEN_NHIEM", "name": "Truyền nhiễm"},
    "Chagas": {"code": "TRUYEN_NHIEM", "name": "Truyền nhiễm"},
    "Scombroid food poisoning": {"code": "TRUYEN_NHIEM", "name": "Truyền nhiễm"},

    # Dị ứng - Miễn dịch
    "Allergic sinusitis": {"code": "DI_UNG", "name": "Miễn dịch - Dị ứng"},
    "Anaphylaxis": {"code": "DI_UNG", "name": "Miễn dịch - Dị ứng"},

    # Thần kinh
    "Cluster headache": {"code": "THAN_KINH", "name": "Thần kinh"},
    "Guillain-Barré syndrome": {"code": "THAN_KINH", "name": "Thần kinh"},
    "Myasthenia gravis": {"code": "THAN_KINH", "name": "Thần kinh"},
    "Acute dystonic reactions": {"code": "THAN_KINH", "name": "Thần kinh"},

    # Cơ xương khớp
    "Costochondritis": {"code": "XUONG_KHOP", "name": "Chấn thương chỉnh hình - Y học thể thao"},
    "Rib fracture": {"code": "XUONG_KHOP", "name": "Chấn thương chỉnh hình - Y học thể thao"},
    "Spontaneous rib fracture": {"code": "XUONG_KHOP", "name": "Chấn thương chỉnh hình - Y học thể thao"},

    # Da liễu
    "Localized edema": {"code": "DA_LIEU", "name": "Da liễu"},

    # Bổ sung các bệnh DDXPlus còn thiếu
    "Spontaneous pneumothorax": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Inguinal hernia": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "Larygospasm": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Bronchospasm / acute asthma exacerbation": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "Acute COPD exacerbation / infection": {"code": "HO_HAP", "name": "Nội hô hấp"},

    # Tâm thần
    "Panic attack": {"code": "TAM_THAN", "name": "Trung tâm chăm sóc sức khỏe tinh thần tích hợp"},
}

# Reverse index: lowercase pathology → specialty info
_PATHOLOGY_INDEX: dict[str, dict[str, str]] = {
    k.lower(): v for k, v in DDXPLUS_PATHOLOGY_SPECIALTY_MAP.items()
}

# Bổ sung ánh xạ tên bệnh tiếng Việt phổ biến vào index
VI_PATHOLOGY_MAP: dict[str, dict[str, str]] = {
    "nhồi máu cơ tim": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "đau thắt ngực": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "suy tim": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "rung nhĩ": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "viêm màng ngoài tim": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "viêm cơ tim": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "phù phổi cấp": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "thuyên tắc phổi": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "thiếu máu": {"code": "TIM_MACH", "name": "Trung tâm Tim mạch"},
    "tràn khí màng phổi": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "viêm phổi": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "viêm phế quản": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "lao phổi": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "hen suyễn": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "hen phế quản": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "copd": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "viêm đường hô hấp trên": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "cúm": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "ho gà": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "co thắt thanh quản": {"code": "HO_HAP", "name": "Nội hô hấp"},
    "trào ngược dạ dày": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "loét dạ dày": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "viêm tụy": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "thoát vị bẹn": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "thủng thực quản": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "u tụy": {"code": "TIEU_HOA", "name": "Tiêu hóa - Gan mật"},
    "viêm họng": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},
    "viêm xoang": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},
    "viêm tai giữa": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},
    "viêm thanh quản": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},
    "viêm nắp thanh quản": {"code": "TAI_MUI_HONG", "name": "Tai - Mũi - Họng"},
    "đau đầu từng cụm": {"code": "THAN_KINH", "name": "Thần kinh"},
    "nhược cơ": {"code": "THAN_KINH", "name": "Thần kinh"},
    "đột quỵ": {"code": "THAN_KINH", "name": "Thần kinh"},
    "đau nửa đầu": {"code": "THAN_KINH", "name": "Thần kinh"},
    "sốc phản vệ": {"code": "DI_UNG", "name": "Miễn dịch - Dị ứng"},
    "lupus ban đỏ": {"code": "DI_UNG", "name": "Miễn dịch - Dị ứng"},
    "gãy xương sườn": {"code": "XUONG_KHOP", "name": "Chấn thương chỉnh hình - Y học thể thao"},
    "cơn hoảng loạn": {"code": "TAM_THAN", "name": "Trung tâm chăm sóc sức khỏe tinh thần tích hợp"},
}
for vi_name, vi_spec in VI_PATHOLOGY_MAP.items():
    _PATHOLOGY_INDEX[vi_name] = vi_spec


def tier1_pathology_lookup(pathology: str) -> dict[str, str] | None:
    """Tầng 1: Tra cứu trực tiếp pathology → specialty (O(1), <1ms)."""
    if not pathology:
        return None
    p_clean = pathology.lower().strip()
    # 1. Khớp chính xác
    result = _PATHOLOGY_INDEX.get(p_clean)
    if result:
        logger.debug(f"[Tier1] Exact match pathology '{pathology}' → {result['name']}")
        return result
    # 2. Khớp chuỗi con (hỗ trợ tên tiếng Việt có kèm tên tiếng Anh trong ngoặc)
    for key, spec_info in _PATHOLOGY_INDEX.items():
        if key in p_clean or p_clean in key:
            logger.debug(f"[Tier1] Substring match pathology '{pathology}' with '{key}' → {spec_info['name']}")
            return spec_info
    return None


# ────────────────────────────────────────────────────────────────
# TẦNG 2: SEMANTIC SYMPTOM ROUTER (TF-IDF + Cosine Similarity)
# ────────────────────────────────────────────────────────────────

# Specialty prototypes: mỗi chuyên khoa có một "profile" gồm keywords
# đặc trưng (cả EN lẫn VI) để tính TF-IDF similarity
SPECIALTY_PROTOTYPES: dict[str, dict[str, Any]] = {
    "Trung tâm Tim mạch": {
        "code": "TIM_MACH",
        "keywords": [
            "chest pain", "heart", "palpitation", "angina", "infarction", "embolism",
            "atrial fibrillation", "cardiac", "tachycardia", "arrhythmia", "dyspnea on exertion",
            "pulmonary embolism", "coughing up blood", "leg swelling",
            "đau ngực", "tim đập nhanh", "đau thắt ngực", "nhồi máu", "rung nhĩ",
            "tức ngực", "khó thở khi gắng sức", "phù chân", "thuyên tắc phổi",
        ],
    },
    "Nội hô hấp": {
        "code": "HO_HAP",
        "keywords": [
            "cough", "shortness of breath", "wheezing", "sputum", "phlegm",
            "pneumonia", "bronchitis", "lung", "respiratory", "dyspnea", "breathe",
            "tuberculosis", "copd", "asthma",
            "ho", "khó thở", "đờm", "viêm phổi", "hen suyễn", "thở rít",
            "lao phổi", "phổi tắc nghẽn",
        ],
    },
    "Tiêu hóa - Gan mật": {
        "code": "TIEU_HOA",
        "keywords": [
            "abdominal pain", "stomach", "nausea", "vomit", "diarrhea", "constipation",
            "epigastric", "gerd", "reflux", "heartburn", "pancreatitis", "liver",
            "đau bụng", "buồn nôn", "tiêu chảy", "đau dạ dày", "trào ngược",
            "đau thượng vị", "viêm tụy", "gan mật", "ợ nóng",
        ],
    },
    "Tai - Mũi - Họng": {
        "code": "TAI_MUI_HONG",
        "keywords": [
            "sore throat", "ear pain", "nasal", "sinusitis", "hoarse", "swallow",
            "pharyngitis", "otitis", "rhinorrhea", "runny nose",
            "đau họng", "đau tai", "ngạt mũi", "viêm xoang", "nuốt đau",
            "chảy nước mũi", "khàn giọng",
        ],
    },
    "Thần kinh": {
        "code": "THAN_KINH",
        "keywords": [
            "headache", "migraine", "seizure", "numbness", "tingling", "weakness",
            "dizziness", "vertigo", "paralysis", "stroke",
            "đau đầu", "chóng mặt", "co giật", "tê bì", "yếu liệt",
            "đột quỵ", "liệt",
        ],
    },
    "Miễn dịch - Dị ứng": {
        "code": "DI_UNG",
        "keywords": [
            "allergy", "rash", "hives", "urticaria", "anaphylaxis", "swelling",
            "itching", "lupus", "autoimmune",
            "dị ứng", "mề đay", "phát ban", "ngứa", "sưng phù", "phản vệ",
        ],
    },
    "Truyền nhiễm": {
        "code": "TRUYEN_NHIEM",
        "keywords": [
            "fever", "infection", "hiv", "tuberculosis", "ebola", "malaria",
            "viral", "bacteria", "contagious", "epidemic",
            "sốt", "nhiễm trùng", "lây nhiễm", "dịch", "virus",
        ],
    },
    "Chấn thương chỉnh hình - Y học thể thao": {
        "code": "XUONG_KHOP",
        "keywords": [
            "joint pain", "back pain", "fracture", "bone", "muscle pain",
            "sprain", "orthopedic", "rib", "costochondritis",
            "đau khớp", "đau lưng", "gãy xương", "đau cơ", "bong gân",
            "đau cổ", "mỏi cổ", "đau vai", "vai gáy", "cổ vai gáy",
            "ngồi máy tính", "làm văn phòng", "sai tư thế",
        ],
    },
    "Da liễu": {
        "code": "DA_LIEU",
        "keywords": [
            "skin", "rash", "lesion", "dermatitis", "eczema", "acne", "edema",
            "da", "mẩn ngứa", "chàm", "mụn", "phù nề",
        ],
    },
}

# Confidence threshold cho Tier 2
TIER2_CONFIDENCE_THRESHOLD = 0.15


def _tokenize(text: str) -> list[str]:
    """Tách tokens đơn giản: lowercase, split theo non-alphanum."""
    return re.findall(r'[a-zàáạảãăắằặẳẵâấầậẩẫđèéẹẻẽêếềệểễìíịỉĩòóọỏõôốồộổỗơớờợởỡùúụủũưứừựửữỳýỵỷỹ0-9]+', text.lower())


def _compute_keyword_score(tokens: list[str], keywords: list[str]) -> float:
    """Tính overlap score giữa query tokens và specialty keywords."""
    if not tokens:
        return 0.0
    # Build keyword token set (mỗi keyword phrase có thể có nhiều tokens)
    keyword_tokens = set()
    keyword_bigrams = set()
    for kw in keywords:
        kw_parts = _tokenize(kw)
        keyword_tokens.update(kw_parts)
        # Thêm bigrams cho precision cao hơn
        for i in range(len(kw_parts) - 1):
            keyword_bigrams.add(f"{kw_parts[i]}_{kw_parts[i+1]}")

    # Unigram matching
    query_set = set(tokens)
    unigram_hits = len(query_set & keyword_tokens)

    # Bigram matching (trọng số x2)
    query_bigrams = set()
    for i in range(len(tokens) - 1):
        query_bigrams.add(f"{tokens[i]}_{tokens[i+1]}")
    bigram_hits = len(query_bigrams & keyword_bigrams)

    # Weighted score, normalize bởi tổng keyword count
    total_possible = len(keyword_tokens) + len(keyword_bigrams)
    if total_possible == 0:
        return 0.0
    raw_score = (unigram_hits + bigram_hits * 2) / total_possible
    return raw_score


def tier2_semantic_route(query_text: str) -> tuple[str, str, float] | None:
    """
    Tầng 2: Semantic routing bằng keyword overlap scoring.
    Returns: (specialty_name, specialty_code, confidence) hoặc None.
    """
    if not query_text or len(query_text.strip()) < 5:
        return None

    tokens = _tokenize(query_text)
    if not tokens:
        return None

    best_name = None
    best_code = None
    best_score = 0.0

    for spec_name, spec_info in SPECIALTY_PROTOTYPES.items():
        score = _compute_keyword_score(tokens, spec_info["keywords"])
        if score > best_score:
            best_score = score
            best_name = spec_name
            best_code = spec_info["code"]

    if best_score >= TIER2_CONFIDENCE_THRESHOLD:
        logger.debug(f"[Tier2] Semantic match → {best_name} (score={best_score:.3f})")
        return (best_name, best_code, best_score)

    logger.debug(f"[Tier2] No confident match (best_score={best_score:.3f} < threshold={TIER2_CONFIDENCE_THRESHOLD})")
    return None


# ────────────────────────────────────────────────────────────────
# TẦNG 3: LLM-BASED SPECIALTY ROUTER (GPT-4o-mini Structured Output)
# ────────────────────────────────────────────────────────────────

# Danh sách chuyên khoa hợp lệ tại Vinmec (cho prompt LLM)
VINMEC_SPECIALTIES_FOR_LLM = [
    "Trung tâm Tim mạch",
    "Nội hô hấp",
    "Tiêu hóa - Gan mật",
    "Tai - Mũi - Họng",
    "Nội thần kinh",
    "Miễn dịch - Dị ứng",
    "Truyền nhiễm",
    "Chấn thương chỉnh hình - Y học thể thao",
    "Da liễu",
    "Nội tiết - Đái tháo đường",
    "Thận - Tiết niệu",
    "Sản phụ khoa",
    "Nhi khoa",
    "Mắt",
    "Nha khoa",
    "Ung bướu",
    "Sức khỏe tổng quát",
    "Cấp cứu",
]

LLM_SPECIALTY_ROUTER_PROMPT = """Bạn là một chuyên gia phân loại bệnh lý (triage) tại bệnh viện Vinmec.

Nhiệm vụ: Phân tích mô tả triệu chứng sau và xác định CHUYÊN KHOA PHÙ HỢP NHẤT.

Triệu chứng / Mô tả:
{query}

Danh sách chuyên khoa hợp lệ tại Vinmec:
{specialties}

Quy tắc:
1. Chỉ được chọn MỘT chuyên khoa từ danh sách trên.
2. Nếu triệu chứng có dấu hiệu cấp cứu (ngừng tim, đau thắt ngực dữ dội, khó thở cấp, nôn máu, liệt nửa người) → chọn "Cấp cứu".
3. Trả về JSON format chính xác (không giải thích thêm):

{{"specialty": "<tên chuyên khoa>", "confidence": <0.0-1.0>, "reasoning": "<1 dòng giải thích>"}}"""


async def tier3_llm_route(query_text: str) -> tuple[str, float, str] | None:
    """
    Tầng 3: Gọi LLM để phân loại chuyên khoa.
    Returns: (specialty_name, confidence, reasoning) hoặc None.
    """
    if not query_text:
        return None

    try:
        from src.medical_assistant.config import get_settings
        settings = get_settings()

        if not settings.openai_api_key or settings.openai_api_key == "sk-your-key-here":
            logger.warning("[Tier3] OpenAI API key not configured, skipping LLM routing")
            return None

        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)

        specialties_text = "\n".join([f"- {s}" for s in VINMEC_SPECIALTIES_FOR_LLM])
        prompt = LLM_SPECIALTY_ROUTER_PROMPT.format(
            query=query_text,
            specialties=specialties_text,
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        specialty = result.get("specialty", "")
        confidence = float(result.get("confidence", 0.0))
        reasoning = result.get("reasoning", "")

        # Validate specialty name
        if specialty not in VINMEC_SPECIALTIES_FOR_LLM:
            # Fuzzy match
            specialty_lower = specialty.lower()
            for valid_spec in VINMEC_SPECIALTIES_FOR_LLM:
                if specialty_lower in valid_spec.lower() or valid_spec.lower() in specialty_lower:
                    specialty = valid_spec
                    break
            else:
                logger.warning(f"[Tier3] LLM returned invalid specialty: '{specialty}'")
                return None

        logger.info(f"[Tier3] LLM route → {specialty} (confidence={confidence:.2f}, reason={reasoning})")
        return (specialty, confidence, reasoning)

    except Exception as e:
        logger.error(f"[Tier3] LLM routing failed: {e}")
        return None


# ────────────────────────────────────────────────────────────────
# UNIFIED ROUTER — Kết hợp 3 tầng
# ────────────────────────────────────────────────────────────────

class SpecialtyRouter:
    """
    Bộ điều phối chuyên khoa thống nhất 3 tầng.

    Usage:
        router = SpecialtyRouter()

        # Sync (Tầng 1 + 2)
        result = router.route(query="chest pain, palpitations", pathology="Atrial fibrillation")

        # Async (Tầng 1 + 2 + 3)
        result = await router.route_async(query="chest pain, palpitations")
    """

    def route(
        self,
        query: str = "",
        pathology: str | None = None,
    ) -> dict[str, Any]:
        """
        Synchronous routing: Tầng 1 → Tầng 2.
        Không gọi LLM (phù hợp cho batch eval).
        """
        # Tầng 1: Lookup pathology
        if pathology:
            tier1 = tier1_pathology_lookup(pathology)
            if tier1:
                return {
                    "specialty_name": tier1["name"],
                    "specialty_code": tier1["code"],
                    "confidence": 1.0,
                    "tier": 1,
                    "reasoning": f"DDXPlus pathology lookup: {pathology}",
                }

        # Tầng 2: Semantic keyword matching
        tier2 = tier2_semantic_route(query)
        if tier2:
            name, code, score = tier2
            return {
                "specialty_name": name,
                "specialty_code": code,
                "confidence": score,
                "tier": 2,
                "reasoning": f"Semantic keyword match (score={score:.3f})",
            }

        # Fallback
        return {
            "specialty_name": "Sức khỏe tổng quát",
            "specialty_code": "TONG_QUAT",
            "confidence": 0.0,
            "tier": 0,
            "reasoning": "No confident match from Tier 1 or Tier 2",
        }

    async def route_async(
        self,
        query: str,
        pathology: str | None = None,
    ) -> dict[str, Any]:
        """
        Async routing: Tầng 1 → Tầng 2 → Tầng 3 (LLM).
        Dành cho production real-time routing.
        """
        # Tầng 1
        if pathology:
            tier1 = tier1_pathology_lookup(pathology)
            if tier1:
                return {
                    "specialty_name": tier1["name"],
                    "specialty_code": tier1["code"],
                    "confidence": 1.0,
                    "tier": 1,
                    "reasoning": f"DDXPlus pathology lookup: {pathology}",
                }

        # Tầng 2
        tier2 = tier2_semantic_route(query)
        if tier2:
            name, code, score = tier2
            # Nếu confidence cao (>= 0.25) → tin tưởng Tier 2
            if score >= 0.25:
                return {
                    "specialty_name": name,
                    "specialty_code": code,
                    "confidence": score,
                    "tier": 2,
                    "reasoning": f"High-confidence semantic match (score={score:.3f})",
                }

        # Tầng 3: LLM routing
        tier3 = await tier3_llm_route(query)
        if tier3:
            spec_name, confidence, reasoning = tier3
            return {
                "specialty_name": spec_name,
                "specialty_code": _get_code_for_specialty(spec_name),
                "confidence": confidence,
                "tier": 3,
                "reasoning": f"LLM: {reasoning}",
            }

        # Nếu Tier 2 có kết quả nhưng dưới threshold cao → vẫn dùng
        if tier2:
            name, code, score = tier2
            return {
                "specialty_name": name,
                "specialty_code": code,
                "confidence": score,
                "tier": 2,
                "reasoning": f"Low-confidence semantic fallback (score={score:.3f})",
            }

        # Fallback cuối
        return {
            "specialty_name": "Sức khỏe tổng quát",
            "specialty_code": "TONG_QUAT",
            "confidence": 0.0,
            "tier": 0,
            "reasoning": "No confident match from all 3 tiers",
        }


def _get_code_for_specialty(name: str) -> str:
    """Lấy specialty code từ tên."""
    for spec_name, spec_info in SPECIALTY_PROTOTYPES.items():
        if spec_name == name or name.lower() in spec_name.lower():
            return spec_info["code"]
    return "TONG_QUAT"


# Singleton
_router_instance: SpecialtyRouter | None = None


def get_specialty_router() -> SpecialtyRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = SpecialtyRouter()
    return _router_instance
