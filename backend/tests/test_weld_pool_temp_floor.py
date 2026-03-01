"""
Regression: weld pool temp must never show room temp (< 200°C) on arc-active frames.
See docs/ISSUE_WELD_POOL_TEMP_39C.md. Floor 200°C matches acceptance criteria.
"""
from data.mock_sessions import (
    generate_expert_session,
    generate_novice_session,
    _generate_stitch_expert_frames,
    _generate_continuous_novice_frames,
)


def _center_temp_10mm(frame):
    if not getattr(frame, "thermal_snapshots", None):
        return None
    snap = next(
        (s for s in frame.thermal_snapshots if s.distance_mm == 10.0),
        frame.thermal_snapshots[0] if frame.thermal_snapshots else None,
    )
    if not snap:
        return None
    c = next((r.temp_celsius for r in snap.readings if r.direction == "center"), None)
    return c


def _arc_active(frame):
    return (
        frame.volts
        and frame.volts > 1.0
        and frame.amps
        and frame.amps > 1.0
    )


FLOOR_CELSIUS = 200.0


def test_mild_steel_expert_never_below_200():
    """Mild steel thermal is sparse (every 100ms); only assert on frames with thermal data."""
    s = generate_expert_session("sess_expert_001")
    for f in s.frames:
        if _arc_active(f):
            t = _center_temp_10mm(f)
            if t is not None:
                assert t >= FLOOR_CELSIUS, f"frame {f.timestamp_ms} center={t}°C < {FLOOR_CELSIUS}"


def test_mild_steel_novice_never_below_200():
    """Mild steel thermal is sparse (every 100ms); only assert on frames with thermal data."""
    s = generate_novice_session("sess_novice_001")
    for f in s.frames:
        if _arc_active(f):
            t = _center_temp_10mm(f)
            if t is not None:
                assert t >= FLOOR_CELSIUS, f"frame {f.timestamp_ms} center={t}°C < {FLOOR_CELSIUS}"


def test_aluminum_expert_never_below_200():
    frames = _generate_stitch_expert_frames(0, 1500)
    for f in frames:
        if _arc_active(f):
            t = _center_temp_10mm(f)
            assert t is not None, f"frame {f.timestamp_ms} has no thermal"
            assert t >= FLOOR_CELSIUS, f"frame {f.timestamp_ms} center={t}°C < {FLOOR_CELSIUS}"


def test_aluminum_novice_never_below_200():
    frames = _generate_continuous_novice_frames(0, 1500)
    for f in frames:
        if _arc_active(f):
            t = _center_temp_10mm(f)
            assert t is not None, f"frame {f.timestamp_ms} has no thermal"
            assert t >= FLOOR_CELSIUS, f"frame {f.timestamp_ms} center={t}°C < {FLOOR_CELSIUS}"


def test_aluminum_never_below_200_even_during_arc_off():
    """Arc-off periods must not drop to room temp (39°C). Floor 180°C allows natural cooling.
    Only assert from first arc-on onward — initial frames (novice 0–11) are pre-arc ambient."""
    ARC_OFF_FLOOR = 180.0
    expert_frames = _generate_stitch_expert_frames(0, 1500)
    novice_frames = _generate_continuous_novice_frames(0, 1500)
    for name, frames in [("expert", expert_frames), ("novice", novice_frames)]:
        first_arc = next(i for i, f in enumerate(frames) if _arc_active(f))
        for i, f in enumerate(frames):
            if i < first_arc:
                continue  # skip pre-arc frames (e.g. novice 0–11)
            t = _center_temp_10mm(f)
            if t is not None:
                assert t >= ARC_OFF_FLOOR, (
                    f"{name} frame {f.timestamp_ms} center={t}°C < {ARC_OFF_FLOOR}"
                )
