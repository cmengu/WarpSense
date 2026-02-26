# Mock Data Foundation — Execution Plan

**Overall Progress:** `100%`

**Source:** [docs/ISSUE_MOCK_DATA_FOUNDATION.md](../docs/ISSUE_MOCK_DATA_FOUNDATION.md)

## TLDR

Fix aluminum expert and novice mock data in `backend/data/mock_sessions.py` so it accurately represents real welder profiles. Add Frame schema fields (heat_input_kj_per_mm, arc_termination_type), update constants, rewrite porosity logic, and fix expert/novice generators for current, voltage, travel speed, arc starts, terminations, and interpass. Do not touch alerts, scoring, or UI.

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping, output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Heat input physics | Target 0.5–0.9 kJ/mm (0.9 allows corner-decel overlap) | Critique | Step 4b, 6 | Yes — see Critical Decisions |
| Corner drop derivation | From speed decel, not flat -12A | Critique | Step 4b | Yes — see Step 4b |
| arc_termination_type semantics | crater_fill_present / no_crater_fill (not ramp-down on full-power frame) | Critique | Step 1, 4c, 5 | Yes — see Critical Decisions |

---

## Pre-Flight — Run Before Any Code Changes

```
Read backend/data/mock_sessions.py in full. Capture:
(1) All AL_* constants (lines 70–101)
(2) Signature of _generate_stitch_expert_frames(session_index, num_frames=1500)
(3) Signature of _generate_continuous_novice_frames(session_index, num_frames=1500)
(4) Signature of _porosity_probability(angle_degrees, travel_speed_mm_per_min, ctwd_mm, base_prob)
(5) Run: cd backend && python -m pytest tests/ -q --tb=no 2>&1 | tail -5
(6) Run: cd backend && python -m scripts.verify_aluminum_mock 2>&1
(7) Run: wc -l backend/data/mock_sessions.py backend/models/frame.py backend/scripts/verify_aluminum_mock.py

Do not change anything. Show full output.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Pytest result: ____
verify_aluminum_mock: ____ (pass/fail)
Line count mock_sessions.py: ____
Line count frame.py: ____
Line count verify_aluminum_mock.py: ____
```

---

## Critical Decisions

- **Heat input target:** 0.5–0.8 kJ/mm typical; assert 0.5–0.9 to allow corner-decel overlap (200A, 24V, 323 mm/min ≈ 0.89). At 180A, 22V, 400 mm/min = 0.594 kJ/mm — correct for spray transfer.
- **Voltage model:** CTWD-driven, not amps-correlated. Arc length (CTWD) dominates voltage. `volts = AL_VOLTS_NOMINAL + (ctwd_mm - AL_CTWD_NOMINAL) * 0.8` (V per mm CTWD deviation).
- **Arc-start spike:** Spike magnitude = `min(25, AL_AMPS_MAX - amps_target)` so high-target sessions do not clip. Spike decays over 20 frames; state machine uses `spike_frames_remaining` and `spike_magnitude`.
- **Corner drop:** Derived from speed decel. At corner, welder backs off — travel speed drops ~15%, amps drop proportionally. Explicit formula: `corner_amps = amps_base * corner_speed_mult` (e.g. 0.85). This reduces heat input at corners (realistic). Do not invoke constant heat input.
- **arc_termination_type:** Use `crater_fill_present` and `no_crater_fill` — operator technique, not literal electrical ramp. Set on last arc-on frame before transition. Full-power frame is correct; label describes the termination that follows.
- **Frame schema:** Add `heat_input_kj_per_mm`, `arc_termination_type: Literal["crater_fill_present", "no_crater_fill"]`. Relax `travel_angle_degrees` ge to -30.
- **Determinism:** Use `random.Random(seed)` only. Never global `random.seed()`.
- **Thermal constants:** `AL_AMPS_THERMAL_REF = 180.0`, `AL_VOLTS_THERMAL_REF = 22.0` — used only inside `_step_thermal_state`. Delete ambiguous `AL_AMPS`/`AL_VOLTS` shims.
- **Novice short-circuit:** Gate on `arc_active == True`. Trigger mid-session (e.g. frames 300–309, 700–709) — not frames 0–9.
- **Novice current pattern:** Use ratios; hot base 185–200 (do not exceed AL_AMPS_MAX 200). `hot_end_frame = int(num_frames * 0.07)`, `cold_start_frame = int(num_frames * 0.13)`, `cold_end_frame = int(num_frames * 0.53)`.
- **Frame count:** Assert `len(expert_frames) == 1500` and `len(novice_frames) == 1500` in verify_aluminum_mock. Catch frame count drift early.
- **Porosity assertion:** `nf["porosity_event_count"] >= 3` — no escape hatch. If it fails, fix the mock or extractor.

