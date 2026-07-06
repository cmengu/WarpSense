"""
Structured logging configuration for WarpSense agent pipeline.

Call configure_logging() once at application startup (eval scripts, main.py).
All agent modules use logging.getLogger(__name__) — they are unaware of
the handler or formatter.

WARPSENSE_LOG_FORMAT=json  → one JSON object per log line (machine-queryable)
WARPSENSE_LOG_FORMAT=text  → human-readable with timestamp (default)
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Emits one JSON object per log line.
    Captures extra fields: session_id, agent_name, prompt_version, run_id.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("session_id", "agent_name", "prompt_version", "run_id"):
            val = getattr(record, field, None)
            if val is not None:
                log_entry[field] = val
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger.

    Idempotent: returns immediately if handlers are already attached.
    Set WARPSENSE_LOG_FORMAT=json for machine-readable output.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    log_format = os.environ.get("WARPSENSE_LOG_FORMAT", "text")
    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        ))

    root.setLevel(level)
    root.addHandler(handler)
