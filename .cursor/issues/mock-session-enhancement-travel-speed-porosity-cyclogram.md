# Mock Session Enhancement Plan — Travel Speed, Porosity, Cyclogram

## What the Research Gives Us as Ground Truth

- **GMAW travel speeds** are typically 150–250 mm/min for standard work. [Howardprecision]
- For **manual aluminum stitch welding** specifically, expert range is **280–420 mm/min**.
- Travel speeds that are **too slow** lead to too much heat and a wide bead.
- Travel speeds that are **too fast** create insufficient weld toe tie-in. [Material Welding] — this is exactly the novice failure pattern to model.

**Parameters need to be reduced toward the end of the weld** to compensate for increased temperature — common advice is to weld aluminum hot and fast due to its high thermal conductivity. [ScienceDirect]

This gives us the expert's **adaptive speed behavior**: speed up when hot, slow down on cold starts.

These are your real-world anchors. Every constant in this plan is traceable to research.

---

## Files This Plan Touches

| File | What changes |
|------|--------------|
| `backend/models/frame.py` | Add `travel_speed_mm_per_min` optional field |
| `backend/data/mock_sessions.py` | Add constants, modify `_step_thermal_state`, modify both generators |
| `backend/features/extractor.py` | Add `travel_speed_stddev`, `cyclogram_area`, `porosity_event_count` |
| `backend/scoring/rule_based.py` | Add 3 new rules for aluminum (travel_speed, cyclogram, porosity) |
| `backend/models/thresholds.py` | Add 3 optional threshold fields |
| `backend/database/models.py` | Add 3 nullable columns to WeldThresholdModel |
| `backend/services/threshold_service.py` | Map new columns; update ALUMINUM_THRESHOLDS |
| `backend/scripts/verify_aluminum_mock.py` | Add new assertions |
| `backend/alembic/versions/` | New migration for weld_thresholds columns |

**Do not touch:** `warp_features.py`, `session.py`, `thermal.py`, existing scoring rules for non-aluminum arc types.

---

## Exploration Findings (from codebase analysis)

### Call Graph for _step_thermal_state

`_step_thermal_state` is only called by:
- `_generate_stitch_expert_frames` (mock_sessions.py)
- `_generate_continuous_novice_frames` (mock_sessions.py)
- `verify_aluminum_mock.py` (direct physics sanity check)

No other arc types use it; they use `generate_frames()` with a different thermal path. Adding a default parameter is safe.

### Data Flow

```
mock_sessions._generate_*_frames()
  → List[Frame] (travel_speed_mm_per_min on every frame — ML needs full resolution)
    → generate_session_for_welder() → Session
      → seed_demo_data / dev routes → DB (frame_data = model_dump() JSON)
        → sessions API → frontend

Scoring: Session → extract_features() → Dict → score_session() → SessionScore
  (aluminum: 8 rules; others: 5 rules)
```

### Frame Storage (no migration needed)

- `FrameModel.frame_data` stores full `model_dump()` as JSON. New field auto-included.
- Old DB rows without `travel_speed_mm_per_min` load as `None` (optional field).

### Critical: Step 3 Heat Formula

Preserve 20× scaling at nominal speed:

```python
speed_scale = AL_TRAVEL_SPEED_NOMINAL / travel_speed_mm_per_min
heat = ((AL_VOLTS * AL_AMPS) / 1000.0) * 20.0 * speed_scale
```

### Step 7: Add numpy Import

`verify_aluminum_mock.py`: Add `import numpy as np` at top.

### Step 6: corrcoef Edge Case

Guard against NaN from flat data: `r = 0.0 if (r_val != r_val or abs(r_val) > 1.0) else float(r_val)`.

### Implementation Order

| Order | File | Rationale |
|-------|------|-----------|
| 1 | `frame.py` | Add-only model change |
| 2 | `mock_sessions.py` (Steps 2+3) | Constants and physics |
| 3 | `mock_sessions.py` (Steps 4+5) | Both generators |
| 4 | `extractor.py` | New features |
| 5 | `verify_aluminum_mock.py` | Assertions |
| 6 | Migration, thresholds, rule_based, threshold_service | Wire features into scoring |

