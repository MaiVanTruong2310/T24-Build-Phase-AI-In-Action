"""Crash-safe JSONL persistence, checkpoints, failure logs, and run locks."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_replace(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        output.write(content)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def atomic_write_json(path: Path, value: Any) -> None:
    _atomic_replace(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def atomic_write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    _atomic_replace(path, "\n".join(lines) + ("\n" if lines else ""))


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    """Append and force one JSON record to durable storage."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(record, ensure_ascii=False) + "\n")
        output.flush()
        os.fsync(output.fileno())


class JsonlStore:
    """Validated append-only JSONL store whose records have a stable URL key."""

    def __init__(
        self,
        path: Path,
        key_fields: tuple[str, ...] = ("crawl_url", "source_url"),
    ) -> None:
        self.path = path
        self.key_fields = key_fields
        self.records = self._load()
        self.keys: set[str] = set()
        for record in self.records:
            key = self.key_for(record)
            if not key:
                raise ValueError(f"Record in {path} has no key in {key_fields}")
            if key in self.keys:
                raise ValueError(f"Duplicate key {key!r} in {path}")
            self.keys.add(key)

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        lines = self.path.read_text(encoding="utf-8-sig").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Corrupt JSONL at {self.path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Expected an object at {self.path}:{line_number}")
            records.append(value)
        return records

    def key_for(self, record: dict[str, Any]) -> str | None:
        for field in self.key_fields:
            value = record.get(field)
            if isinstance(value, str) and value:
                return value.rstrip("/")
        return None

    def contains(self, url: str) -> bool:
        return url.rstrip("/") in self.keys

    def append(self, record: dict[str, Any]) -> bool:
        key = self.key_for(record)
        if not key:
            raise ValueError(f"Record has no key in {self.key_fields}")
        if key in self.keys:
            return False
        append_jsonl(self.path, record)
        self.records.append(record)
        self.keys.add(key)
        return True


class CrawlRunLock:
    """Prevent concurrent writers from using the same output directory."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def __enter__(self) -> CrawlRunLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            details = self.path.read_text(encoding="utf-8", errors="replace").strip()
            raise RuntimeError(f"Another crawl may be running; lock exists at {self.path}. {details}") from exc
        payload = json.dumps({"pid": os.getpid(), "started_at": utc_now()}, ensure_ascii=False)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(payload + "\n")
            output.flush()
            os.fsync(output.fileno())
        self.acquired = True
        return self

    def __exit__(self, *_: object) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False


def update_checkpoint(path: Path, **values: Any) -> None:
    current: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                current = loaded
        except json.JSONDecodeError:
            current = {}
    current.update(values)
    current["updated_at"] = utc_now()
    atomic_write_json(path, current)


def load_failed_urls(failure_path: Path, legacy_summary_path: Path | None = None) -> set[str]:
    urls: set[str] = set()
    if failure_path.exists():
        for line_number, line in enumerate(failure_path.read_text(encoding="utf-8-sig").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Corrupt failure log at {failure_path}:{line_number}: {exc}") from exc
            url = event.get("url") if isinstance(event, dict) else None
            if isinstance(url, str) and url:
                urls.add(url.rstrip("/"))
    if legacy_summary_path and legacy_summary_path.exists():
        summary = json.loads(legacy_summary_path.read_text(encoding="utf-8"))
        for error in summary.get("errors", []):
            url = error.get("url") if isinstance(error, dict) else None
            if isinstance(url, str) and url:
                urls.add(url.rstrip("/"))
    return urls
