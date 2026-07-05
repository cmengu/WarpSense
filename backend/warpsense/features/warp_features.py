"""
Shared warp prediction feature extraction.
Used by training script and prediction_service — NO duplication.
Feature ORDER in FEATURE_COLS determines ONNX input; DO NOT reorder without
retraining and updating this module.
"""
from typing import Optional

from warpsense.signal.stats import mean, safe_float as _safe_float, sample_std
from warpsense.signal.thermal import latest_center_temp, nsew_asymmetry

FEATURE_COLS = [
    "angle_mean",
    "angle_std",
    "amps_mean",
    "amps_std",
    "volts_mean",
    "temp_current",
    "thermal_asymmetry",
    "thermal_asymmetry_delta",
]

# Historical name; implementation moved to signal/thermal.py (semantics unchanged).
extract_asymmetry = nsew_asymmetry


def extract_features(window: list[dict], center_frame: Optional[dict] = None) -> dict:
    """
    Extract 8 features from a rolling window.
    center_frame: frame at prediction time (default: window[-1]).
    Handles JSONB round-trip: DB may return int for temp_celsius; coerce to float.
    Returns all-default dict for empty window (caller must handle).
    """
    if not window:
        return {c: 0.0 for c in FEATURE_COLS}

    center = center_frame if center_frame is not None else window[-1]
    angles = [
        float(f.get("angle_degrees", 45.0))
        for f in window
        if f.get("angle_degrees") is not None
    ]
    amps = [float(f.get("amps", 150.0)) for f in window if f.get("amps") is not None]
    volts = [float(f.get("volts", 22.0)) for f in window if f.get("volts") is not None]

    asym = nsew_asymmetry(center)
    prev = window[-10] if len(window) >= 10 else window[0]
    prev_asym = nsew_asymmetry(prev)
    asym_delta = (asym - prev_asym) if asym >= 0 and prev_asym >= 0 else 0.0

    return {
        "angle_mean": mean(angles, 45.0),
        "angle_std": sample_std(angles),
        "amps_mean": mean(amps, 150.0),
        "amps_std": sample_std(amps),
        "volts_mean": mean(volts, 22.0),
        "temp_current": latest_center_temp(window),
        "thermal_asymmetry": asym,
        "thermal_asymmetry_delta": asym_delta,
    }


def features_to_array(features: dict) -> list[float]:
    """Returns feature values in FEATURE_COLS order for ONNX input."""
    return [float(features[c]) for c in FEATURE_COLS]
