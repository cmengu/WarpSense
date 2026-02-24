# Aluminum 6061 GMAW Mock Session — Implementation Plan

**Target:** 3–6mm medium plate · Real-time alert + post-session scoring · Clean slate  
**Overall Progress:** `0%`  
**Version:** CTO + Expert Welder + agent-trap critique — all fixes applied

---

## How to Read This Document

Every section follows this structure:
1. **Problem** — what is wrong with the current state and why it matters
2. **Method** — the exact implementation to use instead
3. **Verification** — the exact command to confirm it worked

Do not skip verification steps. Do not proceed if a verification fails.

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → STOP. Report: (a) command run, (b) full error verbatim, (c) the fix attempted, (d) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

**Verbatim Cursor prompt:**

> "Read `backend/data/mock_sessions.py` in full. List: (1) every constant currently defined at module level in order, (2) the exact current signature of `_step_thermal_state` including all parameters, (3) the exact current heat computation line inside `_step_thermal_state`, (4) the exact line where `_generate_stitch_expert_frames` builds the Frame object, (5) every file that imports from `mock_sessions.py`, (6) the line number of `def _generate_stitch_expert_frames` and the line number of the next `def` after it, and the same for `def _generate_continuous_novice_frames`. Do not change anything. Show output and wait."

**Required checks:**

```bash
cd backend && python3 -m pytest tests/ -x --tb=short
```
All tests must pass. Document current test count.

```bash
cd backend && python3 -c "from data.mock_sessions import generate_expert_session; print('OK')"
```
Must exit 0. Step 13 (MIG regression) uses `generate_expert_session(session_id='test_mig_regression')`.

```bash
cd backend && python3 -c "
from data.mock_sessions import generate_frames_for_arc, _generate_stitch_expert_frames, _generate_continuous_novice_frames
f, _ = generate_frames_for_arc('continuous_novice', 0, 15000)
assert len(f) == 1500
ef = _generate_stitch_expert_frames(0, 1500)
nf = _generate_continuous_novice_frames(0, 1500)
assert len(ef) == 1500 and len(nf) == 1500
print('Both generators accept (session_index, num_frames): OK')
"
```
Must exit 0. Confirms both `_generate_stitch_expert_frames` and `_generate_continuous_novice_frames` accept two arguments; Step 14 uses `(0, 1500)`.

---

## Constants Reference (Use These Everywhere)

Ground truth for 3–6mm 6061-T6 GMAW (AWS D1.2, Lincoln Electric, ESAB aluminum guide):

```python
# Electrical — from PubMed Central / ScienceDirect research on 6061-T6
AL_AMPS                      = 155.0   # A — center of 130–180A range for 3–6mm
AL_VOLTS                     = 22.0    # V — center of 21–24V range for spray transfer
AL_AMPS_NOISE_EXPERT         =   4.0   # σ A — expert tremor
AL_AMPS_NOISE_NOVICE         =  10.0   # σ A — novice instability (2.5× expert)
AL_VOLTS_NOISE_NORMAL        =   0.3   # σ V — stable arc
AL_VOLTS_NOISE_POROSITY      =   1.8   # σ V — elevated during porosity event

# Travel speed — AWS D1.2 table for 3–6mm aluminum GMAW spray transfer
AL_TRAVEL_SPEED_NOMINAL      = 470.0   # mm/min — expert center target
AL_TRAVEL_SPEED_EXPERT_MIN   = 380.0   # mm/min — expert lower bound
AL_TRAVEL_SPEED_EXPERT_MAX   = 560.0   # mm/min — expert upper bound
AL_TRAVEL_SPEED_NOISE_EXPERT =   8.0   # σ mm/min — expert micro-variation
AL_TRAVEL_SPEED_NOISE_NOVICE =  20.0   # σ mm/min — novice baseline noise
AL_TRAVEL_SPEED_FLOOR        = 200.0   # mm/min — absolute minimum (novice dwell)
AL_TRAVEL_SPEED_CEILING      = 700.0   # mm/min — absolute maximum

# Porosity — Welding Journal: porosity shows as elevated voltage σ, not elevated mean
# Probability math: 0.0030 × 1400 arc-on frames ≈ 4.2 expected events (target 3–6)
AL_POROSITY_PROB_NOVICE      = 0.0030  # per arc-on frame, cause-gated (see Step 4)
AL_POROSITY_PROB_EXPERT      = 0.00030 # 10× less than novice
AL_POROSITY_MIN_FRAMES       =    20   # minimum event duration frames
AL_POROSITY_MAX_FRAMES       =    40   # maximum event duration frames

# Thermal — aluminum specific heat 0.896 J/g·°C, density 2.70 g/cm³
AL_AMBIENT_TEMP              =  25.0   # °C
AL_MELT_POINT                = 660.0   # °C — 6061 solidus ~582°C, liquidus ~652°C
```

**Why these values differ from prior plans:**
- Original `AL_TRAVEL_SPEED_MAX = 550` is within normal expert range. Ceiling must exceed expert range to capture novice dwell. Corrected to 700.
- Original `AL_AMPS = 145` is below research-grounded optimum for 3–6mm. Corrected to 155.
- Original `AL_VOLTS = 21` is at lower edge of spray transfer. Corrected to 22.

**Electrical variance asymmetry:** Research indicates current has ~6× more impact than voltage on weld quality. This plan uses equal rule weighting (amps_stability and volts_stability each count as 1 of 8 rules) for MVP simplicity. For production, consider weighting amps_stability as 2 points and volts_stability as 1.

---

## Step 1 — Frame Model

### Problem
`travel_speed_mm_per_min` and `travel_angle_degrees` do not exist. Work angle is modeled; travel angle (push/drag tilt) is not — Document 1 notes novice drifts from 10–15° push toward perpendicular.

### Method

In `backend/models/frame.py`, add two optional fields immediately after `heat_dissipation_rate_celsius_per_sec`:

```python
travel_speed_mm_per_min: Optional[float] = Field(
    None,
    description=(
        "Torch travel speed along weld seam in mm/min. "
        "Expert 3-6mm aluminum GMAW: 380–560 mm/min (AWS D1.2). "
        "Novice: erratic 200–700 mm/min with dwell events."
    ),
)
travel_angle_degrees: Optional[float] = Field(
    None,
    description=(
        "Travel angle (push/drag tilt, forward-back). "
        "90° = perpendicular. Expert ~12° push. Novice drifts toward 90° under load."
    ),
)
```

Add ONLY these fields. Do not modify any other field.

### Verification

```bash
cd backend && python3 -c "
from models.frame import Frame
f = Frame(timestamp_ms=0, travel_speed_mm_per_min=470.0, travel_angle_degrees=12.0)
assert f.travel_speed_mm_per_min == 470.0
assert f.travel_angle_degrees == 12.0
f2 = Frame(timestamp_ms=0)
assert f2.travel_speed_mm_per_min is None
assert f2.travel_angle_degrees is None
print('Step 1 OK')
"
cd backend && python3 -m pytest tests/ -x --tb=short
```

Both must exit 0.

---

## Step 2 — Constants

### Problem
Current constants in `mock_sessions.py` have incorrect values for 3–6mm plate (see Constants Reference above).

### Method

In `backend/data/mock_sessions.py`, for each constant in the Constants Reference section: (1) Search for the constant by name (e.g. `AL_AMPS`, `AL_VOLTS`). (2) If it exists, replace the entire line with the exact line from the Constants Reference. (3) If it does not exist, insert it immediately after `AL_ARC_INPUT_DISTANCE_MM`. (4) Show the diff for each constant before applying. Do not guess which constants exist — find each by name first.

