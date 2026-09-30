"""Polite, resumable crawler for Vinmec Vietnamese disease articles."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import xml.etree.ElementTree as ET
from collections import deque
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

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
from src.medical_assistant.ingestion.crawlers.doctors.vinmec_crawler import CrawlOptions, VinmecCrawler

from .disease_parser import (
    BASE,
    DETAIL_PREFIX,
    canonical,
    extract_disease_links,
    extract_listing_links,
    parse_disease,
)

LOGGER = logging.getLogger("vinmec_disease_crawler")
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[5] / "data" / "crawled" / "diseases"
DEFAULT_URLS_FILE = DEFAULT_OUTPUT_DIR / "urls_crawl.txt"
PRIMARY_NAME = "vinmec_diseases_vi"
SITEMAP_URL = BASE + "/sitemap/diseases-vi-1.xml"


def primary_path(output_dir: Path) -> Path:
    return output_dir / "processed" / "jsonl" / f"{PRIMARY_NAME}.jsonl"


def _archive_for_fresh(output_dir: Path) -> None:
    candidates = [primary_path(output_dir), output_dir / "errors" / "failed_urls.jsonl",
                  output_dir / "processed" / "json" / "crawl_summary.json"]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return
    backup = output_dir / "backups" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup.mkdir(parents=True, exist_ok=True)
    for path in existing:
        shutil.copy2(path, backup / path.name)
        path.unlink()
    LOGGER.warning("Archived previous primary data to %s", backup)


def rebuild_outputs(output_dir: Path) -> dict:
    store = JsonlStore(primary_path(output_dir))
    json_dir = output_dir / "processed" / "json"
    jsonl_dir = output_dir / "processed" / "jsonl"
    atomic_write_json(json_dir / f"{PRIMARY_NAME}.json", store.records)
    atomic_write_jsonl(jsonl_dir / "vinmec_diseases_all.jsonl", store.records)
    atomic_write_json(json_dir / "vinmec_diseases_all.json", store.records)
    failed = load_failed_urls(output_dir / "errors" / "failed_urls.jsonl") - store.keys
    summary = {
        "finished_at": datetime.now(UTC).isoformat(),
        "languages": ["vi"],
        "disease_counts": {"vi": len(store.records)},
        "total_diseases": len(store.records),
        "errors": [{"url": url, "error": "Unresolved crawl failure"} for url in sorted(failed)],
    }
    atomic_write_json(json_dir / "crawl_summary.json", summary)
    return summary


def read_urls_file(path: Path) -> list[str]:
    urls = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        parsed = urlparse(value)
        tail = parsed.path[len(DETAIL_PREFIX):].strip("/") if parsed.path.startswith(DETAIL_PREFIX) else ""
        if parsed.netloc.lower() != "www.vinmec.com" or not tail or "/" in tail:
            LOGGER.warning("Skipping unsupported URL: %s", value)
            continue
        urls.add(canonical(value))
    return sorted(urls)


class DiseaseCrawler(VinmecCrawler):
    def discover(self, max_listings: int | None = None) -> dict:
        """Merge Vinmec's disease sitemap with the A-Z index."""
        initial = BASE + DETAIL_PREFIX
        queue = deque([initial])
        seen: set[str] = set()
        diseases: set[str] = set()
        anomalies: list[dict] = []
        sitemap_urls: set[str] = set()
        try:
            sitemap = self._request(SITEMAP_URL)
            root = ET.fromstring(sitemap.content)
            for loc in root.findall(".//{*}loc"):
                value = loc.text or ""
                parsed = urlparse(value)
                tail = parsed.path[len(DETAIL_PREFIX):].strip("/") if parsed.path.startswith(DETAIL_PREFIX) else ""
                if parsed.netloc.lower() == "www.vinmec.com" and tail and "/" not in tail:
                    sitemap_urls.add(canonical(value))
            diseases.update(sitemap_urls)
        except (httpx.HTTPError, PermissionError, ET.ParseError) as exc:
            anomalies.append({"url": SITEMAP_URL, "reason": str(exc)})
            LOGGER.error("Could not read disease sitemap: %s", exc)
        while queue and (max_listings is None or len(seen) < max_listings):
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)
            try:
                response = self._request(url)
                html = response.text
                if self.options.save_raw:
                    name = "index" if url == initial else urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
                    path = self.options.output_dir / "raw" / "vi" / "listings" / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.with_suffix(".html").write_text(html, encoding="utf-8")
                found = extract_disease_links(html, str(response.url))
                diseases.update(found)
                if not found and url != initial:
                    anomalies.append({"url": url, "reason": "Listing contained no disease links"})
                for next_url in extract_listing_links(html, str(response.url)):
                    if next_url not in seen and next_url not in queue:
                        queue.append(next_url)
                LOGGER.info("Listing %s: %d disease URLs; total unique %d", url, len(found), len(diseases))
            except (httpx.HTTPError, PermissionError, ValueError) as exc:
                anomalies.append({"url": url, "reason": str(exc)})
                LOGGER.error("Could not read listing %s: %s", url, exc)
        complete = not queue
        report = {"discovered_at": datetime.now(UTC).isoformat(), "listing_count": len(seen),
                  "sitemap_url_count": len(sitemap_urls), "disease_url_count": len(diseases),
                  "complete_traversal": complete,
                  "unvisited_listings": list(queue), "anomalies": anomalies}
        atomic_write_json(self.options.output_dir / "discovery_summary.json", report)
        return {"urls": sorted(diseases), **report}

    def crawl_disease(self, url: str) -> dict:
        response = self._request(url)
        final_url = str(response.url)
        if self.options.save_raw:
            slug = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
            path = self.options.output_dir / "raw" / "vi" / "diseases" / f"{slug}.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(response.text, encoding="utf-8")
        record = parse_disease(response.text, final_url)
        record["crawl_url"] = url
        record["crawled_at"] = datetime.now(UTC).isoformat()
        return record

    def run(self, urls: list[str], *, retry_failed: bool = False) -> dict:
        output_dir = self.options.output_dir
        store = JsonlStore(primary_path(output_dir))
        failed_path = output_dir / "errors" / "failed_urls.jsonl"
        failed = load_failed_urls(failed_path)
        if self.options.max_profiles is not None:
            urls = urls[:self.options.max_profiles]
        remaining = [url for url in urls if not store.contains(url) and (retry_failed or url not in failed)]
        checkpoint = output_dir / "checkpoints" / "vi_state.json"
        update_checkpoint(checkpoint, language="vi", status="running", total_urls=len(urls),
                          completed_count=len(store.records), remaining_count=len(remaining),
                          failed_count=len(failed - store.keys))
        for index, url in enumerate(remaining, 1):
            try:
                LOGGER.info("[vi %d/%d remaining] %s", index, len(remaining), url)
                store.append(self.crawl_disease(url))
            except (httpx.HTTPError, PermissionError, ValueError) as exc:
                LOGGER.error("Could not crawl %s: %s", url, exc)
                append_jsonl(failed_path, {"language": "vi", "url": url,
                             "error_type": type(exc).__name__, "error": str(exc),
                             "failed_at": datetime.now(UTC).isoformat()})
                failed.add(url)
            update_checkpoint(checkpoint, status="running", last_url=url,
                              completed_count=len(store.records), remaining_count=len(remaining)-index,
                              failed_count=len(failed-store.keys))
        update_checkpoint(checkpoint, status="complete", completed_count=len(store.records),
                          remaining_count=0, failed_count=len(failed-store.keys),
                          finished_at=datetime.now(UTC).isoformat())
        return rebuild_outputs(output_dir)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-diseases", type=int)
    parser.add_argument("--max-listings", type=int)
    parser.add_argument("--urls-file", type=Path, default=DEFAULT_URLS_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-raw", action="store_true")
    parser.add_argument("--discover", action="store_true", help="Discover URLs, update urls_crawl.txt, then stop")
    parser.add_argument("--resume", action="store_true", help="Resume from JSONL (default)")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.fresh and args.rebuild:
        raise SystemExit("--fresh and --rebuild cannot be combined")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    options = CrawlOptions(languages=("vi",), delay=args.delay, timeout=args.timeout,
                           retries=args.retries, max_profiles=args.max_diseases,
                           save_raw=not args.no_raw, output_dir=args.output_dir)
    with CrawlRunLock(args.output_dir / "checkpoints" / "crawler.lock"):
        if args.rebuild:
            result = rebuild_outputs(args.output_dir)
        elif args.discover:
            with DiseaseCrawler(options) as crawler:
                result = crawler.discover(args.max_listings)
            reliable = result["complete_traversal"] and result["sitemap_url_count"] > 0
            if reliable:
                args.urls_file.parent.mkdir(parents=True, exist_ok=True)
                args.urls_file.write_text("\n".join(result["urls"]) + ("\n" if result["urls"] else ""), encoding="utf-8")
            else:
                LOGGER.warning("Discovery was partial or sitemap unavailable; keeping existing URL file unchanged")
            result = {key: value for key, value in result.items() if key != "urls"}
            result["urls_file"] = str(args.urls_file.resolve())
            result["urls_file_updated"] = reliable
        else:
            if args.fresh:
                _archive_for_fresh(args.output_dir)
            urls = read_urls_file(args.urls_file)
            with DiseaseCrawler(options) as crawler:
                result = crawler.run(urls, retry_failed=args.retry_failed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.discover:
        return 0 if result["urls_file_updated"] else 1
    return 0 if not result.get("errors") else 1


if __name__ == "__main__":
    raise SystemExit(main())