---

## Pre-Flight — Read Before Cursor Touches Anything

> "Read backend/data/mock_sessions.py in full. List: (1) every constant currently defined at module level, (2) the exact current signature of _step_thermal_state, (3) the exact line where _generate_stitch_expert_frames builds the Frame object. Do not change anything. Show output then wait."

---

## CURSOR SESSION 1: Frame Model + Constants

### Step 1 — Add travel_speed_mm_per_min to Frame

**File:** `backend/models/frame.py`

Add one optional field after `heat_dissipation_rate_celsius_per_sec`:

```python
travel_speed_mm_per_min: Optional[float] = Field(
    None,
    description=(
        "Torch travel speed along weld seam in mm/min. "
        "Expert aluminum stitch: 280–420 mm/min. "
        "Novice: erratic 150–550 mm/min."
    ),
)
```

**Verification:**

```bash
cd backend && python3 -c "
from models.frame import Frame
f = Frame(timestamp_ms=0, travel_speed_mm_per_min=350.0)
assert f.travel_speed_mm_per_min == 350.0
f2 = Frame(timestamp_ms=0)
assert f2.travel_speed_mm_per_min is None
print('OK')
"
cd backend && python3 -m pytest tests/ -x --tb=short
```

---

### Step 2 — Add Travel Speed and Porosity Constants

**File:** `backend/data/mock_sessions.py`

After `AL_ARC_INPUT_DISTANCE_MM` add:

```python
# Travel speed constants — research grounded
AL_TRAVEL_SPEED_NOMINAL    = 350.0   # mm/min — expert center target
AL_TRAVEL_SPEED_MIN        = 150.0   # mm/min — absolute floor (novice panic decel)
AL_TRAVEL_SPEED_MAX        = 550.0   # mm/min — absolute ceiling (novice panic accel)
AL_TRAVEL_SPEED_EXPERT_MIN = 280.0   # mm/min — expert lower bound
AL_TRAVEL_SPEED_EXPERT_MAX = 420.0   # mm/min — expert upper bound
AL_TRAVEL_SPEED_NOISE_EXPERT = 8.0   # σ mm/min — expert tremor
AL_TRAVEL_SPEED_NOISE_NOVICE = 25.0  # σ mm/min — novice baseline noise

# Porosity constants — research grounded
# Target: novice 3–6 events across ~1400 arc-on frames → prob ≈ 4.5/1400 = 0.0032
AL_POROSITY_PROB_NOVICE      = 0.0032  # per arc-on frame → ~3–6 events per session
AL_POROSITY_PROB_EXPERT      = 0.00032 # 10× less likely for expert → 0–1 events
AL_POROSITY_VOLTS_SIGMA      = 1.8     # voltage σ during porosity event
AL_POROSITY_NORMAL_SIGMA     = 0.3     # voltage σ during normal arc
AL_POROSITY_MIN_FRAMES       = 20      # minimum event duration
AL_POROSITY_MAX_FRAMES       = 40      # maximum event duration
```

**Verification:**

```bash
cd backend && python3 -c "
from data.mock_sessions import (
    AL_TRAVEL_SPEED_NOMINAL, AL_POROSITY_PROB_NOVICE,
    AL_POROSITY_VOLTS_SIGMA, AL_TRAVEL_SPEED_EXPERT_MAX
)
assert AL_TRAVEL_SPEED_NOMINAL == 350.0
assert AL_POROSITY_PROB_NOVICE == 0.0032
assert AL_POROSITY_VOLTS_SIGMA == 1.8
assert AL_TRAVEL_SPEED_EXPERT_MAX == 420.0
print('OK')
"
```

---

### Step 3 — Update _step_thermal_state Signature to Accept Travel Speed

**File:** `backend/data/mock_sessions.py`

Add parameter with default; scale heat by travel speed:

```python
def _step_thermal_state(
    state: ThermalState,
    arc_active: bool,
    angle_degrees: float,
    travel_speed_mm_per_min: float = AL_TRAVEL_SPEED_NOMINAL,
) -> ThermalState:
    new = {dist: dict(dirs) for dist, dirs in state.items()}

    if arc_active:
        speed_scale = AL_TRAVEL_SPEED_NOMINAL / travel_speed_mm_per_min
        heat = ((AL_VOLTS * AL_AMPS) / 1000.0) * 20.0 * speed_scale

        raw_bias = (angle_degrees - 45) / 45
        bias = math.copysign(min(0.4, abs(raw_bias)), raw_bias)
        new[10.0]["center"] += heat * 0.5
        new[10.0]["north"]  += heat * (0.25 + bias * 0.2)
        new[10.0]["south"]  += heat * (0.25 - bias * 0.2)

    # ... rest of function unchanged (axial conduction, lateral conduction, dissipation)
```

**Verification:**

```bash
cd backend && python3 -m pytest tests/ -x --tb=short

cd backend && python3 -c "
from data.mock_sessions import _step_thermal_state, _init_thermal_state, AL_AMBIENT_TEMP
s = _init_thermal_state(AL_AMBIENT_TEMP)
s_fast = _step_thermal_state(s, True, 45.0, travel_speed_mm_per_min=500.0)
s_slow = _step_thermal_state(s, True, 45.0, travel_speed_mm_per_min=200.0)
assert s_slow[10.0]['center'] > s_fast[10.0]['center'], 'FAIL: slow travel should deposit more heat'
print(f'Slow: {s_slow[10.0][\"center\"]:.2f} Fast: {s_fast[10.0][\"center\"]:.2f} OK')
"
```

---

## CURSOR SESSION 2: Update Generators

### Step 4 — Update _generate_stitch_expert_frames

**Initialization** (after `angle = 45.0`):

```python
travel_speed = AL_TRAVEL_SPEED_NOMINAL
porosity_frames_remaining = 0
```

**Travel speed update** (after arc_active and angle logic, before `_step_thermal_state`):

```python
temp_at_arc = thermal_state[10.0]["center"]
if temp_at_arc > 180:
    speed_target = 390.0
elif temp_at_arc < 80:
    speed_target = 300.0
else:
    speed_target = AL_TRAVEL_SPEED_NOMINAL

travel_speed += (speed_target - travel_speed) * 0.02
travel_speed += rng.gauss(0, AL_TRAVEL_SPEED_NOISE_EXPERT)
travel_speed = max(AL_TRAVEL_SPEED_EXPERT_MIN, min(AL_TRAVEL_SPEED_EXPERT_MAX, travel_speed))
```

**Call:** `thermal_state = _step_thermal_state(thermal_state, arc_active, angle, travel_speed)`

**Voltage/amps** (porosity-aware):

```python
if arc_active and rng.random() < AL_POROSITY_PROB_EXPERT:
    porosity_frames_remaining = rng.randint(
        AL_POROSITY_MIN_FRAMES, AL_POROSITY_MAX_FRAMES
    )

volts_sigma = AL_POROSITY_VOLTS_SIGMA if porosity_frames_remaining > 0 else AL_POROSITY_NORMAL_SIGMA
if porosity_frames_remaining > 0:
    porosity_frames_remaining -= 1

volts = AL_VOLTS + rng.gauss(0, volts_sigma) if arc_active else 0.0
amps  = AL_AMPS  + rng.gauss(0, 4.0) if arc_active else 0.0
```

**Frame construction** — record travel_speed on every frame (ML needs full resolution):

```python
frames.append(
    Frame(
        timestamp_ms=i * 10,
        volts=volts,
        amps=amps,
        angle_degrees=angle,
        thermal_snapshots=snapshots,
        heat_dissipation_rate_celsius_per_sec=heat_dissipation,
        travel_speed_mm_per_min=travel_speed,
    )
)
```

---

### Step 5 — Update _generate_continuous_novice_frames

**Initialization:** `travel_speed = AL_TRAVEL_SPEED_NOMINAL` and `porosity_frames_remaining = 0`

**Travel speed logic** (before `_step_thermal_state`):

