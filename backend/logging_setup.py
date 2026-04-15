"""Application logging: optional JSON lines and ``request_id`` on every record."""
from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from backend.request_id import get_request_id


class RequestIdFilter(logging.Filter):
    """Attach ``request_id`` for formatters (``-`` when outside a request)."""

    def filter(self, record: logging.LogRecord) -> bool:
        rid = get_request_id()
        record.request_id = rid if rid else "-"
        return True


class JsonLinesFormatter(logging.Formatter):
    """One JSON object per line (good for log aggregators)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            # Use the LogRecord timestamp (event time), not wall-clock at format time.
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = getattr(record, "request_id", None)
        if rid and rid != "-":
            payload["request_id"] = rid
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Optional structured fields from ``logger.info(..., extra={...})``
        for key, value in record.__dict__.items():
            if key in _LOGRECORD_BUILTIN_KEYS or key.startswith("_"):
                continue
            if key in ("asctime",):
                continue
            try:
                json.dumps(value)
            except TypeError:
                payload[key] = repr(value)
            else:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


class TextConsoleFormatter(logging.Formatter):
    """Human-readable default; still includes ``request_id`` when set."""

    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s %(levelname)s [%(request_id)s] %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


_LOGRECORD_BUILTIN_KEYS = frozenset(
    {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
        "message",
        "request_id",
    }
)


def configure_logging(*, json_logs: bool) -> None:
    """Attach a single handler to the ``backend`` logger tree (idempotent)."""
    backend_root = logging.getLogger("backend")
    for h in backend_root.handlers[:]:
        backend_root.removeHandler(h)

    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(JsonLinesFormatter() if json_logs else TextConsoleFormatter())
    backend_root.addHandler(handler)
    backend_root.setLevel(logging.INFO)
    backend_root.propagate = False
