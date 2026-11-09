from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.observability.redaction import redact_text
from app.observability.tracing import get_request_id


class JsonFormatter(logging.Formatter):
    def __init__(self, *, redact: bool = True) -> None:
        super().__init__()
        self.redact = redact

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if self.redact:
            message = redact_text(message)
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            payload["fields"] = extra_fields
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", *, redact: bool = True) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(redact=redact))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
