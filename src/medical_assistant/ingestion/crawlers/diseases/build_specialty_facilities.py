"""Build symptom/specialty-to-facility documents with official facility details."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from src.medical_assistant.ingestion.crawl_utils.chunking import TokenChunker

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_ROUTES = PROJECT_ROOT / "data" / "reference" / "service_policy" / "symptom_specialty_mapping.jsonl"
DEFAULT_HOSPITALS = PROJECT_ROOT / "data" / "crawled" / "hospitals" / "processed" / "jsonl" / "vinmec_hospitals_all.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "datalake" / "rag" / "specialty_facilities.jsonl"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Expected an object at {path}:{line_number}")
            yield value


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold().replace("đ", "d"))
    return re.sub(r"\W+", " ", "".join(c for c in normalized if not unicodedata.combining(c))).strip()


def _find_hospital(name: str, hospitals: list[dict[str, Any]]) -> dict[str, Any] | None:
    target = _fold(name)
    exact = [item for item in hospitals if _fold(str(item.get("name") or "")) == target]
    if exact:
        return exact[0]
    contained = [
        item for item in hospitals
        if target in _fold(str(item.get("name") or "")) or _fold(str(item.get("name") or "")) in target
    ]
    return max(contained, key=lambda item: len(_fold(str(item.get("name") or ""))), default=None)


def build_documents(
    routes: Iterator[dict[str, Any]], hospitals: list[dict[str, Any]], chunk_size: int = 500
) -> Iterator[dict[str, Any]]:
    chunker = TokenChunker(chunk_size=chunk_size, overlap=60)
    seen: set[tuple[str, str]] = set()
    for record in routes:
        structured = record.get("structured_data") or {}
        service = structured.get("service") or {}
        content = str((record.get("content") or {}).get("text") or "").strip()
        specialties = structured.get("medical_specialties") or service.get("categories") or []
        specialty_text = ", ".join(str(item) for item in specialties) or "Chuyên khoa phù hợp"
        # The description and first content window retain symptom vocabulary without
        # copying every commercial/service section into facility retrieval.
        searchable = "\n\n".join(filter(None, [str(service.get("description") or ""), content[:6000]]))
        if not searchable:
            continue
        for branch in structured.get("branches") or []:
            branch_name = str(branch.get("name") or "").strip()
            if not branch_name:
                continue
            hospital = _find_hospital(branch_name, hospitals)
            official_name = str((hospital or {}).get("name") or branch_name)
            key = (str(service.get("id") or record.get("source_url") or ""), official_name)
            if key in seen:
                continue
            seen.add(key)
            address = str((hospital or {}).get("address") or branch.get("location") or "")
            hotline = str((hospital or {}).get("hotline_display") or "")
            url = str((hospital or {}).get("detail_url") or record.get("source_url") or "")
            parent_id = f"specialty-facility-{abs(hash(key))}"
            prefix = (
                f"# {official_name}\n"
                f"- Chuyên khoa/dịch vụ liên quan: {specialty_text}\n"
                f"- Địa chỉ: {address}\n"
                f"- Hotline: {hotline}\n"
                f"- Dịch vụ nguồn: {record.get('title') or service.get('title') or ''}"
            )
            for chunk in chunker.split(searchable, prefix=prefix, suffix=f"Nguồn cơ sở: {url}"):
                yield {
                    "chunk_id": f"{parent_id}-{chunk.index}",
                    "text": chunk.text,
                    "metadata": {
                        "parent_id": parent_id,
                        "category": "specialty_facility",
                        "name": official_name,
                        "language": "vi",
                        "section": "facility_navigation",
                        "source_url": url,
                        "service_source_url": record.get("source_url"),
                        "specialties": specialties,
                        "address": address,
                        "hotline": hotline,
                    },
                }


def write_jsonl(path: Path, records: Iterator[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--routes", type=Path, default=DEFAULT_ROUTES)
    parser.add_argument("--hospitals", type=Path, default=DEFAULT_HOSPITALS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    count = write_jsonl(args.output, build_documents(read_jsonl(args.routes), list(read_jsonl(args.hospitals))))
    print(f"documents: {count}")
    print(f"saved: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
