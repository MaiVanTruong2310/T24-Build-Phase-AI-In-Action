"""Telemetry Logger & Rotating File Handler Configuration.

Cung cấp:
1. RotatingFileHandler ghi log TURN_TELEMETRY ra file xoay vòng (logs/telemetry.log).
2. Hàm get_daily_telemetry_metrics để tổng hợp chỉ số fallback/clarify/data_unavailable theo ngày.
"""

from __future__ import annotations

import glob
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from scripts.stats_telemetry import compute_statistics, parse_telemetry_lines

TELEMETRY_LOG_DIR = Path("logs")
TELEMETRY_LOG_FILE = TELEMETRY_LOG_DIR / "telemetry.log"


def configure_telemetry_rotating_logger(
    log_dir: Path | str = TELEMETRY_LOG_DIR,
    filename: str = "telemetry.log",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Cấu hình RotatingFileHandler cho log telemetry nếu chưa có."""
    dir_path = Path(log_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename

    # Gắn handler vào logger src.medical_assistant và root
    target_logger = logging.getLogger("src.medical_assistant")

    # Kiểm tra xem đã có handler trỏ tới file này chưa
    has_handler = any(
        isinstance(h, RotatingFileHandler) and Path(getattr(h, "baseFilename", "")).name == filename
        for h in target_logger.handlers
    )

    if not has_handler:
        file_handler = RotatingFileHandler(
            filename=str(file_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        target_logger.addHandler(file_handler)

    return target_logger


def get_daily_telemetry_metrics(target_date: str | None = None) -> dict[str, Any]:
    """Đọc dữ liệu log xoay vòng và tổng hợp số liệu thống kê theo ngày."""
    lines: list[str] = []

    if TELEMETRY_LOG_DIR.exists():
        log_files = sorted(glob.glob(str(TELEMETRY_LOG_DIR / "telemetry.log*")), reverse=True)
        for lf in log_files:
            try:
                with open(lf, encoding="utf-8", errors="ignore") as f:
                    lines.extend(f.readlines())
            except Exception:
                continue

    records = parse_telemetry_lines(lines)
    all_stats = compute_statistics(records)

    if target_date:
        return {
            "date": target_date,
            "metrics": all_stats.get(
                target_date,
                {
                    "total_turns": 0,
                    "fallback_count": 0,
                    "fallback_rate_pct": 0.0,
                    "clarify_visit_purpose_count": 0,
                    "clarify_visit_purpose_rate_pct": 0.0,
                    "data_unavailable_count": 0,
                    "data_unavailable_rate_pct": 0.0,
                    "info_unavailable_count": 0,
                    "info_unavailable_rate_pct": 0.0,
                    "route_distribution": {"info_agent": 0, "clinical": 0, "chitchat": 0},
                    "avg_latency_ms": 0.0,
                },
            ),
        }

    return {
        "dates_available": list(all_stats.keys()),
        "metrics_by_date": all_stats,
    }
