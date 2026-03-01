# Weld Pool Temp 39°C Fix Plan

**Overall Progress:** `80%`

## TLDR

Session B (and possibly Session A) on the compare page displays 39°C for "Weld pool temp" — room temperature, physically impossible during welding. The bug originates in mock data generation: aluminum stitch sessions start with thermal state at ambient (25°C) and the first arc-on frames emit transitional temps (30–60°C) before the pool heats up. Mild steel uses BASE_CENTER_TEMPS (never ambient). This plan adds a diagnostic test, fixes aluminum mock generation with 250°C pre-warm so arc-active frames never emit center-10mm < 200°C, extends `verify_aluminum_mock.py` with thermal floor assertions, and adds regression tests. Manual verification requires wipe-then-seed to avoid stale DB data.

---

## Critical Decisions

- **Decision 1:** Fix in mock generation, not frontend — Raw data contract: backend produces correct values; frontend displays. No defensive clamp in `extractCenterTemperatureWithCarryForward`.
- **Decision 2:** Pre-warm aluminum thermal state to 250°C on first arc-on — 150°C can cool below 200°C after one `_step_thermal_state`; 250°C ensures first rendered frame stays ≥200°C (matches acceptance criteria).
- **Decision 3:** Test floor 200°C — Assertions use 200°C (not 100°C) to match acceptance criteria ("300–600°C range" implies floor 200°C). Closes the silent gap where tests pass at 101°C but manual check fails.
- **Decision 4:** Wipe before seed for manual verification — `seed-mock-sessions` may skip regeneration if sessions exist. Call `wipe-mock-sessions` first.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Exact session/URL where 39°C appears | sess_expert_001/sess_novice_001 vs aluminum | Human / repro | Step 1 diagnostic | ⬜ |
| Mild steel thermal path | Confirm BASE_CENTER_TEMPS only, no ambient | Pre-flight grep | Step 2 | ⬜ |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping, output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read backend/data/mock_sessions.py, my-app/src/utils/frameUtils.ts in full.
Capture and output:
(1) THERMAL_DISTANCES_MM, BASE_CENTER_TEMPS, AL_AMBIENT_TEMP, _init_thermal_state signature
(2) extractCenterTemperature, extractCenterTemperatureWithCarryForward — exact signatures and line numbers
(3) grep -n "stitch_count == 1" backend/data/mock_sessions.py
(4) grep -n "extractCenterTemperatureWithCarryForward" my-app/src --r
(5) Run: cd backend && python -m pytest tests/ -q 2>/dev/null | tail -5
(6) Run: wc -l backend/data/mock_sessions.py backend/scripts/verify_aluminum_mock.py my-app/src/utils/frameUtils.ts

