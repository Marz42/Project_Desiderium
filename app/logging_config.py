import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

# Redact Google API keys (AIzaSy…) from log messages to prevent accidental exposure.
_API_KEY_RE = re.compile(r"AIzaSy[A-Za-z0-9_-]{33}")


class ApiKeyRedactFilter(logging.Filter):
    """Strip Google API keys from log records before they are emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _API_KEY_RE.sub("[REDACTED]", str(record.msg))
        record.args = _redact_args(record.args)
        return True


def _redact_args(args: object) -> object:
    if isinstance(args, str):
        return _API_KEY_RE.sub("[REDACTED]", args)
    if isinstance(args, tuple):
        return tuple(_redact_args(a) for a in args)
    if isinstance(args, dict):
        return {k: _redact_args(v) for k, v in args.items()}
    return args


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in ("request_id", "service", "component"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ApiKeyRedactFilter())
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