---

## Steps Analysis

| Step | Class | Reason | Idempotent |
|------|-------|--------|------------|
| 1 | Critical | Frame schema used everywhere | Yes |
| 2 | Critical | Constants drive both generators | Yes |
| 3 | Critical | Porosity used by both | Yes |
| 4a | Critical | Expert current + voltage | Yes |
| 4b | Critical | Expert travel speed + heat input, corner from decel | Yes |
| 4c | Critical | Expert arc termination label | Yes |
| 5 | Critical | Novice generator | Yes |
| 6 | Non-critical | Verification script | Yes |
| 7 | Non-critical | Tests | Yes |

---

## Phase 1 — Schema

**Goal:** Frame accepts new fields; travel_angle allows negative.

---

- [x] 🟩 **Step 1: Add Frame schema fields and relax travel_angle** — *Critical: Frame is canonical model*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "travel_angle_degrees" backend/models/frame.py` — find Field definition
  - `grep -n "ctwd_mm" backend/models/frame.py` — anchor for insert after
  - `grep -n "heat_input" backend/models/frame.py` — must return nothing

  In `backend/models/frame.py`:

  1. Add `Literal` to imports: `from typing import Dict, List, Literal, Optional`
  2. Change `travel_angle_degrees` Field: `ge=0.0` → `ge=-30.0`
  3. After `ctwd_mm` Field, add:

  ```python
  heat_input_kj_per_mm: Optional[float] = Field(
      None,
      ge=0.0,
      description="Heat input in kJ/mm. Formula: (Amps × Volts × 60) / (travel_speed_mm_per_min × 1000). Expert 0.5–0.9.",
  )
  arc_termination_type: Optional[Literal["crater_fill_present", "no_crater_fill"]] = Field(
      None,
      description="Operator termination technique. crater_fill_present = controlled stop. no_crater_fill = abrupt stop (crater defect risk).",
  )
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/models/frame.py
  git commit -m "step 1: add heat_input_kj_per_mm, arc_termination_type; relax travel_angle ge to -30"
  ```

  **✓ Verification:**
  - **Action:** `cd backend && python -c "from models.frame import Frame; f = Frame(timestamp_ms=0, travel_angle_degrees=-10.0, heat_input_kj_per_mm=0.65, arc_termination_type='no_crater_fill'); print(f.travel_angle_degrees, f.heat_input_kj_per_mm, f.arc_termination_type)"`
  - **Expected:** `-10.0 0.65 no_crater_fill`
  - **Fail:** ImportError/ValidationError → check Field definitions and Literal import

---

## Phase 2 — Constants and Porosity

**Goal:** Constants match expert profile; porosity uses correct compound; thermal refs explicit.

---

- [x] 🟩 **Step 2: Update aluminum constants and thermal refs** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "AL_AMPS\|AL_VOLTS\|AL_TRAVEL_SPEED\|_step_thermal_state" backend/data/mock_sessions.py`

  In `backend/data/mock_sessions.py`:

  1. Replace `AL_AMPS` and `AL_VOLTS` with explicit thermal refs:
     - Add `AL_AMPS_THERMAL_REF = 180.0` and `AL_VOLTS_THERMAL_REF = 22.0`
     - In `_step_thermal_state`, change line 131 from `AL_VOLTS * AL_AMPS` to `AL_VOLTS_THERMAL_REF * AL_AMPS_THERMAL_REF`
     - Delete `AL_AMPS` and `AL_VOLTS` constants

  2. Add/update:
     - `AL_AMPS_MIN = 160.0`, `AL_AMPS_MAX = 200.0`
     - `AL_AMPS_NOISE_EXPERT = 6.0`, `AL_AMPS_NOISE_NOVICE = 12.0`
     - `AL_CTWD_NOMINAL = 15.0`
     - `AL_VOLTS_CTWD_SENSITIVITY = 0.8` (V per mm CTWD deviation)
     - `AL_VOLTS_NOMINAL = 22.0` (base voltage)
     - `AL_TRAVEL_SPEED_NOMINAL = 400.0`, `AL_TRAVEL_SPEED_EXPERT_MIN = 350.0`, `AL_TRAVEL_SPEED_EXPERT_MAX = 450.0`
  3. Keep: `AL_VOLTS_NOISE_NORMAL`, `AL_VOLTS_NOISE_POROSITY`, `AL_TRAVEL_SPEED_NOISE_EXPERT = 8.0`, `AL_TRAVEL_SPEED_NOISE_NOVICE`, `AL_TRAVEL_SPEED_FLOOR`, `AL_TRAVEL_SPEED_CEILING`

  **Git Checkpoint:**
  ```bash
  git add backend/data/mock_sessions.py
  git commit -m "step 2: replace AL_AMPS/AL_VOLTS with AL_*_THERMAL_REF; update aluminum constants"
  ```

  **✓ Verification:**
  - **Action:** `cd backend && python -c "from data.mock_sessions import AL_AMPS_THERMAL_REF, AL_VOLTS_THERMAL_REF, AL_AMPS_MIN, AL_TRAVEL_SPEED_EXPERT_MIN; assert AL_AMPS_THERMAL_REF == 180; assert AL_AMPS_MIN == 160; assert AL_TRAVEL_SPEED_EXPERT_MIN == 350; print('ok')"`
  - **Expected:** `ok`
  - **Fail:** NameError/AssertionError → fix constant names