Mild steel thermal path (Point of Failure 2):
(7) grep -n "_init_thermal_state\|BASE_CENTER_TEMPS\|generate_thermal_snapshots" backend/data/mock_sessions.py
(8) Confirm: mild steel (generate_expert_session, generate_novice_session) uses generate_frames → generate_thermal_snapshots. That function uses BASE_CENTER_TEMPS[distance_mm] with center_temp = max(20.0, center_temp). It never calls _init_thermal_state. So mild steel starts from BASE_CENTER_TEMPS[10.0]=520 on every arc-on frame.
(9) If grep shows mild steel path uses _init_thermal_state or ambient on arc-on → STOP and add parallel fix for mild steel in Step 2. Otherwise proceed.

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____
Line count mock_sessions.py: ____
Line count verify_aluminum_mock.py: ____
Line count frameUtils.ts: ____
Mild steel uses: [BASE_CENTER_TEMPS only / _init_thermal_state — confirm]
```

**Automated checks (all must pass before Step 1):**
- [ ] Existing test suite passes. Document test count: `____`
- [ ] `_init_thermal_state(ambient: float)` exists in mock_sessions.py
- [ ] `extractCenterTemperatureWithCarryForward(frames, timestamp)` in frameUtils.ts
- [ ] Mild steel path confirmed: generate_thermal_snapshots uses BASE_CENTER_TEMPS; no ambient init on arc-on
- [ ] No uncommitted schema or migration changes

---

## Environment Matrix

| Step | Dev | Staging | Prod | Notes |
|------|-----|---------|------|-------|
| Step 1 | ✅ | N/A | N/A | Diagnostic only |
| Step 2 | ✅ | ✅ | ✅ | Mock generation fix |
| Step 3 | ✅ | ✅ | ✅ | verify_aluminum_mock |
| Step 4 | ✅ | ✅ | ✅ | Regression test |
| Step 5 | ✅ | Manual | Manual | Manual verification (wipe + seed) |

---

## Tasks

### Phase 1 — Root Cause & Fix

**Goal:** Mock data never produces weld pool center temp < 200°C on arc-active frames.

---

- [ ] 🟥 **Step 1: Add diagnostic test** — *Non-critical: reproduces bug before fix*

  **Idempotent:** Yes — test either fails (bug present) or passes (bug fixed). Re-running does not change state.

  **Context:** Reproduce the 39°C bug programmatically. Use backend mock generators to build expert/novice sessions (mild steel + aluminum), iterate all frames, fail if any arc-active frame has center temp < 200°C. Floor is 200°C to match acceptance criteria (300–600°C range).

  **Pre-Read Gate:**
  - `grep -n "def generate_expert_session" backend/data/mock_sessions.py` → exactly 1 match
  - `grep -n "def _generate_stitch_expert_frames" backend/data/mock_sessions.py` → exactly 1 match
  - `grep -n "arc_active" backend/data/mock_sessions.py` → confirm arc logic exists

  **Self-Contained Rule:** All code below is complete. No placeholders.

  Create `backend/tests/test_weld_pool_temp_floor.py`:

  ```python
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
      snap = next((s for s in frame.thermal_snapshots if s.distance_mm == 10.0), frame.thermal_snapshots[0] if frame.thermal_snapshots else None)
      if not snap:
          return None
      c = next((r.temp_celsius for r in snap.readings if r.direction == "center"), None)
      return c

  def _arc_active(frame):
      return frame.volts and frame.volts > 1.0 and frame.amps and frame.amps > 1.0

  FLOOR_CELSIUS = 200.0

  def test_mild_steel_expert_never_below_200():
      s = generate_expert_session("sess_expert_001")
      for f in s.frames:
          if _arc_active(f):
              t = _center_temp_10mm(f)
              assert t is not None, f"frame {f.timestamp_ms} has no thermal"
              assert t >= FLOOR_CELSIUS, f"frame {f.timestamp_ms} center={t}°C < {FLOOR_CELSIUS}"

  def test_mild_steel_novice_never_below_200():
      s = generate_novice_session("sess_novice_001")
      for f in s.frames:
          if _arc_active(f):
              t = _center_temp_10mm(f)
              assert t is not None, f"frame {f.timestamp_ms} has no thermal"
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
  ```

  **What it does:** Four tests that fail if any arc-active frame has 10mm center < 200°C. Expect aluminum tests to fail before Step 2; mild steel should pass (BASE_CENTER_TEMPS).

  **Git Checkpoint:** None. Do not commit until Step 2. This step is diagnostic only.

  **✓ Verification Test:**

  **Type:** Unit
  **Action:** `cd backend && python -m pytest tests/test_weld_pool_temp_floor.py -v`
  **Expected:** At least one aluminum test fails with `center=39` or similar (confirms bug). Mild steel may pass.
  **Observe:** Failure message includes frame timestamp and actual temp
  **Pass:** Tests exist and run; failure confirms root cause
  **Fail:** All pass → bug may be environment-specific; report and continue

---

- [ ] 🟥 **Step 2: Fix aluminum thermal init on first arc-on** — *Critical: mock generation*

  **Idempotent:** Yes — re-running produces same correct output.

  **Context:** Aluminum stitch expert/novice start thermal state at `AL_AMBIENT_TEMP` (25°C). First arc-on frames emit 30–60°C before heating. Pre-warm to **250°C** (not 150°C): `_step_thermal_state` runs immediately after and can cool 150°C below 200°C on first frame. 250°C ensures first rendered frame stays ≥200°C.

  **Pre-Read Gate:**
  - `grep -n "if not prev_arc_active and arc_active:" backend/data/mock_sessions.py` → exactly 1 match (stitch_expert only; continuous_novice has different structure)
  - `grep -n "stitch_count > 1" backend/data/mock_sessions.py` → confirm block exists in stitch_expert
  - `grep -n "thermal_state = _step_thermal_state" backend/data/mock_sessions.py` → one match in _generate_continuous_novice_frames

  **Edit 1 — `_generate_stitch_expert_frames`** (approx line 289):

  Find:
  ```python
          if not prev_arc_active and arc_active:
              stitch_count += 1
              frame_in_stitch = 0
              spike_frames_remaining = 20
              spike_magnitude = min(25.0, AL_AMPS_MAX - amps_target)
              if stitch_count > 1:
                  bias = _compute_interpass_bias(stitch_count - 1, last_arc_end_temp)
                  thermal_state = _init_thermal_state(AL_AMBIENT_TEMP + bias)
  ```

  Replace with:
  ```python
          if not prev_arc_active and arc_active:
              stitch_count += 1
              frame_in_stitch = 0
              spike_frames_remaining = 20
              spike_magnitude = min(25.0, AL_AMPS_MAX - amps_target)
              if stitch_count > 1:
                  bias = _compute_interpass_bias(stitch_count - 1, last_arc_end_temp)
                  thermal_state = _init_thermal_state(AL_AMBIENT_TEMP + bias)
              else:
                  # Stitch 1: pre-warm to 250°C so first frame stays ≥200°C after _step_thermal_state
                  thermal_state = _init_thermal_state(250.0)
  ```

  **Edit 2 — `_generate_continuous_novice_frames`** (no stitch_count; use first-arc-on detection):

  Add `first_arc_on_seen = False` with other loop state (after `wrong_correction_fired = False`, ~line 437).

  Insert **before** `thermal_state = _step_thermal_state(thermal_state, arc_active, angle, travel_speed)` (approx line 497):
  ```python
          if not prev_arc_active and arc_active and not first_arc_on_seen:
              first_arc_on_seen = True
              thermal_state = _init_thermal_state(250.0)
  ```
  This runs when arc turns on for the first time (frame 12, since 0–11 are arc-off). 250°C ensures first arc-on frame stays ≥200°C after one cooling step.

  **Anchor:** The line `thermal_state = _step_thermal_state(thermal_state, arc_active, angle, travel_speed)` appears exactly once in _generate_continuous_novice_frames. Insert the new block immediately before it.

  **What it does:** Ensures first arc-on frames in aluminum sessions start from 250°C so first rendered frame stays ≥200°C.
  **Why:** 150°C can cool below 200°C after one step; 250°C survives one cooling step.

  **Assumptions:**
  - `_init_thermal_state(250.0)` produces a valid ThermalState
  - AL_DISSIPATION_COEFF and conduction in _step_thermal_state do not cool 250→<200 in one step

  **If Step 2 verification fails:** Raise pre-warm from 250°C to 350°C in both edits (stitch_expert and continuous_novice) and re-run `pytest tests/test_weld_pool_temp_floor.py -v`. Do not attempt any other fix without human instruction.

  **Risks:**
  - Thermal profile of first few frames altered → mitigation: 250°C is plausible for preheated plate
  - Aggressive cooling may drop 250→<200 in one step → mitigation: use 350°C if verification fails

  **Git Checkpoint:**
  ```bash
  git add backend/data/mock_sessions.py
  git commit -m "fix: pre-warm aluminum thermal state to 250C on first arc-on to avoid 39C display"
  ```

  **✓ Verification Test:**

  **Type:** Unit
  **Action:** `cd backend && python -m pytest tests/test_weld_pool_temp_floor.py -v`
  **Expected:** All four tests pass
  **Observe:** No assertion errors
  **Pass:** All tests pass
  **Fail:** Aluminum tests still fail → raise pre-warm to 350°C in both edits and re-run; if still failing, STOP and report

---

- [ ] 🟥 **Step 3: Extend verify_aluminum_mock.py with thermal floor** — *Non-critical*

  **Idempotent:** Yes — script is pure assertion.

  **Context:** Acceptance criteria require `verify_aluminum_mock.py` to pass with no thermal values < 200°C at arc-active frames (matches test floor).

  **Pre-Read Gate:**
  - `grep -n "for f in expert_frames" backend/scripts/verify_aluminum_mock.py`
  - `grep -n "def main" backend/scripts/verify_aluminum_mock.py` → insert new assertions before `# --- Session schema validation ---`

  **Add after existing expert/novice assertions (before `# --- Session schema validation ---`):**

  ```python
      # --- Thermal floor at arc-active frames (ISSUE_WELD_POOL_TEMP_39C) ---
      FLOOR_C = 200.0
      for f in expert_frames:
          if f.volts and f.volts > 1.0 and f.amps and f.amps > 1.0:
              for s in f.thermal_snapshots:
                  if s.distance_mm == 10.0:
                      c = next((r.temp_celsius for r in s.readings if r.direction == "center"), None)
                      assert c is not None, f"frame {f.timestamp_ms}: no center"
                      assert c >= FLOOR_C, f"frame {f.timestamp_ms}: center {c}°C < {FLOOR_C}"
                      break
      for f in novice_frames:
          if f.volts and f.volts > 1.0 and f.amps and f.amps > 1.0:
              for s in f.thermal_snapshots:
                  if s.distance_mm == 10.0:
                      c = next((r.temp_celsius for r in s.readings if r.direction == "center"), None)
                      assert c is not None, f"frame {f.timestamp_ms}: no center"
                      assert c >= FLOOR_C, f"frame {f.timestamp_ms}: center {c}°C < {FLOOR_C}"
                      break
  ```

  **What it does:** Ensures aluminum mock never emits center temp < 200°C when arc is on.
  **Git Checkpoint:**
  ```bash
  git add backend/scripts/verify_aluminum_mock.py
  git commit -m "verify: aluminum mock thermal floor >= 200C at arc-active frames"
  ```

  **✓ Verification Test:**

  **Type:** Integration
  **Action:** `cd backend && python -m scripts.verify_aluminum_mock`
  **Expected:** `ALL ASSERTIONS PASSED`
  **Pass:** Script exits 0
  **Fail:** AssertionError → Step 2 fix insufficient; raise pre-warm or re-check mock_sessions.py