### Verification

```bash
cd backend && python3 -c "
from data.mock_sessions import (
    AL_AMPS, AL_VOLTS,
    AL_AMPS_NOISE_EXPERT, AL_AMPS_NOISE_NOVICE,
    AL_VOLTS_NOISE_NORMAL, AL_VOLTS_NOISE_POROSITY,
    AL_TRAVEL_SPEED_NOMINAL, AL_TRAVEL_SPEED_EXPERT_MIN, AL_TRAVEL_SPEED_EXPERT_MAX,
    AL_TRAVEL_SPEED_NOISE_EXPERT, AL_TRAVEL_SPEED_NOISE_NOVICE,
    AL_TRAVEL_SPEED_FLOOR, AL_TRAVEL_SPEED_CEILING,
    AL_POROSITY_PROB_NOVICE, AL_POROSITY_PROB_EXPERT,
    AL_POROSITY_MIN_FRAMES, AL_POROSITY_MAX_FRAMES,
    AL_AMBIENT_TEMP, AL_MELT_POINT,
)
assert AL_AMPS == 155.0, f'FAIL: AL_AMPS={AL_AMPS}'
assert AL_VOLTS == 22.0, f'FAIL: AL_VOLTS={AL_VOLTS}'
assert AL_AMPS_NOISE_EXPERT == 4.0, f'FAIL: AL_AMPS_NOISE_EXPERT={AL_AMPS_NOISE_EXPERT}'
assert AL_AMPS_NOISE_NOVICE == 10.0, f'FAIL: AL_AMPS_NOISE_NOVICE={AL_AMPS_NOISE_NOVICE}'
assert AL_VOLTS_NOISE_NORMAL == 0.3, f'FAIL: AL_VOLTS_NOISE_NORMAL={AL_VOLTS_NOISE_NORMAL}'
assert AL_VOLTS_NOISE_POROSITY == 1.8, f'FAIL: AL_VOLTS_NOISE_POROSITY={AL_VOLTS_NOISE_POROSITY}'
assert AL_TRAVEL_SPEED_NOMINAL == 470.0, f'FAIL: AL_TRAVEL_SPEED_NOMINAL={AL_TRAVEL_SPEED_NOMINAL}'
assert AL_TRAVEL_SPEED_EXPERT_MIN == 380.0, f'FAIL: AL_TRAVEL_SPEED_EXPERT_MIN={AL_TRAVEL_SPEED_EXPERT_MIN}'
assert AL_TRAVEL_SPEED_EXPERT_MAX == 560.0, f'FAIL: AL_TRAVEL_SPEED_EXPERT_MAX={AL_TRAVEL_SPEED_EXPERT_MAX}'
assert AL_TRAVEL_SPEED_NOISE_EXPERT == 8.0, f'FAIL: AL_TRAVEL_SPEED_NOISE_EXPERT={AL_TRAVEL_SPEED_NOISE_EXPERT}'
assert AL_TRAVEL_SPEED_NOISE_NOVICE == 20.0, f'FAIL: AL_TRAVEL_SPEED_NOISE_NOVICE={AL_TRAVEL_SPEED_NOISE_NOVICE}'
assert AL_TRAVEL_SPEED_FLOOR == 200.0, f'FAIL: AL_TRAVEL_SPEED_FLOOR={AL_TRAVEL_SPEED_FLOOR}'
assert AL_TRAVEL_SPEED_CEILING == 700.0, f'FAIL: AL_TRAVEL_SPEED_CEILING={AL_TRAVEL_SPEED_CEILING}'
assert AL_POROSITY_PROB_NOVICE == 0.0030, f'FAIL: AL_POROSITY_PROB_NOVICE={AL_POROSITY_PROB_NOVICE}'
assert AL_POROSITY_PROB_EXPERT == 0.00030, f'FAIL: AL_POROSITY_PROB_EXPERT={AL_POROSITY_PROB_EXPERT}'
assert AL_POROSITY_MIN_FRAMES == 20, f'FAIL: AL_POROSITY_MIN_FRAMES={AL_POROSITY_MIN_FRAMES}'
assert AL_POROSITY_MAX_FRAMES == 40, f'FAIL: AL_POROSITY_MAX_FRAMES={AL_POROSITY_MAX_FRAMES}'
assert AL_AMBIENT_TEMP == 25.0, f'FAIL: AL_AMBIENT_TEMP={AL_AMBIENT_TEMP}'
assert AL_MELT_POINT == 660.0, f'FAIL: AL_MELT_POINT={AL_MELT_POINT}'
expected = AL_POROSITY_PROB_NOVICE * 1400
assert 3.0 < expected < 7.0, f'FAIL: expected events {expected:.1f} outside 3–7'
print(f'Expected novice events: {expected:.1f}')
print('Step 2 OK')
"
```

---

## Step 3 — Thermal Physics

### Pre-condition — before any edits

Run `grep -n 'arc_active' backend/data/mock_sessions.py`. Show every line with its number.

Run `grep -n 'last_thermal_center_10mm' backend/data/mock_sessions.py`. If it exists in `_generate_stitch_expert_frames`, that line is anchor M. If it does not exist, run `grep -n '_init_thermal_state' backend/data/mock_sessions.py` and identify the line containing `thermal_state = _init_thermal_state(AL_AMBIENT_TEMP)` inside `_generate_stitch_expert_frames` — that line is anchor M.

Report both: (a) line N for the transition block insertion (last line inside the loop that can set or override `arc_active`), and (b) line M for the pre-loop init anchor (last_thermal_center_10mm if it exists, else the _init_thermal_state line). STOP. Human must confirm both N and M before any edit. Do not assume the arc pattern (e.g. `(i % 250) < 150`).

### Problem
The original `_step_thermal_state` uses a single `* 20.0` magic scaling factor. This is acceptable. The fix is only to add `travel_speed_mm_per_min` as a parameter correctly.

The original plan does NOT model interpass heat buildup across stitches. For stitch weld on 3–6mm plate, each stitch raises base metal temperature. A novice with slow travel or short interpass pause risks burn-through on later stitches. This must be captured.

### Method — Part A: Update `_step_thermal_state` signature

Run `grep -n 'heat =' backend/data/mock_sessions.py`. Show all matches. Locate the line number within `_step_thermal_state`. If no match is inside `_step_thermal_state`, STOP and report regardless of how many matches exist. Replace only the `heat =` line inside `_step_thermal_state`'s `if arc_active:` block.

In `backend/data/mock_sessions.py`, find `_step_thermal_state`. Make exactly two changes:

1. Add `travel_speed_mm_per_min: float = AL_TRAVEL_SPEED_NOMINAL` as the fourth parameter, after `angle_degrees`.
2. Replace the existing `heat =` line inside the `if arc_active:` block with:

```python
        speed_scale = AL_TRAVEL_SPEED_NOMINAL / travel_speed_mm_per_min
        heat = ((AL_VOLTS * AL_AMPS) / 1000.0) * 20.0 * speed_scale
```

Do not change any other line in this function.

**Why speed_scale is inverted:** Slower travel = more heat per mm = higher temperature. At nominal speed, speed_scale = 1.0, so behavior is unchanged.

### Method — Part B: Add interpass preheat helper and integrate

In `backend/data/mock_sessions.py`, add a module-level helper immediately before `_generate_stitch_expert_frames`:

```python
def _compute_interpass_bias(stitch_index: int, end_temp_celsius: float) -> float:
    """
    Returns ambient temperature offset for the next stitch based on
    end temperature of previous stitch and fixed cooling time.
    AWS D1.2 specifies max interpass temp 150°C for aluminum.
    Models 30-second interpass pause; aluminum cooling τ ≈ 45s for 3–6mm plate.
    """
    if stitch_index == 0:
        return 0.0
    cooling_tau = 45.0           # seconds — empirical for 3–6mm plate
    interpass_pause = 30.0       # seconds — operator pause between stitches
    cooled_temp = AL_AMBIENT_TEMP + (end_temp_celsius - AL_AMBIENT_TEMP) * (
        math.exp(-interpass_pause / cooling_tau)
    )
    return max(0.0, cooled_temp - AL_AMBIENT_TEMP)
```

**Exact integration in `_generate_stitch_expert_frames`:** Insert the interpass transition block immediately after line N (confirmed by human in the pre-condition). Do not interpret "last line" yourself — use the line number provided.

**Before the loop** (after line M confirmed by human), add:
```python
    prev_arc_active = False
    last_arc_end_temp = AL_AMBIENT_TEMP
    stitch_count = 0
```

**Immediately after line N** (confirmed by human) and **before** the angle_target/north_10mm block, insert:
```python
        if prev_arc_active and not arc_active:
            last_arc_end_temp = thermal_state[10.0]["center"]
        if not prev_arc_active and arc_active:
            stitch_count += 1
            if stitch_count > 1:
                bias = _compute_interpass_bias(stitch_count - 1, last_arc_end_temp)
                thermal_state = _init_thermal_state(AL_AMBIENT_TEMP + bias)
```

**At the end of the loop body** (immediately before `frames.append`), add:
```python
        prev_arc_active = arc_active
```

### Verification — thermal sanity

```bash
cd backend && python3 -c "
from data.mock_sessions import (
    _step_thermal_state, _init_thermal_state, AL_AMBIENT_TEMP, AL_TRAVEL_SPEED_NOMINAL
)
import random
random.seed(0)
state = _init_thermal_state(AL_AMBIENT_TEMP)

for _ in range(50):
    state = _step_thermal_state(state, True, 45.0, AL_TRAVEL_SPEED_NOMINAL)

center = state[10.0]['center']
assert 80 < center < 380, (
    f'FAIL: center temp {center:.1f}C. '
    f'Expected 80–380C for 3–6mm at nominal speed. '
    f'If near 25C: 20x factor missing. If above 380C: heat too high.'
)
print(f'Thermal sanity: {center:.1f}C — OK')
"
```

```bash
cd backend && python3 -c "
from data.mock_sessions import _step_thermal_state, _init_thermal_state, AL_AMBIENT_TEMP
import random; random.seed(0)
s = _init_thermal_state(AL_AMBIENT_TEMP)
slow = _step_thermal_state(s, True, 45.0, 250.0)
fast = _step_thermal_state(s, True, 45.0, 600.0)
assert slow[10.0]['center'] > fast[10.0]['center'], (
    f'FAIL: slow travel should be hotter. slow={slow[10.0][\"center\"]:.2f} fast={fast[10.0][\"center\"]:.2f}'
)
print(f'Heat direction: slow={slow[10.0][\"center\"]:.2f} fast={fast[10.0][\"center\"]:.2f} — OK')
"
```

Both must pass. Report center temperature verbatim if either fails.

### Verification — interpass bias

```bash
cd backend && python3 -c "
from data.mock_sessions import _compute_interpass_bias
assert _compute_interpass_bias(0, 300.0) == 0.0
bias = _compute_interpass_bias(1, 300.0)
assert 0 < bias < 275, f'FAIL: bias={bias:.1f}'
print(f'Interpass bias: {bias:.1f}C — OK')
"
```

---

## Step 4 — Porosity Model (Critical Correction)

### Problem — Original plan is physically wrong

Flat random porosity probability on every arc-on frame is wrong: ML learns noise→defect, not cause→defect. Porosity causes for aluminum GMAW are known: (a) work angle deviation beyond ±10° from 90° — disrupts shielding gas, (b) travel speed above 560 mm/min — reduces shielding dwell time, (c) CTWD too long — reduces gas effectiveness at the puddle.

### Pre-condition — before any edits

Run `grep -n 'AL_POROSITY_PROB' backend/data/mock_sessions.py`. Show all matches. These are the replacement targets for the flat-probability porosity trigger. Confirm line numbers and enclosing function names before replacing. If no matches, STOP and report — the flat trigger may use a different pattern.

### Method

Replace the flat-probability porosity trigger in both generators with a cause-gated trigger.

Define this helper in `mock_sessions.py` immediately before the generator functions:

```python
def _porosity_probability(
    angle_degrees: float,
    travel_speed_mm_per_min: float,
    ctwd_mm: float,
    base_prob: float,
) -> float:
    """
    Returns per-frame porosity probability gated on physical causes.
    Causes: angle deviation, excessive travel speed, excessive CTWD.
    Physical basis: AWS D1.2 ±10° angle; Lincoln GMAW speed; ESAB CTWD 12–19mm.
    """
    prob = base_prob

    angle_deviation = abs(angle_degrees - 90.0)
    if angle_deviation > 20.0:
        prob *= 4.0
    elif angle_deviation > 10.0:
        prob *= 2.0

    if travel_speed_mm_per_min > 560.0:
        prob *= 3.0
    elif travel_speed_mm_per_min > 500.0:
        prob *= 1.5

    if ctwd_mm > 19.0:
        prob *= 2.5

    return min(prob, 0.10)
```

In both generators, replace `rng.random() < AL_POROSITY_PROB_NOVICE` (or EXPERT) with:

```python
porosity_prob = _porosity_probability(
    angle_degrees=angle,
    travel_speed_mm_per_min=travel_speed,
    ctwd_mm=ctwd_mm,
    base_prob=AL_POROSITY_PROB_NOVICE,  # or AL_POROSITY_PROB_EXPERT
)
if arc_active and rng.random() < porosity_prob:
    porosity_frames_remaining = rng.randint(AL_POROSITY_MIN_FRAMES, AL_POROSITY_MAX_FRAMES)
```

`ctwd_mm` must be tracked in both generators (Step 5 and 6).

### Verification

```bash
cd backend && python3 -c "
from data.mock_sessions import _porosity_probability
p = _porosity_probability(90.0, 470.0, 15.0, 0.003)
assert abs(p - 0.003) < 1e-9, f'FAIL: {p}'
p = _porosity_probability(75.0, 470.0, 15.0, 0.003)
assert abs(p - 0.006) < 1e-9, f'FAIL: {p}'
p = _porosity_probability(60.0, 600.0, 22.0, 0.003)
assert p == 0.10, f'FAIL: {p}'
print('Step 4 OK')
"
```

---

## Step 5 — Generator: Expert Frames

### Problem
Prior plan: novice accelerates when hot. Reality: novice slows down or freezes when the puddle looks wrong. CTWD modeled as sinusoidal — it should be monotonic positional drift. Expert speed range corrected by Constants Reference.

### Pre-conditions — before any edits

Run `grep -n 'angle' backend/data/mock_sessions.py`. Show the full grep output. The relevant lines are those between the `def _generate_stitch_expert_frames` line number and the next `def` line (established in pre-flight). Confirm the exact initialization line to insert after (e.g. `angle = 45.0`). If the generator uses a different variable or initialization, use that line. Do not assume.

Run `grep -nE 'volts =|amps =' backend/data/mock_sessions.py`. Show all matches. The replacement targets for Step 5 are the two lines inside the arc-on block of `_generate_stitch_expert_frames` (the `volts =` and `amps =` assignments that apply when arc is on). Confirm line numbers before replacing. Do not replace arc-off assignments.