---

- [x] 🟩 **Step 3: Replace porosity probability with compound condition** — *Critical*

  **Idempotent:** Yes.

  Replace `_porosity_probability` signature and body:

  ```python
  def _porosity_probability(
      travel_angle_degrees: float,
      travel_speed_mm_per_min: float,
      base_prob: float,
  ) -> float:
      """Porosity risk: travel angle into drag (negative) AND speed below 250 mm/min."""
      if travel_angle_degrees >= 0 or travel_speed_mm_per_min >= 250.0:
          return 0.0
      return min(base_prob * 10.0, 0.10)
  ```

  Update call sites to pass `travel_angle_degrees=travel_angle`, `travel_speed_mm_per_min=travel_speed`, `base_prob=...`. Remove `angle_degrees` and `ctwd_mm`.

  **✓ Verification:**
  - **Action:** `cd backend && python -c "
  from data.mock_sessions import _porosity_probability
  assert _porosity_probability(-5, 200, 0.003) > 0
  assert _porosity_probability(5, 200, 0.003) == 0
  assert _porosity_probability(-5, 300, 0.003) == 0
  print('ok')
  "`

---

## Phase 3 — Expert Mock

**Goal:** Expert has target current, arc-start spike (state machine), corner from speed decel, CTWD-driven voltage, travel speed profile, heat input 0.5–0.9 kJ/mm, crater_fill_present label.

---

- [x] 🟩 **Step 4a: Expert mock — current generation and voltage (CTWD-driven)** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "amps = \|volts = \|ctwd_mm" backend/data/mock_sessions.py` in `_generate_stitch_expert_frames`

  **CTWD source:** Expert generator already produces `ctwd_mm` per frame (existing: `ctwd_mm += rng.gauss(0, 0.05)`; clamp 12–17mm). Use that value in the voltage formula. Do not invent CTWD.

  **Arc-start spike state machine (implement exactly):**

  Before loop, initialize:
  ```python
  spike_frames_remaining = 0
  spike_magnitude = 0.0
  ```

  At start of stitch (`not prev_arc_active and arc_active`):
  ```python
  spike_frames_remaining = 20
  spike_magnitude = min(25.0, AL_AMPS_MAX - amps_target)
  ```

  Each frame, after computing amps_base:
  ```python
  if spike_frames_remaining > 0:
      amps += spike_magnitude * (spike_frames_remaining / 20.0)
      spike_frames_remaining -= 1
  ```

  Then clamp amps to [AL_AMPS_MIN, AL_AMPS_MAX]. This ensures spike never clips; high-target sessions get a smaller but visible spike.

  **Current:** `amps_target = rng.uniform(AL_AMPS_MIN, AL_AMPS_MAX)` once before loop. `amps_base = amps_target + rng.gauss(0, AL_AMPS_NOISE_EXPERT)`.

  **Voltage (CTWD-driven):** `volts = AL_VOLTS_NOMINAL + (ctwd_mm - AL_CTWD_NOMINAL) * AL_VOLTS_CTWD_SENSITIVITY + rng.gauss(0, AL_VOLTS_NOISE_NORMAL)` when arc_active. Clamp 20–24. `ctwd_mm` from existing per-frame generator. Do not correlate with amps.

  **Git Checkpoint:**
  ```bash
  git add backend/data/mock_sessions.py
  git commit -m "step 4a: expert current with spike state machine, CTWD-driven voltage"
  ```

  **✓ Verification:**
  - **Action:** `cd backend && python -c "
  from data.mock_sessions import _generate_stitch_expert_frames
  fs = _generate_stitch_expert_frames(0, 1500)
  arc_on = [f for f in fs if f.amps and f.amps > 1]
  amps = [f.amps for f in arc_on]
  assert len(amps) > 500
  assert min(amps) >= 155 and max(amps) <= 205
  first_stitch = [f.amps for f in fs[0:25] if f.amps and f.amps > 1]
  assert len(first_stitch) > 0 and max(first_stitch) > 175
  print('ok')
  "`
  - **Expected:** `ok`
  - **Fail:** AssertionError → check spike logic and state vars

