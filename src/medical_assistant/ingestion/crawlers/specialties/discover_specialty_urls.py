"""Discover all Vinmec specialty URLs in Vietnamese and English."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable
from pathlib import Path

from src.medical_assistant.ingestion.crawlers.doctors.vinmec_crawler import CrawlOptions

from .specialty_crawler import DEFAULT_OUTPUT_DIR, DEFAULT_URLS_FILE, SpecialtyCrawler


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("vi", "en", "both"), default="both")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--output-file", type=Path, default=DEFAULT_URLS_FILE)
    parser.add_argument("--no-raw", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    languages = ("vi", "en") if args.language == "both" else (args.language,)
    options = CrawlOptions(
        languages=languages,
        delay=args.delay,
        save_raw=not args.no_raw,
        output_dir=DEFAULT_OUTPUT_DIR,
    )
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    discovered: dict[str, list[str]] = {}
    with SpecialtyCrawler(options) as crawler:
        for language in languages:
            discovered[language] = crawler.discover_specialties(language)
    urls = sorted({url for values in discovered.values() for url in values})
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    args.output_file.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")
    for language in languages:
        print(f"{language}: {len(discovered[language])} URLs")
    print(f"total: {len(urls)} URLs")
    print(f"saved: {args.output_file.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