Run `grep -n '_step_thermal_state' backend/data/mock_sessions.py`. Show all matches. Add the fourth argument `travel_speed` to every `_step_thermal_state` call inside `_generate_stitch_expert_frames`. Do not leave any call with only three arguments.

Run `grep -n 'Frame(' backend/data/mock_sessions.py`. Show all matches inside `_generate_stitch_expert_frames`. If more than one Frame() call exists inside that function, confirm which to update. Add `travel_speed_mm_per_min=travel_speed` and `travel_angle_degrees=travel_angle` on EVERY frame. Update ALL Frame() calls inside the target function. Remove any `if is_thermal_frame` condition that would skip adding these fields.

### Method — Expert Generator

Find `_generate_stitch_expert_frames`. Add immediately after the angle initialization line confirmed in the pre-condition:

```python
travel_speed = AL_TRAVEL_SPEED_NOMINAL
travel_angle = 12.0  # expert push angle, stable
porosity_frames_remaining = 0
ctwd_mm = 15.0  # nominal CTWD for aluminum GMAW (ESAB: 12–19mm)
```

Inside the loop, after angle clamping and before `_step_thermal_state`:

```python
        # Expert: adaptive speed — AWS "weld hot and fast" for aluminum
        temp_at_arc = thermal_state[10.0]['center']
        if temp_at_arc > 200:
            speed_target = 530.0
        elif temp_at_arc < 80:
            speed_target = 410.0
        else:
            speed_target = AL_TRAVEL_SPEED_NOMINAL
        travel_speed += (speed_target - travel_speed) * 0.02
        travel_speed += rng.gauss(0, AL_TRAVEL_SPEED_NOISE_EXPERT)
        travel_speed = max(AL_TRAVEL_SPEED_EXPERT_MIN, min(AL_TRAVEL_SPEED_EXPERT_MAX, travel_speed))

        ctwd_mm += rng.gauss(0, 0.05)
        ctwd_mm = max(12.0, min(17.0, ctwd_mm))

        travel_angle += rng.gauss(0, 0.5)
        travel_angle = max(8.0, min(18.0, travel_angle))
```

Add fourth argument `travel_speed` to every `_step_thermal_state` call inside `_generate_stitch_expert_frames` (line numbers confirmed in pre-condition). Do not leave any call with three arguments.

Expert porosity is suppressed primarily by the base rate `AL_POROSITY_PROB_EXPERT = 0.00030`, not by cause multipliers — expert parameters (CTWD 12–17mm, angle 8–18°) stay within safe bounds.

Replace the `volts =` and `amps =` lines inside the arc-on block of `_generate_stitch_expert_frames` (line numbers confirmed in pre-condition) with this exact block:
```python
        porosity_prob = _porosity_probability(
            angle_degrees=angle,
            travel_speed_mm_per_min=travel_speed,
            ctwd_mm=ctwd_mm,
            base_prob=AL_POROSITY_PROB_EXPERT,
        )
        if arc_active and rng.random() < porosity_prob:
            porosity_frames_remaining = rng.randint(AL_POROSITY_MIN_FRAMES, AL_POROSITY_MAX_FRAMES)
        volts_sigma = AL_VOLTS_NOISE_POROSITY if porosity_frames_remaining > 0 else AL_VOLTS_NOISE_NORMAL
        if porosity_frames_remaining > 0:
            porosity_frames_remaining -= 1
        volts = AL_VOLTS + rng.gauss(0, volts_sigma) if arc_active else 0.0
        amps = AL_AMPS + rng.gauss(0, AL_AMPS_NOISE_EXPERT) if arc_active else 0.0
```

Add `travel_speed_mm_per_min=travel_speed` and `travel_angle_degrees=travel_angle` to every Frame() call inside `_generate_stitch_expert_frames` (confirmed in pre-condition). Remove any `if is_thermal_frame` condition that would skip these fields.

### Verification — Step 5 only (run before Step 6)

```bash
cd backend && python3 -c "
import numpy as np
from data.mock_sessions import _generate_stitch_expert_frames, AL_TRAVEL_SPEED_EXPERT_MIN, AL_TRAVEL_SPEED_EXPERT_MAX

expert = _generate_stitch_expert_frames(0, 1500)
assert len(expert) == 1500
speeds = [f.travel_speed_mm_per_min for f in expert if f.travel_speed_mm_per_min is not None]
assert len(speeds) == 1500
p2, p98 = np.percentile(speeds, 2), np.percentile(speeds, 98)
assert p2 >= 360, f'FAIL: expert p2 {p2:.0f} < 360'
assert p98 <= 580, f'FAIL: expert p98 {p98:.0f} > 580'
angles = [f.travel_angle_degrees for f in expert if f.travel_angle_degrees is not None]
assert len(angles) == 1500
assert all(8 <= a <= 18 for a in angles), 'FAIL: expert travel_angle out of 8–18°'
print(f'Expert: {len(speeds)} frames, speed p2={p2:.0f} p98={p98:.0f} — OK')
"
```

---

## Step 6 — Generator: Novice Frames

### Problem
Prior plan: novice accelerates when hot. Reality: novice slows down or freezes when puddle looks wrong. Panic deceleration deposits more heat and worsens the condition.

Interpass bias is not integrated into the novice generator — the continuous arc model does not have stitch boundaries. Thermal buildup is captured implicitly through the slow travel speed and panic deceleration behavior.

### Pre-conditions — before any edits

Run `grep -n 'wrong_correction_fired' backend/data/mock_sessions.py`. Must return exactly one match, and that line must fall within `_generate_continuous_novice_frames`. If zero matches or the match is outside that function (e.g. in a comment, test, or another function), STOP and report.

Run `grep -nE 'volts =|amps =' backend/data/mock_sessions.py`. Show all matches. The replacement targets for Step 6 are the two lines inside the arc-on block of `_generate_continuous_novice_frames`. Confirm line numbers before replacing. Do not replace arc-off assignments.

Run `grep -n '_step_thermal_state' backend/data/mock_sessions.py`. Show all matches. Add the fourth argument `travel_speed` to every `_step_thermal_state` call inside `_generate_continuous_novice_frames`. Do not leave any call with only three arguments.

Run `grep -n 'Frame(' backend/data/mock_sessions.py`. Show all matches inside `_generate_continuous_novice_frames`. If more than one Frame() call exists inside that function, confirm which to update. Add `travel_speed_mm_per_min=travel_speed` and `travel_angle_degrees=travel_angle` on every frame. Update ALL Frame() calls inside the target function. Remove any `if is_thermal_frame` condition that would skip adding these fields.

### Method — Novice Generator

Find `_generate_continuous_novice_frames`. Add after `wrong_correction_fired = False`:

```python
travel_speed = AL_TRAVEL_SPEED_NOMINAL
travel_angle = 12.0  # novice starts at push, drifts toward perpendicular under load
porosity_frames_remaining = 0
ctwd_mm = 15.0
ctwd_drift_rate = rng.gauss(0, 0.01)
```

Inside the loop, after angle computation and before `_step_thermal_state`:

```python
        # Novice: panic deceleration — sees bright puddle and slows down
        temp_at_arc = thermal_state[10.0]['center']
        if temp_at_arc > 200 and rng.random() < 0.06:
            travel_speed -= rng.uniform(40, 100)
        elif temp_at_arc > 200 and rng.random() < 0.01:
            travel_speed += rng.uniform(80, 180)
        travel_speed += rng.gauss(0, AL_TRAVEL_SPEED_NOISE_NOVICE)
        travel_speed = max(AL_TRAVEL_SPEED_FLOOR, min(AL_TRAVEL_SPEED_CEILING, travel_speed))

        ctwd_mm += ctwd_drift_rate
        ctwd_mm = max(10.0, min(25.0, ctwd_mm))
        if ctwd_mm >= 24.0:
            ctwd_drift_rate = -abs(ctwd_drift_rate)
        elif ctwd_mm <= 11.0:
            ctwd_drift_rate = abs(ctwd_drift_rate)

        # Novice travel angle: drifts from 10–15° push toward perpendicular under thermal load
        if temp_at_arc > 180 and rng.random() < 0.02:
            travel_angle += rng.uniform(2, 8)
        travel_angle += rng.gauss(0, 1.5)
        travel_angle = max(5.0, min(90.0, travel_angle))
```

Add fourth argument `travel_speed` to every `_step_thermal_state` call inside `_generate_continuous_novice_frames` (line numbers confirmed in pre-condition). Do not leave any call with three arguments.

Replace the `volts =` and `amps =` lines inside the arc-on block of `_generate_continuous_novice_frames` (line numbers confirmed in pre-condition) with this exact block:
```python
        porosity_prob = _porosity_probability(
            angle_degrees=angle,
            travel_speed_mm_per_min=travel_speed,
            ctwd_mm=ctwd_mm,
            base_prob=AL_POROSITY_PROB_NOVICE,
        )
        if arc_active and rng.random() < porosity_prob:
            porosity_frames_remaining = rng.randint(AL_POROSITY_MIN_FRAMES, AL_POROSITY_MAX_FRAMES)
        volts_sigma = AL_VOLTS_NOISE_POROSITY if porosity_frames_remaining > 0 else AL_VOLTS_NOISE_NORMAL
        if porosity_frames_remaining > 0:
            porosity_frames_remaining -= 1
        volts = AL_VOLTS + rng.gauss(0, volts_sigma) if arc_active else 0.0
        amps = AL_AMPS + rng.gauss(0, AL_AMPS_NOISE_NOVICE) if arc_active else 0.0
        if arc_active and rng.random() < 0.003:
            amps += rng.uniform(15, 25)
```

Add `travel_speed_mm_per_min=travel_speed` and `travel_angle_degrees=travel_angle` to every Frame() call inside `_generate_continuous_novice_frames` (confirmed in pre-condition). Remove any `if is_thermal_frame` condition that would skip these fields.

### Verification — Run After Both Steps 5 and 6

```bash
cd backend && python3 -c "
import statistics, numpy as np
from data.mock_sessions import (
    _generate_stitch_expert_frames,
    _generate_continuous_novice_frames,
    AL_TRAVEL_SPEED_EXPERT_MIN, AL_TRAVEL_SPEED_EXPERT_MAX
)

expert = _generate_stitch_expert_frames(0, 1500)
novice = _generate_continuous_novice_frames(0, 1500)

def stats(frames, label):
    amps   = [f.amps for f in frames if f.amps and f.amps > 0]
    volts  = [f.volts for f in frames if f.volts and f.volts > 1.0]
    speeds = [f.travel_speed_mm_per_min for f in frames if f.travel_speed_mm_per_min is not None]
    print(f'{label}: speed σ={statistics.stdev(speeds):.1f} p2={np.percentile(speeds,2):.0f} p98={np.percentile(speeds,98):.0f}')
    return amps, volts, speeds

e_amps, e_volts, e_speeds = stats(expert, 'EXPERT')
n_amps, n_volts, n_speeds = stats(novice, 'NOVICE')

amps_ratio  = statistics.stdev(n_amps)  / statistics.stdev(e_amps)
volts_ratio = statistics.stdev(n_volts) / statistics.stdev(e_volts)
speed_ratio = statistics.stdev(n_speeds)/ statistics.stdev(e_speeds)
assert amps_ratio  > 2.0, f'FAIL: amps {amps_ratio:.1f}x < 2.0x'
assert volts_ratio > 1.5, f'FAIL: volts {volts_ratio:.1f}x < 1.5x'
assert speed_ratio > 2.0, f'FAIL: speed {speed_ratio:.1f}x < 2.0x'

dwell_events = [s for s in n_speeds if s < AL_TRAVEL_SPEED_EXPERT_MIN]
assert len(dwell_events) > 0, 'FAIL: novice never dwelled — panic decel not firing'
assert np.percentile(e_speeds, 2)  >= 360, 'FAIL: expert p2 < 360'
assert np.percentile(e_speeds, 98) <= 580, 'FAIL: expert p98 > 580'

# Cause multipliers must have elevated porosity probability at least once (ctwd=15 nominal)
from data.mock_sessions import _porosity_probability, AL_POROSITY_PROB_NOVICE
max_prob = 0.0
for f in novice:
    if f.travel_speed_mm_per_min is not None and f.angle_degrees is not None:
        p = _porosity_probability(f.angle_degrees, f.travel_speed_mm_per_min, 15.0, AL_POROSITY_PROB_NOVICE)
        max_prob = max(max_prob, p)
assert max_prob > AL_POROSITY_PROB_NOVICE, f'FAIL: cause multipliers never elevated prob (max={max_prob:.4f})'

print('ALL GENERATOR ASSERTIONS PASSED')
"
```

---

## Step 7 — Feature Extractor

### Problem
`POROSITY_SIGMA_THRESHOLD = 0.8` is hardcoded before calibration. Use as starting value; confirm in Step 8.

### Method

In `backend/features/extractor.py`:

**1.** Add `import math` and `import numpy as np` if not present.

**2.** Add `_compute_cyclogram_area` before `extract_features`:

```python
def _compute_cyclogram_area(volts: list, amps: list) -> float:
    """Ellipse area of V-I scatter. Expert: small. Novice: large. π×σ_v×σ_a×sqrt(1-r²)"""
    if len(volts) < 10 or len(amps) < 10:
        return 0.0
    v_std = float(np.std(volts))
    a_std = float(np.std(amps))
    if v_std == 0.0 or a_std == 0.0:
        return 0.0
    r_val = float(np.corrcoef(volts, amps)[0, 1])
    r = 0.0 if (r_val != r_val or abs(r_val) > 1.0) else r_val
    return round(math.pi * v_std * a_std * math.sqrt(max(0.0, 1.0 - r ** 2)), 4)
```

**3.** Immediately before the existing `return {` statement in `extract_features`, insert this exact block:
```python
    # Travel speed stddev
    travel_speeds = [
        f.travel_speed_mm_per_min for f in session.frames
        if f.travel_speed_mm_per_min is not None
    ]
    travel_speed_stddev = float(np.std(travel_speeds)) if len(travel_speeds) > 1 else 0.0

    # Cyclogram area — arc-on frames only
    arc_frames = [f for f in session.frames if f.volts and f.volts > 1.0 and f.amps]
    cyclogram_area = _compute_cyclogram_area(
        [f.volts for f in arc_frames],
        [f.amps for f in arc_frames],
    )

    # Porosity event count — rolling 30-frame windows; threshold 0.8 confirmed by Step 8
    POROSITY_SIGMA_THRESHOLD = 0.8
    porosity_event_count = 0
    window_size = 30
    if len(arc_frames) >= window_size:
        for idx in range(0, len(arc_frames) - window_size, window_size):
            w = [f.volts for f in arc_frames[idx : idx + window_size] if f.volts]
            if len(w) >= window_size // 2 and float(np.std(w)) > POROSITY_SIGMA_THRESHOLD:
                porosity_event_count += 1
```