---

- [x] 🟩 **Step 4b: Expert mock — travel speed with decel, corner-derived current drop, heat input** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "stitch_count" backend/data/mock_sessions.py` — stitch_count is incremented when arc turns on: `if not prev_arc_active and arc_active: stitch_count += 1`

  **Corner logic (derived from speed; welder backs off):**

  At every 3rd stitch start (`stitch_count % 3 == 0 and stitch_count > 0`), travel speed drops ~15% for the first 15 frames. `corner_speed_mult = 0.85`. `travel_speed *= corner_speed_mult` during corner window.

  **Current drop:** Welder backs off amps at corners to reduce heat input. Apply corner multiplier to amps_base before adding spike and before clamp. Order: (1) amps_base = amps_target + rng.gauss; (2) if in corner window: amps_base *= 0.85; (3) add spike; (4) clamp to [AL_AMPS_MIN, AL_AMPS_MAX]. Clamp enforces floor — if corner pushes below 160, clamp sets floor and corner drop is partially visible.

  **Travel speed:** Base 380–420 mm/min. At bead start (first 20 frames of each stitch) and bead end (last 20 frames of each stitch), multiply by 0.85 (15% decel). Corner overlaps with start of stitch 3,6,9 — use the same 0.85 multiplier for both corner and start decel when they coincide.

  **Heat input:** `heat_input_kj_per_mm = (amps * volts * 60) / (travel_speed_mm_per_min * 1000)` when arc_active and travel_speed > 0. Set on Frame. Expect 0.5–0.9 kJ/mm (0.9 allows corner-decel overlap).

  **Git Checkpoint:**
  ```bash
  git add backend/data/mock_sessions.py
  git commit -m "step 4b: expert travel speed decel, corner-derived amps drop, heat input"
  ```

  **✓ Verification:**
  - **Action:** `cd backend && python -c "
  from data.mock_sessions import _generate_stitch_expert_frames
  fs = _generate_stitch_expert_frames(0, 1500)
  heat = [f.heat_input_kj_per_mm for f in fs if f.heat_input_kj_per_mm is not None]
  assert len(heat) > 500
  assert all(0.5 <= h <= 0.9 for h in heat), f'heat out of range: min={min(heat)}, max={max(heat)}'
  speeds = [f.travel_speed_mm_per_min for f in fs if f.travel_speed_mm_per_min]
  assert min(speeds) >= 300 and max(speeds) <= 470
  print('ok')
  "`
  - **Expected:** `ok`
  - **Fail:** heat out of range → adjust amps/volts/speed; speeds → check decel logic

---

