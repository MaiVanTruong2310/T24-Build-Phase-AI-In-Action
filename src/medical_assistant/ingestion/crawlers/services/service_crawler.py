"""Polite, resumable crawler for public Vinmec Online medical services."""

from __future__ import annotations

import argparse
import json
import logging
import random
import shutil
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import robotparser

import httpx

from src.medical_assistant.ingestion.crawl_utils import (
    CrawlRunLock,
    JsonlStore,
    append_jsonl,
    atomic_write_json,
    atomic_write_jsonl,
    load_failed_urls,
    update_checkpoint,
)

from .service_parser import BASE_URL, canonical_service_url, extract_service_links, parse_service, service_key_for_url

LOGGER = logging.getLogger("vinmec_service_crawler")
API_BASE_URL = "https://api-online.vinmec.com"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
LISTING_URL = f"{BASE_URL}/vn/dich-vu"
PUBLISHABLE_KEY = "pk_9dbf7bb6c1b6d15885a6bff1a82906b8be2c043f82c195b9d6420f42ce4f1a44"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[5] / "data" / "crawled" / "services"
DEFAULT_URLS_FILE = DEFAULT_OUTPUT_DIR / "urls_crawl.txt"
PRIMARY_NAME = "vinmec_services_vi"


@dataclass(slots=True)
class ServiceCrawlOptions:
    delay: float = 2.0
    timeout: float = 45.0
    retries: int = 3
    max_services: int | None = None
    save_raw: bool = True
    output_dir: Path = DEFAULT_OUTPUT_DIR
    user_agent: str = "P124VinmecServiceCrawler/1.0"


def primary_path(output_dir: Path) -> Path:
    return output_dir / "processed" / "jsonl" / f"{PRIMARY_NAME}.jsonl"


