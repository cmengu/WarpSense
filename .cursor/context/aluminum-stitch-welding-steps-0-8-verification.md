# Aluminum Stitch Welding Implementation — Steps 0–11: Full Code and Verification

This document captures all code executed from Step 0 through Step 11 of the aluminum stitch welding mock data implementation. It includes the verification script that asserts behavioral differences between **stitch_expert** (expert) and **continuous_novice** (novice) sessions.

**Related:** `.cursor/plans/aluminum-threshold-implementation-plan.md` — wiring scoring to dedicated aluminum thresholds (process_type, migrations, score verification).

---

## Verification Script (Primary Test for Expert + Novice)

**Location:** `backend/scripts/verify_aluminum_mock.py`

**Run:**
```bash
cd backend && python3 -m scripts.verify_aluminum_mock
```

**Purpose:** Asserts behavioral differences between expert and novice aluminum sessions (stitch pattern vs continuous arc, thermal symmetry vs asymmetry).

---

### Full Verification Script Code

```python
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
from models.session import Session
from models.session import SessionStatus


def _north_south_delta(snapshot) -> float:
    north = next(r.temp_celsius for r in snapshot.readings if r.direction == "north")
    south = next(r.temp_celsius for r in snapshot.readings if r.direction == "south")
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


def _frame_brief(frame) -> Dict[str, Any]:
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
```

---

## Step 0: Raise heat_diss_consistency Threshold

### `backend/scoring/rule_based.py`

```python
# Line ~24:
HEAT_DISS_CONSISTENCY_THRESHOLD = 80.0   # was 40.0
```

### `backend/services/threshold_service.py`

MIG fallback uses `heat_diss_consistency=80` in both `if not _threshold_cache` and `if not rows` branches (lines 63–88).

### `backend/tests/test_scoring_thresholds.py`

```python
# seeded_weld_thresholds fixture:
("mig", 45.0, 5.0, 15.0, 60.0, 80.0, 5.0, 1.0, 80.0),
("tig", 75.0, 10.0, 20.0, 60.0, 80.0, 5.0, 1.0, 80.0),
```

### `backend/tests/test_thresholds_api.py`

Same `hd=80.0` in `seeded_weld_thresholds` fixture for mig/tig/stick/flux_core.

---

## Step 1: Add Welder Entries to mock_welders.py

### `backend/data/mock_welders.py`

```python
WELDER_ARCHETYPES = [
    # ... existing 10 entries ...
    {"welder_id": "expert_aluminium_001", "name": "Senior Welder A", "arc": "stitch_expert", "sessions": 4, "base": 85, "delta": 4},
    {"welder_id": "novice_aluminium_001", "name": "Trainee Welder B", "arc": "continuous_novice", "sessions": 6, "base": 48, "delta": -3},
]
```

### `backend/tests/test_mock_welders.py`

```python
def test_welder_archetypes_has_12():
    assert len(WELDER_ARCHETYPES) == 12
```

And `test_mock_sessions_fast_learner_session0_in_band` band updated to `80 <= sc.total <= 100` for heat_diss threshold change.

---

## Step 2: Add Aluminum Constants to mock_sessions.py

### `backend/data/mock_sessions.py`

```python
# Aluminum 6061 constants (used by stitch_expert / continuous_novice generators)
# ---------------------------------------------------------------------------
AL_VOLTS = 21.0
AL_AMPS = 145.0
AL_AMBIENT_TEMP = 25.0
AL_DISSIPATION_COEFF = 0.09
AL_MAX_TEMP = 480.0
AL_CONDUCTIVITY_AXIAL = 0.035    # heat flow 10→20→30→40→50mm per frame
AL_CONDUCTIVITY_LATERAL = 0.045  # heat flow center→N/S/E/W per frame
AL_CONDUCTIVITY_EW_RATIO = 0.6   # east/west conduct less (not on arc axis)
AL_ARC_INPUT_DISTANCE_MM = 10    # arc energy enters at closest node only
```

Ensure `import random` is present.

---

## Step 3: Add _init_thermal_state, _step_thermal_state, _aluminum_state_to_snapshots

