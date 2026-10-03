"""Shallow-crawl Vinmec hospital and clinic listing pages."""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.medical_assistant.ingestion.crawlers.doctors.vinmec_crawler import CrawlOptions, VinmecCrawler

from .hospital_parser import parse_facilities

LOGGER = logging.getLogger("vinmec_hospital_crawler")
BASE_URL = "https://www.vinmec.com"
LISTING_URLS = {
    "vi": f"{BASE_URL}/vie/co-so-y-te/",
    "en": f"{BASE_URL}/eng/hospital/",
}
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[5] / "data" / "crawled" / "hospitals"


class HospitalCrawler(VinmecCrawler):
    def crawl_listing(self, language: str) -> list[dict[str, Any]]:
        url = LISTING_URLS[language]
        LOGGER.info("Crawling %s facilities from %s", language, url)
        response = self._request(url)
        if self.options.save_raw:
            raw_dir = self.options.output_dir / "raw" / language
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / "hospitals.html").write_text(response.text, encoding="utf-8")
        crawled_at = datetime.now(UTC).isoformat()
        records = parse_facilities(response.text, str(response.url), language)
        for record in records:
            record["crawled_at"] = crawled_at
        return records

    def run(self) -> dict[str, Any]:
        json_dir = self.options.output_dir / "processed" / "json"
        jsonl_dir = self.options.output_dir / "processed" / "jsonl"
        json_dir.mkdir(parents=True, exist_ok=True)
        jsonl_dir.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        counts: dict[str, dict[str, int]] = {}

        for language in self.options.languages:
            records = self.crawl_listing(language)
            self._write_json(json_dir / f"vinmec_hospitals_{language}.json", records)
            self._write_jsonl(jsonl_dir / f"vinmec_hospitals_{language}.jsonl", records)
            all_records.extend(records)
            counts[language] = {
                "hospital": sum(r["facility_type"] == "hospital" for r in records),
                "clinic": sum(r["facility_type"] == "clinic" for r in records),
                "total": len(records),
            }

        self._write_json(json_dir / "vinmec_hospitals_all.json", all_records)
        self._write_jsonl(jsonl_dir / "vinmec_hospitals_all.jsonl", all_records)
        summary = {
            "finished_at": datetime.now(UTC).isoformat(),
            "languages": list(self.options.languages),
            "counts": counts,
            "total_records": len(all_records),
            "errors": self.errors,
        }
        self._write_json(json_dir / "crawl_summary.json", summary)
        return summary

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
        lines = [json.dumps(record, ensure_ascii=False) for record in records]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("vi", "en", "both"), default="both")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-raw", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    languages = ("vi", "en") if args.language == "both" else (args.language,)
    options = CrawlOptions(
        languages=languages,
        delay=args.delay,
        timeout=args.timeout,
        retries=args.retries,
        save_raw=not args.no_raw,
        output_dir=args.output_dir,
    )
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with HospitalCrawler(options) as crawler:
        summary = crawler.run()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
