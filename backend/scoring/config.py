"""
Load and validate scoring_config.json. Single source for WPS range and component weights.
"""

import json
from pathlib import Path

REQUIRED_KEYS = (
    "wps_heat_input_min_kj_per_mm",
    "wps_heat_input_max_kj_per_mm",
    "torch_angle_max_degrees",
    "interpass_min_ms",
    "interpass_max_temp_c",
    "arc_termination_weight",
    "heat_input_weight",
    "torch_angle_weight",
    "defect_alert_weight",
    "interpass_weight",
)


def load_scoring_config(config_path: str) -> dict:
    """Load and validate scoring_config.json. Raises ValueError on missing keys."""
    path = Path(config_path)
    if not path.is_absolute():
        backend = Path(__file__).resolve().parent.parent
        path = backend / config_path
    if not path.exists():
        raise FileNotFoundError(f"scoring_config not found: {path}")
    data = json.loads(path.read_text())
    for key in REQUIRED_KEYS:
        if data.get(key) is None:
            raise ValueError(f"scoring_config key {key!r} is null or missing in {path}")
    return data
