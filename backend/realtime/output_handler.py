"""
Output handler for alerts: console (print) or websocket (HTTP POST).
"""

from __future__ import annotations

import logging
from typing import Literal

from realtime.alert_models import AlertPayload

logger = logging.getLogger(__name__)

# Base URL for HTTP POST. Overridable for tests.
ALERT_BASE_URL = "http://localhost:8000"


def handle_alert(
    payload: AlertPayload,
    mode: Literal["console", "websocket"] = "console",
    base_url: str = ALERT_BASE_URL,
) -> None:
    """Emit alert to console or POST to /internal/alert."""
    if mode == "console":
        print(
            f"ALERT frame={payload.frame_index} rule={payload.rule_triggered} "
            f"severity={payload.severity} correction={payload.correction}"
        )
    elif mode == "websocket":
        import requests
        url = f"{base_url.rstrip('/')}/internal/alert"
        try:
            r = requests.post(url, json=payload.model_dump(), timeout=2)
            r.raise_for_status()
        except Exception as e:
            logger.warning("Failed to POST alert to %s: %s", url, e)