### `backend/data/mock_sessions.py`

```python
ThermalState = Dict[float, Dict[str, float]]

def _init_thermal_state(ambient: float) -> ThermalState:
    return {
        dist: {d: ambient for d in ("center", "north", "south", "east", "west")}
        for dist in THERMAL_DISTANCES_MM
    }


def _step_thermal_state(
    state: ThermalState,
    arc_active: bool,
    angle_degrees: float,
) -> ThermalState:
    new = {dist: dict(dirs) for dist, dirs in state.items()}

    # 1) Arc input at 10mm only (closest node)
    if arc_active:
        heat = ((AL_VOLTS * AL_AMPS) / 1000.0) * 20.0   # scaled for realistic temps
        raw_bias = (angle_degrees - 45.0) / 45.0
        bias = math.copysign(min(0.4, abs(raw_bias)), raw_bias)

        d0 = float(AL_ARC_INPUT_DISTANCE_MM)
        new[d0]["center"] += heat * 0.5
        new[d0]["north"] += heat * (0.25 + bias * 0.2)
        new[d0]["south"] += heat * (0.25 - bias * 0.2)

    # 2) Axial conduction (along seam axis: 10→20→30→40→50)
    distances = sorted(THERMAL_DISTANCES_MM)
    for direction in ("center", "north", "south", "east", "west"):
        for i in range(1, len(distances)):
            near, far = distances[i - 1], distances[i]
            delta = (state[near][direction] - state[far][direction]) * AL_CONDUCTIVITY_AXIAL
            new[near][direction] -= delta
            new[far][direction] += delta

    # 3) Lateral conduction — reads from new (post arc-input)
    for dist in THERMAL_DISTANCES_MM:
        center_temp = new[dist]["center"]
        for direction in ("north", "south"):
            delta = (center_temp - new[dist][direction]) * AL_CONDUCTIVITY_LATERAL
            new[dist]["center"] -= delta
            new[dist][direction] += delta
        for direction in ("east", "west"):
            delta = (
                (center_temp - new[dist][direction])
                * AL_CONDUCTIVITY_LATERAL
                * AL_CONDUCTIVITY_EW_RATIO
            )
            new[dist]["center"] -= delta
            new[dist][direction] += delta

    # 4) Dissipation (per node)
    for dist in THERMAL_DISTANCES_MM:
        for direction in new[dist]:
            excess = new[dist][direction] - AL_AMBIENT_TEMP
            new[dist][direction] -= AL_DISSIPATION_COEFF * excess
            new[dist][direction] = max(
                AL_AMBIENT_TEMP, min(AL_MAX_TEMP, new[dist][direction])
            )

    return new


def _aluminum_state_to_snapshots(state: ThermalState) -> List[ThermalSnapshot]:
    snapshots: List[ThermalSnapshot] = []
    for dist in THERMAL_DISTANCES_MM:
        d = state[dist]
        readings = [
            TemperaturePoint(direction="center", temp_celsius=d["center"]),
            TemperaturePoint(direction="north", temp_celsius=d["north"]),
            TemperaturePoint(direction="south", temp_celsius=d["south"]),
            TemperaturePoint(direction="east", temp_celsius=d["east"]),
            TemperaturePoint(direction="west", temp_celsius=d["west"]),
        ]
        snapshots.append(ThermalSnapshot(distance_mm=dist, readings=readings))
    return snapshots
```

---

## Step 4: Add _generate_stitch_expert_frames

### `backend/data/mock_sessions.py`

