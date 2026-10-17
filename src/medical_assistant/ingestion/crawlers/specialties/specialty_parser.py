"""Parse Vinmec Vietnamese and English specialty pages."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

LANGUAGE_PATHS = {"vi": "/vie/chuyen-khoa/", "en": "/eng/specialties/"}
DOCTOR_PATHS = {"vi": "/vie/chuyen-gia-y-te/", "en": "/eng/professionals/"}
SECTION_NAMES = {
    "tong_quan": "overview",
    "dich_vu": "services",
    "cong_nghe": "technologies",
}


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    path = re.sub(r"/{2,}", "/", parsed.path).rstrip("/")
    return f"https://www.vinmec.com{path}"


def extract_specialty_links(html: str, page_url: str, language: str) -> list[str]:
    """Extract unique, single-level specialty detail URLs."""
    prefix = LANGUAGE_PATHS[language]
    soup = BeautifulSoup(html, "html.parser")
    links: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        absolute = _normalize_url(urljoin(page_url, anchor["href"]))
        parsed = urlparse(absolute)
        if parsed.netloc.casefold() != "www.vinmec.com":
            continue
        if not parsed.path.startswith(prefix):
            continue
        tail = parsed.path[len(prefix) :].strip("/")
        if tail and "/" not in tail:
            links.add(absolute)
    return sorted(links)


def _content_items(container: Tag) -> list[str]:
    candidates = container.find_all(["p", "li"], recursive=True)
    items = [clean_text(node.get_text(" ", strip=True)) for node in candidates]
    items = [item for item in items if item]
    if items:
        return list(dict.fromkeys(items))
    text = clean_text(container.get_text(" ", strip=True))
    return [text] if text else []


def _parse_section(section: Tag, page_url: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, block in enumerate(section.select(".list_content_subcate"), start=1):
        title_node = block.select_one(".tit_content_subcate")
        title = clean_text(title_node.get_text(" ", strip=True)) if title_node else ""
        description = block.select_one(".desc_subcate") or block
        content = _content_items(description)
        if title and content and content[0] == title:
            content = content[1:]
        image = block.select_one("img[src]")
        blocks.append(
            {
                "index": index,
                "title": title,
                "content": content,
                "image_url": urljoin(page_url, image["src"]) if image else None,
            }
        )
    if not blocks:
        content = _content_items(section)
        if content:
            blocks.append({"index": 1, "title": "", "content": content, "image_url": None})
    return blocks


def parse_specialty(html: str, url: str, language: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one(".cover_list_news .name_cate_cover")
    if title_node is None:
        raise ValueError(f"Specialty title was not found at {url}")
    title = clean_text(title_node.get_text(" ", strip=True))
    if not title:
        raise ValueError(f"Specialty title was empty at {url}")

    cover = soup.select_one(".cover_list_news img[src]")
    record: dict[str, Any] = {
        "specialty_key": urlparse(url).path.rstrip("/").rsplit("/", 1)[-1],
        "language": language,
        "name": title,
        "cover_image_url": urljoin(url, cover["src"]) if cover else None,
        "overview": [],
        "services": [],
        "technologies": [],
        "doctor_urls": [],
        "source_url": _normalize_url(url),
    }
    for html_id, field in SECTION_NAMES.items():
        section = soup.select_one(f"section#{html_id}")
        if section:
            record[field] = _parse_section(section, url)

    doctor_prefix = DOCTOR_PATHS[language]
    doctors: set[str] = set()
    doctor_section = soup.select_one("section#bac_si")
    if doctor_section:
        for anchor in doctor_section.find_all("a", href=True):
            absolute = _normalize_url(urljoin(url, anchor["href"]))
            path = urlparse(absolute).path
            tail = path[len(doctor_prefix) :].strip("/") if path.startswith(doctor_prefix) else ""
            if tail and "/" not in tail:
                doctors.add(absolute)
    record["doctor_urls"] = sorted(doctors)
    return record