def _archive_for_fresh(output_dir: Path) -> None:
    candidates = [
        primary_path(output_dir),
        output_dir / "errors" / "failed_urls.jsonl",
        output_dir / "processed" / "json" / "crawl_summary.json",
        output_dir / "rag" / "documents.jsonl",
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return
    backup = output_dir / "backups" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup.mkdir(parents=True, exist_ok=True)
    for path in existing:
        shutil.copy2(path, backup / path.name)
        path.unlink()
    LOGGER.warning("Archived previous service artifacts to %s", backup)


def rebuild_outputs(output_dir: Path, *, build_rag: bool = True) -> dict[str, Any]:
    store = JsonlStore(primary_path(output_dir))
    json_dir = output_dir / "processed" / "json"
    jsonl_dir = output_dir / "processed" / "jsonl"
    atomic_write_json(json_dir / f"{PRIMARY_NAME}.json", store.records)
    atomic_write_jsonl(jsonl_dir / "vinmec_services_all.jsonl", store.records)
    atomic_write_json(json_dir / "vinmec_services_all.json", store.records)
    failures = load_failed_urls(output_dir / "errors" / "failed_urls.jsonl") - store.keys
    branch_count = sum(len(record.get("branches") or []) for record in store.records)
    summary: dict[str, Any] = {
        "finished_at": datetime.now(UTC).isoformat(),
        "languages": ["vi"],
        "service_counts": {"vi": len(store.records)},
        "total_services": len(store.records),
        "total_service_branches": branch_count,
        "errors": [{"url": url, "error": "Unresolved crawl failure"} for url in sorted(failures)],
    }
    if build_rag:
        from .build_rag_documents import build_documents, write_jsonl

        summary["rag_documents"] = write_jsonl(
            output_dir / "rag" / "documents.jsonl",
            build_documents(store.records),
        )
    atomic_write_json(json_dir / "crawl_summary.json", summary)
    return summary


def read_urls_file(path: Path) -> list[str]:
    urls: set[str] = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        canonical = canonical_service_url(value)
        if not service_key_for_url(canonical):
            LOGGER.warning("Skipping unsupported service URL: %s", value)
            continue
        urls.add(canonical)
    return sorted(urls)


class ServiceCrawler:
    def __init__(self, options: ServiceCrawlOptions) -> None:
        if options.delay < 0:
            raise ValueError("delay must be non-negative")
        self.options = options
        self.last_request_at = 0.0
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=options.timeout,
            headers={"User-Agent": options.user_agent, "Accept-Language": "vi"},
        )
        self.robots = robotparser.RobotFileParser()

    def __enter__(self) -> ServiceCrawler:
        response = self._request(ROBOTS_URL, check_robots=False)
        self.robots.set_url(ROBOTS_URL)
        self.robots.parse(response.text.splitlines())
        for url in (SITEMAP_URL, LISTING_URL):
            if not self.robots.can_fetch(self.options.user_agent, url):
                raise PermissionError(f"robots.txt does not allow crawling {url}")
        return self

    def __exit__(self, *_: object) -> None:
        self.client.close()

    def _wait(self) -> None:
        remaining = self.options.delay - (time.monotonic() - self.last_request_at)
        if remaining > 0:
            time.sleep(remaining + random.uniform(0, min(0.35, self.options.delay / 4)))

    def _request(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None,
        headers: Mapping[str, str] | None = None,
        check_robots: bool = True,
    ) -> httpx.Response:
        if check_robots and url.startswith(BASE_URL) and not self.robots.can_fetch(self.options.user_agent, url):
            raise PermissionError(f"robots.txt does not allow crawling {url}")
        for attempt in range(1, self.options.retries + 1):
            self._wait()
            try:
                response = self.client.get(url, params=params, headers=headers)
                self.last_request_at = time.monotonic()
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == self.options.retries:
                        response.raise_for_status()
                    retry_after = response.headers.get("Retry-After", "")
                    pause = float(retry_after) if retry_after.isdigit() else 2**attempt
                    LOGGER.warning("HTTP %s for %s; retrying in %.1fs", response.status_code, url, pause)
                    time.sleep(pause)
                    continue
                response.raise_for_status()
                return response
            except httpx.HTTPError:
                if attempt == self.options.retries:
                    raise
                pause = 2**attempt
                LOGGER.warning("Request failed for %s; retrying in %ss", url, pause)
                time.sleep(pause)
        raise RuntimeError(f"Unable to fetch {url}")

    @property
    def api_headers(self) -> dict[str, str]:
        return {"x-publishable-api-key": PUBLISHABLE_KEY, "x-medusa-locale": "vi"}

    def discover(self) -> dict[str, Any]:
        sitemap_response = self._request(SITEMAP_URL)
        try:
            root = ET.fromstring(sitemap_response.content)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid service sitemap: {exc}") from exc
        sitemap_records: dict[str, dict[str, Any]] = {}
        sitemap_total = 0
        for node in root.findall(".//{*}url"):
            sitemap_total += 1
            loc = node.findtext("{*}loc") or ""
            canonical = canonical_service_url(loc)
            key = service_key_for_url(canonical)
            if not key:
                continue
            sitemap_records[canonical] = {
                "source_url": canonical,
                "service_key": key,
                "lastmod": node.findtext("{*}lastmod"),
                "changefreq": node.findtext("{*}changefreq"),
                "priority": node.findtext("{*}priority"),
                "discovered_from": ["sitemap"],
            }

        listing_response = self._request(LISTING_URL)
        listing_urls = set(extract_service_links(listing_response.text, str(listing_response.url)))
        if self.options.save_raw:
            raw = self.options.output_dir / "raw" / "vi" / "listings"
            raw.mkdir(parents=True, exist_ok=True)
            (raw / "index.html").write_text(listing_response.text, encoding="utf-8")
            (raw / "sitemap.xml").write_bytes(sitemap_response.content)
        for url in listing_urls:
            record = sitemap_records.setdefault(
                url,
                {
                    "source_url": url,
                    "service_key": service_key_for_url(url),
                    "lastmod": None,
                    "changefreq": None,
                    "priority": None,
                    "discovered_from": [],
                },
            )
            if "listing" not in record["discovered_from"]:
                record["discovered_from"].append("listing")
        now = datetime.now(UTC).isoformat()
        for record in sitemap_records.values():
            record["discovered_at"] = now
        urls = sorted(sitemap_records)
        sitemap_only = sorted(set(urls) - listing_urls)
        listing_only = sorted(
            listing_urls - {url for url, row in sitemap_records.items() if "sitemap" in row["discovered_from"]}
        )
        anomalies = []
        if not listing_urls:
            anomalies.append(
                {
                    "url": LISTING_URL,
                    "reason": (
                        "Server-rendered listing contains no service links; "
                        "the sitemap is used as the authoritative discovery source."
                    ),
                }
            )

        report = {
            "discovered_at": now,
            "sitemap_url": SITEMAP_URL,
            "sitemap_total_urls": sitemap_total,
            "sitemap_service_urls": sum("sitemap" in row["discovered_from"] for row in sitemap_records.values()),
            "listing_service_urls": len(listing_urls),
            "union_service_urls": len(urls),
            "sitemap_only_count": len(sitemap_only),
            "listing_only_count": len(listing_only),
            "sitemap_only_urls": sitemap_only,
            "listing_only_urls": listing_only,
            "complete_discovery": bool(urls),
            "anomalies": anomalies,
        }
        atomic_write_json(self.options.output_dir / "discovery_summary.json", report)
        atomic_write_jsonl(
            self.options.output_dir / "sitemap_services.jsonl",
            (sitemap_records[url] for url in urls),
        )
        return {"urls": urls, **report}

    def _api_json(
        self, path: str, params: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None
    ) -> dict[str, Any]:
        response = self._request(f"{API_BASE_URL}{path}", params=params, headers=self.api_headers, check_robots=False)
        value = response.json()
        if not isinstance(value, dict):
            raise ValueError(f"Expected JSON object from {path}")
        return value

    def crawl_service(self, url: str, *, sitemap_lastmod: str | None = None) -> dict[str, Any]:
        key = service_key_for_url(url)
        if not key:
            raise ValueError(f"Unsupported service URL: {url}")
        product_payload = self._api_json(
            "/store/products",
            {
                "handle": key,
                "fields": "*variants.images,*images,+metadata,*categories,+tags",
                "country_code": "vn",
            },
        )
        products = product_payload.get("products") or []
        if len(products) != 1 or not isinstance(products[0], dict):
            raise ValueError(f"Expected exactly one product for {url}; found {len(products)}")
        product = products[0]
        product_id = str(product.get("id") or "")
        prices_payload = self._api_json(f"/store/v1/products/{product_id}/branch-prices")
        price_data = prices_payload.get("data") if isinstance(prices_payload.get("data"), dict) else prices_payload
        branch_ids = [str(row.get("branch_id")) for row in price_data.get("prices") or [] if row.get("branch_id")]
        details_payload: dict[str, Any] = {"service_branch_details": []}
        if branch_ids:
            params: list[tuple[str, Any]] = [("service_id", product_id)]
            params.extend(("branch_id", branch_id) for branch_id in branch_ids)
            details_payload = self._api_json("/store/v1/service-branch-details", params)
        details = details_payload.get("service_branch_details") or []
        record = parse_service(product, prices_payload, details, url)
        record["crawl_url"] = canonical_service_url(url)
        record["sitemap_lastmod"] = sitemap_lastmod
        record["crawled_at"] = datetime.now(UTC).isoformat()
        if self.options.save_raw:
            raw_dir = self.options.output_dir / "raw" / "vi" / "services" / key
            raw_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(raw_dir / "product.json", product_payload)
            atomic_write_json(raw_dir / "branch_prices.json", prices_payload)
            atomic_write_json(raw_dir / "branch_details.json", details_payload)
        return record

    def run(self, urls: list[str], *, retry_failed: bool = False) -> dict[str, Any]:
        output = self.options.output_dir
        store = JsonlStore(primary_path(output))
        failed_path = output / "errors" / "failed_urls.jsonl"
        failed = load_failed_urls(failed_path)
        if self.options.max_services is not None:
            urls = urls[: self.options.max_services]
        sitemap_metadata: dict[str, str | None] = {}
        metadata_path = output / "sitemap_services.jsonl"
        if metadata_path.exists():
            for line in metadata_path.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    item = json.loads(line)
                    sitemap_metadata[str(item.get("source_url"))] = item.get("lastmod")
        remaining = [url for url in urls if not store.contains(url) and (retry_failed or url not in failed)]
        checkpoint = output / "checkpoints" / "vi_state.json"
        update_checkpoint(
            checkpoint,
            language="vi",
            status="running",
            started_at=datetime.now(UTC).isoformat(),
            total_urls=len(urls),
            completed_count=len(store.records),
            remaining_count=len(remaining),
            failed_count=len(failed - store.keys),
        )
        for index, url in enumerate(remaining, 1):
            try:
                LOGGER.info("[vi %d/%d remaining] %s", index, len(remaining), url)
                store.append(self.crawl_service(url, sitemap_lastmod=sitemap_metadata.get(url)))
            except (httpx.HTTPError, PermissionError, ValueError, json.JSONDecodeError) as exc:
                LOGGER.error("Could not crawl %s: %s", url, exc)
                append_jsonl(
                    failed_path,
                    {
                        "language": "vi",
                        "url": url,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "failed_at": datetime.now(UTC).isoformat(),
                    },
                )
                failed.add(url)
            update_checkpoint(
                checkpoint,
                status="running",
                last_url=url,
                completed_count=len(store.records),
                remaining_count=len(remaining) - index,
                failed_count=len(failed - store.keys),
            )
        update_checkpoint(
            checkpoint,
            status="complete",
            completed_count=len(store.records),
            remaining_count=0,
            failed_count=len(failed - store.keys),
            finished_at=datetime.now(UTC).isoformat(),
        )
        return rebuild_outputs(output)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-services", type=int)
    parser.add_argument("--urls-file", type=Path, default=DEFAULT_URLS_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-raw", action="store_true")
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Resume from JSONL (default)")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--no-rag", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.fresh and args.rebuild:
        raise SystemExit("--fresh and --rebuild cannot be combined")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    options = ServiceCrawlOptions(
        delay=args.delay,
        timeout=args.timeout,
        retries=args.retries,
        max_services=args.max_services,
        save_raw=not args.no_raw,
        output_dir=args.output_dir,
    )
    with CrawlRunLock(args.output_dir / "checkpoints" / "crawler.lock"):
        if args.rebuild:
            result = rebuild_outputs(args.output_dir, build_rag=not args.no_rag)
        elif args.discover:
            with ServiceCrawler(options) as crawler:
                result = crawler.discover()
            reliable = bool(result["complete_discovery"] and result["sitemap_service_urls"])
            if reliable:
                args.urls_file.parent.mkdir(parents=True, exist_ok=True)
                args.urls_file.write_text("\n".join(result["urls"]) + "\n", encoding="utf-8")
            result = {key: value for key, value in result.items() if key != "urls"}
            result["urls_file"] = str(args.urls_file.resolve())
            result["urls_file_updated"] = reliable
        else:
            if args.fresh:
                _archive_for_fresh(args.output_dir)
            urls = read_urls_file(args.urls_file)
            with ServiceCrawler(options) as crawler:
                result = crawler.run(urls, retry_failed=args.retry_failed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.discover:
        return 0 if result["urls_file_updated"] else 1
    return 0 if not result.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())
