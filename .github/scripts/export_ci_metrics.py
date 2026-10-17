"""Export the current GitHub Actions run as a small Prometheus payload."""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.request
from datetime import UTC, datetime


def _escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _labels(values: dict[str, object]) -> str:
    return ",".join(f'{key}="{_escape(value)}"' for key, value in values.items())


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_metrics(run: dict[str, object], jobs: list[dict[str, object]], conclusion: str) -> str:
    common = {
        "repository": run["repository"]["full_name"],
        "workflow": run["name"],
        "event": run["event"],
        "branch": run.get("head_branch") or "unknown",
        "conclusion": conclusion,
        "run_id": run["id"],
        "run_attempt": run["run_attempt"],
        "run_url": run["html_url"],
    }
    now = datetime.now(UTC)
    lines = [
        f"ci_pipeline_run_info{{{_labels(common)}}} 1",
        f"ci_pipeline_run_duration_seconds{{{_labels(common)}}} "
        f"{max(0, int((now - _timestamp(str(run['run_started_at']))).total_seconds()))}",
    ]
    for job in jobs:
        if not job.get("completed_at") or not job.get("started_at"):
            continue
        labels = common | {
            # Không dùng nhãn "job": trùng nhãn nhóm job=github_actions của Pushgateway → cả gói bị từ chối (HTTP 400).
            "ci_job": job["name"],
            "job_conclusion": job.get("conclusion") or "unknown",
        }
        duration = int((_timestamp(str(job["completed_at"])) - _timestamp(str(job["started_at"]))).total_seconds())
        lines.append(f"ci_pipeline_job_duration_seconds{{{_labels(labels)}}} {max(0, duration)}")
    return "\n".join(lines) + "\n"


def _get_json(url: str, token: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _get_paginated_items(url: str, token: str, key: str) -> list[dict[str, object]]:
    items = []
    next_url = url
    while next_url:
        request = urllib.request.Request(
            next_url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            items.extend(json.load(response)[key])
            link_header = response.headers.get("Link", "")
        next_url = next(
            (
                match.group(1)
                for match in re.finditer(r'<([^>]+)>;\s*rel="([^"]+)"', link_header)
                if match.group(2) == "next"
            ),
            "",
        )
    return items


def main() -> None:
    repository = os.environ["GITHUB_REPOSITORY"]
    run_id = os.environ["GITHUB_RUN_ID"]
    api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    token = os.environ["GITHUB_TOKEN"]
    run = _get_json(f"{api_url}/repos/{repository}/actions/runs/{run_id}", token)
    jobs = _get_paginated_items(
        f"{api_url}/repos/{repository}/actions/runs/{run_id}/jobs?per_page=100",
        token,
        "jobs",
    )
    payload = base64.b64encode(build_metrics(run, jobs, sys.argv[1]).encode()).decode()
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"payload={payload}\n")


if __name__ == "__main__":
    main()