---

### Phase 2 — Regression & Manual Check

**Goal:** Automated regression guard and manual verification path documented.

---

- [ ] 🟥 **Step 4: Add frontend regression test** — *Non-critical*

  **Idempotent:** Yes — test uses fixture, asserts invariants.

  **Context:** Acceptance criteria: "Both sessions show weld pool temp > 200°C at any arc-active frame." Add test in frameUtils.test.ts using the existing `makeSnapshot` / `makeThermalFrame` pattern. Agent must read `my-app/src/types/frame.ts` and `my-app/src/__tests__/utils/frameUtils.test.ts` (lines 36–79) before constructing fixture.

  **Pre-Read Gate:**
  - Read `my-app/src/types/frame.ts` — Frame interface, thermal_snapshots shape
  - Read `my-app/src/__tests__/utils/frameUtils.test.ts` lines 36–79 — makeReadings, makeSnapshot, makeThermalFrame, makeSensorOnlyFrame helpers
  - `grep -n "makeSensorOnlyFrame" my-app/src/__tests__/utils/frameUtils.test.ts` → must exist (used in fixture)

  **Add to `my-app/src/__tests__/utils/frameUtils.test.ts`** inside the `extractCenterTemperatureWithCarryForward` describe block (or create new describe if none):

  ```typescript
  it("returns >= 200 for arc-active frames with realistic thermal fixture", () => {
    const frames: Frame[] = [
      makeSensorOnlyFrame({ timestamp_ms: 0, volts: 22, amps: 150 }),
      makeThermalFrame({
        timestamp_ms: 50,
        volts: 22.5,
        amps: 150,
        thermal_snapshots: [makeSnapshot(10.0, 350)],
      }),
      makeSensorOnlyFrame({ timestamp_ms: 60, volts: 22.4, amps: 149 }),
      makeThermalFrame({
        timestamp_ms: 100,
        volts: 22.6,
        amps: 151,
        thermal_snapshots: [makeSnapshot(10.0, 420)],
      }),
      makeSensorOnlyFrame({ timestamp_ms: 110, volts: 22.5, amps: 150 }),
    ];
    const t50 = extractCenterTemperatureWithCarryForward(frames, 50);
    const t75 = extractCenterTemperatureWithCarryForward(frames, 75);
    const t100 = extractCenterTemperatureWithCarryForward(frames, 100);
    expect(t50).toBe(350);
    expect(t75).toBe(350);
    expect(t100).toBe(420);
    expect(t50).toBeGreaterThanOrEqual(200);
    expect(t75).toBeGreaterThanOrEqual(200);
    expect(t100).toBeGreaterThanOrEqual(200);
  });
  ```

  **What it does:** Verifies extractCenterTemperatureWithCarryForward returns values ≥200 with realistic thermal fixture. Uses existing helpers; no placeholder.
  **Git Checkpoint:**
  ```bash
  git add my-app/src/__tests__/utils/frameUtils.test.ts
  git commit -m "test: weld pool temp extraction with realistic thermal fixture >= 200C"
  ```

  **✓ Verification Test:**

  **Type:** Unit
  **Action:** `cd my-app && npm test -- frameUtils.test.ts --run`
  **Expected:** All tests pass including new one
  **Pass:** Test passes
  **Fail:** Fixture malformed → ensure makeSnapshot(10.0, 350) produces readings with center 350; check Frame type compatibility

