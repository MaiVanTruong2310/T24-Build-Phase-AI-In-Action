"""Parse hospitals and clinics directly from Vinmec listing pages."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_hotline(value: str) -> str:
    """Return digits only so phone numbers can be filtered consistently."""
    return re.sub(r"\D", "", value)


def _facility_type(heading: str) -> str | None:
    normalized = heading.casefold()
    if "phòng khám" in normalized or "clinic" in normalized:
        return "clinic"
    if "bệnh viện" in normalized or "hospital" in normalized:
        return "hospital"
    return None


def _type_label(facility_type: str, language: str) -> str:
    labels = {
        "vi": {"hospital": "Bệnh viện", "clinic": "Phòng khám"},
        "en": {"hospital": "Hospital", "clinic": "Clinic"},
    }
    return labels[language][facility_type]


def _facility_name(name_node: Any) -> str:
    direct_text = " ".join(
        clean_text(str(child)) for child in name_node.find_all(string=True, recursive=False) if clean_text(str(child))
    )
    name = direct_text or clean_text(name_node.get_text(" ", strip=True))
    return re.sub(r"\s+(?:Xem thêm|View more)$", "", name, flags=re.IGNORECASE).strip()


def parse_facilities(html: str, source_url: str, language: str) -> list[dict[str, Any]]:
    """Parse all facility cards without visiting their detail pages."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []

    for section in soup.select("main section.bottom_news_main"):
        heading_node = section.select_one(".title_cate_news")
        heading = clean_text(heading_node.get_text(" ", strip=True)) if heading_node else ""
        facility_type = _facility_type(heading)
        if facility_type is None:
            continue

        for card in section.select(".list_hospital_main > .col-4"):
            name_node = card.select_one("a.name_hospital[href]")
            address_node = card.select_one(".address_hospital")
            phone_node = card.select_one(".phone_hospital")
            if name_node is None:
                continue
            name = _facility_name(name_node)
            detail_url = urljoin(source_url, name_node["href"])
            slug = urlparse(detail_url).path.rstrip("/").rsplit("/", 1)[-1]
            hotline_display = clean_text(phone_node.get_text(" ", strip=True)) if phone_node else ""
            records.append(
                {
                    "facility_key": slug,
                    "language": language,
                    "name": name,
                    "facility_type": facility_type,
                    "facility_type_label": _type_label(facility_type, language),
                    "address": (clean_text(address_node.get_text(" ", strip=True)) if address_node else ""),
                    "hotline_display": hotline_display,
                    "hotline_normalized": normalize_hotline(hotline_display),
                    "detail_url": detail_url.rstrip("/"),
                    "source_url": source_url,
                }
            )
    return records
