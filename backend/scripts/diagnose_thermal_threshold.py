"""
Diagnose thermal override threshold for aluminum mock.

Run: cd backend && python -m scripts.diagnose_thermal_threshold

Finds: (1) center_10mm distribution during arc-on for expert/novice,
(2) how often override at 380°C fires, (3) recommended threshold so data
looks realistic and stitch pattern dominates.
"""
from collections import defaultdict

from data.mock_sessions import (
    AL_MAX_TEMP,
    _generate_stitch_expert_frames,
    _generate_continuous_novice_frames,
)


def _center_10mm(frame):
    if not getattr(frame, "thermal_snapshots", None):
        return None
    snap = next(
        (s for s in frame.thermal_snapshots if s.distance_mm == 10.0),
        frame.thermal_snapshots[0] if frame.thermal_snapshots else None,
    )
    if not snap:
        return None
    return next((r.temp_celsius for r in snap.readings if r.direction == "center"), None)


def _arc_active(frame):
    return frame.volts and frame.volts > 1.0 and frame.amps and frame.amps > 1.0


def percentiles(vals, ps):
    xs = sorted(v for v in vals if v is not None)
    if not xs:
        return {}
    n = len(xs)
    return {p: xs[max(0, int(n * p / 100) - 1)] for p in ps}


def main():
    print("=== Aluminum Thermal Threshold Diagnosis ===\n")

    expert_frames = _generate_stitch_expert_frames(0, 1500)
    novice_frames = _generate_continuous_novice_frames(0, 1500)

    for name, frames in [("expert", expert_frames), ("novice", novice_frames)]:
        arc_on_temps = []
        arc_off_temps = []
        override_count_380 = 0
        override_count_450 = 0
        override_count_500 = 0

        for i, f in enumerate(frames):
            t = _center_10mm(f)
            if t is None:
                continue
            if _arc_active(f):
                arc_on_temps.append(t)
                if t > 380:
                    override_count_380 += 1
                if t > 450:
                    override_count_450 += 1
                if t > 500:
                    override_count_500 += 1
            else:
                arc_off_temps.append(t)

        total_arc_on = len(arc_on_temps)
        total_frames = len([f for f in frames if _center_10mm(f) is not None])

        print(f"--- {name.upper()} ---")
        print(f"  Arc-on frames: {total_arc_on} / {total_frames}")
        if arc_on_temps:
            pct = percentiles(arc_on_temps, [5, 25, 50, 75, 95, 99])
            print(f"  Center 10mm during arc-on: min={min(arc_on_temps):.1f} max={max(arc_on_temps):.1f}")
            print(f"    p5={pct[5]:.1f} p25={pct[25]:.1f} p50={pct[50]:.1f} p75={pct[75]:.1f} p95={pct[95]:.1f} p99={pct[99]:.1f}")
            print(f"  Frames where center > 380°C (override fires): {override_count_380} ({100*override_count_380/total_arc_on:.1f}% of arc-on)")
            print(f"  Frames where center > 450°C: {override_count_450}")
            print(f"  Frames where center > 500°C (above AL_MAX): {override_count_500}")
        if arc_off_temps:
            print(f"  Arc-off center 10mm: min={min(arc_off_temps):.1f} max={max(arc_off_temps):.1f}")
        print()

    print("--- AL_MAX_TEMP (hard clamp in _step_thermal_state) ---")
    print(f"  {AL_MAX_TEMP}°C")
    print()
    print("--- Summary ---")
    print(f"  AL_MAX_TEMP = {AL_MAX_TEMP}°C (hard clamp)")
    print(f"  AL_HEAT_INPUT_SCALE drives equilibrium; thermal uses actual amps/volts for power.")


if __name__ == "__main__":
    main()
