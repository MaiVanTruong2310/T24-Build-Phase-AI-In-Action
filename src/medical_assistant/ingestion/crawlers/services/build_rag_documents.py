"""Convert normalized Vinmec services into RAG-ready JSONL chunks."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from src.medical_assistant.ingestion.crawl_utils.chunking import TokenChunker

from .service_crawler import DEFAULT_OUTPUT_DIR

DEFAULT_INPUT_FILE = DEFAULT_OUTPUT_DIR / "processed" / "jsonl" / "vinmec_services_all.jsonl"
DEFAULT_RAG_FILE = DEFAULT_OUTPUT_DIR / "rag" / "documents.jsonl"


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Expected an object at {path}:{number}")
        yield value


def _render_block(block: dict[str, Any]) -> str:
    data = block.get("data") if isinstance(block.get("data"), dict) else {}
    values: list[str] = []
    for key in ("html_text", "suitable_html_text", "symptoms_html_text"):
        if data.get(key):
            values.append(str(data[key]))
    for item in data.get("items") or []:
        if isinstance(item, dict):
            text = item.get("text") or item.get("fact") or item.get("myth")
            if text:
                values.append(str(text))
    for group in data.get("groups") or []:
        if not isinstance(group, dict):
            continue
        title = str(group.get("name") or group.get("title") or "").strip()
        items = [str(item.get("text") or "").strip() for item in group.get("items") or [] if isinstance(item, dict)]
        values.append("\n".join(filter(None, [title, *items])))
    for phase in data.get("phases") or []:
        if not isinstance(phase, dict):
            continue
        steps = [
            ": ".join(filter(None, [str(step.get("title") or "").strip(), str(step.get("description") or "").strip()]))
            for step in phase.get("steps") or []
            if isinstance(step, dict)
        ]
        values.append("\n".join(filter(None, [str(phase.get("title") or "").strip(), *steps])))
    return "\n".join(value for value in values if value.strip())


def service_to_documents(
    record: dict[str, Any], chunk_size: int = 500, chunk_overlap: int = 80
) -> list[dict[str, Any]]:
    chunker = TokenChunker(chunk_size=chunk_size, overlap=chunk_overlap)
    key = str(record.get("service_key") or "unknown-service")
    name = str(record.get("name") or "Unknown service")
    source_url = str(record.get("source_url") or "")
    documents: list[dict[str, Any]] = []
    sections: list[tuple[str, str]] = [("summary", str(record.get("description") or ""))]
    for section, blocks in (record.get("content") or {}).items():
        body = "\n\n".join(_render_block(block) for block in blocks if isinstance(block, dict))
        sections.append((str(section), body))
    price_lines = []
    for branch in record.get("branches") or []:
        for variant in branch.get("variants") or []:
            price_lines.append(
                f"{branch.get('name')} ({branch.get('location')}): {variant.get('amount')} {variant.get('currency')}"
            )
    if price_lines:
        sections.append(("branches_and_prices", "\n".join(price_lines)))
    for section, body in sections:
        if not body.strip():
            continue
        parent_id = f"vinmec-service-{key}-vi-{section}"
        prefix = f"# {name}\n- Language: vi\n\n## {section.replace('_', ' ').title()}"
        suffix = f"Source: {source_url}" if source_url else ""
        for chunk in chunker.split(body, prefix=prefix, suffix=suffix):
            documents.append(
                {
                    "chunk_id": f"{parent_id}-{chunk.index}",
                    "text": chunk.text,
                    "metadata": {
                        "parent_id": parent_id,
                        "service_key": key,
                        "service_id": record.get("service_id"),
                        "language": "vi",
                        "name": name,
                        "section": section,
                        "chunk_index": chunk.index,
                        "chunk_count": chunk.count,
                        "token_count": chunk.token_count,
                        "source_url": source_url,
                    },
                }
            )
    return documents


def build_documents(
    records: Iterable[dict[str, Any]], chunk_size: int = 500, chunk_overlap: int = 80
) -> Iterator[dict[str, Any]]:
    for record in records:
        yield from service_to_documents(record, chunk_size, chunk_overlap)


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
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_RAG_FILE)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--chunk-overlap", type=int, default=80)
    args = parser.parse_args(argv)
    count = write_jsonl(args.output, build_documents(read_jsonl(args.input), args.chunk_size, args.chunk_overlap))
    print(f"documents: {count}")
    print(f"saved: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
