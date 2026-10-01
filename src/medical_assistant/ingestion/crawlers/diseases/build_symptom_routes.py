"""Convert reviewed source records into symptom-to-specialty retrieval documents.

The source currently has draft review metadata. Documents remain source-grounded and
are used only to navigate to a specialty; they never expose a disease prediction.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from src.medical_assistant.ingestion.crawl_utils.chunking import TokenChunker

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "reference" / "service_policy" / "symptom_specialty_mapping.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "datalake" / "rag" / "symptom_specialty_mapping.jsonl"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"Expected an object at {path}:{line_number}")
            yield value


def _specialties(record: dict[str, Any]) -> list[str]:
    structured = record.get("structured_data") or {}
    values = structured.get("medical_specialties") or []
    if not values:
        values = (structured.get("service") or {}).get("categories") or []
    result: list[str] = []
    for value in values:
        # Product categories sometimes use "Specialty - Service". Keep only the
        # navigation label, not a possible disease/service claim.
        item = re.split(r"\s+-\s+", str(value).strip(), maxsplit=1)[0]
        if item and item not in result:
            result.append(item)
    return result or ["Nội tổng quát"]


def route_to_documents(record: dict[str, Any], chunk_size: int = 500, chunk_overlap: int = 80) -> list[dict[str, Any]]:
    content = str((record.get("content") or {}).get("text") or "").strip()
    source_url = str(record.get("source_url") or "")
    title = str(record.get("title") or "Thông tin điều hướng chuyên khoa")
    specialties = _specialties(record)
    if not content or not source_url:
        return []
    chunker = TokenChunker(chunk_size=chunk_size, overlap=chunk_overlap)
    parent_id = "symptom-route-" + str(
        (record.get("structured_data") or {}).get("service", {}).get("id") or abs(hash(source_url))
    )
    prefix = "# Điều hướng chuyên khoa\n\nChuyên khoa phù hợp để thăm khám: " + ", ".join(specialties)
    return [
        {
            "chunk_id": f"{parent_id}-{chunk.index}",
            "text": chunk.text,
            "metadata": {
                "parent_id": parent_id,
                "category": "symptom_specialty",
                "name": ", ".join(specialties),
                "specialties": specialties,
                "service_title": title,
                "language": "vi",
                "section": "navigation",
                "chunk_index": chunk.index,
                "chunk_count": chunk.count,
                "token_count": chunk.token_count,
                "source_url": source_url,
                "source_review_status": (record.get("review") or {}).get("status", "unknown"),
            },
        }
        for chunk in chunker.split(content, prefix=prefix, suffix=f"Nguồn: {source_url}")
    ]


def build_documents(records: Iterable[dict[str, Any]], **kwargs: int) -> Iterator[dict[str, Any]]:
    for record in records:
        yield from route_to_documents(record, **kwargs)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--chunk-overlap", type=int, default=80)
    args = parser.parse_args(argv)
    count = write_jsonl(
        args.output,
        build_documents(read_jsonl(args.input), chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap),
    )
    print(f"documents: {count}")
    print(f"saved: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