- [x] 🟩 **Step 4c: Expert mock — arc termination label** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:** `grep -n "pydantic" backend/requirements.txt` — Pydantic v1 uses `.copy(update={...})`; v2 uses `.model_copy(update={...})`. Use defensive helper so code works on both.

  **Define `_with_termination` at module level, not inside `_generate_stitch_expert_frames`** — Step 5 reuses it from `_generate_continuous_novice_frames`.
  ```python
  def _with_termination(f, label):
      try:
          return f.model_copy(update={"arc_termination_type": label})
      except AttributeError:
          return f.copy(update={"arc_termination_type": label})
  frames[-1] = _with_termination(frames[-1], "crater_fill_present")
  ```

  **Approach: prev_arc_active with retroactive update.** Do not use lookahead — it fails on last stitch (i=1499: (i+1)%250=0 &lt; 150).

  Order within loop: (1) compute arc_active for frame i; (2) if `prev_arc_active and not arc_active`, update last frame with arc_termination_type (see defensive helper above); (3) build and append Frame for frame i; (4) `prev_arc_active = arc_active`. Initialize `prev_arc_active = False` before loop.

  This catches every transition. Last stitch: frame 1399 is last arc-on; at i=1400 we compute arc_active=False, prev_arc_active=True → update frames[-1] (1399), then append frame 1400.

  **Git Checkpoint:**
  ```bash
  git add backend/data/mock_sessions.py
  git commit -m "step 4c: expert arc_termination_type crater_fill_present"
  ```

  **✓ Verification:**
  - **Action:** `cd backend && python -c "
  from data.mock_sessions import _generate_stitch_expert_frames
  fs = _generate_stitch_expert_frames(0, 1500)
  labeled = [f for f in fs if f.arc_termination_type == 'crater_fill_present']
  assert len(labeled) >= 4
  assert len(fs) == 1500
  print('ok')
  "`

---

## Phase 4 — Novice Mock

**Goal:** Novice has negative travel angle, hot-start/cold-mid current (ratios), short-circuit voltage (arc_active gated, mid-session), no_crater_fill label.

---

- [x] 🟩 **Step 5: Novice mock — travel angle, current pattern, voltage short-circuit, termination** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:** `grep -n "arc_off\|arc_on\|380\|300\|368" backend/data/mock_sessions.py` — confirm novice arc cycle length. Trigger `(i - 200) % 500 < 10` fires at 200–209, 700–709, 1200–1209; arc must be on at those frames. If cycle ≠ ~380 frames arc-on, adjust trigger windows.

  **Travel angle:** `travel_angle = max(-30.0, min(90.0, travel_angle))` — remove 5° floor.

  **Current pattern (ratios, not absolute frame indices):**
  ```python
  hot_end_frame = int(num_frames * 0.07)
  cold_start_frame = int(num_frames * 0.13)
  cold_end_frame = int(num_frames * 0.53)
  ```
  - Frames 0 to hot_end_frame: base 185–200, add spikes (do not exceed AL_AMPS_MAX)
  - Frames cold_start_frame to cold_end_frame: base 145–155. **Do not clamp novice amps to AL_AMPS_MIN** — novice is allowed to go below 160 (cold mid is the defect signature).
  - Otherwise: base 165–180

  **Voltage short-circuit (arc_active gated, mid-session):**
  - Trigger when `arc_active and i >= 200 and (i - 200) % 500 < 10`. Fires at 200–209, 700–709, 1200–1209. Never on frames 0–9.
  - When triggered: `volts = rng.uniform(17.0, 18.5)`.
  - Do not fire when arc_active is False.

  **Arc termination:** Use prev_arc_active retroactive approach (same as expert). Reuse module-level `_with_termination` from Step 4c. Initialize prev_arc_active before loop; update at end of each iteration.

  **Porosity call:** `_porosity_probability(travel_angle_degrees=travel_angle, travel_speed_mm_per_min=travel_speed, base_prob=AL_POROSITY_PROB_NOVICE)`.

  **Git Checkpoint:**
  ```bash
  git add backend/data/mock_sessions.py
  git commit -m "step 5: novice travel angle negative, current ratios, voltage short-circuit gated, no_crater_fill"
  ```

  **✓ Verification:**
  - **Action:** `cd backend && python -c "
  from data.mock_sessions import _generate_continuous_novice_frames
  fs = _generate_continuous_novice_frames(0, 1500)
  assert len(fs) == 1500
  neg = [f for f in fs if f.travel_angle_degrees is not None and f.travel_angle_degrees < 0]
  abd = [f for f in fs if f.arc_termination_type == 'no_crater_fill']
  low_v = [f for f in fs if f.volts and f.volts < 19 and f.amps and f.amps > 1]
  assert len(neg) > 0
  assert len(abd) > 0
  assert len(low_v) > 0
  early_low_v = [f for idx, f in enumerate(fs) if idx < 200 and f.volts and f.volts < 19 and f.amps and f.amps > 1]
  assert len(early_low_v) == 0, 'short-circuit must not fire before frame 200'
  print('ok')
  "`
  - **Expected:** `ok`
  - **Fail:** 0 counts → check clamp, termination, voltage trigger (must gate on arc_active; must not fire 0–9)

