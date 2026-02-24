"""
Calibrate alert thresholds from 30 expert + 30 novice aluminum sessions.

Output schema (written only in Phase B with --write):
{ "thermal_ns_warning": float, "thermal_ns_critical": float, "angle_deviation_warning": float,
  "angle_deviation_critical": float, "speed_drop_warning_pct": float, "speed_drop_critical_pct": float,
  "nominal_travel_angle": 12.0, "suppression_ms": 1000 }

Run from backend/: python -m scripts.calibrate_alert_thresholds [--write]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
from pathlib import Path

from data.mock_sessions import (
    _generate_continuous_novice_frames,
    _generate_stitch_expert_frames,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOMINAL_TRAVEL_ANGLE = 12.0
REFERENCE_THERMAL_NS = (6.0, 14.0)
REFERENCE_ANGLE_DEV = (3.0, 7.0)
REFERENCE_SPEED_DROP = (6.0, 12.0)


def _north_south_asymmetry(frame) -> float:
    """North minus south temperature at 10mm. 0 if no thermal."""
    if not frame.thermal_snapshots:
        return 0.0
    snap = frame.thermal_snapshots[0]
    north = next((r.temp_celsius for r in snap.readings if r.direction == "north"), None)
    south = next((r.temp_celsius for r in snap.readings if r.direction == "south"), None)
    if north is None or south is None:
        logger.warning("Missing north or south in thermal snapshot")
        return 0.0
    return north - south


def _travel_angle_deviation(frame) -> float:
    """|travel_angle_degrees - 12|."""
    if frame.travel_angle_degrees is None:
        return 0.0
    return abs(frame.travel_angle_degrees - NOMINAL_TRAVEL_ANGLE)


def _speed_change_pct(speeds: list[float], idx: int) -> float:
    """(current - speed_10_ago) / speed_10_ago * 100 when speed_10_ago > 0. Same as frame_buffer."""
    if idx < 10:
        return 0.0
    current = speeds[idx]
    speed_10_ago = speeds[idx - 10]
    if speed_10_ago <= 0:
        return 0.0
    return (current - speed_10_ago) / speed_10_ago * 100.0


def _percentile(values: list[float], p: float) -> float:
    """Approximate percentile. p in 0..100."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = max(0, min(len(sorted_vals) - 1, int(len(sorted_vals) * p / 100)))
    return sorted_vals[idx]


def _collect_expert_metrics() -> tuple[list[float], list[float], list[float]]:
    """Collect ns_asymmetry (abs), angle_deviation, speed_drop (abs of negative) per frame."""
    ns_vals: list[float] = []
    angle_vals: list[float] = []
    speed_drop_vals: list[float] = []

    for i in range(30):
        frames = _generate_stitch_expert_frames(session_index=i, num_frames=1500)
        speeds: list[float] = []
        for frame in frames:
            ns = _north_south_asymmetry(frame)
            ns_vals.append(abs(ns))
            angle_vals.append(_travel_angle_deviation(frame))
            s = frame.travel_speed_mm_per_min or 0.0
            speeds.append(s)
        for idx in range(10, len(speeds)):
            pct = _speed_change_pct(speeds, idx)
            if pct < 0:
                speed_drop_vals.append(abs(pct))
    return ns_vals, angle_vals, speed_drop_vals


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate alert thresholds from expert/novice sessions")
    parser.add_argument("--write", action="store_true", help="Write alert_thresholds.json after calibration")
    args = parser.parse_args()

    ns_vals, angle_vals, speed_drop_vals = _collect_expert_metrics()

    thermal_ns_warning = _percentile(ns_vals, 95)
    thermal_ns_critical = _percentile(ns_vals, 99)
    angle_deviation_warning = _percentile(angle_vals, 95)
    angle_deviation_critical = _percentile(angle_vals, 99)
    speed_drop_warning_pct = _percentile(speed_drop_vals, 95) if speed_drop_vals else 0.0
    speed_drop_critical_pct = _percentile(speed_drop_vals, 99) if speed_drop_vals else 0.0

    thermal_ok = REFERENCE_THERMAL_NS[0] <= thermal_ns_warning <= REFERENCE_THERMAL_NS[1]
    angle_ok = REFERENCE_ANGLE_DEV[0] <= angle_deviation_warning <= REFERENCE_ANGLE_DEV[1]
    speed_ok = REFERENCE_SPEED_DROP[0] <= speed_drop_warning_pct <= REFERENCE_SPEED_DROP[1]

    print("Calibration results (expert p95 warning / p99 critical):")
    print(f"  thermal_ns_warning:   {thermal_ns_warning:.2f} °C  {'PASS' if thermal_ok else 'WARN'} (ref {REFERENCE_THERMAL_NS})")
    print(f"  thermal_ns_critical:  {thermal_ns_critical:.2f} °C")
    print(f"  angle_deviation_warning:  {angle_deviation_warning:.2f} °  {'PASS' if angle_ok else 'WARN'} (ref {REFERENCE_ANGLE_DEV})")
    print(f"  angle_deviation_critical: {angle_deviation_critical:.2f} °")
    print(f"  speed_drop_warning_pct:   {speed_drop_warning_pct:.2f} %  {'PASS' if speed_ok else 'WARN'} (ref {REFERENCE_SPEED_DROP})")
    print(f"  speed_drop_critical_pct:  {speed_drop_critical_pct:.2f} %")

    all_ok = thermal_ok and angle_ok and speed_ok
    if not all_ok:
        print("WARN: Some values outside reference range. Review before --write.")

    if args.write and all_ok:
        config_dir = Path(__file__).resolve().parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        out_path = config_dir / "alert_thresholds.json"
        payload = {
            "thermal_ns_warning": round(thermal_ns_warning, 2),
            "thermal_ns_critical": round(thermal_ns_critical, 2),
            "angle_deviation_warning": round(angle_deviation_warning, 2),
            "angle_deviation_critical": round(angle_deviation_critical, 2),
            "speed_drop_warning_pct": round(speed_drop_warning_pct, 2),
            "speed_drop_critical_pct": round(speed_drop_critical_pct, 2),
            "nominal_travel_angle": NOMINAL_TRAVEL_ANGLE,
            "suppression_ms": 1000,
        }
        out_path.write_text(json.dumps(payload, indent=2))
        print(f"Wrote {out_path}")
    elif args.write and not all_ok:
        print("Refusing to write — values outside reference range. Fix or approve manually.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