```python
temp_at_arc = thermal_state[10.0]["center"]
if temp_at_arc > 190 and rng.random() < 0.08:
    travel_speed -= rng.uniform(30, 70)
elif rng.random() < 0.004:
    travel_speed += rng.uniform(50, 120)

travel_speed += rng.gauss(0, AL_TRAVEL_SPEED_NOISE_NOVICE)
travel_speed = max(AL_TRAVEL_SPEED_MIN, min(AL_TRAVEL_SPEED_MAX, travel_speed))
```

**Porosity voltage model** and amps (CTWD drift, wire feed slip) — use `AL_POROSITY_PROB_NOVICE = 0.0032`.

**Frame construction** — record travel_speed on every frame:

```python
frames.append(
    Frame(
        timestamp_ms=i * 10,
        volts=volts,
        amps=amps,
        angle_degrees=angle,
        thermal_snapshots=snapshots,
        heat_dissipation_rate_celsius_per_sec=heat_dissipation,
        travel_speed_mm_per_min=travel_speed,
    )
)
```

**Verification after Steps 4 and 5:**

```bash
cd backend && python3 -m pytest tests/ -x --tb=short

cd backend && python3 -c "
import numpy as np
from data.mock_sessions import _generate_stitch_expert_frames, _generate_continuous_novice_frames

expert = _generate_stitch_expert_frames(0)
novice = _generate_continuous_novice_frames(0)

expert_speeds = [f.travel_speed_mm_per_min for f in expert if f.travel_speed_mm_per_min is not None]
novice_speeds = [f.travel_speed_mm_per_min for f in novice if f.travel_speed_mm_per_min is not None]

assert len(expert_speeds) > 0, 'FAIL: no expert travel speed frames'
assert len(expert_speeds) == 1500, 'FAIL: expert must record travel_speed every frame'
assert np.percentile(expert_speeds, 2) >= 270, f'FAIL: expert 2nd pct {np.percentile(expert_speeds, 2):.0f}'
assert np.percentile(expert_speeds, 98) <= 430, f'FAIL: expert 98th pct {np.percentile(expert_speeds, 98):.0f}'

assert any(f.travel_speed_mm_per_min < 280 or f.travel_speed_mm_per_min > 420 for f in novice if f.travel_speed_mm_per_min), \
    'FAIL: novice speed never left expert range'

import statistics
expert_amps = [f.amps for f in expert if f.amps]
novice_amps = [f.amps for f in novice if f.amps]
assert statistics.stdev(novice_amps) > statistics.stdev(expert_amps) * 2.5, 'FAIL: amps gap too small'

expert_volts = [f.volts for f in expert if f.volts]
novice_volts = [f.volts for f in novice if f.volts]
assert statistics.stdev(novice_volts) > statistics.stdev(expert_volts) * 2.0, 'FAIL: voltage gap too small'

print('OK')
"
```

---

## CURSOR SESSION 3: Cyclogram Feature Extractor

### Step 6 — Add Three New Features to extractor.py

**Add** `import math` and `import numpy as np` if not present.

**Helper** `_compute_cyclogram_area(volts, amps)` — use NaN guard: `r = 0.0 if (r_val != r_val or abs(r_val) > 1.0) else float(r_val)`.

**In extract_features** add:

- `travel_speed_stddev` from frames with `travel_speed_mm_per_min is not None`
- `cyclogram_area` from arc-on frames (volts > 1.0, amps present)
- `porosity_event_count` — 30-frame windows over arc_on_frames, count windows where `np.std(window_volts) > 0.8`

**Return dict** gains the 3 new keys.

**Verification:**

