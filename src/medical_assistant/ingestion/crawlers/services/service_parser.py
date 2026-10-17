"""Normalize Vinmec Online product and service-detail API payloads."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

BASE_URL = "https://online.vinmec.com"
DETAIL_PREFIX = "/vn/dich-vu/"


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def canonical_service_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{BASE_URL}{parsed.path.rstrip('/')}"


def service_key_for_url(url: str) -> str | None:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    tail = path[len(DETAIL_PREFIX) :] if path.startswith(DETAIL_PREFIX) else ""
    if parsed.netloc.casefold() != "online.vinmec.com" or not tail or "/" in tail:
        return None
    return tail


def extract_service_links(html: str, page_url: str = f"{BASE_URL}/vn/dich-vu") -> list[str]:
    """Extract canonical, single-level service links from the unfiltered listing."""
    from urllib.parse import urljoin

    soup = BeautifulSoup(html, "html.parser")
    urls: set[str] = set()
    for anchor in soup.select("a[href]"):
        absolute = canonical_service_url(urljoin(page_url, str(anchor.get("href"))))
        if service_key_for_url(absolute):
            urls.add(absolute)
    return sorted(urls)


def html_to_text(html: Any) -> str:
    if not isinstance(html, str) or not html.strip():
        return ""
    return clean_text(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))


def _tags(product: dict[str, Any]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for tag in product.get("tags") or []:
        if not isinstance(tag, dict):
            continue
        metadata = tag.get("metadata") if isinstance(tag.get("metadata"), dict) else {}
        group = clean_text(metadata.get("group") or "other")
        value = clean_text(tag.get("value"))
        if value and value not in grouped.setdefault(group, []):
            grouped[group].append(value)
    return grouped


def _images(product: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    seen: set[str] = set()
    candidates = list(product.get("images") or [])
    for variant in product.get("variants") or []:
        if isinstance(variant, dict):
            candidates.extend(variant.get("images") or [])
    for image in candidates:
        if not isinstance(image, dict):
            continue
        url = clean_text(image.get("url"))
        if url and url not in seen:
            values.append({"url": url, "rank": image.get("rank"), "metadata": image.get("metadata")})
            seen.add(url)
    return values


def _variants(product: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for variant in product.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        result.append(
            {
                "id": variant.get("id"),
                "title": clean_text(variant.get("title")),
                "sku": variant.get("sku"),
                "options": [
                    {
                        "title": clean_text((option.get("option") or {}).get("title")),
                        "value": clean_text(option.get("value")),
                    }
                    for option in variant.get("options") or []
                    if isinstance(option, dict)
                ],
            }
        )
    return result


def _branches(branch_prices: dict[str, Any]) -> list[dict[str, Any]]:
    data = branch_prices.get("data") if isinstance(branch_prices.get("data"), dict) else branch_prices
    prices = data.get("prices") if isinstance(data, dict) else []
    result: list[dict[str, Any]] = []
    for branch in prices or []:
        if not isinstance(branch, dict):
            continue
        result.append(
            {
                "id": branch.get("branch_id"),
                "name": clean_text(branch.get("branch_name")),
                "code": branch.get("branch_code"),
                "location": clean_text(branch.get("branch_location")),
                "type": branch.get("branch_type"),
                "price_list_id": branch.get("price_list_id"),
                "variants": [
                    {
                        "variant_id": price.get("variant_id"),
                        "variant_title": clean_text(price.get("variant_title")),
                        "sku": price.get("variant_sku"),
                        "amount": price.get("amount"),
                        "currency": str(price.get("currency_code") or "").lower() or None,
                    }
                    for price in branch.get("variants") or []
                    if isinstance(price, dict)
                ],
            }
        )
    return result


def _normalize_tabs(tabs: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(tabs, dict):
        return {}
    normalized: dict[str, list[dict[str, Any]]] = {}
    for section, blocks in tabs.items():
        section_blocks: list[dict[str, Any]] = []
        for block in blocks or []:
            if not isinstance(block, dict):
                continue
            value = deepcopy(block)
            data = value.get("data")
            if isinstance(data, dict):
                for key in ("html", "suitable_html", "symptoms_html"):
                    if key in data:
                        data[f"{key}_text"] = html_to_text(data.get(key))
            section_blocks.append(value)
        if section_blocks:
            normalized[str(section)] = section_blocks
    return normalized


def parse_service(
    product: dict[str, Any],
    branch_prices: dict[str, Any],
    branch_details: list[dict[str, Any]],
    source_url: str,
) -> dict[str, Any]:
    """Build one stable processed record from the public Medusa responses."""
    service_key = service_key_for_url(source_url)
    product_id = clean_text(product.get("id"))
    name = clean_text(product.get("title"))
    if not service_key or not product_id or not name:
        raise ValueError(f"Invalid service payload for {source_url}")

    details_by_branch: dict[str, dict[str, Any]] = {}
    content: dict[str, list[dict[str, Any]]] = {}
    for detail in branch_details:
        if not isinstance(detail, dict):
            continue
        branch_id = clean_text(detail.get("branch_id"))
        tabs = _normalize_tabs((detail.get("metadata") or {}).get("tabs"))
        if branch_id:
            details_by_branch[branch_id] = {"id": detail.get("id"), "tabs": tabs}
        for section, blocks in tabs.items():
            if section not in content and blocks:
                content[section] = blocks

    branches = _branches(branch_prices)
    for branch in branches:
        branch["detail"] = details_by_branch.get(str(branch.get("id")))

    metadata = product.get("metadata") if isinstance(product.get("metadata"), dict) else {}
    return {
        "schema_version": "1.0",
        "service_key": service_key,
        "service_id": product_id,
        "language": "vi",
        "name": name,
        "subtitle": clean_text(product.get("subtitle")),
        "description": clean_text(product.get("description")),
        "categories": [
            {
                "id": category.get("id"),
                "name": clean_text(category.get("name")),
                "handle": category.get("handle"),
            }
            for category in product.get("categories") or []
            if isinstance(category, dict)
        ],
        "tags": _tags(product),
        "variants": _variants(product),
        "branches": branches,
        "content": content,
        "images": _images(product),
        "thumbnail": product.get("thumbnail"),
        "rating": metadata.get("star"),
        "sold_count": metadata.get("sold_count"),
        "valid_duration_days": metadata.get("valid_duration"),
        "published_at": metadata.get("last_published_at"),
        "product_created_at": product.get("created_at"),
        "product_updated_at": product.get("updated_at"),
        "source_url": canonical_service_url(source_url),
    }
