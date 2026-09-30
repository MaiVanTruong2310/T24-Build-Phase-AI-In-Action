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
    ("central_park", ("central park",)),
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


def facility_key(value: Any) -> tuple[str, str] | None:
    """Return ``(site, kind)`` only when a canonical Vinmec site is explicit."""
    text = normalize_text(value)
    if not text or "vinmec" not in text:
        return None
    site = next(
        (site_name for site_name, markers in SITE_MARKERS if any(marker in text for marker in markers)),
        None,
    )
    if not site:
        return None
    is_general_clinic = "phong kham da khoa" in text or "general clinic" in text
    clinic_only_sites = {"royal_island", "royal_city", "grand_park", "duong_dong", "ocean_park"}
    kind = "clinic" if is_general_clinic or site in clinic_only_sites else "hospital"
    return site, kind


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
            bool(current)
            and normalize_text(current.get("name")).startswith(("benh vien", "phong kham"))
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
    if normalized.startswith(("benh vien", "phong kham da khoa", "vinmec ")):
        return None
    parts = re.split(
        r"\s*[-,]\s*(?=(?:Bệnh viện|Bệnh viện|Phòng khám Đa khoa|Vinmec\s+\w+\s+(?:Hospital|Clinic))\b)",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )
    department = parts[0].strip(" -,.") if len(parts) > 1 else ""
    return department or None
