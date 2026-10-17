"""HTML parsing helpers for Vinmec professional profiles."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

LANGUAGE_PATHS = {
    "vi": "/vie/chuyen-gia-y-te/",
    "en": "/eng/professionals/",
}

FIELD_ALIASES = {
    "positions": {"positions", "chức vụ"},
    "specialties": {"specialties", "chuyên khoa"},
    "workplace": {"workplace", "nơi công tác", "cơ sở công tác"},
    "years_of_experience": {"years of experience", "số năm kinh nghiệm"},
    "services": {"services", "dịch vụ"},
    "education": {
        "education background",
        "education",
        "quá trình đào tạo",
        "đào tạo",
    },
    "experience": {"experience", "quá trình công tác", "kinh nghiệm"},
    "memberships": {
        "member of",
        "memberships",
        "thành viên của",
        "thành viên tổ chức",
    },
    "awards": {
        "awards and achievements",
        "awards",
        "giải thưởng và thành tích",
        "giải thưởng và ghi nhận",
    },
    "publications": {
        "researches and publications",
        "research and publications",
        "công trình nghiên cứu",
        "nghiên cứu và xuất bản",
    },
}


def clean_text(value: str) -> str:
    """Collapse HTML whitespace while retaining readable text."""
    return re.sub(r"\s+", " ", value).strip()


def canonical_field(label: str) -> str | None:
    normalized = clean_text(label).casefold().rstrip(":")
    for field, aliases in FIELD_ALIASES.items():
        if normalized in aliases:
            return field
    return None


def extract_profile_links(html: str, page_url: str, language: str) -> list[str]:
    """Return unique profile URLs found on a Vinmec listing page."""
    prefix = LANGUAGE_PATHS[language]
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(page_url, anchor["href"])
        parsed = urlparse(absolute)
        path = parsed.path
        if parsed.netloc.casefold() != "www.vinmec.com":
            continue
        if not path.startswith(prefix) or path.rstrip("/") == prefix.rstrip("/"):
            continue
        tail = path[len(prefix) :].strip("/")
        if not tail or tail.startswith("page_") or "/" in tail:
            continue
        links.add(f"https://www.vinmec.com{path.rstrip('/')}")
    return sorted(links)


def _text_items(container: Tag | None) -> list[str]:
    if container is None:
        return []
    candidates = container.find_all(["p", "li"], recursive=True)
    items = [clean_text(node.get_text(" ", strip=True)) for node in candidates]
    items = [item for item in items if item]
    if items:
        return list(dict.fromkeys(items))
    text = clean_text(container.get_text(" ", strip=True))
    return [text] if text else []


def _inline_value(heading: Tag) -> list[str]:
    values: list[str] = []
    for sibling in heading.next_siblings:
        if not isinstance(sibling, Tag):
            continue
        classes = sibling.get("class", [])
        if "line_ver" in classes:
            break
        value = clean_text(sibling.get_text(" ", strip=True))
        if value:
            values.append(value)
    return list(dict.fromkeys(values))


def _profile_id(url: str) -> str | None:
    match = re.search(r"-(\d+)-(?:vi|en)/?$", urlparse(url).path)
    return match.group(1) if match else None


def parse_profile(html: str, url: str, language: str) -> dict[str, Any]:
    """Parse one Vietnamese or English Vinmec professional profile."""
    soup = BeautifulSoup(html, "html.parser")
    profile = soup.select_one("section.profile_doctor")
    if profile is None:
        raise ValueError(f"Profile section was not found at {url}")

    name_node = profile.select_one(".f22.bold.cl-blue")
    if name_node is None:
        raise ValueError(f"Professional name was not found at {url}")

    credentials = [
        clean_text(node.get_text(" ", strip=True)) for node in profile.select(".avar_doctor .bold.cl-blue span")
    ]
    credentials = [item for item in credentials if item]
    image_node = profile.select_one(".avar_doctor img[src]")
    overview_node = profile.select_one(".desc_detail")

    record: dict[str, Any] = {
        "profile_id": _profile_id(url),
        "language": language,
        "name": clean_text(name_node.get_text(" ", strip=True)),
        "credentials": credentials,
        "overview": "\n".join(_text_items(overview_node)),
        "positions": [],
        "specialties": [],
        "workplace": [],
        "years_of_experience": [],
        "services": [],
        "education": [],
        "experience": [],
        "memberships": [],
        "awards": [],
        "publications": [],
        "image_url": urljoin(url, image_node["src"]) if image_node else None,
        "source_url": url,
        "sections": {},
    }

    right_column = profile.select_one(".col-7")
    if right_column:
        for heading in right_column.select(".f18.bold.cl-blue"):
            label = clean_text(heading.get_text(" ", strip=True))
            values = _inline_value(heading)
            if not values:
                continue
            record["sections"][label] = values
            field = canonical_field(label)
            if field:
                record[field] = values

        for button in right_column.select("button.collapsible"):
            label = clean_text(button.get_text(" ", strip=True))
            content = button.find_next_sibling(class_="content")
            values = _text_items(content)
            if not values:
                continue
            record["sections"][label] = values
            field = canonical_field(label)
            if field:
                record[field] = values

    return record
