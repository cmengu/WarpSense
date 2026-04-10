"""
Output handler for alerts: console (logger) or websocket (HTTP POST).
"""

from __future__ import annotations

import logging
import os
from typing import Literal

from realtime.alert_models import AlertPayload

logger = logging.getLogger(__name__)

# Base URL for HTTP POST. Reads BACKEND_URL env var; falls back to localhost for local dev.
ALERT_BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def handle_alert(
    payload: AlertPayload,
    mode: Literal["console", "websocket"] = "console",
    base_url: str = ALERT_BASE_URL,
) -> None:
    """Emit alert to console or POST to /internal/alert."""
    if mode == "console":
        logger.info(
            "ALERT frame=%s rule=%s severity=%s correction=%s",
            payload.frame_index,
            payload.rule_triggered,
            payload.severity,
            payload.correction,
        )
    elif mode == "websocket":
        import requests
        url = f"{base_url.rstrip('/')}/internal/alert"
        try:
            r = requests.post(url, json=payload.model_dump(), timeout=2)
            r.raise_for_status()
        except Exception as e:
            logger.warning("Failed to POST alert to %s: %s", url, e)
