"""
Verification script for aluminum mock generators.

Run (from backend/):
  python3 -m scripts.verify_aluminum_mock

This script asserts behavioral differences between:
  - stitch_expert (controlled, symmetric thermals)
  - continuous_novice (drift + wrong correction, asymmetric thermals)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

from data.mock_sessions import (
    AL_AMBIENT_TEMP,
    _generate_continuous_novice_frames,
    _generate_stitch_expert_frames,
    _init_thermal_state,
    _step_thermal_state,
)
from models.frame import Frame
from models.session import Session
from models.session import SessionStatus
from models.thermal import ThermalSnapshot


def _north_south_delta(snapshot: ThermalSnapshot) -> float:
    north = next(
        (r.temp_celsius for r in snapshot.readings if r.direction == "north"), None
    )
    south = next(
        (r.temp_celsius for r in snapshot.readings if r.direction == "south"), None
    )
    assert north is not None and south is not None, (
        "ThermalSnapshot must have north and south readings"
    )
    return abs(north - south)

def _percentile(values: list[float], p: float) -> float:
    """
    Pure-Python percentile (linear interpolation, like NumPy default).
    Avoids importing NumPy, which may be unavailable/unstable in some environments.
    """
    if not values:
        raise ValueError("values must be non-empty")
    if p < 0.0 or p > 100.0:
        raise ValueError("p must be in [0, 100]")

    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])

    k = (p / 100.0) * (len(xs) - 1)
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return float(xs[f])
    d0 = xs[f] * (c - k)
    d1 = xs[c] * (k - f)
    return float(d0 + d1)


def _frame_brief(frame: Frame) -> Dict[str, Any]:
    return {
        "t_ms": frame.timestamp_ms,
        "volts": frame.volts,
        "amps": frame.amps,
        "angle": frame.angle_degrees,
        "has_thermal": frame.has_thermal_data,
        "heat_diss": frame.heat_dissipation_rate_celsius_per_sec,
    }


def main() -> None:
    expert_frames = _generate_stitch_expert_frames(0, 1500)
    novice_frames = _generate_continuous_novice_frames(0, 1500)

    # --- Lateral conduction sanity (physics primitive) ---
    state = _init_thermal_state(AL_AMBIENT_TEMP)
    for _ in range(10):
        state = _step_thermal_state(state, True, 85.0)
    assert state[10.0]["north"] > state[10.0]["south"], (
        f"FAIL: north {state[10.0]['north']:.1f} should exceed south {state[10.0]['south']:.1f} at high angle"
    )

    # --- Expert assertions ---
    assert len(expert_frames) == 1500, "FAIL: expert frame count != 1500"
    assert expert_frames[149].volts and expert_frames[149].volts > 0.0, "FAIL: frame 149 should be arc-on"
    assert expert_frames[150].volts == 0.0, "FAIL: frame 150 should be arc-off (volts)"
    assert expert_frames[150].amps == 0.0, "FAIL: frame 150 should be arc-off (amps)"

    for f in expert_frames:
        assert f.angle_degrees is not None
        assert 20.0 <= f.angle_degrees <= 85.0, f"FAIL: expert angle out of range: {f.angle_degrees}"

    expert_deltas = [
        _north_south_delta(s)
        for f in expert_frames
        for s in f.thermal_snapshots
    ]
    assert expert_deltas, "FAIL: expert has no thermal snapshots"
    expert_95 = _percentile(expert_deltas, 95.0)
    assert expert_95 < 12.0, f"FAIL: expert 95th pct N-S asymmetry too high: {expert_95:.1f}°C"

    # --- Novice assertions ---
    assert len(novice_frames) == 1500, "FAIL: novice frame count != 1500"
    for f in novice_frames:
        assert f.angle_degrees is not None
        assert 20.0 <= f.angle_degrees <= 85.0, f"FAIL: novice angle out of range: {f.angle_degrees}"

    novice_deltas = [
        _north_south_delta(s)
        for f in novice_frames
        for s in f.thermal_snapshots
    ]
    assert novice_deltas, "FAIL: novice has no thermal snapshots"
    novice_max = float(max(novice_deltas))
    assert novice_max > 20.0, f"FAIL: novice N-S asymmetry never exceeded 20°C: {novice_max:.1f}°C"
    assert novice_max > expert_95 * 2.0, "FAIL: expert and novice sessions look too similar"

    # --- Session schema validation ---
    expert_session = Session(
        session_id="sess_expert_aluminium_001_001",
        operator_id="expert_aluminium_001",
        start_time=datetime.now(timezone.utc),
        weld_type="aluminum",
        process_type="aluminum",
        thermal_sample_interval_ms=200,
        thermal_directions=["center", "north", "south", "east", "west"],
        thermal_distance_interval_mm=10.0,
        sensor_sample_rate_hz=100,
        frames=expert_frames,
        status=SessionStatus.COMPLETE,
        frame_count=len(expert_frames),
        expected_frame_count=len(expert_frames),
        last_successful_frame_index=len(expert_frames) - 1,
        validation_errors=[],
        completed_at=datetime.now(timezone.utc),
        disable_sensor_continuity_checks=True,
    )

    novice_session = expert_session.model_copy(
        update={
            "session_id": "sess_novice_aluminium_001_001",
            "operator_id": "novice_aluminium_001",
            "frames": novice_frames,
            "frame_count": len(novice_frames),
            "expected_frame_count": len(novice_frames),
            "last_successful_frame_index": len(novice_frames) - 1,
        }
    )

    Session.model_validate(expert_session.model_dump())
    Session.model_validate(novice_session.model_dump())

    # Print brief JSON for inspection
    payload = {
        "expert": {
            "frame_0_30": [_frame_brief(f) for f in expert_frames[:30]],
            "expert_95_ns_delta": expert_95,
        },
        "novice": {
            "frame_0_30": [_frame_brief(f) for f in novice_frames[:30]],
            "frame_200_220": [_frame_brief(f) for f in novice_frames[200:221]],
            "novice_max_ns_delta": novice_max,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    print("ALL ASSERTIONS PASSED")


if __name__ == "__main__":
    main()

