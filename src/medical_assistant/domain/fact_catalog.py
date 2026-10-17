"""Single Source of Truth Fact Catalog for P-124 Clinical Fact & Triage Systems.

This module defines standardized clinical facts, anatomical grounding, systems,
synonyms, and emergency red-flag indicators. It provides automatic regex compilation
with strict word boundaries and diacritics normalization, preventing vocabulary collisions.
"""

from __future__ import annotations

import re
import unicodedata
from typing import NamedTuple


def normalize_term(text: str) -> str:
    """Strip Vietnamese diacritics and normalize whitespace."""
    val = unicodedata.normalize("NFD", (text or "").lower())
    val = "".join(c for c in val if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", val.replace("đ", "d")).strip()


class ClinicalFactItem(NamedTuple):
    code: str
    name_vi: str
    primary_system: str
    body_region: str
    synonyms: tuple[str, ...]
    negation_cues: tuple[str, ...] = ()
    is_red_flag: bool = False
    red_flag_severity: str = "none"  # "critical", "warning", "none"


CLINICAL_FACT_CATALOG: dict[str, ClinicalFactItem] = {
    # ================= TIM MẠCH (Cardiology) =================
    "chest_pain": ClinicalFactItem(
        code="chest_pain",
        name_vi="Đau ngực / Thắt ngực",
        primary_system="cardiology",
        body_region="thorax_chest",
        synonyms=(
            "dau nguc",
            "tuc nguc",
            "that nguc",
            "dau tuc nguc",
            "dau that nguc",
            "nang nguc",
            "de nang nguc",
            "bop nghet nguc",
            "dau vung nguc",
            "chest pain",
            "chest tightness",
            "chest pressure",
            "chest heaviness",
            "chest discomfort",
        ),
        negation_cues=("khong dau nguc", "khong tuc nguc", "khong thay tuc nguc", "het dau nguc"),
        is_red_flag=True,
        red_flag_severity="critical",
    ),
    "palpitations": ClinicalFactItem(
        code="palpitations",
        name_vi="Hồi hộp / Đánh trống ngực",
        primary_system="cardiology",
        body_region="thorax_chest",
        synonyms=("hoi hop", "danh trong nguc", "tim dap nhanh", "tim dap don dap", "palpitations"),
        negation_cues=("khong danh trong nguc", "khong hoi hop"),
        is_red_flag=False,
    ),
    # ================= HÔ HẤP (Respiratory) =================
    "shortness_of_breath": ClinicalFactItem(
        code="shortness_of_breath",
        name_vi="Khó thở / Hụt hơi / Thở dốc",
        primary_system="respiratory",
        body_region="respiratory",
        synonyms=(
            "kho tho",
            "hut hoi",
            "tho gap",
            "tho doc",
            "tho rit",
            "nghen tho",
            "tho kho khe",
            "shortness of breath",
            "dyspnea",
            "breathless",
        ),
        negation_cues=("khong kho tho", "tho binh thuong", "het kho tho"),
        is_red_flag=True,
        red_flag_severity="critical",
    ),
    "cough": ClinicalFactItem(
        code="cough",
        name_vi="Ho (khan hoặc có đờm)",
        primary_system="respiratory",
        body_region="respiratory",
        synonyms=("ho khan", "ho co dom", "bi ho", "con ho", "ho nhieu", "ho hung hang", "cough"),
        negation_cues=("khong ho", "khong bi ho", "het ho", "khong con ho"),
        is_red_flag=False,
    ),
    "hemoptysis": ClinicalFactItem(
        code="hemoptysis",
        name_vi="Ho ra máu",
        primary_system="respiratory",
        body_region="respiratory",
        synonyms=("ho ra mau", "khac ra mau", "ho khac ra mau", "hemoptysis"),
        negation_cues=("khong ho ra mau",),
        is_red_flag=True,
        red_flag_severity="critical",
    ),
    # ================= THẦN KINH (Neurology) =================
    "headache": ClinicalFactItem(
        code="headache",
        name_vi="Đau đầu / Nhức đầu",
        primary_system="neurology",
        body_region="head",
        synonyms=(
            "dau dau",
            "nhuc dau",
            "dau nua dau",
            "buot dau",
            "nang dau",
            "headache",
            "migraine",
        ),
        negation_cues=("khong dau dau", "khong nhuc dau", "khong bi dau dau", "het dau dau", "khong con dau dau"),
        is_red_flag=False,
    ),
    "dizziness": ClinicalFactItem(
        code="dizziness",
        name_vi="Chóng mặt / Mất thăng bằng / Choáng váng",
        primary_system="neurology",
        body_region="vestibular",
        synonyms=(
            "chong mat",
            "nhuc dau hoa mat",
            "hoa mat",
            "chao dao",
            "mat thang bang",
            "quay cuong",
            "choang vang",
            "dizzy",
            "dizziness",
            "vertigo",
        ),
        negation_cues=("khong chong mat", "het chong mat", "khong con chong mat"),
        is_red_flag=False,
    ),
    "syncope": ClinicalFactItem(
        code="syncope",
        name_vi="Ngất / Bất tỉnh / Mất ý thức",
        primary_system="neurology",
        body_region="systemic",
        synonyms=(
            "ngat xiu",
            "bat tinh",
            "ngat di",
            "lim di",
            "hon me",
            "mat y thuc",
            "ngat",
            "syncope",
            "fainting",
            "loss of consciousness",
        ),
        negation_cues=("khong ngat", "khong bat tinh", "tinh tao"),
        is_red_flag=True,
        red_flag_severity="critical",
    ),
    "stroke_signs": ClinicalFactItem(
        code="stroke_signs",
        name_vi="Dấu hiệu đột quỵ / Liệt nửa người / Méo miệng",
        primary_system="neurology",
        body_region="systemic",
        synonyms=(
            "meo mieng",
            "lech mieng",
            "liet nua nguoi",
            "yeu nua nguoi",
            "noi ngo",
            "kho noi",
            "noi kho nghe",
            "mat thi luc dot ngot",
            "stroke",
        ),
        negation_cues=("khong meo mieng", "khong liet"),
        is_red_flag=True,
        red_flag_severity="critical",
    ),
    "seizure": ClinicalFactItem(
        code="seizure",
        name_vi="Co giật / Động kinh",
        primary_system="neurology",
        body_region="systemic",
        synonyms=("co giat", "len con co giat", "dong kinh", "sui bot mep", "seizure", "convulsion"),
        negation_cues=("khong co giat",),
        is_red_flag=True,
        red_flag_severity="critical",
    ),
    "numbness_weakness": ClinicalFactItem(
        code="numbness_weakness",
        name_vi="Tê bì / Yếu tay chân",
        primary_system="neurology",
        body_region="systemic",
        synonyms=("te yeu", "te bi", "yeu tay chan", "te tay", "te chan"),
        negation_cues=("khong te", "khong yeu", "khong te yeu", "tay chan binh thuong"),
        is_red_flag=False,
    ),
    # ================= TIÊU HÓA (Gastroenterology) =================
    "abdominal_pain": ClinicalFactItem(
        code="abdominal_pain",
        name_vi="Đau bụng / Dạ dày / Thượng vị",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=(
            "dau bung",
            "dau thuong vi",
            "bung dau",
            "dau da day",
            "dau quanh ron",
            "dau ha vi",
            "stomach ache",
            "stomach pain",
            "abdominal pain",
        ),
        negation_cues=("khong dau bung", "khong bi dau bung", "het dau bung", "khong con dau bung"),
        is_red_flag=False,
    ),
    "severe_abdominal_pain": ClinicalFactItem(
        code="severe_abdominal_pain",
        name_vi="Đau bụng dữ dội / Quặn thắt cấp",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=("dau bung du doi", "bung dau quan du doi", "dau bung tang nhanh", "dau bung cap"),
        negation_cues=("khong dau du doi", "khong quan du doi"),
        is_red_flag=True,
        red_flag_severity="warning",
    ),
    "constipation": ClinicalFactItem(
        code="constipation",
        name_vi="Táo bón / Khó đi ngoài",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=("tao bon", "kho di ngoai", "ngay moi di cau", "ngay moi di ngoai"),
        negation_cues=("khong tao bon", "het tao bon", "di ngoai binh thuong"),
        is_red_flag=False,
    ),
    "hard_stool": ClinicalFactItem(
        code="hard_stool",
        name_vi="Phân khô / Cứng",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=("phan kho", "phan cung", "phan kho cung", "hard stool"),
        negation_cues=("phan mem", "khong kho"),
    ),
    "straining": ClinicalFactItem(
        code="straining",
        name_vi="Phải rặn nhiều khi đi ngoài",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=("phai ran", "ran kho", "ran met", "ran muon xiu", "ran nhieu", "straining"),
        negation_cues=("khong phai ran", "khong can ran"),
    ),
    "vomiting": ClinicalFactItem(
        code="vomiting",
        name_vi="Nôn / Buồn nôn ói",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=("non oi", "bi non", "non", "oi", "vomiting"),
        negation_cues=("khong non", "khong bi non", "khong oi"),
    ),
    "hematemesis": ClinicalFactItem(
        code="hematemesis",
        name_vi="Nôn ra máu / Ói ra máu",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=("non ra mau", "oi ra mau", "non mau", "hematemesis"),
        negation_cues=("khong non ra mau",),
        is_red_flag=True,
        red_flag_severity="critical",
    ),
    "blood_in_stool": ClinicalFactItem(
        code="blood_in_stool",
        name_vi="Đi ngoài ra máu / Phân đen",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=("di ngoai ra mau", "phan co mau", "phan den", "di cau ra mau", "dinh chut mau tren giay"),
        negation_cues=("khong di ngoai ra mau", "khong co mau trong phan"),
        is_red_flag=True,
        red_flag_severity="warning",
    ),
    "diarrhea": ClinicalFactItem(
        code="diarrhea",
        name_vi="Tiêu chảy / Đi ngoài phân lỏng",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=("tieu chay", "di ngoai phan long", "di long", "tieu chay cap", "di phan long"),
        negation_cues=("khong tieu chay", "khong di ngoai phan long"),
    ),
    "heartburn": ClinicalFactItem(
        code="heartburn",
        name_vi="Ợ chua / Ợ nóng / Trào ngược",
        primary_system="gastroenterology",
        body_region="abdomen",
        synonyms=("o chua", "o nong", "trao nguoc", "trao nguoc da day"),
        negation_cues=("khong o chua", "khong o nong"),
    ),
    # ================= CƠ XƯƠNG KHỚP (Musculoskeletal) =================
    "muscle_pain": ClinicalFactItem(
        code="muscle_pain",
        name_vi="Đau cơ / Đau bắp đùi / Đau chân",
        primary_system="musculoskeletal",
        body_region="lower_limb",
        synonyms=(
            "bap dui",
            "dau dui",
            "co dui",
            "dau bap dui",
            "dau co dui",
            "bap chan",
            "dau bap chan",
            "dau cang chan",
            "cang chan",
            "dau co",
            "dau co bap",
            "dau bap tay",
            "dau chan",
            "thigh pain",
            "muscle pain",
            "leg pain",
            "calf pain",
            "muscle ache",
            "sore muscle",
        ),
        negation_cues=("khong dau co", "khong dau dui", "khong dau bap dui", "khong dau chan", "het dau co"),
    ),
    "joint_pain": ClinicalFactItem(
        code="joint_pain",
        name_vi="Đau khớp / Khớp gối / Sưng khớp",
        primary_system="musculoskeletal",
        body_region="lower_limb",
        synonyms=(
            "dau khop",
            "dau xuong khop",
            "nhuc khop",
            "dau dau goi",
            "dau goi",
            "khop goi",
            "moi goi",
            "sung dau goi",
            "sung goi",
            "dau khop co tay",
            "dau khop co chan",
            "knee pain",
            "joint pain",
        ),
        negation_cues=("khong dau khop", "het dau khop", "khong con dau khop"),
    ),
    "back_pain": ClinicalFactItem(
        code="back_pain",
        name_vi="Đau lưng / Mỏi lưng / Cột sống",
        primary_system="musculoskeletal",
        body_region="spine_back",
        synonyms=("dau lung", "moi lung", "dau cot song", "dau that lung", "back pain"),
        negation_cues=("khong dau lung", "het dau lung", "khong con dau lung"),
    ),
    "neck_shoulder_pain": ClinicalFactItem(
        code="neck_shoulder_pain",
        name_vi="Đau mỏi cổ vai gáy",
        primary_system="musculoskeletal",
        body_region="spine_back",
        synonyms=("dau vai gay", "moi vai gay", "moi co", "co vai gay", "dau co vai gay"),
        negation_cues=("khong dau vai gay", "het dau vai gay", "khong con dau vai gay"),
    ),
    # ================= TAI MŨI HỌNG (Ear Nose Throat) =================
    "sore_throat": ClinicalFactItem(
        code="sore_throat",
        name_vi="Đau họng / Rát họng / Viêm họng",
        primary_system="ear_nose_throat",
        body_region="head",
        synonyms=(
            "dau hong",
            "rat hong",
            "kho chiu o hong",
            "viem hong",
            "sore throat",
            "dau hoc",  # typo tolerance
        ),
        negation_cues=("khong dau hong", "het dau hong", "khong con dau hong"),
    ),
    # ================= DA LIỄU (Dermatology) =================
    "skin_lesion": ClinicalFactItem(
        code="skin_lesion",
        name_vi="Mẩn ngứa / Mề đay / Tổn thương da",
        primary_system="dermatology",
        body_region="skin",
        synonyms=(
            "bong troc",
            "bong da",
            "troc da",
            "troc vay",
            "vay nen",
            "ngua da",
            "man ngua",
            "viem da",
            "phat ban",
            "noi me day",
            "bi me day",
            "man me day",
            "di ung me day",
            "skin peeling",
            "rash",
        ),
        negation_cues=("khong bi ngua da", "khong phat ban"),
    ),
    "hair_loss": ClinicalFactItem(
        code="hair_loss",
        name_vi="Rụng tóc / Hói đầu",
        primary_system="dermatology",
        body_region="head",
        synonyms=("rung toc", "toc rung", "hair loss", "alopecia", "hoi dau"),
        negation_cues=("khong rung toc",),
    ),
    # ================= TOÀN THÂN & KHÁC =================
    "fever": ClinicalFactItem(
        code="fever",
        name_vi="Sốt / Sốt cao / Cơn sốt",
        primary_system="general_medicine",
        body_region="systemic",
        synonyms=("bi sot", "sot cao", "len con sot", "nhiet do cao", "sot", "fever"),
        negation_cues=("khong sot", "khong bi sot", "het sot", "khong con sot"),
    ),
    "insomnia": ClinicalFactItem(
        code="insomnia",
        name_vi="Mất ngủ / Khó ngủ",
        primary_system="psychiatry",
        body_region="systemic",
        synonyms=("mat ngu", "kho ngu", "khong ngu duoc", "thuc trang dem", "ngu kem", "insomnia"),
        negation_cues=("khong mat ngu", "ngu tot", "ngu binh thuong"),
    ),
}


def build_compiled_fact_patterns() -> tuple[dict[str, list[re.Pattern]], dict[str, list[re.Pattern]], list[re.Pattern]]:
    """Biên dịch catalog thành regex pattern an toàn với word boundaries (\b).

    Trả về:
    - positive_patterns: dict[code, list[Pattern]]
    - negation_patterns: dict[code, list[Pattern]]
    - red_flag_patterns: list[Pattern]
    """
    pos_compiled: dict[str, list[re.Pattern]] = {}
    neg_compiled: dict[str, list[re.Pattern]] = {}
    red_flag_compiled: list[re.Pattern] = []

    for code, item in CLINICAL_FACT_CATALOG.items():
        pos_list = []
        for term in item.synonyms:
            norm = normalize_term(term)
            if not norm:
                continue
            # Bọc \b chặt chẽ ở 2 đầu từ (tránh nhầm "dau co" với "dau co hong")
            if norm == "dau co":
                pat = re.compile(rf"\b{re.escape(norm)}\b(?!\s*hong)", re.IGNORECASE)
            else:
                pat = re.compile(rf"\b{re.escape(norm)}\b", re.IGNORECASE)
            pos_list.append(pat)
            if item.is_red_flag:
                red_flag_compiled.append(pat)
        pos_compiled[code] = pos_list

        neg_list = []
        for term in item.negation_cues:
            norm = normalize_term(term)
            if not norm:
                continue
            neg_list.append(re.compile(rf"\b{re.escape(norm)}\b", re.IGNORECASE))
        neg_compiled[code] = neg_list

    return pos_compiled, neg_compiled, red_flag_compiled


# Khởi tạo in-memory pre-compiled patterns
COMPILED_POS_PATTERNS, COMPILED_NEG_PATTERNS, COMPILED_RED_FLAGS = build_compiled_fact_patterns()
