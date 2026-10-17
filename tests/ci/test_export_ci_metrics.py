import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / ".github" / "scripts" / "export_ci_metrics.py"
SPEC = importlib.util.spec_from_file_location("export_ci_metrics", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_build_metrics_escapes_labels_and_exports_completed_jobs(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 16, 10, 1, tzinfo=UTC)

    monkeypatch.setattr(MODULE, "datetime", FixedDateTime)
    run = {
        "id": 123,
        "run_attempt": 2,
        "name": 'CI "main"',
        "event": "push",
        "head_branch": "feature/metrics",
        "html_url": "https://github.com/org/repo/actions/runs/123",
        "run_started_at": "2026-10-16T10:00:00Z",
        "repository": {"full_name": "org/repo"},
    }
    jobs = [
        {
            "name": "Feature checks",
            "conclusion": "success",
            "started_at": "2026-10-16T10:00:05Z",
            "completed_at": "2026-10-16T10:00:35Z",
        },
        {"name": "Reporter", "started_at": "2026-10-16T10:00:40Z", "completed_at": None},
    ]

    metrics = MODULE.build_metrics(run, jobs, "success")

    assert 'workflow="CI \\"main\\""' in metrics
    assert "ci_pipeline_run_duration_seconds" in metrics
    assert metrics.endswith(" 30\n")
    assert "Reporter" not in metrics
    # Pushgateway nhóm theo job=github_actions: số liệu có nhãn "job" riêng bị từ chối (HTTP 400).
    assert 'ci_job="' in metrics
    assert ',job="' not in metrics and '{job="' not in metrics


def test_get_paginated_items_follows_next_link(monkeypatch):
    class FakeResponse:
        def __init__(self, body, link=""):
            self.body = body
            self.headers = {"Link": link}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps(self.body).encode()

    urls = []
    responses = [
        FakeResponse(
            {"jobs": [{"id": 1}]},
            '<https://api.github.com/jobs?page=2>; rel="next", <https://api.github.com/jobs?page=2>; rel="last"',
        ),
        FakeResponse({"jobs": [{"id": 2}]}),
    ]

    def fake_urlopen(request, timeout):
        urls.append(request.full_url)
        return responses.pop(0)

    monkeypatch.setattr(MODULE.urllib.request, "urlopen", fake_urlopen)

    assert MODULE._get_paginated_items("https://api.github.com/jobs?page=1", "token", "jobs") == [
        {"id": 1},
        {"id": 2},
    ]
    assert urls == ["https://api.github.com/jobs?page=1", "https://api.github.com/jobs?page=2"]
