"""Polite crawler for Vinmec Vietnamese and English professional profiles."""

from __future__ import annotations

import argparse
import json
import logging
import random
import shutil
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import robotparser
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

from .vinmec_parser import extract_profile_links, parse_profile

LOGGER = logging.getLogger("vinmec_crawler")
BASE_URL = "https://www.vinmec.com"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
LISTING_URLS = {
    "vi": f"{BASE_URL}/vie/chuyen-gia-y-te/",
    "en": f"{BASE_URL}/eng/professionals/",
}
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[5] / "data" / "crawled" / "doctors"
DEFAULT_URLS_FILE = DEFAULT_OUTPUT_DIR / "urls_crawl.txt"


def _primary_path(output_dir: Path, language: str) -> Path:
    return output_dir / "processed" / "jsonl" / f"vinmec_professionals_{language}.jsonl"


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
        atomic_write_json(json_dir / f"vinmec_professionals_{language}.json", store.records)
    atomic_write_jsonl(jsonl_dir / "vinmec_professionals_all.jsonl", all_records)
    atomic_write_json(json_dir / "vinmec_professionals_all.json", all_records)
    completed = stores["vi"].keys | stores["en"].keys
    unresolved = sorted(load_failed_urls(failure_path, legacy_summary) - completed)
    summary = {
        "finished_at": datetime.now(UTC).isoformat(),
        "languages": ["vi", "en"],
        "profile_counts": {language: len(store.records) for language, store in stores.items()},
        "total_profiles": len(all_records),
        "errors": [{"url": url, "error": "Unresolved crawl failure"} for url in unresolved],
    }
    atomic_write_json(json_dir / "crawl_summary.json", summary)
    return summary


def language_for_url(url: str) -> str | None:
    """Infer the supported Vinmec language from a professional profile URL."""
    path = urlparse(url).path
    if path.startswith("/vie/chuyen-gia-y-te/"):
        return "vi"
    if path.startswith("/eng/professionals/"):
        return "en"
    return None


def read_urls_file(path: Path) -> dict[str, list[str]]:
    """Read a one-URL-per-line crawl file and group supported URLs by language."""
    grouped: dict[str, set[str]] = {"vi": set(), "en": set()}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        url = raw_line.strip()
        if not url or url.startswith("#"):
            continue
        language = language_for_url(url)
        if language is None:
            LOGGER.warning("Skipping unsupported URL in %s: %s", path, url)
            continue
        grouped[language].add(url)
    return {language: sorted(urls) for language, urls in grouped.items()}


@dataclass(slots=True)
class CrawlOptions:
    languages: tuple[str, ...] = ("vi", "en")
    delay: float = 2.0
    timeout: float = 30.0
    retries: int = 3
    max_pages: int | None = None
    max_profiles: int | None = None
    save_raw: bool = True
    output_dir: Path = DEFAULT_OUTPUT_DIR
    user_agent: str = "P124VinmecResearchCrawler/1.0"


class VinmecCrawler:
    def __init__(self, options: CrawlOptions) -> None:
        if options.delay < 0:
            raise ValueError("delay must be non-negative")
        self.options = options
        self.client = httpx.Client(
            follow_redirects=True,
            timeout=options.timeout,
            headers={
                "User-Agent": options.user_agent,
                "Accept-Language": "vi,en;q=0.8",
            },
        )
        self.robots = robotparser.RobotFileParser()
        self.last_request_at = 0.0
        self.errors: list[dict[str, str]] = []

    def __enter__(self) -> VinmecCrawler:
        self._load_robots()
        return self

    def __exit__(self, *_: object) -> None:
        self.client.close()

    def _wait(self) -> None:
        elapsed = time.monotonic() - self.last_request_at
        wait_for = self.options.delay - elapsed
        if wait_for > 0:
            time.sleep(wait_for + random.uniform(0, min(0.35, self.options.delay / 4)))

    def _request(self, url: str, *, check_robots: bool = True) -> httpx.Response:
        if check_robots and not self.robots.can_fetch(self.options.user_agent, url):
            raise PermissionError(f"robots.txt does not allow crawling {url}")

        for attempt in range(1, self.options.retries + 1):
            self._wait()
            try:
                response = self.client.get(url)
                self.last_request_at = time.monotonic()
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == self.options.retries:
                        response.raise_for_status()
                    retry_after = response.headers.get("Retry-After")
                    pause = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
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

    def _load_robots(self) -> None:
        response = self._request(ROBOTS_URL, check_robots=False)
        self.robots.set_url(ROBOTS_URL)
        self.robots.parse(response.text.splitlines())
        for url in LISTING_URLS.values():
            if not self.robots.can_fetch(self.options.user_agent, url):
                raise PermissionError(f"robots.txt does not allow crawling {url}")

    def _listing_url(self, language: str, page: int) -> str:
        base = LISTING_URLS[language]
        return base if page == 1 else f"{base}page_{page}"

    def discover_profiles(self, language: str) -> list[str]:
        found: set[str] = set()
        page = 1
        raw_dir = self.options.output_dir / "raw" / language / "listings"

        while self.options.max_pages is None or page <= self.options.max_pages:
            url = self._listing_url(language, page)
            LOGGER.info("Discovering %s profiles from %s", language, url)
            response = self._request(url)
            links = extract_profile_links(response.text, str(response.url), language)
            new_links = set(links) - found
            if self.options.save_raw:
                raw_dir.mkdir(parents=True, exist_ok=True)
                (raw_dir / f"page_{page}.html").write_text(response.text, encoding="utf-8")
            if not links or not new_links:
                break
            found.update(new_links)
            page += 1

        return sorted(found)

    def crawl_profile(self, url: str, language: str) -> dict[str, Any]:
        response = self._request(url)
        final_url = str(response.url)
        if self.options.save_raw:
            slug = urlparse(final_url).path.rstrip("/").rsplit("/", 1)[-1]
            raw_dir = self.options.output_dir / "raw" / language / "profiles"
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / f"{slug}.html").write_text(response.text, encoding="utf-8")
        record = parse_profile(response.text, final_url, language)
        record["crawled_at"] = datetime.now(UTC).isoformat()
        return record

    def run(
        self,
        profile_urls: dict[str, list[str]] | None = None,
        *,
        retry_failed: bool = False,
    ) -> dict[str, Any]:
        output_dir = self.options.output_dir
        failure_path = output_dir / "errors" / "failed_urls.jsonl"
        legacy_summary = output_dir / "processed" / "json" / "crawl_summary.json"
        known_failed = load_failed_urls(failure_path, legacy_summary)

        for language in self.options.languages:
            urls = profile_urls.get(language, []) if profile_urls is not None else self.discover_profiles(language)
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
                    record = self.crawl_profile(url, language)
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
    parser.add_argument("--delay", type=float, default=2.0, help="Minimum delay between requests")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--max-profiles", type=int)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--urls-file",
        type=Path,
        help="Crawl URLs from a discovery file instead of scanning listing pages",
    )
    parser.add_argument("--no-raw", action="store_true", help="Do not retain source HTML")
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
        max_pages=args.max_pages,
        max_profiles=args.max_profiles,
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
            profile_urls = read_urls_file(args.urls_file) if args.urls_file else None
            with VinmecCrawler(options) as crawler:
                summary = crawler.run(profile_urls, retry_failed=args.retry_failed)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