```bash
cd backend && python3 -m pytest tests/ -x --tb=short

cd backend && python3 -c "
from data.mock_sessions import generate_session_for_welder
from features.extractor import extract_features

expert_s = generate_session_for_welder('expert_aluminium_001', 'stitch_expert', 0, 'test_expert')
novice_s = generate_session_for_welder('novice_aluminium_001', 'continuous_novice', 0, 'test_novice')
ef = extract_features(expert_s)
nf = extract_features(novice_s)

assert 'cyclogram_area' in ef and 'travel_speed_stddev' in ef and 'porosity_event_count' in ef

assert nf['cyclogram_area'] > ef['cyclogram_area'], f'FAIL: novice cyclogram should exceed expert'
assert nf['travel_speed_stddev'] > ef['travel_speed_stddev'], f'FAIL: novice speed variance should exceed expert'

assert nf['porosity_event_count'] >= 3, f\"FAIL: novice should have >=3 porosity events, got {nf['porosity_event_count']}\"
assert ef['porosity_event_count'] <= 1, f\"FAIL: expert should have <=1 porosity event, got {ef['porosity_event_count']}\"

print('OK')
"
```

---

## CURSOR SESSION 4: Verify and Reseed

### Step 7 — Update verify_aluminum_mock.py

Add `import numpy as np` at top.

**Travel speed assertions** (use percentile bounds — Gaussian noise can exceed 280–420):

```python
expert_speeds = [f.travel_speed_mm_per_min for f in expert_frames if f.travel_speed_mm_per_min is not None]
novice_speeds = [f.travel_speed_mm_per_min for f in novice_frames if f.travel_speed_mm_per_min is not None]

assert len(expert_speeds) > 0, "FAIL: no expert travel speed data"
assert np.percentile(expert_speeds, 2) >= 270, \
    f"FAIL: expert speed 2nd percentile too low: {np.percentile(expert_speeds, 2):.0f}"
assert np.percentile(expert_speeds, 98) <= 430, \
    f"FAIL: expert speed 98th percentile too high: {np.percentile(expert_speeds, 98):.0f}"
assert np.std(novice_speeds) > np.std(expert_speeds) * 2.0, "FAIL: novice speed variance not high enough"
```

**Voltage variance** and **cyclogram area** assertions — same as before.

**Porosity assertions** (call extract_features and assert):

```python
from features.extractor import extract_features
ef = extract_features(expert_session)
nf = extract_features(novice_session)
assert nf['porosity_event_count'] >= 3, f"FAIL: novice porosity events {nf['porosity_event_count']}"
assert ef['porosity_event_count'] <= 1, f"FAIL: expert porosity events {ef['porosity_event_count']}"
```

---

### Step 8 — Reseed and Verify Scores (after Session 5)

```bash
cd backend && python3 -m scripts.verify_aluminum_mock
curl -X POST localhost:8000/api/dev/wipe-mock-sessions
curl -X POST localhost:8000/api/dev/seed-mock-sessions

curl -s localhost:8000/api/sessions/sess_expert_aluminium_001_001/score | \
  python3 -c "import sys,json; d=json.load(sys.stdin); s=d['total']; assert s >= 80, f'FAIL: {s}'; print(f'Expert: {s}')"

curl -s localhost:8000/api/sessions/sess_novice_aluminium_001_001/score | \
  python3 -c "import sys,json; d=json.load(sys.stdin); s=d['total']; assert 20 <= s <= 60, f'FAIL: {s}'; print(f'Novice: {s}')"
```

*(Score bounds adjusted for 8 rules; exact band may need tuning after implementation.)*

---

## CURSOR SESSION 5: Wire New Features Into Scoring

**Decision:** New features must feed scoring. Aluminum sessions use 8 rules; others use 5.

### Step 9 — Add Threshold Fields and Migration

**File:** `backend/models/thresholds.py`

Add 3 optional fields to `WeldTypeThresholds`:

```python
travel_speed_consistency: Optional[float] = Field(None, ge=0)   # pass if travel_speed_stddev <= this
cyclogram_area_max: Optional[float] = Field(None, ge=0)         # pass if cyclogram_area <= this
porosity_event_max: Optional[float] = Field(None, ge=0)         # pass if porosity_event_count <= this
```

**File:** `backend/database/models.py` — add 3 nullable columns to `WeldThresholdModel`:

```python
travel_speed_consistency = Column(Float, nullable=True)
cyclogram_area_max = Column(Float, nullable=True)
porosity_event_max = Column(Float, nullable=True)
```

