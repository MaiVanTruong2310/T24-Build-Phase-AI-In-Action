"""Application logging configuration and structured event helpers."""

import json
import logging
import sys
from datetime import datetime, timezone

from src.core.context import session_id_var, trace_id_var, turn_id_var


class JsonFormatter(logging.Formatter):
    """Render one structured JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "trace_id": trace_id_var.get(),
            "session_id": session_id_var.get(),
            "turn_id": turn_id_var.get(),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure the application root logger with the shared JSON formatter."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    description: str | None = None,
    exc_info: bool = False,
    **fields,
) -> None:
    """Write a searchable event name and its structured fields."""
    if description is not None:
        fields["description"] = description
    logger.log(level, event, exc_info=exc_info, extra={"fields": fields})


def get_logger(name: str) -> logging.Logger:
    """Return a logger using the standard library logging API."""
    return logging.getLogger(name)
