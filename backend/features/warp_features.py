"""
Shared warp prediction feature extraction.
Used by training script and prediction_service — NO duplication.
Feature ORDER in FEATURE_COLS determines ONNX input; DO NOT reorder without
retraining and updating this module.
"""
import statistics
from typing import Optional

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


def _safe_float(val, default: float = 0.0) -> float:
    """Coerce to float; return default on ValueError/TypeError. Shared by extract_asymmetry and extract_features."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def extract_asymmetry(frame: dict) -> float:
    """Returns max(|N-S|, |E-W|) from thermal_snapshots, or -1 if no thermal data.
    Duplicate direction keys: first occurrence wins (avoids silent overwrite).
    Direction keys normalized to lowercase — DB may return NORTH, north, North; all map to north.
    temp_celsius: uses _safe_float to avoid crash on non-numeric values from DB/mock."""
    snapshots = frame.get("thermal_snapshots") or []
    if not snapshots:
        return -1.0
    readings_list = snapshots[0].get("readings") or []
    readings = {}
    for r in readings_list:
        d = r.get("direction")
        if d is not None:
            key = str(d).lower()
            if key not in readings:
                readings[key] = _safe_float(r.get("temp_celsius"), 0.0)
    ns = abs(readings.get("north", 0) - readings.get("south", 0))
    ew = abs(readings.get("east", 0) - readings.get("west", 0))
    return max(ns, ew)


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

    asym = extract_asymmetry(center)
    prev = window[-10] if len(window) >= 10 else window[0]
    prev_asym = extract_asymmetry(prev)
    asym_delta = (asym - prev_asym) if asym >= 0 and prev_asym >= 0 else 0.0

    temp = -1.0
    for f in reversed(window):
        snapshots = f.get("thermal_snapshots") or []
        if snapshots:
            for r in snapshots[0].get("readings") or []:
                if str(r.get("direction") or "").lower() == "center":
                    temp = _safe_float(r.get("temp_celsius"), -1.0)
                    break
        if temp >= 0:
            break

    return {
        "angle_mean": statistics.mean(angles) if angles else 45.0,
        "angle_std": statistics.stdev(angles) if len(angles) > 1 else 0.0,
        "amps_mean": statistics.mean(amps) if amps else 150.0,
        "amps_std": statistics.stdev(amps) if len(amps) > 1 else 0.0,
        "volts_mean": statistics.mean(volts) if volts else 22.0,
        "temp_current": temp,
        "thermal_asymmetry": asym,
        "thermal_asymmetry_delta": asym_delta,
    }


def features_to_array(features: dict) -> list[float]:
    """Returns feature values in FEATURE_COLS order for ONNX input."""
    return [float(features[c]) for c in FEATURE_COLS]