```python
def _generate_stitch_expert_frames(
    session_index: int,
    num_frames: int = 1500,
) -> List[Frame]:
    """
    Aluminum stitch expert:
    - Stitch pattern: 150 frames arc-on, 100 frames arc-off (repeats)
    - Thermal override: if 10mm center > 220°C, force arc off
    - Thermal grid state advances every frame; thermal snapshots emitted every 20 frames (200ms)
    - heat_dissipation_rate set only on thermal frames (cooling-only metric: clamp at 0)
    """
    random.seed(session_index * 42)

    frames: List[Frame] = []
    thermal_state = _init_thermal_state(AL_AMBIENT_TEMP)
    angle = 45.0

    last_thermal_center_10mm: Optional[float] = None
    thermal_interval_sec = 0.2  # 20 frames × 10ms

    for i in range(num_frames):
        arc_active = (i % 250) < 150

        # Thermal override after stitch logic — thermal wins
        center_10mm = thermal_state[10.0]["center"]
        if center_10mm > 220.0:
            arc_active = False

        # Angle reacts to thermal state (expert behavior)
        north_10mm = thermal_state[10.0]["north"]
        south_10mm = thermal_state[10.0]["south"]
        if center_10mm > 180.0 and (north_10mm - south_10mm) > 10.0:
            angle_target = 35.0
        elif center_10mm > 220.0:
            angle_target = 90.0
        else:
            angle_target = 45.0

        angle += (angle_target - angle) * 0.03 + random.gauss(0.0, 1.2)
        angle = max(20.0, min(85.0, angle))

        thermal_state = _step_thermal_state(thermal_state, arc_active, angle)
        new_center_10mm = thermal_state[10.0]["center"]

        volts = AL_VOLTS + random.gauss(0.0, 0.2) if arc_active else 0.0
        amps = AL_AMPS + random.gauss(0.0, 3.0) if arc_active else 0.0

        is_thermal_frame = (i % 20 == 0)
        snapshots = _aluminum_state_to_snapshots(thermal_state) if is_thermal_frame else []

        heat_dissipation: Optional[float] = None
        if is_thermal_frame:
            if last_thermal_center_10mm is not None:
                heat_dissipation = max(
                    0.0,
                    (last_thermal_center_10mm - new_center_10mm) / thermal_interval_sec,
                )
            last_thermal_center_10mm = new_center_10mm

        frames.append(
            Frame(
                timestamp_ms=i * 10,
                volts=volts,
                amps=amps,
                angle_degrees=angle,
                thermal_snapshots=snapshots,
                heat_dissipation_rate_celsius_per_sec=heat_dissipation,
            )
        )

    return frames
```

---

## Step 5: Add _generate_continuous_novice_frames

### `backend/data/mock_sessions.py`

```python
def _generate_continuous_novice_frames(
    session_index: int,
    num_frames: int = 1500,
) -> List[Frame]:
    """
    Aluminum continuous novice:
    - Continuous arc with brief accidental breaks: off for 12 frames every 380 frames
    - Angle drifts upward with periodic overcorrection and a one-time wrong correction
    - drift += 0.08 (tuned to pass verification: novice_max > 20 and novice_max > expert_95 * 2)
    """
    random.seed(session_index * 99)

    frames: List[Frame] = []
    thermal_state = _init_thermal_state(AL_AMBIENT_TEMP)
    drift = 0.0
    wrong_correction_fired = False

    last_thermal_center_10mm: Optional[float] = None
    thermal_interval_sec = 0.2  # 20 frames × 10ms

    for i in range(num_frames):
        arc_active = not ((i % 380) < 12)

        center_10mm = thermal_state[10.0]["center"]

        # (1) Wrong correction (fires once, before drift reset)
        if (not wrong_correction_fired) and center_10mm > 200.0:
            drift += 15.0
            wrong_correction_fired = True

        # (2) Periodic overcorrection snap
        if i % 300 == 0 and i > 0:
            drift -= 22.0

        # (3) Continuous drift
        drift += 0.08

        # (4) Clamp
        angle = 45.0 + drift + random.gauss(0.0, 2.5)
        angle = max(20.0, min(85.0, angle))

        thermal_state = _step_thermal_state(thermal_state, arc_active, angle)
        new_center_10mm = thermal_state[10.0]["center"]

        volts = AL_VOLTS + random.gauss(0.0, 0.3) if arc_active else 0.0
        amps = AL_AMPS + random.gauss(0.0, 5.0) if arc_active else 0.0

        is_thermal_frame = (i % 20 == 0)
        snapshots = _aluminum_state_to_snapshots(thermal_state) if is_thermal_frame else []

        heat_dissipation: Optional[float] = None
        if is_thermal_frame:
            if last_thermal_center_10mm is not None:
                heat_dissipation = max(
                    0.0,
                    (last_thermal_center_10mm - new_center_10mm) / thermal_interval_sec,
                )
            last_thermal_center_10mm = new_center_10mm

        frames.append(
            Frame(
                timestamp_ms=i * 10,
                volts=volts,
                amps=amps,
                angle_degrees=angle,
                thermal_snapshots=snapshots,
                heat_dissipation_rate_celsius_per_sec=heat_dissipation,
            )
        )

    return frames
```