**4.** Add these three keys to the existing return dict (inside the `return {` block, after the five existing keys):
```python
        "travel_speed_stddev": travel_speed_stddev,
        "cyclogram_area": cyclogram_area,
        "porosity_event_count": porosity_event_count,
```

### Verification

```bash
cd backend && python3 -c "
from data.mock_sessions import generate_session_for_welder
from features.extractor import extract_features

expert_s = generate_session_for_welder('expert_aluminium_001', 'stitch_expert', 0, 'verify_expert')
novice_s = generate_session_for_welder('novice_aluminium_001', 'continuous_novice', 0, 'verify_novice')
ef = extract_features(expert_s)
nf = extract_features(novice_s)

required = ['amps_stddev','angle_max_deviation','north_south_delta_avg','heat_diss_stddev','volts_range',
            'travel_speed_stddev','cyclogram_area','porosity_event_count']
for key in required:
    assert key in ef and key in nf, f'FAIL: {key} missing'

assert nf['porosity_event_count'] >= 3, f'FAIL: novice porosity {nf[\"porosity_event_count\"]} < 3'
assert ef['porosity_event_count'] <= 1, f'FAIL: expert porosity {ef[\"porosity_event_count\"]} > 1'
assert nf['cyclogram_area'] > ef['cyclogram_area'], 'FAIL: cyclogram not separated'
assert nf['travel_speed_stddev'] > ef['travel_speed_stddev'], 'FAIL: speed stddev not separated'
print('Step 7 OK')
"
```

---

## Step 8 — Calibration (Mandatory Before Scoring)

### Problem
5 sessions is insufficient for count variables like `porosity_event_count`. Use 30 sessions per skill level.

### Method

Run 30 sessions per level. Human must review output. Do not proceed to Step 9 until human confirms NO OVERLAP for all three features.

```bash
cd backend && python3 -c "
import numpy as np
from data.mock_sessions import generate_session_for_welder
from features.extractor import extract_features

expert_features = []
novice_features = []

for i in range(30):
    es = generate_session_for_welder('expert_aluminium_001', 'stitch_expert', i, f'calib_e_{i}')
    ns = generate_session_for_welder('novice_aluminium_001', 'continuous_novice', i, f'calib_n_{i}')
    expert_features.append(extract_features(es))
    novice_features.append(extract_features(ns))

features = ['cyclogram_area', 'travel_speed_stddev', 'porosity_event_count']
print(f'{\"Feature\":<30} {\"E_mean\":>8} {\"E_p95\":>8} {\"N_mean\":>8} {\"N_p5\":>8} {\"Gap\":>8} {\"Suggested\":>10}  Status')
print('-' * 100)
for feat in features:
    e_vals = [f[feat] for f in expert_features]
    n_vals = [f[feat] for f in novice_features]
    e_p95 = np.percentile(e_vals, 95)
    n_p5 = np.percentile(n_vals, 5)
    gap = n_p5 - e_p95
    suggested = round((e_p95 + n_p5) / 2, 2) if gap > 0 else None
    status = 'NO OVERLAP' if gap > 0 else 'OVERLAP — CANNOT SEPARATE'
    print(f'{feat:<30} {np.mean(e_vals):>8.2f} {e_p95:>8.2f} {np.mean(n_vals):>8.2f} {n_p5:>8.2f} {gap:>8.2f} {str(suggested):>10}  {status}')
"
```

**Human gate:** Do not proceed to Step 9 until a human reads the output and confirms which threshold values to use. If you have not received explicit human confirmation: output `WAITING FOR HUMAN CONFIRMATION — Step 8` as the final line of your response. Do not write any code after this line. Do not call any tools after this line. Do not proceed on your own judgment.

---

## Step 9 — Database Migration (Two Separate Migrations)

### Problem
Combining schema change and data update in one migration risks: ALTER succeeds, UPDATE fails, Alembic marks migration applied, aluminum row has NULL thresholds, scoring silently uses fallback.

**Pre-condition gate — STOP before any edits:** Before editing any file in this step, run `cd backend && alembic history --verbose`, show the complete output, and STOP. Do not proceed until a human confirms the head revision string. Use that revision as `down_revision` when writing Migration A. Do not guess.

### Method — Model Updates (after pre-condition)


In `backend/models/thresholds.py`, add three optional fields to `WeldTypeThresholds` after existing fields:

```python
travel_speed_consistency: Optional[float] = Field(None, ge=0)
cyclogram_area_max:        Optional[float] = Field(None, ge=0)
porosity_event_max:        Optional[float] = Field(None, ge=0)
```

In `backend/database/models.py`, add three nullable columns to `WeldThresholdModel`:

```python
travel_speed_consistency = Column(Float, nullable=True)
cyclogram_area_max       = Column(Float, nullable=True)
porosity_event_max       = Column(Float, nullable=True)
```

### Method — Migration A (schema only)

Add three nullable Float columns to `weld_thresholds`: `travel_speed_consistency`, `cyclogram_area_max`, `porosity_event_max`. No data changes. Set `down_revision` to the head revision string confirmed in the pre-condition.

Run `alembic upgrade head`.

### Verification — after Migration A

```bash
cd backend && alembic current
```
Output must show Migration A as head. Do not write Migration B until this passes.

Verify all three columns appear (works on PostgreSQL, MySQL, SQLite):

```bash
cd backend && python3 -c "
from database.connection import SessionLocal
from sqlalchemy import inspect
db = SessionLocal()
cols = [c['name'] for c in inspect(db.get_bind()).get_columns('weld_thresholds')]
db.close()
for col in ('travel_speed_consistency', 'cyclogram_area_max', 'porosity_event_max'):
    assert col in cols, f'FAIL: {col} missing from weld_thresholds'
print('Migration A columns: OK')
"
```

**Human gate before Migration B:** After Migration A verification passes, output `MIGRATION A COMPLETE — WAITING FOR MIGRATION B VALUES FROM STEP 8` as the final line of your response. Do not write Migration B until a human provides the three threshold values (travel_speed_consistency, cyclogram_area_max, porosity_event_max) from Step 8 calibration output.

### Method — Migration B (data only, AFTER human provides Step 8 values)

**Agent instruction:** Substitute the three values provided by the human into the UPDATE statement. Do not copy literal `<VALUE_FROM_STEP_8_...>` text — that would produce invalid SQL. If Step 8 showed OVERLAP for any feature, STOP and do not write Migration B.

Example (replace X, Y, Z with actual numbers from Step 8):

```python
def upgrade():
    op.execute("""
        UPDATE weld_thresholds
        SET
            travel_speed_consistency = X,
            cyclogram_area_max       = Y,
            porosity_event_max       = Z
        WHERE weld_type = 'aluminum'
    """)
```

Run `alembic upgrade head`.

### Verification — after Migration B

```bash
cd backend && python3 -c "
from database.connection import SessionLocal
from sqlalchemy import text
db = SessionLocal()
row = db.execute(text(\"SELECT weld_type, travel_speed_consistency, cyclogram_area_max, porosity_event_max FROM weld_thresholds WHERE weld_type = 'aluminum'\")).fetchone()
db.close()
assert row is not None, 'FAIL: no aluminum row'
assert row[1] is not None and row[2] is not None and row[3] is not None, f'FAIL: aluminum row has NULL thresholds: {row}'
print('Migration B: aluminum row populated — OK')
"
```
All three values must be non-null numbers. If zero rows updated, the migration ran but `weld_type = 'aluminum'` matched nothing.

---

