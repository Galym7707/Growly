from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any


_REDACTIONS = (
    (
        re.compile(r"(?i)(https://api\.telegram\.org/bot)[^/\s]+"),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"\b\d{7,12}:[A-Za-z0-9_-]{25,}\b"),
        "[REDACTED]",
    ),
    (re.compile(r"(?i)(bearer\s+)[^\s]+"), r"\1[REDACTED]"),
    (
        re.compile(r"(?i)(postgres(?:ql)?(?:\+\w+)?://[^:\s]+:)[^@\s]+(@)"),
        r"\1[REDACTED]\2",
    ),
    (
        re.compile(
            r"(?i)((?:api[_-]?key|token|password|secret|database_url)\s*[=:]\s*)[^\s,;]+"
        ),
        r"\1[REDACTED]",
    ),
)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if any(part in key.lower() for part in ("key", "token", "password", "secret", "url"))
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if not isinstance(value, str):
        return value
    result = value
    for pattern, replacement in _REDACTIONS:
        result = pattern.sub(replacement, result)
    return result


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    for noisy_logger in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
