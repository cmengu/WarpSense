"""
Sweep AL_MAX_TEMP to find a threshold where novice weld pool temps look natural
(not obviously capped). Run: cd backend && python -m scripts.sweep_al_max_temp

Reports percentile spread (p95-p5) for novice arc-on frames. When spread is
> ~40°C, data looks legitimate; flat p5=p95=cap means obviously capped.
"""


def run_sweep():
    from data import mock_sessions

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

    caps = [500, 520, 530, 550, 580, 600, 620, 650, 700]
    print("AL_MAX_TEMP  |  min   max   p5    p25   p50   p75   p95  | p95-p5  | Verdict")
    print("-" * 80)

    for cap in caps:
        mock_sessions.AL_MAX_TEMP = float(cap)
        frames = mock_sessions._generate_continuous_novice_frames(0, 1500)
        arc_on = [t for f in frames if (t := _center_10mm(f)) is not None and _arc_active(f)]
        if not arc_on:
            print(f"{cap:>11}  |  (no arc-on thermal)")
            continue
        pct = percentiles(arc_on, [5, 25, 50, 75, 95])
        spread = pct[95] - pct[5]
        hit_cap = sum(1 for t in arc_on if t >= cap - 0.5) / len(arc_on) * 100
        if hit_cap > 90 and spread < 15:
            verdict = "FLAT (capped)"
        elif spread < 25:
            verdict = "marginal"
        else:
            verdict = "natural"
        print(f"{cap:>11}  | {min(arc_on):5.1f} {max(arc_on):5.1f} {pct[5]:5.1f} {pct[25]:5.1f} {pct[50]:5.1f} {pct[75]:5.1f} {pct[95]:5.1f} | {spread:5.1f}°C | {verdict} ({hit_cap:.0f}% at cap)")

    print("\nRecommendation: Pick lowest AL_MAX_TEMP where verdict=natural and <80% at cap.")
    print("Aluminum HAZ at 10mm ~500°C; 580–620°C is conservative for demo realism.")


if __name__ == "__main__":
    run_sweep()
