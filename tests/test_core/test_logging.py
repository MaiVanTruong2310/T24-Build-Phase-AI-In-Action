import json
import logging

from src.core.logging import JsonFormatter


def test_json_formatter_emits_level_message_and_safe_request_fields_only():
    record = logging.LogRecord("test", logging.WARNING, __file__, 1, "booking.update.failed", (), None)
    record.fields = {
        "booking_id": "booking-1",
        "status": "cancelled",
        "status_code": 409,
        "user_id": "private-user",
        "description": "verbose description",
        "error_type": "ConflictError",
    }

    result = json.loads(JsonFormatter().format(record))

    assert result == {
        "level": "WARNING",
        "message": "booking.update.failed",
        "booking_id": "booking-1",
        "status": "cancelled",
        "status_code": 409,
    }
