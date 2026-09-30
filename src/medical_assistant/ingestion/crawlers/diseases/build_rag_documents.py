"""Build production-safe disease education RAG documents."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from src.medical_assistant.ingestion.crawl_utils.chunking import TokenChunker

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "crawled" / "diseases" / "processed" / "jsonl" / "vinmec_diseases_vi.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "datalake" / "rag" / "disease_education.jsonl"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as source:
        for line_number, raw_line in enumerate(source, start=1):
            if not raw_line.strip():
                continue
            value = json.loads(raw_line)
            if not isinstance(value, dict):
                raise ValueError(f"Expected an object at {path}:{line_number}")
            yield value


def disease_to_documents(
    disease: dict[str, Any], chunk_size: int = 500, chunk_overlap: int = 80
) -> list[dict[str, Any]]:
    """Create section-aware chunks. These documents are educational, not diagnostic."""
    chunker = TokenChunker(chunk_size=chunk_size, overlap=chunk_overlap)
    key = str(disease.get("disease_key") or "unknown")
    name = str(disease.get("name") or key)
    language = str(disease.get("language") or "vi")
    source_url = str(disease.get("source_url") or "")
    documents: list[dict[str, Any]] = []
    for section in disease.get("sections") or []:
        section_key = str(section.get("key") or "other")
        heading = str(section.get("heading") or section_key)
        items = [str(item).strip() for item in section.get("content") or [] if str(item).strip()]
        if not items:
            continue
        parent_id = f"vinmec-disease-{key}-{section_key}"
        prefix = f"# {name}\n\n## {heading}"
        suffix = f"Nguồn: {source_url}" if source_url else ""
        for chunk in chunker.split("\n\n".join(items), prefix=prefix, suffix=suffix):
            documents.append(
                {
                    "chunk_id": f"{parent_id}-{chunk.index}",
                    "text": chunk.text,
                    "metadata": {
                        "parent_id": parent_id,
                        "category": "disease_education",
                        "disease_key": key,
                        "name": name,
                        "language": language,
                        "section": section_key,
                        "chunk_index": chunk.index,
                        "chunk_count": chunk.count,
                        "token_count": chunk.token_count,
                        "source_url": source_url,
                        "usage": "education_only",
                    },
                }
            )
    return documents


def build_documents(records: Iterable[dict[str, Any]], **kwargs: int) -> Iterator[dict[str, Any]]:
    for record in records:
        yield from disease_to_documents(record, **kwargs)


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
        build_documents(
            read_jsonl(args.input),
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        ),
    )
    print(f"documents: {count}")
    print(f"saved: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
