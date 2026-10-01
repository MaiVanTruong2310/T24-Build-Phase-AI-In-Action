"""Convert normalized Vinmec specialties into RAG-ready JSONL chunks."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from src.medical_assistant.ingestion.crawl_utils.chunking import TokenChunker

from .specialty_crawler import DEFAULT_OUTPUT_DIR

DEFAULT_INPUT_FILE = DEFAULT_OUTPUT_DIR / "processed" / "jsonl" / "vinmec_specialties_all.jsonl"
DEFAULT_RAG_FILE = DEFAULT_OUTPUT_DIR / "rag" / "documents.jsonl"
SECTION_LABELS = {
    "overview": {"vi": "Tổng quan", "en": "Overview"},
    "services": {"vi": "Dịch vụ", "en": "Services"},
    "technologies": {"vi": "Công nghệ", "en": "Technologies"},
}


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not raw_line.strip():
            continue
        value = json.loads(raw_line)
        if not isinstance(value, dict):
            raise ValueError(f"Expected an object at {path}:{line_number}")
        yield value


def specialty_to_documents(
    record: dict[str, Any],
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> list[dict[str, Any]]:
    chunker = TokenChunker(chunk_size=chunk_size, overlap=chunk_overlap)
    language = record.get("language") if record.get("language") in {"vi", "en"} else "en"
    specialty_key = str(record.get("specialty_key") or "unknown-specialty")
    name = str(record.get("name") or "Unknown specialty")
    source_url = str(record.get("source_url") or "")
    doctor_urls = record.get("doctor_urls") or []
    documents: list[dict[str, Any]] = []

    for section, labels in SECTION_LABELS.items():
        blocks = record.get(section) or []
        for block_index, block in enumerate(blocks, start=1):
            title = str(block.get("title") or "").strip()
            content = [str(item).strip() for item in block.get("content", []) if str(item).strip()]
            if not title and not content:
                continue
            prefix_lines = [f"# {name}", f"- Language: {language}", "", f"## {labels[language]}"]
            if title:
                prefix_lines.extend(["", f"### {title}"])
            body = "\n".join(f"- {item}" for item in content) if content else title
            parent_id = f"vinmec-specialty-{specialty_key}-{language}-{section}-{block_index}"
            suffix = f"Source: {source_url}" if source_url else ""
            for chunk in chunker.split(body, prefix="\n".join(prefix_lines), suffix=suffix):
                documents.append(
                    {
                        "chunk_id": f"{parent_id}-{chunk.index}",
                        "text": chunk.text,
                        "metadata": {
                            "parent_id": parent_id,
                            "specialty_key": specialty_key,
                            "language": language,
                            "name": name,
                            "section": section,
                            "block_index": block_index,
                            "chunk_index": chunk.index,
                            "chunk_count": chunk.count,
                            "token_count": chunk.token_count,
                            "doctor_urls": doctor_urls,
                            "source_url": source_url,
                        },
                    }
                )
    return documents


def build_documents(
    records: Iterable[dict[str, Any]],
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> Iterator[dict[str, Any]]:
    for record in records:
        yield from specialty_to_documents(record, chunk_size, chunk_overlap)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_RAG_FILE)
    parser.add_argument("--chunk-size", type=int, default=500, help="Maximum tokens per chunk")
    parser.add_argument("--chunk-overlap", type=int, default=80, help="Overlapping body tokens")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    count = write_jsonl(
        args.output,
        build_documents(read_jsonl(args.input), args.chunk_size, args.chunk_overlap),
    )
    print(f"documents: {count}")
    print(f"saved: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