## Step 10 — Update threshold_service

### Problem
`_load_all` builds `WeldTypeThresholds` from DB rows. Without mapping the new columns, they are not loaded. The project uses `get_thresholds(db, process_type)` — there is no `get_thresholds_fallback`.

### Method

In `backend/services/threshold_service.py`, the `_load_all` function has exactly one place where `WeldTypeThresholds` is built from a DB row: the `for r in rows:` try block. Add the three keyword arguments to that constructor call only:

```python
travel_speed_consistency=getattr(r, 'travel_speed_consistency', None),
cyclogram_area_max=getattr(r, 'cyclogram_area_max', None),
porosity_event_max=getattr(r, 'porosity_event_max', None),
```

Do not add them to the fallback mig constructors — they must remain 5-field.

In `ALUMINUM_THRESHOLDS` dict, add the three keys using the same three values the human provided during the Step 9 Migration B gate. Do not re-derive or invent values.

### Verification

```bash
cd backend && python3 -c "
from database.connection import SessionLocal
from services.threshold_service import get_thresholds

db = SessionLocal()
try:
    t = get_thresholds(db, 'aluminum')
    assert t.travel_speed_consistency is not None, 'FAIL: travel_speed_consistency is None'
    assert t.cyclogram_area_max is not None, 'FAIL: cyclogram_area_max is None'
    assert t.porosity_event_max is not None, 'FAIL: porosity_event_max is None'
    m = get_thresholds(db, 'mig')
    assert m.travel_speed_consistency is None, 'FAIL: MIG has travel_speed_consistency'
finally:
    db.close()
print('Step 10 OK')
"
```

---

## Step 11 — (No action)

No action required. Proceed to Step 12.

---

## Step 12 — Add Scoring Rules

**SessionScore uses `rules` and `total`** per `backend/models/scoring.py`. Use `ScoreRule` (not `RuleResult`).

Before editing: run `grep -n 'passed' backend/scoring/rule_based.py`. Show all matches. STOP. Confirm the variable name for the passing rule count (e.g. `passed_count`) before writing the replacement line. If the name differs, use the existing variable name.

Run `grep -n 'total' backend/scoring/rule_based.py`. Show all matches. Confirm the line number of the final total computation (after the rules loop, not any initializer such as `total = 0`). Do not replace an initializer — replace only the final computation line.

### Method — Part A

Add three check functions after the existing five. Use `ScoreRule` with `rule_id`, `threshold`, `passed`, `actual_value`:

```python
def _check_travel_speed_consistency(features: dict, t: WeldTypeThresholds) -> ScoreRule:
    actual = features.get('travel_speed_stddev', 0.0)
    th = t.travel_speed_consistency
    return ScoreRule(rule_id='travel_speed_consistency', threshold=th, passed=actual <= th, actual_value=actual)

def _check_cyclogram_area(features: dict, t: WeldTypeThresholds) -> ScoreRule:
    actual = features.get('cyclogram_area', 0.0)
    th = t.cyclogram_area_max
    return ScoreRule(rule_id='cyclogram_area', threshold=th, passed=actual <= th, actual_value=actual)

def _check_porosity_events(features: dict, t: WeldTypeThresholds) -> ScoreRule:
    actual = features.get('porosity_event_count', 0.0)
    th = t.porosity_event_max
    return ScoreRule(rule_id='porosity_events', threshold=th, passed=actual <= th, actual_value=actual)
```

These functions are only invoked when the Part B guards pass. Do not add guards inside these functions.

### Method — Part B

In `score_session`, append new rules only when threshold fields are non-None:

```python
if t and t.travel_speed_consistency is not None:
    rules.append(_check_travel_speed_consistency(features, t))
if t and t.cyclogram_area_max is not None:
    rules.append(_check_cyclogram_area(features, t))
if t and t.porosity_event_max is not None:
    rules.append(_check_porosity_events(features, t))
```

Replace the final total computation line (line number confirmed in pre-condition, not any initializer) with `total = int(round(100 * passed_count / len(rules)))`, substituting `passed_count` with the variable name confirmed by the grep if it differs (e.g. if the grep shows `num_passed`, use that instead).

### Verification — Aluminum

```bash
cd backend && python3 -c "
from data.mock_sessions import generate_session_for_welder
from features.extractor import extract_features
from scoring.rule_based import score_session
from database.connection import SessionLocal
from services.threshold_service import get_thresholds

expert_s = generate_session_for_welder('expert_aluminium_001', 'stitch_expert', 0, 'score_verify')
ef = extract_features(expert_s)
db = SessionLocal()
t = get_thresholds(db, 'aluminum')
db.close()
score = score_session(expert_s, ef, t)
rule_list = score.rules
total = score.total
assert len(rule_list) == 8, f'FAIL: expected 8 rules, got {len(rule_list)}'
assert total >= 75, f'FAIL: expert score {total} < 75'
print(f'Aluminum: {len(rule_list)} rules, total={total} — OK')
"
```

### Verification — MIG regression (non-negotiable)

```bash
cd backend && python3 -c "
from data.mock_sessions import generate_expert_session
from features.extractor import extract_features
from scoring.rule_based import score_session

s = generate_expert_session(session_id='test_mig_regression')
ef = extract_features(s)
score = score_session(s, ef, None)
rule_list = score.rules
total = score.total
assert len(rule_list) == 5, f'FAIL: MIG rules changed to {len(rule_list)}'
print(f'MIG regression: {len(rule_list)} rules, total={total} — OK')
"
```

---

## Step 13 — Final Integration Test

```bash
curl -X POST localhost:8000/api/dev/wipe-mock-sessions
curl -X POST localhost:8000/api/dev/seed-mock-sessions

# Session existence check — fail clearly if seeding missed a session
python3 -c "
import json
import sys
import urllib.request
for sid in ('sess_expert_aluminium_001_001', 'sess_novice_aluminium_001_001'):
    try:
        r = urllib.request.urlopen(f'http://localhost:8000/api/sessions/{sid}')
        d = r.read()
        j = json.loads(d)
        assert 'frames' in j, f'FAIL: {sid} response missing frames key'
        assert len(j.get('frames', [])) == 1500, f'FAIL: {sid} frame count != 1500'
    except urllib.error.HTTPError as e:
        sys.exit(f'FAIL: {sid} returned {e.code} (session missing)')
    except Exception as e:
        sys.exit(f'FAIL: {sid} check failed: {e}')
print('Session existence: OK')
"

curl -s localhost:8000/api/sessions/sess_expert_aluminium_001_001/score | \
  python3 -c "import sys,json; d=json.load(sys.stdin); assert 'total' in d; s=d['total']; print(f'Expert: {s}'); assert s >= 75, f'FAIL: {s}'"

curl -s localhost:8000/api/sessions/sess_novice_aluminium_001_001/score | \
  python3 -c "import sys,json; d=json.load(sys.stdin); assert 'total' in d; s=d['total']; print(f'Novice: {s}'); assert 15 <= s <= 55, f'FAIL: {s}'"

curl -s localhost:8000/api/sessions/sess_sara-okafor_001/score | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert 'rules' in d or 'rule_results' in d, f'FAIL: score missing rules key. Keys: {list(d.keys())}'
rules = d.get('rules', d.get('rule_results', []))
assert len(rules) == 5, f'FAIL: MIG rules = {len(rules)}'
print(f'MIG: {len(rules)} rules — OK')
"
```

---

## Step 14 — Update verify_aluminum_mock.py

### Pre-conditions — before any edits