---

- [ ] 🟥 **Step 5: Manual verification** — *Human gate*

  **Idempotent:** N/A — human action.

  **Context:** Acceptance criteria require manual check on `/compare/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001`. **Point of Failure 3:** If sessions already exist from a previous seed, `seed-mock-sessions` may skip regeneration. Must wipe first.

  **Prerequisites:**
  - Backend running with `ENV=development`
  - **Wipe then seed** — sessions must be regenerated with fixed mock data
  - Aluminum sessions from WELDER_ARCHETYPES: expert_aluminium_001, novice_aluminium_001

  **Session IDs:** `sess_expert_aluminium_001_001`, `sess_novice_aluminium_001_001` — first session of each welder.

  **Action:**
  1. Start backend: `cd backend && ENV=development uvicorn main:app --reload`
  2. **Wipe first:** `curl -X POST http://localhost:8000/api/dev/wipe-mock-sessions`
  3. **Then seed:** `curl -X POST http://localhost:8000/api/dev/seed-mock-sessions`
  4. Open `http://localhost:3000/compare/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001`
  5. Play timeline or scrub to several arc-active moments (e.g. 0.5s, 2s, 6.67s)
  6. Observe "Weld pool temp" for Session A and Session B — must show 300–600°C range, never 39°C or similar

  **Pass:** Both sessions show weld pool temp in 300–600°C range at arc-active times.
  **Fail:** If 39°C still appears → verify wipe ran; try `/compare/sess_expert_001/sess_novice_001` (mild steel) and confirm both URLs fixed.

  **Human Gate:**
  Output `"[MANUAL VERIFICATION REQUIRED — Wipe + seed, then open /compare/sess_novice_aluminium_001_001/sess_expert_aluminium_001_001 and confirm weld pool temp 300–600°C]"` as final line.
  Do not write code after this line.

