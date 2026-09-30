"""Extract source-grounded Vietnamese disease data from Vinmec HTML."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

BASE = "https://www.vinmec.com"
DETAIL_PREFIX = "/vie/benh/"
LIST_PREFIX = "/vie/tra-cuu-benh/"
SECTION_KEYS = (
    ("tổng quan", "overview"),
    ("nguyên nhân", "causes"),
    ("triệu chứng", "symptoms"),
    ("đối tượng nguy cơ", "risk_groups"),
    ("phòng ngừa", "prevention"),
    ("chẩn đoán", "diagnosis"),
    ("điều trị", "treatment"),
)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def canonical(url: str) -> str:
    parsed = urlparse(url)
    return BASE + parsed.path.rstrip("/")


def extract_disease_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: set[str] = set()
    for anchor in soup.select("a[href]"):
        parsed = urlparse(urljoin(page_url, anchor["href"]))
        path = parsed.path.rstrip("/")
        tail = path[len(DETAIL_PREFIX) :] if path.startswith(DETAIL_PREFIX) else ""
        if parsed.netloc.lower() == "www.vinmec.com" and tail and "/" not in tail:
            urls.add(BASE + path)
    return sorted(urls)


def extract_listing_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: set[str] = set()
    for anchor in soup.select("a[href]"):
        parsed = urlparse(urljoin(page_url, anchor["href"]))
        path = parsed.path.rstrip("/")
        tail = path[len(LIST_PREFIX) :] if path.startswith(LIST_PREFIX) else ""
        if parsed.netloc.lower() == "www.vinmec.com" and tail and "/" not in tail:
            urls.add(BASE + path)
    return sorted(urls)


def _section_key(heading: str) -> str:
    lower = heading.casefold()
    for phrase, key in SECTION_KEYS:
        if phrase in lower:
            return key
    return "other"


def parse_disease(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select(".item_detial_sick")
    if not blocks:
        raise ValueError(f"Disease sections were not found at {url}")
    sections = []
    for block in blocks:
        heading_node = block.select_one("h2.title_detail_sick")
        body = block.select_one(".body")
        if not heading_node or not body:
            continue
        heading = clean(heading_node.get_text(" ", strip=True))
        content = []
        # Keep paragraph/list order, but do not repeat paragraphs nested in <li>.
        for node in body.find_all(["p", "li", "h3", "h4"]):
            if node.name == "li" and node.find("p"):
                continue
            value = clean(node.get_text(" ", strip=True))
            if value and (not content or value != content[-1]):
                content.append(value)
        if not content:
            value = clean(body.get_text(" ", strip=True))
            content = [value] if value else []
        if heading or content:
            sections.append({"key": _section_key(heading), "heading": heading, "content": content})
    if not sections or not any(section["content"] for section in sections):
        raise ValueError(f"Disease content was empty at {url}")
    title_node = soup.select_one("h1")
    title = clean(title_node.get_text(" ", strip=True)) if title_node else ""
    if not title:
        heading = sections[0]["heading"]
        title = re.sub(r"^Tổng quan bệnh\s+", "", heading, flags=re.IGNORECASE)
    if not title:
        raise ValueError(f"Disease name was not found at {url}")
    return {
        "disease_key": urlparse(url).path.rstrip("/").rsplit("/", 1)[-1],
        "language": "vi",
        "name": title,
        "sections": sections,
        "source_url": canonical(url),
    }
