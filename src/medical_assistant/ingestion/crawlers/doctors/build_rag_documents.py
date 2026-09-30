"""Convert normalized Vinmec profiles into section-aware RAG documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.medical_assistant.ingestion.crawl_utils.chunking import TokenChunker

from .vinmec_crawler import DEFAULT_OUTPUT_DIR

DEFAULT_INPUT_FILE = DEFAULT_OUTPUT_DIR / "processed" / "jsonl" / "vinmec_professionals_all.jsonl"
DEFAULT_RAG_FILE = DEFAULT_OUTPUT_DIR / "rag" / "documents.jsonl"

SECTION_LABELS = {
    "overview": {"vi": "Giới thiệu", "en": "Overview"},
    "positions": {"vi": "Chức vụ", "en": "Positions"},
    "specialties": {"vi": "Chuyên khoa", "en": "Specialties"},
    "workplace": {"vi": "Nơi công tác", "en": "Workplace"},
    "years_of_experience": {"vi": "Số năm kinh nghiệm", "en": "Years of experience"},
    "services": {"vi": "Dịch vụ", "en": "Services"},
    "education": {"vi": "Đào tạo", "en": "Education"},
    "experience": {"vi": "Kinh nghiệm", "en": "Experience"},
    "memberships": {"vi": "Thành viên tổ chức", "en": "Memberships"},
    "awards": {"vi": "Giải thưởng", "en": "Awards"},
    "publications": {"vi": "Nghiên cứu và xuất bản", "en": "Publications"},
}


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"Expected an object at {path}:{line_number}")
        yield value


def _stable_profile_key(profile: dict[str, Any]) -> str:
    language = profile.get("language") or "unknown"
    if profile.get("profile_id"):
        return f"{profile['profile_id']}-{language}"
    source_url = str(profile.get("source_url") or "")
    slug = urlparse(source_url).path.rstrip("/").rsplit("/", 1)[-1]
    if slug:
        return slug
    digest = hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:12]
    return f"profile-{digest}-{language}"


def _as_items(value: Any) -> list[str]:
    values = value if isinstance(value, list) else ([] if value is None else [value])
    items = [re.sub(r"\s+", " ", str(item)).strip() for item in values]
    return [item for item in items if item]


def _header(profile: dict[str, Any]) -> str:
    credentials = ", ".join(_as_items(profile.get("credentials")))
    name = str(profile.get("name") or "Unknown professional").strip()
    title = f"{credentials} {name}".strip() if credentials else name
    lines = [f"# {title}"]
    if profile.get("language"):
        lines.append(f"- Language: {profile['language']}")
    specialties = ", ".join(_as_items(profile.get("specialties")))
    if specialties:
        lines.append(f"- Specialties: {specialties}")
    workplace = ", ".join(_as_items(profile.get("workplace")))
    if workplace:
        lines.append(f"- Workplace: {workplace}")
    return "\n".join(lines)


def profile_to_documents(
    profile: dict[str, Any],
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> list[dict[str, Any]]:
    """Create deterministic, section-level chunks from one normalized profile."""
    chunker = TokenChunker(chunk_size=chunk_size, overlap=chunk_overlap)
    language = str(profile.get("language") or "en")
    if language not in {"vi", "en"}:
        language = "en"
    profile_key = _stable_profile_key(profile)
    header = _header(profile)
    source_url = str(profile.get("source_url") or "")
    documents: list[dict[str, Any]] = []

    for section, labels in SECTION_LABELS.items():
        items = _as_items(profile.get(section))
        if not items:
            continue
        body = "\n\n".join(items) if section == "overview" else "\n".join(
            f"- {item}" for item in items
        )
        parent_id = f"vinmec-{profile_key}-{section}"
        prefix = f"{header}\n\n## {labels[language]}"
        suffix = f"Source: {source_url}" if source_url else ""
        for chunk in chunker.split(body, prefix=prefix, suffix=suffix):
            documents.append(
                {
                    "chunk_id": f"{parent_id}-{chunk.index}",
                    "text": chunk.text,
                    "metadata": {
                        "parent_id": parent_id,
                        "profile_key": profile_key,
                        "profile_id": profile.get("profile_id"),
                        "language": profile.get("language"),
                        "name": profile.get("name"),
                        "section": section,
                        "chunk_index": chunk.index,
                        "chunk_count": chunk.count,
                        "token_count": chunk.token_count,
                        "specialties": _as_items(profile.get("specialties")),
                        "workplace": _as_items(profile.get("workplace")),
                        "source_url": source_url,
                    },
                }
            )
    return documents


def build_documents(
    profiles: Iterable[dict[str, Any]],
    chunk_size: int = 500,
    chunk_overlap: int = 80,
) -> Iterator[dict[str, Any]]:
    for profile in profiles:
        yield from profile_to_documents(profile, chunk_size, chunk_overlap)


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
