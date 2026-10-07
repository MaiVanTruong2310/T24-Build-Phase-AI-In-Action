"""Deterministic helpers for linking Vinmec workplace labels to facilities."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("đ", "d")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


SITE_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ocean_park_2", ("ocean park 2", "ocean city")),
    ("times_city", ("times city",)),
    ("smart_city", ("smart city",)),
    ("central_park", ("central park", "sai gon", "tan cang")),
    ("royal_island", ("royal island", "dao vu yen", "vu yen island")),
    ("royal_city", ("royal city",)),
    ("grand_park", ("grand park",)),
    ("duong_dong", ("duong dong",)),
    ("ocean_park", ("ocean park",)),
    ("ha_long", ("ha long",)),
    ("hai_phong", ("hai phong",)),
    ("nha_trang", ("nha trang",)),
    ("phu_quoc", ("phu quoc",)),
    ("da_nang", ("da nang",)),
    ("can_tho", ("can tho",)),
    ("riverside", ("riverside",)),
)

SPECIAL_TIMES_CITY_CENTERS: tuple[str, ...] = (
    "sao phuong dong",
    "suc khoe tinh than",
    "te bao goc",
    "cong nghe cao vinmec",
    "trung tam cong nghe cao",
    "ngan hang mo",
    "ngan hang sinh hoc",
    "huyet hoc",
    "y hoc bao thai",
    "tieu chuan chat luong",
    "he thong y te vinmec",
    "vinmec view",
    "view dental",
    "di truyen y hoc",
    "di truyen phan tu",
    "lieu phap te bao",
    "nha khoa tham my",
)


def facility_key(value: Any) -> tuple[str, str] | None:
    """Return ``(site, kind)`` when a canonical Vinmec site is explicit or recognized center."""
    text = normalize_text(value)
    if not text:
        return None
    site = next(
        (site_name for site_name, markers in SITE_MARKERS if any(marker in text for marker in markers)),
        None,
    )
    if site:
        is_general_clinic = "phong kham da khoa" in text or "general clinic" in text
        clinic_only_sites = {"royal_island", "royal_city", "grand_park", "duong_dong", "ocean_park"}
        kind = "clinic" if is_general_clinic or site in clinic_only_sites else "hospital"
        return site, kind

    if any(marker in text for marker in SPECIAL_TIMES_CITY_CENTERS):
        return "times_city", "hospital"

    return None


def canonical_facilities(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Choose one canonical row per physical facility, preferring Vietnamese rows."""
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = facility_key(row.get("name"))
        if not key:
            continue
        current = selected.get(key)
        code = str(row.get("code") or "")
        score = int(not code.startswith("VINMEC_")) + int(
            normalize_text(row.get("name")).startswith(("benh vien", "phong kham"))
        )
        current_code = str((current or {}).get("code") or "")
        current_score = int(bool(current) and not current_code.startswith("VINMEC_")) + int(
            bool(current) and normalize_text(current.get("name")).startswith(("benh vien", "phong kham"))
        )
        if current is None or score > current_score:
            selected[key] = row
    return selected


def match_facility(value: Any, facilities: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any] | None:
    key = facility_key(value)
    return facilities.get(key) if key else None


def workplace_department(value: Any) -> str | None:
    """Extract the department/center prefix without treating the facility as a department."""
    text = " ".join(str(value or "").split())
    if not text:
        return None
    normalized = normalize_text(text)
    if normalized.startswith(("benh vien", "phong kham da khoa")):
        return None
    if normalized.startswith("vinmec ") and not any(m in normalized for m in SPECIAL_TIMES_CITY_CENTERS):
        return None
    parts = re.split(
        r"\s*[-,]\s*(?=(?:Bệnh viện|Bệnh viện|Phòng khám Đa khoa|Vinmec\s+\w+\s+(?:Hospital|Clinic))\b)",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )
    department = parts[0].strip(" -,.") if len(parts) > 1 else ""
    if not department and any(k in normalized for k in ("trung tam", "vien", "khoa", "phong", "khoi")):
        department = text.strip(" -,.")
    return department or None


def extract_workplaces_from_record(record: dict[str, Any]) -> list[str]:
    """Extract active workplaces from crawl record with multi-field fallback."""
    sections = record.get("sections") or {}
    values = record.get("workplace") or sections.get("Nơi làm việc") or []
    if isinstance(values, str):
        values = [values]
    workplaces = [" ".join(str(v).split()) for v in values if str(v).strip()]
    if workplaces:
        return workplaces

    # Fallback: check 'Chức vụ'
    chuc_vu = sections.get("Chức vụ") or []
    if isinstance(chuc_vu, str):
        chuc_vu = [chuc_vu]
    for cv in chuc_vu:
        if facility_key(cv):
            workplaces.append(cv)

    # Fallback: check 'Kinh nghiệm làm việc' for current roles
    kinh_nghiem = sections.get("Kinh nghiệm làm việc") or []
    if isinstance(kinh_nghiem, str):
        kinh_nghiem = [kinh_nghiem]
    for kn in reversed(kinh_nghiem):
        norm = normalize_text(kn)
        if any(w in norm for w in ["den nay", "hien nay", "hien tai", "nay"]):
            if facility_key(kn):
                workplaces.append(kn)

    # Fallback: check 'overview'
    overview = record.get("overview") or ""
    if not workplaces and overview:
        for sentence in re.split(r"[\n\.]+", overview):
            norm = normalize_text(sentence)
            if any(w in norm for w in ["hien la", "hien nay", "cong tac tai", "lam viec tai", "gia nhap"]):
                if facility_key(sentence):
                    workplaces.append(sentence.strip())
                    break

    # Fallback: check specialties
    if not workplaces:
        specs = record.get("specialties") or sections.get("Chuyên khoa") or []
        for sp in specs:
            if facility_key(sp):
                workplaces.append(sp)
                break

    # Fallback: any mention in kinh_nghiem
    if not workplaces:
        for kn in reversed(kinh_nghiem):
            if facility_key(kn):
                workplaces.append(kn)
                break

    return workplaces
