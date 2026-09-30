"""Deterministic clinical fact extraction for safe dialogue-state management.

This layer does not diagnose. It records facts explicitly stated by the patient,
including negations, so the dialogue policy does not ask the same question twice.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFD", (text or "").lower())
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", value.replace("đ", "d")).strip()


FACT_PATTERNS = {
    # Táo bón / Tiêu hóa
    "hard_stool": [r"phan (?:kho|cung|kho cung)"],
    "straining": [r"(?:phai )?ran", r"ran (?:met|muon xiu|nhieu)"],
    "abdominal_bloating": [r"bung(?:\s+\w+){0,2}\s+(?:chuong|cang)", r"day bung", r"i ach"],
    "passing_gas": [r"van (?:danh hoi|trung tien) duoc", r"van xa hoi duoc"],
    "unable_to_pass_gas": [r"khong (?:danh hoi|trung tien) duoc"],
    "vomiting": [r"non oi", r"bi non", r"nôn"],
    "fever": [r"bi sot", r"sot cao", r"len con sot", r"nhiet do cao"],
    "weight_loss": [r"sut can", r"giam can khong chu y"],
    "blood_in_stool": [r"mau (?:do )?(?:tren giay|trong phan)", r"dinh (?:chut )?mau", r"di ngoai ra mau"],
    "severe_abdominal_pain": [r"dau bung (?:du doi|quan du doi|tang nhieu)", r"bung dau quan"],
    "mild_abdominal_pain": [
        r"dau (?:bung )?(?:am i|lam ram)",
        r"bung(?:\s+\w+){0,6}\s+dau (?:am i|lam ram)",
        r"khong quan du doi",
    ],
    "eating_normally": [r"an uong van duoc", r"van an uong duoc", r"an uong binh thuong"],
    "diarrhea": [r"tieu chay", r"di ngoai phan long", r"di long"],
    "heartburn": [r"o chua", r"o nong", r"trao nguoc"],
    "abdominal_pain": [
        r"dau bung", r"dau thuong vi", r"bung dau",
        r"bung(?:\s+\w+){0,6}\s+dau",
        r"(?:dau|bi dau)\s+(?:them\s+(?:ca\s+)?)?bung",
        r"bung\s+(?:cung\s+)?(?:bi\s+)?dau",
        r"(?:ngoai ra|them vao|va con)\s+(?:bi\s+)?dau\s+bung",
        r"stomach\s+(?:ache|pain|hurts?)", r"abdominal pain",
    ],
    "constipation": [r"tao bon", r"kho di ngoai", r"phan (?:kho|cung)", r"ngay moi di (?:cau|ngoai)"],

    # Thần kinh / Đau đầu
    "headache": [r"dau dau", r"nhuc dau", r"dau nua dau", r"buot dau", r"nang dau", r"headache", r"migraine"],
    "one_sided_headache": [r"nua dau (?:ben )?(?:trai|phai)", r"dau mot ben"],
    "nausea": [r"buon non", r"mac non", r"nausea"],
    "photophobia": [r"so anh sang", r"choi mat"],
    "vision_changes": [r"nhin mo", r"nhin doi", r"hoa mat", r"mo mat"],
    "dizziness": [r"chong mat", r"choang vang", r"dizzy", r"dizziness"],
    "numbness_weakness": [r"te (?:yeu|bi)", r"yeu nua nguoi", r"yeu tay chan", r"te tay", r"te chan"],
    "fatigue": [
        r"(?:rat |qua |thay )?met(?: moi| la| lu)?", r"co the (?:rat )?met",
        r"kiet suc", r"u oai", r"fatigue", r"lethargy", r"exhausted",
    ],
    "sore_throat": [
        r"dau hong", r"rat hong", r"kho chiu o hong", r"viem hong", r"sore throat",
        r"throat\s+(?:pain|ache|sore)",
        # Bounded tolerance for the common phrase-level typo "đau học".
        r"\bdau hoc\b",
    ],

    # Tim mạch / Hô hấp
    "chest_pain": [
        r"dau nguc", r"tuc nguc", r"that nguc",
        r"dau\s+(?:tuc|that|nang|de)\s+(?:long\s+)?nguc",
        r"(?:tuc|that|nang|de)\s+(?:vung\s+|long\s+)?nguc",
        r"chest (?:pain|tightness|pressure|heaviness|discomfort)",
    ],
    "shortness_of_breath": [r"kho tho", r"hut hoi", r"tho gap", r"shortness of breath", r"dyspnea"],
    "cough": [r"\bho khan\b", r"\bho co dom\b", r"\bbi ho\b", r"\bcon ho\b", r"\bcough\b"],

    # Cơ xương khớp
    "joint_pain": [r"dau khop", r"dau xuong khop", r"nhuc khop"],
    "back_pain": [r"dau lung", r"moi lung", r"dau cot song"],
    "neck_shoulder_pain": [r"dau vai gay", r"moi vai gay", r"moi co", r"cổ vai gáy"],
}

NEGATION_PATTERNS = {
    "vomiting": [r"khong (?:non|oi)", r"khong bi non", r"chua bi non"],
    "fever": [r"khong sot", r"het sot", r"chua tung sot", r"dau co sot"],
    "weight_loss": [r"khong sut can", r"khong giam can"],
    "severe_abdominal_pain": [r"khong (?:dau )?quan du doi", r"chi dau lam ram"],
    "unable_to_pass_gas": [r"van (?:danh hoi|trung tien) duoc"],
    "blood_in_stool": [
        r"khong (?:bi )?di ngoai ra mau",
        r"khong (?:co |thay )?mau (?:do )?(?:tren giay|trong phan)",
    ],
    "diarrhea": [r"khong (?:bi )?tieu chay", r"khong di ngoai phan long"],
    "headache": [r"khong dau dau", r"khong nhuc dau", r"khong bi dau dau", r"het dau dau", r"khong con dau dau"],
    "abdominal_pain": [r"khong dau bung", r"khong bi dau bung", r"het dau bung", r"khong con dau bung"],
    "constipation": [r"khong tao bon", r"het tao bon", r"di ngoai binh thuong"],
    "nausea": [r"khong buon non", r"khong mac non", r"khong thay non nao"],
    "fatigue": [r"khong met", r"khong thay met", r"het met", r"khong con met"],
    "chest_pain": [r"khong dau nguc", r"khong tuc nguc", r"khong thay tuc nguc"],
    "shortness_of_breath": [r"khong kho tho", r"tho binh thuong"],
    "cough": [r"khong ho", r"khong bi ho"],
    "sore_throat": [r"khong dau hong", r"het dau hong", r"khong con dau hong"],
    "back_pain": [r"khong dau lung", r"het dau lung", r"khong con dau lung"],
    "joint_pain": [r"khong dau khop", r"het dau khop", r"khong con dau khop"],
    "neck_shoulder_pain": [r"khong dau vai gay", r"het dau vai gay", r"khong con dau vai gay"],
    "vision_changes": [
        r"khong mo mat", r"mat van ro", r"nhin binh thuong", r"nhin ro",
        r"mat (?:em |toi )?nhin ro", r"mat binh thuong", r"khong (?:bi )?nhin (?:mo|doi)",
    ],
    "numbness_weakness": [
        r"khong (?:bi )?te", r"khong (?:bi )?yeu", r"khong te yeu",
        r"tay chan binh thuong", r"khong (?:bi )?te (?:\w+\s+)?tay chan",
        r"khong te tay", r"khong te chan",
    ],
}


COMPLAINT_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("constipation", "gastroenterology", tuple(FACT_PATTERNS["constipation"])),
    ("headache", "neurology", tuple(FACT_PATTERNS["headache"])),
    ("sore_throat", "ear_nose_throat", tuple(FACT_PATTERNS["sore_throat"])),
    ("chest_pain", "cardiology", tuple(FACT_PATTERNS["chest_pain"])),
    ("shortness_of_breath", "respiratory", tuple(FACT_PATTERNS["shortness_of_breath"])),
    ("abdominal_pain", "gastroenterology", tuple(FACT_PATTERNS["abdominal_pain"])),
    ("back_pain", "musculoskeletal", tuple(FACT_PATTERNS["back_pain"])),
    ("joint_pain", "musculoskeletal", tuple(FACT_PATTERNS["joint_pain"])),
    ("cough", "respiratory", tuple(FACT_PATTERNS["cough"])),
    ("fever", "general_medicine", tuple(FACT_PATTERNS["fever"])),
    ("neck_shoulder_pain", "musculoskeletal", tuple(FACT_PATTERNS["neck_shoulder_pain"])),
)

COMPLAINT_SYSTEMS = {code: system for code, system, _ in COMPLAINT_RULES}


def _is_resolution(text: str, code: str) -> bool:
    return bool(
        re.search(r"\b(?:het|khong con|da khoi)\b", text)
        and code in {"headache", "abdominal_pain", "constipation", "sore_throat", "back_pain", "joint_pain", "neck_shoulder_pain"}
    )


def _normalize_complaint(value: Any) -> Dict[str, Any] | None:
    if isinstance(value, str):
        code = value.strip()
        return {
            "code": code,
            "system": COMPLAINT_SYSTEMS.get(code, "unknown"),
            "status": "active",
            "first_seen_turn": None,
            "last_seen_turn": None,
            "severity": None,
            "duration_days": None,
            "evidence": [],
            "confidence": 1.0,
            "source": "legacy",
        } if code else None
    if not isinstance(value, dict) or not value.get("code"):
        return None
    code = str(value["code"])
    normalized = dict(value)
    normalized.setdefault("system", COMPLAINT_SYSTEMS.get(code, "unknown"))
    normalized.setdefault("status", "active")
    normalized.setdefault("first_seen_turn", None)
    normalized.setdefault("last_seen_turn", None)
    normalized.setdefault("severity", None)
    normalized.setdefault("duration_days", None)
    normalized.setdefault("evidence", [])
    normalized.setdefault("confidence", 1.0)
    normalized.setdefault("source", "unknown")
    return normalized


class ClinicalFactService:
    def extract(self, text: str, turn_index: int | None = None) -> Dict[str, Any]:
        normalized = _normalize(text)
        positive: set[str] = set()
        negative: set[str] = set()

        for fact, patterns in FACT_PATTERNS.items():
            if any(re.search(pattern, normalized) for pattern in patterns):
                positive.add(fact)
        for fact, patterns in NEGATION_PATTERNS.items():
            if any(re.search(pattern, normalized) for pattern in patterns):
                negative.add(fact)
                positive.discard(fact)

        # Kiểm tra bổ sung qua ClinicalNegationService để chống sót câu phủ định
        from src.medical_assistant.domain.clinical_negation_service import get_clinical_negation_service
        negation_svc = get_clinical_negation_service()
        for fact in list(positive):
            patterns = FACT_PATTERNS.get(fact, [])
            for p in patterns:
                m = re.search(p, normalized)
                if m and negation_svc.is_phrase_negated(m.group(0), text):
                    negative.add(fact)
                    positive.discard(fact)
                    break

        duration_days = None
        if re.search(r"dung (?:mot )?tuan|1 tuan", normalized):
            duration_days = 7
        elif re.search(r"(?:hom qua|tu hom qua|duoc 1 ngay|mot ngay)", normalized):
            duration_days = 1
        elif re.search(r"(?:hom kia|2 ngay|hai ngay)", normalized):
            duration_days = 2
        elif re.search(r"(?:ba ngay|3 ngay)", normalized):
            duration_days = 3
        else:
            match = re.search(r"(\d+)\s+ngay", normalized)
            if match:
                duration_days = int(match.group(1))

        bowel_interval_days = None
        interval = re.search(r"(\d+)\s*(?:-|den)?\s*(\d+)?\s*ngay moi di (?:cau|ngoai)", normalized)
        if interval:
            bowel_interval_days = int(interval.group(2) or interval.group(1))
        elif re.search(r"ba bon ngay moi di (?:cau|ngoai)", normalized):
            bowel_interval_days = 4

        location = None
        abdominal_location = re.search(
            r"dau bung(?:\s+(?:o|vung))?\s+(?:ben\s+)?(trai|phai|tren|duoi)",
            normalized,
        )
        if not abdominal_location:
            abdominal_location = re.search(
                r"bung\s+(?:ben\s+)?(trai|phai|tren|duoi)(?:\s+\w+){0,6}\s+dau",
                normalized,
            )
        if abdominal_location:
            location = f"bụng bên {abdominal_location.group(1)}"
        elif re.search(r"(?:left|right)\s+(?:side\s+of\s+)?(?:the\s+)?(?:abdomen|stomach)", normalized):
            side = "left" if "left" in normalized else "right"
            location = f"{side} abdomen"

        complaints: list[Dict[str, Any]] = []
        for code, system, patterns in COMPLAINT_RULES:
            matched = next((re.search(pattern, normalized) for pattern in patterns if re.search(pattern, normalized)), None)
            is_negative = code in negative
            if not matched and not is_negative:
                continue
            status = "resolved" if is_negative and _is_resolution(normalized, code) else ("denied" if is_negative else "active")
            complaints.append({
                "code": code,
                "system": system,
                "status": status,
                "first_seen_turn": turn_index,
                "last_seen_turn": turn_index,
                "severity": (
                    "severe" if code == "abdominal_pain" and "severe_abdominal_pain" in positive
                    else "mild" if code == "abdominal_pain" and "mild_abdominal_pain" in positive
                    else None
                ),
                "duration_days": duration_days,
                "evidence": [matched.group(0) if matched else text.strip()[:240]],
                "confidence": 1.0 if matched else 0.95,
                "source": "deterministic",
            })

        active_complaints = [item["code"] for item in complaints if item["status"] == "active"]
        chief_complaint = active_complaints[0] if active_complaints else None
        explicit_primary = None
        if re.search(r"\b(?:la chinh|kho chiu hon|nang hon|uu tien)\b", normalized):
            for code, _, patterns in COMPLAINT_RULES:
                if code not in active_complaints:
                    continue
                if any(re.search(rf"(?:{pattern}).{{0,32}}\b(?:la chinh|kho chiu hon|nang hon|uu tien)\b", normalized) for pattern in patterns):
                    explicit_primary = code
                    break
            explicit_primary = explicit_primary or chief_complaint

        return {
            "chief_complaint": chief_complaint,
            "primary_complaint": explicit_primary or chief_complaint,
            "primary_complaint_explicit": explicit_primary is not None,
            "primary_complaint_explicit_code": explicit_primary,
            "complaints": complaints,
            "positive_facts": sorted(positive),
            "negative_facts": sorted(negative),
            "duration_days": duration_days,
            "bowel_interval_days": bowel_interval_days,
            "location": location,
        }

    def merge(self, existing: Dict[str, Any] | None, new: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(existing or {})
        positive = set(merged.get("positive_facts") or [])
        negative = set(merged.get("negative_facts") or [])
        for fact in new.get("positive_facts") or []:
            positive.add(fact)
            negative.discard(fact)
        for fact in new.get("negative_facts") or []:
            negative.add(fact)
            positive.discard(fact)
        merged["positive_facts"] = sorted(positive)
        merged["negative_facts"] = sorted(negative)

        existing_items = [
            item for value in (merged.get("complaints") or [])
            if (item := _normalize_complaint(value)) is not None
        ]
        if not existing_items and merged.get("chief_complaint"):
            legacy = _normalize_complaint(merged["chief_complaint"])
            if legacy:
                existing_items.append(legacy)
        by_code = {item["code"]: item for item in existing_items}
        order = [item["code"] for item in existing_items]

        incoming_values = list(new.get("complaints") or [])
        if not incoming_values and new.get("chief_complaint"):
            incoming_values = [new["chief_complaint"]]
        for value in incoming_values:
            incoming = _normalize_complaint(value)
            if not incoming:
                continue
            code = incoming["code"]
            if code not in by_code:
                by_code[code] = incoming
                order.append(code)
                continue
            current = by_code[code]
            for field in ("system", "last_seen_turn", "severity", "duration_days", "confidence"):
                if incoming.get(field) is not None:
                    current[field] = incoming[field]
            incoming_status = incoming.get("status")
            preserve_deterministic_status = bool(
                current.get("source") == "deterministic"
                and incoming.get("source") == "llm"
                and incoming.get("last_seen_turn") is None
            )
            if incoming_status and incoming_status != "uncertain" and not preserve_deterministic_status:
                current["status"] = incoming_status
            if incoming.get("source") and not preserve_deterministic_status:
                current["source"] = incoming["source"]
            if current.get("first_seen_turn") is None:
                current["first_seen_turn"] = incoming.get("first_seen_turn")
            current["evidence"] = list(dict.fromkeys([
                *(current.get("evidence") or []), *(incoming.get("evidence") or [])
            ]))[-6:]

        merged["complaints"] = [by_code[code] for code in order]
        active_codes = [
            item["code"] for item in merged["complaints"] if item.get("status") == "active"
        ]
        previous_primary = merged.get("primary_complaint") or merged.get("chief_complaint")
        requested_primary = new.get("primary_complaint") or new.get("chief_complaint")
        if new.get("primary_complaint_explicit") and requested_primary in active_codes:
            primary = requested_primary
            merged["primary_complaint_explicit_code"] = requested_primary
        else:
            primary = previous_primary if previous_primary in active_codes else (active_codes[0] if active_codes else None)
        if merged.get("primary_complaint_explicit_code") not in active_codes:
            merged["primary_complaint_explicit_code"] = None
        merged["primary_complaint_explicit"] = bool(merged.get("primary_complaint_explicit_code"))
        merged["primary_complaint"] = primary
        merged["chief_complaint"] = primary
        merged["active_complaint_codes"] = active_codes

        for key in (
            "duration_days", "bowel_interval_days", "subject",
            "location", "severity", "pain_severity_0_10", "onset",
        ):
            if new.get(key) is not None:
                merged[key] = new[key]

        if new.get("qualifiers"):
            merged["qualifiers"] = list(dict.fromkeys((merged.get("qualifiers") or []) + new["qualifiers"]))

        # Merge new arrays while keeping old elements
        if new.get("observations"):
            merged["observations"] = merged.get("observations", []) + new["observations"]
        if new.get("corrections"):
            merged["corrections"] = merged.get("corrections", []) + new["corrections"]

        return merged

    @staticmethod
    def knows_any(facts: Dict[str, Any] | None, names: Iterable[str]) -> bool:
        if not facts:
            return False
        known = set(facts.get("positive_facts") or []) | set(facts.get("negative_facts") or [])
        return any(name in known for name in names)


_clinical_fact_service = ClinicalFactService()


def get_clinical_fact_service() -> ClinicalFactService:
    return _clinical_fact_service
