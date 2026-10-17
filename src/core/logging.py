"""Application logging configuration and structured event helpers."""

import json
import logging
import sys

_LOG_FIELDS = {
    "entity_id",
    "booking_id",
    "case_id",
    "consultation_id",
    "doctor_id",
    "facility_id",
    "request_id",
    "resource_id",
    "schedule_id",
    "service_id",
    "specialty_id",
    "status",
    "status_code",
}


class JsonFormatter(logging.Formatter):
    """Render a compact JSON object with only useful request fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {"level": record.levelname, "message": record.getMessage()}
        payload.update({key: value for key, value in getattr(record, "fields", {}).items() if key in _LOG_FIELDS})
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
