import json
from pathlib import Path

import pytest

from src.medical_assistant.ingestion.crawl_utils import (
    CrawlRunLock,
    JsonlStore,
    append_jsonl,
    atomic_write_json,
    load_failed_urls,
    update_checkpoint,
)


def test_jsonl_store_appends_durably_and_deduplicates(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    store = JsonlStore(path)
    record = {"source_url": "https://example.com/a", "name": "A"}

    assert store.append(record) is True
    assert store.append(record) is False
    assert JsonlStore(path).records == [record]


def test_jsonl_store_rejects_corrupt_data(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"
    path.write_text('{"source_url":"ok"}\n{"broken":', encoding="utf-8")
    with pytest.raises(ValueError, match="Corrupt JSONL"):
        JsonlStore(path)


def test_checkpoint_failure_log_and_lock(tmp_path: Path) -> None:
    checkpoint = tmp_path / "state.json"
    atomic_write_json(checkpoint, {"status": "starting"})
    update_checkpoint(checkpoint, status="running", completed_count=2)
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert state["status"] == "running"
    assert state["completed_count"] == 2
    assert "updated_at" in state

    failures = tmp_path / "failed.jsonl"
    append_jsonl(failures, {"url": "https://example.com/fail"})
    assert load_failed_urls(failures) == {"https://example.com/fail"}

    lock_path = tmp_path / "crawler.lock"
    with CrawlRunLock(lock_path):
        with pytest.raises(RuntimeError, match="lock exists"):
            with CrawlRunLock(lock_path):
                pass
    assert not lock_path.exists()