---

## Step 6: Update generate_frames_for_arc Routing

### `backend/data/mock_sessions.py`

Add at top of `generate_frames_for_arc`, before existing branches:

```python
def generate_frames_for_arc(
    arc_type: str,
    session_index: int,
    duration_ms: int = 15_000,
) -> Tuple[List[Frame], bool]:
    # ...
    if arc_type == "stitch_expert":
        num_frames = duration_ms // 10
        return _generate_stitch_expert_frames(session_index, num_frames), True
    if arc_type == "continuous_novice":
        num_frames = duration_ms // 10
        return _generate_continuous_novice_frames(session_index, num_frames), True

    if arc_type == "fast_learner":
        # ... rest unchanged
```

---

## Step 7: Update generate_session_for_welder

### `backend/data/mock_sessions.py`

```python
def generate_session_for_welder(
    welder_id: str,
    arc_type: str,
    session_index: int,
    session_id: str,
    duration_ms: int = 15_000,
) -> Session:
    frames, disable = generate_frames_for_arc(arc_type, session_index, duration_ms)

    is_aluminum_arc = arc_type in ("stitch_expert", "continuous_novice")

    return Session(
        session_id=session_id,
        operator_id=welder_id,
        start_time=datetime.now(timezone.utc),
        weld_type="aluminum" if is_aluminum_arc else "mild_steel",
        process_type="aluminum" if is_aluminum_arc else "mig",
        thermal_sample_interval_ms=200 if is_aluminum_arc else THERMAL_SAMPLE_INTERVAL_MS,
        thermal_directions=THERMAL_DIRECTIONS,
        thermal_distance_interval_mm=THERMAL_DISTANCE_INTERVAL_MM,
        sensor_sample_rate_hz=SENSOR_SAMPLE_RATE_HZ,
        frames=frames,
        status=SessionStatus.COMPLETE,
        frame_count=len(frames),
        expected_frame_count=len(frames),
        last_successful_frame_index=len(frames) - 1,
        validation_errors=[],
        completed_at=datetime.now(timezone.utc),
        disable_sensor_continuity_checks=True if is_aluminum_arc else disable,
    )
```

---

## Step 8: Verification Script + Arc Input Scaling

### Arc input scaling in _step_thermal_state

```python
heat = ((AL_VOLTS * AL_AMPS) / 1000.0) * 20.0   # ×20 for realistic aluminum temps
```

### Novice drift tuning

```python
drift += 0.08   # was 0.008 — needed for novice_max > 20 and novice_max > expert_95 * 2
```

### Verification script

See **Verification Script (Primary Test for Expert + Novice)** at the top of this document.

---

## Quick Reference: Run Verification

```bash
cd backend && python3 -m scripts.verify_aluminum_mock
```

**Expected:** Prints JSON with expert/novice frame briefs and numeric deltas; ends with `ALL ASSERTIONS PASSED`.

---

## Steps 9–11: Seed and Verification (Brief)

**Step 9:** Wipe then seed — `POST /api/dev/wipe-mock-sessions`, then `POST /api/dev/seed-mock-sessions`. New welders (expert_aluminium_001, novice_aluminium_001) included via WELDER_ARCHETYPES.

**Step 10:** API verification — `GET /api/sessions/sess_expert_aluminium_001_001` (1500 frames, weld_type aluminum). Expert score target ≥85, novice 28–55. Set `heat_diss_consistency` to 80 via `PUT /api/thresholds/mig` if DB has 40.

**Step 11:** Browser — Open replay for expert vs novice; heatmaps and angle graphs should differ (blue/violet vs amber).

