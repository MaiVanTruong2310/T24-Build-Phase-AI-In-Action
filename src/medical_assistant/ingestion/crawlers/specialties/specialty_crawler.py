"""Crawl Vinmec specialty pages in Vietnamese and English."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
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

from .specialty_parser import extract_specialty_links, parse_specialty

LOGGER = logging.getLogger("vinmec_specialty_crawler")
BASE_URL = "https://www.vinmec.com"
LISTING_URLS = {
    "vi": f"{BASE_URL}/vie/chuyen-khoa/",
    "en": f"{BASE_URL}/eng/specialties/",
}
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[5] / "data" / "crawled" / "specialties"
DEFAULT_URLS_FILE = DEFAULT_OUTPUT_DIR / "urls_crawl.txt"


def _primary_path(output_dir: Path, language: str) -> Path:
    return output_dir / "processed" / "jsonl" / f"vinmec_specialties_{language}.jsonl"


def _archive_for_fresh(output_dir: Path, languages: Iterable[str]) -> None:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = output_dir / "backups" / timestamp
    candidates = [_primary_path(output_dir, language) for language in languages]
    candidates.extend(
        [
            output_dir / "errors" / "failed_urls.jsonl",
            output_dir / "processed" / "json" / "crawl_summary.json",
        ]
    )
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    for path in existing:
        shutil.copy2(path, backup_dir / path.name)
        path.unlink()
    LOGGER.warning("Archived previous primary data to %s", backup_dir)


def rebuild_outputs(output_dir: Path) -> dict[str, Any]:
    json_dir = output_dir / "processed" / "json"
    jsonl_dir = output_dir / "processed" / "jsonl"
    failure_path = output_dir / "errors" / "failed_urls.jsonl"
    legacy_summary = json_dir / "crawl_summary.json"
    stores = {language: JsonlStore(_primary_path(output_dir, language)) for language in ("vi", "en")}
    all_records = stores["vi"].records + stores["en"].records
    for language, store in stores.items():
        atomic_write_json(json_dir / f"vinmec_specialties_{language}.json", store.records)
    atomic_write_jsonl(jsonl_dir / "vinmec_specialties_all.jsonl", all_records)
    atomic_write_json(json_dir / "vinmec_specialties_all.json", all_records)
    completed = stores["vi"].keys | stores["en"].keys
    unresolved = sorted(load_failed_urls(failure_path, legacy_summary) - completed)
    summary = {
        "finished_at": datetime.now(UTC).isoformat(),
        "languages": ["vi", "en"],
        "specialty_counts": {language: len(store.records) for language, store in stores.items()},
        "total_specialties": len(all_records),
        "errors": [{"url": url, "error": "Unresolved crawl failure"} for url in unresolved],
    }
    atomic_write_json(json_dir / "crawl_summary.json", summary)
    return summary


def language_for_url(url: str) -> str | None:
    path = urlparse(url).path
    if path.startswith("/vie/chuyen-khoa/"):
        return "vi"
    if path.startswith("/eng/specialties/"):
        return "en"
    return None


def read_urls_file(path: Path) -> dict[str, list[str]]:
    grouped: dict[str, set[str]] = {"vi": set(), "en": set()}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        url = raw_line.strip()
        if not url or url.startswith("#"):
            continue
        language = language_for_url(url)
        if language:
            grouped[language].add(url.rstrip("/"))
        else:
            LOGGER.warning("Skipping unsupported URL in %s: %s", path, url)
    return {language: sorted(urls) for language, urls in grouped.items()}


class SpecialtyCrawler(VinmecCrawler):
    def discover_specialties(self, language: str) -> list[str]:
        url = LISTING_URLS[language]
        LOGGER.info("Discovering %s specialties from %s", language, url)
        response = self._request(url)
        if self.options.save_raw:
            raw_dir = self.options.output_dir / "raw" / language / "listings"
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "index.html").write_text(response.text, encoding="utf-8")
        return extract_specialty_links(response.text, str(response.url), language)

    def crawl_specialty(self, url: str, language: str) -> dict[str, Any]:
        response = self._request(url)
        final_url = str(response.url)
        if self.options.save_raw:
            slug = urlparse(final_url).path.rstrip("/").rsplit("/", 1)[-1]
            raw_dir = self.options.output_dir / "raw" / language / "profiles"
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / f"{slug}.html").write_text(response.text, encoding="utf-8")
        record = parse_specialty(response.text, final_url, language)
        record["crawled_at"] = datetime.now(UTC).isoformat()
        return record

    def run(
        self,
        specialty_urls: dict[str, list[str]] | None = None,
        *,
        retry_failed: bool = False,
    ) -> dict[str, Any]:
        output_dir = self.options.output_dir
        failure_path = output_dir / "errors" / "failed_urls.jsonl"
        legacy_summary = output_dir / "processed" / "json" / "crawl_summary.json"
        known_failed = load_failed_urls(failure_path, legacy_summary)
        for language in self.options.languages:
            urls = (
                specialty_urls.get(language, []) if specialty_urls is not None else self.discover_specialties(language)
            )
            if self.options.max_profiles is not None:
                urls = urls[: self.options.max_profiles]
            store = JsonlStore(_primary_path(output_dir, language))
            remaining = [
                url for url in urls if not store.contains(url) and (retry_failed or url.rstrip("/") not in known_failed)
            ]
            checkpoint = output_dir / "checkpoints" / f"{language}_state.json"
            update_checkpoint(
                checkpoint,
                language=language,
                status="running",
                started_at=datetime.now(UTC).isoformat(),
                total_urls=len(urls),
                completed_count=len(store.records),
                remaining_count=len(remaining),
                failed_count=len(known_failed - store.keys),
            )
            LOGGER.info(
                "%s: %d completed, %d remaining, %d known failed",
                language,
                len(store.records),
                len(remaining),
                len(known_failed - store.keys),
            )
            for index, url in enumerate(remaining, start=1):
                try:
                    LOGGER.info(
                        "[%s %d/%d remaining] %s",
                        language,
                        index,
                        len(remaining),
                        url,
                    )
                    record = self.crawl_specialty(url, language)
                    record["crawl_url"] = url.rstrip("/")
                    store.append(record)
                except (httpx.HTTPError, PermissionError, ValueError) as exc:
                    LOGGER.error("Could not crawl %s: %s", url, exc)
                    append_jsonl(
                        failure_path,
                        {
                            "language": language,
                            "url": url.rstrip("/"),
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "failed_at": datetime.now(UTC).isoformat(),
                        },
                    )
                    known_failed.add(url.rstrip("/"))
                update_checkpoint(
                    checkpoint,
                    status="running",
                    last_url=url,
                    completed_count=len(store.records),
                    remaining_count=len(remaining) - index,
                    failed_count=len(known_failed - store.keys),
                )
            update_checkpoint(
                checkpoint,
                status="complete",
                completed_count=len(store.records),
                remaining_count=0,
                failed_count=len(known_failed - store.keys),
                finished_at=datetime.now(UTC).isoformat(),
            )
        return rebuild_outputs(output_dir)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("vi", "en", "both"), default="both")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-specialties", type=int)
    parser.add_argument("--urls-file", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-raw", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Resume from JSONL (default)")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.fresh and args.rebuild:
        raise SystemExit("--fresh and --rebuild cannot be used together")
    languages = ("vi", "en") if args.language == "both" else (args.language,)
    options = CrawlOptions(
        languages=languages,
        delay=args.delay,
        timeout=args.timeout,
        retries=args.retries,
        max_profiles=args.max_specialties,
        save_raw=not args.no_raw,
        output_dir=args.output_dir,
    )
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    lock_path = args.output_dir / "checkpoints" / "crawler.lock"
    with CrawlRunLock(lock_path):
        if args.rebuild:
            summary = rebuild_outputs(args.output_dir)
        else:
            if args.fresh:
                _archive_for_fresh(args.output_dir, languages)
            urls = read_urls_file(args.urls_file) if args.urls_file else None
            with SpecialtyCrawler(options) as crawler:
                summary = crawler.run(urls, retry_failed=args.retry_failed)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