---

## Regression Guard

**Systems at risk:**
- Aluminum stitch/continuous mock — thermal profile of first arc-on changed
- verify_aluminum_mock — new assertions

**Regression verification:**

| System | Pre-change | Post-change |
|--------|------------|-------------|
| Mild steel expert/novice | Thermal at 10mm ~500/400°C | Same; no change to generate_expert_session |
| Aluminum expert | First stitch started at 25°C | First stitch starts at 250°C |
| Aluminum novice | First arc-on at 25°C | First arc-on at 250°C |
| verify_aluminum_mock | Passed on thermal symmetry etc. | Still passes + thermal floor 200°C |
| extractCenterTemperatureWithCarryForward | Unchanged | Unchanged |

**Test count:** Run `cd backend && python -m pytest tests/ -q` and `cd my-app && npm test -- --run`. Count must be >= pre-flight baseline.

---

## Rollback Procedure

```bash
git revert HEAD~3..HEAD   # Revert Steps 2–4 (3 commits)
# Or revert individually:
git revert <commit_step2>
git revert <commit_step3>
git revert <commit_step4>
cd backend && python -m pytest tests/ -q
cd my-app && npm test -- --run
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| Pre-flight | Baseline snapshot | Test count, line counts | ⬜ |
| Pre-flight | mock_sessions structure | grep anchors | ⬜ |
| Pre-flight | Mild steel path | generate_thermal_snapshots only, no ambient | ⬜ |
| Step 1 | Diagnostic test runs | pytest test_weld_pool_temp_floor | ⬜ |
| Step 2 | Aluminum pre-warm 250°C | Both generators edited | ⬜ |
| Step 3 | verify_aluminum_mock | Script exits 0 | ⬜ |
| Step 4 | Frontend test | frameUtils.test.ts passes | ⬜ |
| Step 5 | Manual (wipe + seed) | Human confirms compare page | ⬜ |

---

## Risk Heatmap

| Step | Risk | Mitigation | Idempotent |
|------|------|------------|------------|
| Step 1 | Low — test only | N/A | Yes |
| Step 2 | Medium — thermal profile change | 250°C plausible preheat; survives one cooling step | Yes |
| Step 3 | Low — additive assertions | Fail fast | Yes |
| Step 4 | Low — additive test | Uses existing helpers | Yes |
| Step 5 | Stale seed data | Wipe before seed | N/A |

---

## Success Criteria

| Criterion | Target | Verification |
|-----------|--------|--------------|
| Mock floor | Arc-active 10mm center >= 200°C | test_weld_pool_temp_floor passes |
| Aluminum verify | Script passes | verify_aluminum_mock exits 0 |
| Compare page | 300–600°C displayed | Manual on aluminum compare URL (after wipe + seed) |
| Test count | >= baseline | pytest + npm test |

---

⚠️ **Do not mark a step 🟩 Done until its verification passes.**
⚠️ **Do not proceed past Human Gate (Step 5) without manual confirmation.**
⚠️ **If blocked, output State Manifest before stopping.**