Run both greps in one pass:
- `grep -n 'model_validate\|payload\|print' backend/scripts/verify_aluminum_mock.py`
- `grep -nE 'expert_frames|novice_frames|expert_session|novice_session' backend/scripts/verify_aluminum_mock.py`

Show all output. STOP. Wait for human to confirm (a) insertion line number (before which to insert the new assertion blocks) and (b) correct variable names for frame lists and Session objects before proceeding. If any of the four names differ in the script (e.g. `frames_e`, `sess_expert`), substitute them in the insertion block below. Do not assume.

**If expert_session and novice_session as Session objects do not exist** (grep shows no such variables), build them inline before the cyclogram block. Before constructing: run `python3 -c "from models.session import Session; import inspect; print(inspect.signature(Session.__init__))"` (or `Session.model_fields` for Pydantic). Show the output. Include all required fields with appropriate values. Insert these two assignments immediately before the cyclogram block.

### Method

In `backend/scripts/verify_aluminum_mock.py`:

1. Add `import numpy as np` if not present.
2. Add `from features.extractor import extract_features`.
3. Insert the following assertion blocks at the line number confirmed by human (immediately before the `payload =` or `print` line).

**Exact blocks to insert (verbatim).** Replace `expert_frames` and `novice_frames` with the variable names confirmed in the pre-condition if different:

```python
    # --- Travel speed assertions (expert p2≥360, p98≤580) ---
    expert_speeds = [f.travel_speed_mm_per_min for f in expert_frames if f.travel_speed_mm_per_min is not None]
    assert len(expert_speeds) == 1500, f"FAIL: expert travel_speed missing on some frames: {len(expert_speeds)}"
    expert_p2 = float(np.percentile(expert_speeds, 2))
    expert_p98 = float(np.percentile(expert_speeds, 98))
    assert expert_p2 >= 360, f"FAIL: expert travel speed p2 {expert_p2:.0f} < 360"
    assert expert_p98 <= 580, f"FAIL: expert travel speed p98 {expert_p98:.0f} > 580"

    # --- Voltage variance (novice σ / expert σ > 1.5) ---
    e_volts = [f.volts for f in expert_frames if f.volts and f.volts > 1.0]
    n_volts = [f.volts for f in novice_frames if f.volts and f.volts > 1.0]
    assert len(e_volts) > 1 and len(n_volts) > 1, "FAIL: insufficient arc-on frames for voltage variance"
    volts_ratio = float(np.std(n_volts)) / float(np.std(e_volts))
    assert volts_ratio > 1.5, f"FAIL: voltage variance ratio {volts_ratio:.2f} ≤ 1.5"

    # --- Cyclogram area and porosity via extract_features ---
    ef = extract_features(expert_session)
    nf = extract_features(novice_session)
    assert "cyclogram_area" in ef and "cyclogram_area" in nf, "FAIL: cyclogram_area missing from extract_features"
    assert "porosity_event_count" in ef and "porosity_event_count" in nf, "FAIL: porosity_event_count missing"
    assert nf["cyclogram_area"] > ef["cyclogram_area"], (
        f"FAIL: cyclogram not separated (expert={ef['cyclogram_area']}, novice={nf['cyclogram_area']})"
    )
    assert nf["porosity_event_count"] >= 3, f"FAIL: novice porosity_event_count {nf['porosity_event_count']} < 3"
    assert ef["porosity_event_count"] <= 1, f"FAIL: expert porosity_event_count {ef['porosity_event_count']} > 1"
```

Use `_generate_stitch_expert_frames(0, 1500)` and `_generate_continuous_novice_frames(0, 1500)` — both accept `(session_index, num_frames)`.

### Verification

```bash
cd backend && python3 -m scripts.verify_aluminum_mock
```

Must exit 0.

---

## Rollback Procedure

If any step after Migration A causes irreversible state:

```bash
cd backend && alembic downgrade -1   # roll back Migration B
cd backend && alembic downgrade -1   # roll back Migration A
curl -X POST localhost:8000/api/dev/wipe-mock-sessions
curl -X POST localhost:8000/api/dev/seed-mock-sessions
```

Document and test this path before running migrations.

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|---------------|
| Travel speed on every frame | 1500/1500 | Step 5/6 assertions |
| Travel angle modeled | Expert ~12° push, novice drifts | Step 5/6, Frame has field |
| Expert speed bounds | p2≥360, p98≤580 | Generator verification |
| Novice dwell behavior | dwell events below expert min | Generator verification |
| Interpass bias integrated | at arc False→True transitions | Step 3 Part B |
| Porosity cause-gated | multipliers elevate prob at least once | Step 4 verification + Step 6 assertion |
| Cyclogram separated | Novice > expert | Step 7 |
| Aluminum scoring | 8 rules, expert ≥75 | Step 12 |
| MIG scoring unchanged | 5 rules | Step 12 regression + Step 13 curl |
| Migration B placeholders | agent substitutes values from Step 8 | Step 9 instruction |
| Threshold key assertion | clear failure if missing | Step 13 curl |
| Human gates enforced | stop if no confirmation | Step 8 |

---

## Summary of Changes From Original Plan

| Topic | Original | This Plan | Reason |
|-------|----------|-----------|--------|
| Travel speed range | Expert 280–420 | Expert 380–560 | AWS D1.2 for 3–6mm plate |
| Novice panic | Accelerates when hot | Decelerates and dwells | Physically correct operator behavior |
| Porosity trigger | Flat random | Cause-gated (angle+speed+CTWD) | ML learns cause→defect |
| CTWD model | Sinusoidal | Monotonic fatigue drift | Positional creep |
| Calibration sessions | 5 | 30 | Sufficient for count statistics |
| Migration structure | 1 (schema+data) | 2 (schema then data) | Silent failure risk |
| Migration B | literal `<VALUE>` placeholders | Agent substitutes Step 8 values | Invalid SQL avoided |
| Interpass bias | Vague "integrate if tracked" | Exact call at arc False→True | Deferral removed |
| Travel angle | Not modeled | Frame field, expert 12°, novice drifts | Document 1 research |
| Porosity Step 4 | No verification | Standalone _porosity_probability test | Cause-gated physics verified |
| Electrical weighting | Unspecified | Equal weighting documented | Research notes 6× amps impact |
| get_thresholds | get_thresholds_fallback | get_thresholds(db, type) | Fallback does not exist |
| Rule model | RuleResult | ScoreRule (hardcoded) | No inspect/placeholder contradiction |
| MIG curl key check | len() on maybe-empty | Explicit key assert | Clear error message |
| Step 2 constants | Agent guesses which exist | Find by name, replace or insert, show diff | No guessing |
| Step 3 interpass | Agent infers arc pattern | Exact line reference, prev_arc_active init | No hallucination |
| Step 5/6 volts/amps | Reference Step 4 | Verbatim code block in each step | No inference |
| Step 7 extract_features | Agent decides variable names | Exact block to insert | No hallucination |
| Step 9 Migration A | Run and write in one go | Show output, STOP for human confirm | Wrong revision avoided |
| Step 9 Migration B | No verification | SELECT to confirm non-null | Zero rows detected |
| Step 10 ALUMINUM_THRESHOLDS | Placeholder values | Exact Step 8 values only | No invented numbers |
| Step 6 ctwd reversal | *= -1 at boundaries | abs() direction flag | No oscillation trap |
| Step 11 numbering | 10→12 gap | Placeholder "No action" | No agent confusion |
| Step 13 score curl | No pre-check | Session existence before score | Clear 404 vs KeyError |
| Step 14 verify script | Agent finds "final print" | grep -n, human confirms line | No wrong insertion |