---

## Phase 5 — Verification

**Goal:** verify_aluminum_mock passes; frame count asserted.

---

- [x] 🟩 **Step 6: Update verify_aluminum_mock.py** — *Non-critical*

  **Idempotent:** Yes.

  Ensure frame count assertions remain (verify_aluminum_mock already has these at lines 93, 112):
  `assert len(expert_frames) == 1500` and `assert len(novice_frames) == 1500`. Do not remove.

  Change travel speed: `expert_p2 >= 320`, `expert_p98 <= 480`.

  Add heat input (0.5–0.9 kJ/mm):

  ```python
  expert_heat = [f.heat_input_kj_per_mm for f in expert_frames if f.heat_input_kj_per_mm is not None and f.volts and f.volts > 1]
  assert len(expert_heat) > 100, "FAIL: expert heat_input too few"
  for h in expert_heat:
      assert 0.5 <= h <= 0.9, f"FAIL: expert heat_input {h:.3f} outside 0.5-0.9 kJ/mm"
  ```

  Add novice travel_angle:

  ```python
  novice_neg_angle = [f for f in novice_frames if f.travel_angle_degrees is not None and f.travel_angle_degrees < 0]
  assert len(novice_neg_angle) > 0, "FAIL: novice never has negative travel angle (drag)"
  ```

  **Porosity:** Keep `assert nf["porosity_event_count"] >= 3`. No "else relax". If it fails, fix mock or extractor so porosity events fire under compound condition.

  **Git Checkpoint:**
  ```bash
  git add backend/scripts/verify_aluminum_mock.py
  git commit -m "step 6: verify_aluminum_mock — frame count, heat 0.5-0.9, porosity no relax"
  ```

  **✓ Verification:**
  - **Action:** `cd backend && python -m scripts.verify_aluminum_mock 2>&1`
  - **Expected:** `ALL ASSERTIONS PASSED`

---

- [x] 🟩 **Step 7: Adjust tests if needed** — *Non-critical*

  **Idempotent:** Yes.

  **Action:** `cd backend && python -m pytest tests/ -q --tb=short 2>&1`

  **If tests fail:** If a test asserts on specific amps/volts/angle values from aluminum generators, update the test constants to match the new ranges (160–200A, 350–450 mm/min, etc.). Do not change mock generator logic to satisfy tests. Do not relax plan assertions.

  **✓ Verification:** All tests pass.

---

## Regression Guard

| System | Pre-change | Post-change |
|--------|------------|-------------|
| Mild steel expert/novice | Unchanged | Same |
| Aluminum stitch/continuous | verify_aluminum_mock passes | Passes with new assertions |
| Frame count | 1500 | Asserted; must stay 1500 |
| Test count | Baseline | ≥ baseline |

---

## Rollback Procedure

```bash
git revert --no-commit HEAD~9..HEAD
git commit -m "rollback mock data foundation"
cd backend && python -m pytest tests/ -q
cd backend && python -m scripts.verify_aluminum_mock
```

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Expert current | 160–200A target, ±6 drift, spike visible | Amps in range; first stitch elevated |
| Expert voltage | CTWD-driven, 20–24V | Volts from ctwd, not amps |
| Expert travel speed | 350–450, 15% decel | p2≥320, p98≤480 |
| Expert heat input | 0.5–0.9 kJ/mm | All arc-on in range |
| Expert corner | Derived from speed decel | No flat -12A |
| Expert termination | crater_fill_present | Frames labeled |
| Novice travel angle | Negative (drag) | Some < 0 |
| Novice current | Hot-start (7%), cold mid (13–53%) | Ratios |
| Novice voltage | Short-circuit < 19V when arc on | arc_active gated, mid-session |
| Novice termination | no_crater_fill | Frames labeled |
| Porosity | travel_angle < 0 AND speed < 250 | nf["porosity_event_count"] >= 3 |
| Frame count | 1500 each | Asserted in verify script |

---

⚠️ **Do not mark a step 🟩 Done until its verification passes.**
⚠️ **Use `random.Random(seed)` only — never global `random.seed()`.**
