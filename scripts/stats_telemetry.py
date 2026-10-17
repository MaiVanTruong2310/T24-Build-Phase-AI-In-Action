#!/usr/bin/env python3
"""
scripts/stats_telemetry.py
Thống kê tỷ lệ fallback, tỷ lệ clarify_visit_purpose, tỷ lệ data_unavailable theo ngày/phiên
từ structured telemetry logs.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any


def parse_telemetry_lines(lines: list[str]) -> list[dict[str, Any]]:
    """Trích xuất các bản ghi JSON từ dòng TURN_TELEMETRY."""
    records = []
    pattern = re.compile(r"TURN_TELEMETRY:\s*(\{.*\})")
    timestamp_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})")

    for line in lines:
        match = pattern.search(line)
        if match:
            try:
                data = json.loads(match.group(1))
                # Tìm date nếu có ở đầu dòng log
                ts_match = timestamp_pattern.search(line.strip())
                data["_date"] = ts_match.group(1) if ts_match else datetime.now().strftime("%Y-%m-%d")
                records.append(data)
            except Exception:
                continue
    return records


def compute_statistics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Tính toán thống kê chi tiết theo ngày."""
    stats_by_date = defaultdict(lambda: {
        "total_turns": 0,
        "fallback_count": 0,
        "clarify_visit_purpose_count": 0,
        "data_unavailable_count": 0,
        "info_unavailable_count": 0,
        "info_agent_turns": 0,
        "clinical_turns": 0,
        "chitchat_turns": 0,
        "total_latency_ms": 0.0,
        "latencies": [],
    })

    for rec in records:
        d = rec.get("_date", "unknown")
        s = stats_by_date[d]
        s["total_turns"] += 1

        if rec.get("fallback_used"):
            s["fallback_count"] += 1

        if rec.get("workflow_status") == "VISIT_PURPOSE_CLARIFICATION":
            s["clarify_visit_purpose_count"] += 1

        if rec.get("workflow_status") == "INFO_UNAVAILABLE":
            s["info_unavailable_count"] += 1

        if rec.get("data_unavailable"):
            s["data_unavailable_count"] += 1

        route = rec.get("route", "")
        if route == "info_agent":
            s["info_agent_turns"] += 1
        elif route == "clinical":
            s["clinical_turns"] += 1
        elif route == "chitchat":
            s["chitchat_turns"] += 1

        lat = float(rec.get("latency_ms", 0.0))
        s["total_latency_ms"] += lat
        s["latencies"].append(lat)

    report = {}
    for d, s in sorted(stats_by_date.items()):
        total = s["total_turns"]
        fallback_rate = (s["fallback_count"] / total * 100) if total else 0.0
        clarify_rate = (s["clarify_visit_purpose_count"] / total * 100) if total else 0.0
        data_unavail_rate = (s["data_unavailable_count"] / total * 100) if total else 0.0
        info_unavail_rate = (s["info_unavailable_count"] / total * 100) if total else 0.0
        avg_latency = (s["total_latency_ms"] / total) if total else 0.0

        report[d] = {
            "total_turns": total,
            "fallback_count": s["fallback_count"],
            "fallback_rate_pct": round(fallback_rate, 2),
            "clarify_visit_purpose_count": s["clarify_visit_purpose_count"],
            "clarify_visit_purpose_rate_pct": round(clarify_rate, 2),
            "data_unavailable_count": s["data_unavailable_count"],
            "data_unavailable_rate_pct": round(data_unavail_rate, 2),
            "info_unavailable_count": s["info_unavailable_count"],
            "info_unavailable_rate_pct": round(info_unavail_rate, 2),
            "route_distribution": {
                "info_agent": s["info_agent_turns"],
                "clinical": s["clinical_turns"],
                "chitchat": s["chitchat_turns"],
            },
            "avg_latency_ms": round(avg_latency, 2),
        }
    return report


def format_markdown_report(stats: dict[str, Any]) -> str:
    """Định dạng báo cáo ra Markdown."""
    lines = [
        "# Báo Cáo Thống Kê Telemetry Hàng Ngày",
        "",
        "| Ngày | Tổng lượt | Tỷ lệ Fallback | Tỷ lệ Clarify | DB Unavailable | Avg Latency (ms) |",
        "|---|---|---|---|---|---|",
    ]
    if not stats:
        lines.append("| Không có dữ liệu | 0 | 0% | 0% | 0% | 0 |")
    else:
        for d, item in stats.items():
            lines.append(
                f"| {d} | {item['total_turns']} | "
                f"{item['fallback_rate_pct']}% ({item['fallback_count']}) | "
                f"{item['clarify_visit_purpose_rate_pct']}% ({item['clarify_visit_purpose_count']}) | "
                f"{item['data_unavailable_rate_pct']}% ({item['data_unavailable_count']}) | "
                f"{item['avg_latency_ms']} |"
            )
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Thống kê tỷ lệ fallback & clarify từ log")
    parser.add_argument("--log-file", type=str, help="Đường dẫn file log cần phân tích", default=None)
    parser.add_argument("--json", action="store_true", help="Xuất kết quả dạng JSON")
    args = parser.parse_args()

    lines = []
    if args.log_file and os.path.exists(args.log_file):
        with open(args.log_file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    elif not sys.stdin.isatty():
        lines = sys.stdin.readlines()

    records = parse_telemetry_lines(lines)
    stats = compute_statistics(records)

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        print(format_markdown_report(stats))


if __name__ == "__main__":
    main()
