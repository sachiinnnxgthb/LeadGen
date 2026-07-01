"""Structured logging setup.

Provides a single ``configure_logging`` entry point and a ``get_logger`` helper.
Supports either human-readable console output (development) or line-delimited
JSON (production, ``LOG_JSON=true``) suitable for log aggregators.

Kept dependency-free (stdlib ``logging`` only) so the core has no third-party
logging requirement.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_CONFIGURED = False

# Reserved LogRecord attributes we skip when collecting structured "extra" fields.
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Render each record as a single JSON line, including any ``extra`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO", *, json_output: bool = False) -> None:
    """Configure the root logger once for the whole process.

    Args:
        level: Log level name (``DEBUG``/``INFO``/``WARNING``/``ERROR``).
        json_output: Emit structured JSON lines instead of console text.

    Idempotent: repeated calls are no-ops so importing modules can't reconfigure
    logging out from under the application entry point.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger (call ``configure_logging`` first at startup)."""
    return logging.getLogger(f"lead_intel.{name}")