**New migration** `backend/alembic/versions/012_add_aluminum_feature_thresholds.py`:
- Add 3 columns to `weld_thresholds`
- Update aluminum row: `travel_speed_consistency=15`, `cyclogram_area_max=15`, `porosity_event_max=2`

### Step 10 — Update threshold_service

**File:** `backend/services/threshold_service.py`

- In `_load_all`, map the 3 new columns when building `WeldTypeThresholds`
- Add to `ALUMINUM_THRESHOLDS`: `"travel_speed_consistency": 15, "cyclogram_area_max": 15, "porosity_event_max": 2`

### Step 11 — Add 3 Rules to rule_based.py

**File:** `backend/scoring/rule_based.py`

Add `_check_travel_speed_consistency`, `_check_cyclogram_area`, `_check_porosity_events`. Each uses `features.get(...)` and `t.<field>` if `t` and the field is not None. Pass when `actual <= threshold`.

In `score_session`:
- Build `rules` list from existing 5 checks
- If thresholds has any of the 3 new fields non-None, append the 3 new rule results
- `total_rules = len(rules)`
- `total = int(round(100 * passed_count / total_rules))` (so 8 rules → each pass = 12.5, 5 rules → each pass = 20)

**Verification:**

```bash
cd backend && alembic upgrade head
cd backend && python3 -m pytest tests/ -x --tb=short

cd backend && python3 -c "
from data.mock_sessions import generate_session_for_welder
from features.extractor import extract_features
from scoring.rule_based import score_session

expert_s = generate_session_for_welder('expert_aluminium_001', 'stitch_expert', 0, 'test_expert')
ef = extract_features(expert_s)
# Must have 8 rules for aluminum when thresholds include new fields
from models.thresholds import WeldTypeThresholds
t = WeldTypeThresholds(weld_type='aluminum', angle_target_degrees=45, angle_warning_margin=20,
    angle_critical_margin=35, thermal_symmetry_warning_celsius=9, thermal_symmetry_critical_celsius=35,
    amps_stability_warning=75, volts_stability_warning=25, heat_diss_consistency=250,
    travel_speed_consistency=15, cyclogram_area_max=15, porosity_event_max=2)
score = score_session(expert_s, ef, t)
assert len(score.rules) == 8, f'Expected 8 rules for aluminum, got {len(score.rules)}'
print('OK')
"
```

---

## Success Criteria

| Feature | Expert value | Novice value | Research basis |
|---------|--------------|--------------|----------------|
| Travel speed σ | < 15 mm/min | > 40 mm/min | AWS: consistent pace required |
| Amps σ | ~4A | ~12A+ | ANOVA: current = 63% of quality variance |
| Voltage σ (arc-on) | ~0.3V | ~0.7V+ with event spikes to 1.8V | Welding Journal: porosity in σ not mean |
| Cyclogram area | Small, tight | Large, scattered | Valensi research: skill discriminator |
| Porosity events | 0–1 | 3–6 | Physical: novice CTWD drift and angle instability |

| Implementation | Requirement |
|----------------|--------------|
| Travel speed on Frame | Every frame (not just thermal) — ML needs full resolution |
| Porosity prob novice | 0.0032 (target ~4.5 events over ~1400 arc-on frames) |
| Porosity prob expert | 0.00032 (10× less) |
| Expert speed assertion | Percentile bounds (2nd ≥ 270, 98th ≤ 430) |
| Porosity assertions | Novice ≥ 3, expert ≤ 1 |
| New features | Wired into scoring for aluminum (8 rules) |

---

## Risk Table

| Risk | Detection | Fix |
|------|-----------|-----|
| `_step_thermal_state` default breaks existing arc types | pytest after Step 3 | Default value; no change for callers |
| Novice speeds never leave expert range | Step 5 verify | Increase panic probability |
| Cyclogram area identical | Step 6 verify | Widen amps variance |
| Score drops for expert | curl score check | Adjust aluminum thresholds |
| Porosity events 0 for both | Step 6 verify | Raise AL_POROSITY_PROB_NOVICE |