---

## Part B: Aluminum Threshold Implementation (from aluminum-threshold-implementation-plan.md)

**Goal:** Wire scoring to use dedicated aluminum thresholds. Expert score ≥85, novice 28–55.

### Critical Decisions

- **process_type vs weld_type:** Scoring uses `process_type`, not `weld_type`. Mock sessions must pass `process_type="aluminum"` when `is_aluminum_arc` (see Step 7 above).
- **Threshold values:** Stitch welding produces amps/volts/heat_diss variance by design; thresholds must bracket expert (pass) and fail novice on angle/thermal/amps.
- **volts_stability_warning = 25:** Stitch has volts 0 (arc off) and ~21 (arc on) → volts_range ≈ 21. 25 accommodates.
- **Do not restart server** between adding aluminum to KNOWN_PROCESS_TYPES and running migration seed.

### Phase 1 — Model + Constants

**Step TH-1: Raise thermal_symmetry cap in WeldTypeThresholds**

In `backend/models/thresholds.py`: change `thermal_symmetry_warning_celsius` and `thermal_symmetry_critical_celsius` from `le=200` → `le=500`.

**Step TH-2: Add aluminum to KNOWN_PROCESS_TYPES**

In `backend/services/threshold_service.py`:

```python
KNOWN_PROCESS_TYPES = frozenset({"mig", "tig", "stick", "flux_core", "aluminum"})
```

### Phase 2 — ALUMINUM_THRESHOLDS and Migrations

**Step TH-3: Add ALUMINUM_THRESHOLDS constants**

In `backend/services/threshold_service.py` (post-migration 011 values):

```python
ALUMINUM_THRESHOLDS = {
    "weld_type": "aluminum",
    "angle_target_degrees": 45.0,
    "angle_warning_margin": 20.0,
    "angle_critical_margin": 35.0,
    "thermal_symmetry_warning_celsius": 9.0,   # novice discriminator
    "thermal_symmetry_critical_celsius": 35.0,
    "amps_stability_warning": 75.0,   # stitch 0 vs ~145 variance
    "volts_stability_warning": 25.0,
    "heat_diss_consistency": 250.0,
}
```

**Step TH-4: Migrations**

- `010_add_aluminum_threshold.py` — INSERT aluminum row (initial values)
- `011_adjust_aluminum_thresholds.py` — UPDATE amps=75, thermal_symmetry_warning=9

Run `alembic upgrade head`.

### Phase 3 — Score Verification

```bash
curl -s localhost:8000/api/sessions/sess_expert_aluminium_001_001/score  # total ≥ 85
curl -s localhost:8000/api/sessions/sess_novice_aluminium_001_001/score  # 28 ≤ total ≤ 55
```

**Narrative check:** `POST .../sess_novice_aluminium_001_001/narrative` — narrative_text should not contain "Strong performance" (generic).

### Phase 4 — Frontend Spot Check

- Replay `sess_expert_aluminium_001_001` → weld type label "Aluminum"
- Compare expert vs novice → ScorePanel shows "ALUMINUM" spec

### Success Criteria (End-to-End)

| Feature           | Target                           | Verification                                              |
|-------------------|----------------------------------|-----------------------------------------------------------|
| Aluminum thresholds | GET /api/thresholds/aluminum      | weld_type=aluminum, heat_diss=250, amps=75, thermal=9     |
| Expert score      | ≥ 85                             | curl score endpoint                                       |
| Novice score      | 28–55                            | curl score endpoint                                       |
| Replay label      | "Aluminum"                       | Browser metadata                                          |
| Narrative         | Not generic                      | POST narrative, no "Strong performance"                   |

---

## Related Unit Tests

- `backend/tests/test_mock_welders.py` — `test_welder_archetypes_has_12`, `test_mock_sessions_fast_learner_session0_in_band`
- `backend/tests/test_scoring_thresholds.py` — heat_diss 80 in seeded thresholds; TIG/MIG threshold selection
- `backend/tests/test_thresholds_api.py` — heat_diss 80 in seeded thresholds; GET/PUT thresholds; aluminum in weld_type allowlist
