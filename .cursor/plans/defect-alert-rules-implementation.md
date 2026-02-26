# Feature Implementation Plan: Defect Alert Rules

**Overall Progress:** `0%`

## TLDR

Implement seven defect-signature rules in the alert engine (porosity, arc instability, crater crack, oxide inclusion, undercut, lack of fusion, burn-through), keeping the existing three proxy rules. Extend `FrameInput` with optional `volts` and `amps`; add time-based buffers for arc instability (voltage sustain) and crater crack (current ramp-down); wire callers to pass volts/amps. Scope: `alert_engine`, `alert_models`, `frame_buffer`, `alert_thresholds.json`, `simulate_realtime`, `sessions.get_session_alerts` only. No mock data, scoring, or UI changes.

---

## Critical Decisions

- **FrameInput extension:** Add optional `volts: Optional[float]` and `amps: Optional[float]`. Rules that need them log a warning and skip when `None` — never silently fail.
- **Per-rule warning flags:** Each rule that requires volts or amps has its own flag (_warned_volts_missing, _warned_amps_missing_crater, _warned_amps_missing_undercut, _warned_amps_missing_burn_through). Shared flags cause silent diagnostic failure when one rule consumes the flag before another can log.
- **Time-based buffers:** Voltage sustain and current ramp-down use `timestamp_ms` exclusively. No frame-count assumptions. Buffers and warning flags reset implicitly on `AlertEngine.__init__` (one engine per session). If session reuse is added without reconstructing the engine, warning flags would permanently silence after the first session.
- **Suppression:** Spike rules (porosity, oxide, crater, undercut, burn-through) use `suppression_ms`. Sustained rules (arc instability, lack_of_fusion_amps) re-fire every `sustained_repeat_ms`. Lack-of-fusion speed branch is a spike rule (transient).
- **Lack of fusion split:** Low amps (< 140A) = sustained (prolonged low heat input). High speed (> 520 mm/min) = spike (transient excursion). Different suppression per branch.
- **Porosity vs oxide inclusion:** Both can fire when travel_angle < 0 — porosity is compound (angle + speed), oxide is standalone. When porosity fires, suppress oxide for the same `suppression_ms` to avoid dual alerts for same root cause. Messages distinguish: porosity = "drag angle and low speed"; oxide = "argon trailing (negative travel angle)".
- **rule_triggered values:** Use `"rule1"`–`"rule3"` for existing; `"porosity"`, `"arc_instability"`, `"crater_crack"`, `"oxide_inclusion"`, `"undercut"`, `"lack_of_fusion_amps"`, `"lack_of_fusion_speed"`, `"burn_through"` for defect rules. Lack-of-fusion split enables QA to distinguish low-amps vs high-speed triggers.
- **Lack-of-fusion dual fire:** When both amps and speed conditions fire on the same frame, both append candidates. Assign lack_of_fusion_amps = 9, lack_of_fusion_speed = 10, burn_through = 11. Lower number wins; amps takes priority when both fire. Only one alert returns per frame (candidates[0][2]).
- **lack_of_fusion_speed_max:** Set to 520 mm/min (not 480) so expert mock (380–560) does not trigger on normal operation. Known: novice can hit > 520; expert stays below except edge cases.
- **Undercut and burn-through:** Current mock peaks ~195A; thresholds 210A and 220A will not fire. Unit-test only; no mock scenario. Document as known limitation until Session 1 extends mock.
- **Crater crack arming:** Buffer arms only after arc has been on (amps > 1.0) for at least 500ms. Prevents false positives from wire feed hiccups (brief arc interruption mid-bead).
- **Type hints:** Use `Optional[float]` everywhere for Python 3.8/3.9 compatibility. No `float | None`.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| sustained_repeat_ms value | 2000 | issue doc; hardcoded in Step 2 JSON | Step 8 | ✅ |
| Config key naming | voltage_lo_V, etc. | issue doc; defined in Step 2 | Step 2 | ✅ |

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
Read backend/realtime/alert_engine.py, alert_models.py, frame_buffer.py in full.
Capture and output:
(1) Every class, function, and field in AlertEngine, FrameInput, SpeedFrameBuffer
(2) Exact signature of load_thresholds, AlertEngine.push_frame
(3) Exact line where "if not candidates:" appears in alert_engine.py
(4) Read the 5 lines FOLLOWING "if not candidates:" — confirm: it is "return None" (early return when empty), then severity_rank and candidates.sort, then return candidates[0][2]. All rules append to candidates BEFORE this block; defect rules must do the same. If this block is different, STOP and report.
(5) Every file that imports from realtime.alert_engine or realtime.alert_models
(6) Run: cd backend && python -m pytest tests/test_alert_engine.py -v 2>&1 | tail -20
(7) Run: wc -l backend/realtime/alert_engine.py backend/realtime/alert_models.py backend/config/alert_thresholds.json
(8) grep -n "from collections" backend/realtime/frame_buffer.py — must show deque import
Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____
Line count alert_engine.py:    ____
Line count alert_models.py:    ____
Line count alert_thresholds.json: ____
```

**Automated checks (all must pass before Step 1):**
- [ ] Existing test suite passes. Document count: `____`
- [ ] `load_thresholds` exists and raises on missing keys
- [ ] `FrameInput` has frame_index, timestamp_ms, travel_angle_degrees, travel_speed_mm_per_min, ns_asymmetry
- [ ] `FrameInput` does NOT have volts or amps yet
- [ ] `alert_thresholds.json` has thermal_ns_warning, suppression_ms, etc.
- [ ] Lines following "if not candidates:" are: return None, then sort, then return candidates[0][2]
- [ ] `grep -n "timestamp_ms" backend/realtime/alert_engine.py` — confirm `now_ms = frame.timestamp_ms if frame.timestamp_ms is not None else time.time() * 1000` (or equivalent). All suppression comparisons use now_ms; if timestamp_ms were used directly without fallback, None would cause TypeError.

---

## Steps Analysis

| Step | Critical? | Reason | Idempotent |
|------|-----------|--------|------------|
| 1 | Yes | FrameInput is shared contract | Yes |
| 2 | Yes | Config is loaded by all engines | Yes |
| 3 | Yes | load_thresholds validates config | Yes |
| 4 | No | Wiring only | Yes |
| 5 | Yes | API contract | Yes |
| 6 | Yes | New buffer used by arc instability | Yes |
| 7 | Yes | New buffer used by crater crack | Yes |
| 8 | Yes | First defect rule | Yes |
| 9–14 | Yes | Defect rules; each needs re-read gate | Yes |
| 15 | No | Tests | Yes |
| 16 | No | Regression guard | Yes |

---

## Tasks

### Phase 1 — Foundation

**Goal:** FrameInput has volts/amps; config has defect thresholds; callers pass volts/amps; time-based buffers exist.

---

- [ ] 🟥 **Step 1: Extend FrameInput with volts and amps** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "travel_speed_mm_per_min" backend/realtime/alert_models.py` → 1 match
  - `grep -n "volts" backend/realtime/alert_models.py` → 0 matches

  **Self-Contained Rule:** Code block is complete. No placeholders.

  ```python
  # In backend/realtime/alert_models.py, add two optional fields to FrameInput after travel_speed_mm_per_min:
  volts: Optional[float] = Field(
      None,
      description="Arc voltage in V. Required for arc_instability, undercut, lack_of_fusion, burn_through.",
  )
  amps: Optional[float] = Field(
      None,
      description="Arc current in A. Required for crater_crack, undercut, lack_of_fusion, burn_through.",
  )
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/alert_models.py
  git commit -m "step 1: extend FrameInput with optional volts and amps"
  ```

  **✓ Verification Test:**
  - **Type:** Unit
  - **Action:** `cd backend && python -c "
  from realtime.alert_models import FrameInput
  f = FrameInput(frame_index=0, ns_asymmetry=0)
  assert f.volts is None
  assert f.amps is None
  f2 = FrameInput(frame_index=0, ns_asymmetry=0, volts=22.0, amps=155.0)
  assert f2.volts == 22.0
  assert f2.amps == 155.0
  print('OK')
  "`
  - **Expected:** Prints `OK`
  - **Pass:** Exit 0
  - **Fail:** ImportError or assertion → check alert_models.py syntax

---

- [ ] 🟥 **Step 2: Add defect thresholds to alert_thresholds.json** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "suppression_ms" backend/config/alert_thresholds.json` → 1 match

  **Self-Contained Rule:** Add new keys. Preserve all existing keys. Use lack_of_fusion_speed_max_mm_per_min = 520 (expert mock 380–560; 520 avoids expert false triggers).

  ```json
  {
    "thermal_ns_warning": 25,
    "thermal_ns_critical": 40,
    "angle_deviation_warning": 6.5,
    "angle_deviation_critical": 8,
    "speed_drop_warning_pct": 13,
    "speed_drop_critical_pct": 18,
    "nominal_travel_angle": 12,
    "suppression_ms": 1000,
    "voltage_lo_V": 19.5,
    "voltage_sustain_ms": 500,
    "crater_ramp_pct": 30,
    "crater_ramp_min_ms": 300,
    "crater_arc_on_min_ms": 500,
    "porosity_speed_max_mm_per_min": 250,
    "undercut_amps_min": 210,
    "undercut_speed_min_mm_per_min": 500,
    "lack_of_fusion_amps_max": 140,
    "lack_of_fusion_speed_max_mm_per_min": 520,
    "burn_through_amps_min": 220,
    "burn_through_speed_max_mm_per_min": 200,
    "sustained_repeat_ms": 2000
  }
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/config/alert_thresholds.json
  git commit -m "step 2: add defect rule thresholds to config"
  ```

  **✓ Verification Test:**
  - **Type:** Unit
  - **Action:** `cd backend && python -c "
  import json
  from pathlib import Path
  p = Path('config/alert_thresholds.json')
  d = json.loads(p.read_text())
  assert d['lack_of_fusion_speed_max_mm_per_min'] == 520
  assert d['crater_arc_on_min_ms'] == 500
  print('OK')
  "`
  - **Pass:** Exit 0
  - **Fail:** KeyError → check JSON keys match

---

- [ ] 🟥 **Step 3: Extend load_thresholds to validate new keys** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "required = " backend/realtime/alert_engine.py` → 1 match inside load_thresholds

  **Self-Contained Rule:** Extend the `required` tuple to include all new keys including `crater_arc_on_min_ms`.

  ```python
  required = (
      "thermal_ns_warning",
      "thermal_ns_critical",
      "angle_deviation_warning",
      "angle_deviation_critical",
      "speed_drop_warning_pct",
      "speed_drop_critical_pct",
      "nominal_travel_angle",
      "suppression_ms",
      "voltage_lo_V",
      "voltage_sustain_ms",
      "crater_ramp_pct",
      "crater_ramp_min_ms",
      "crater_arc_on_min_ms",
      "porosity_speed_max_mm_per_min",
      "undercut_amps_min",
      "undercut_speed_min_mm_per_min",
      "lack_of_fusion_amps_max",
      "lack_of_fusion_speed_max_mm_per_min",
      "burn_through_amps_min",
      "burn_through_speed_max_mm_per_min",
      "sustained_repeat_ms",
  )
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/alert_engine.py
  git commit -m "step 3: extend load_thresholds to validate defect thresholds"
  ```

  **✓ Verification Test:**
  - **Type:** Unit
  - **Action:** `cd backend && python -m pytest tests/test_alert_engine.py -v -k "load_thresholds" 2>&1 | tail -5`
  - **Pass:** test_load_thresholds_missing_raises passes; load_thresholds does not raise for valid config

---

- [ ] 🟥 **Step 4: Wire simulate_realtime to pass volts and amps into FrameInput** — *Non-critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "FrameInput(" backend/scripts/simulate_realtime.py` → 1 match

  **Self-Contained Rule:**

  ```python
  fin = FrameInput(
      frame_index=i,
      timestamp_ms=i * 10.0,
      travel_angle_degrees=travel_angle,
      travel_speed_mm_per_min=travel_speed,
      ns_asymmetry=ns,
      volts=frame.volts,
      amps=frame.amps,
  )
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/scripts/simulate_realtime.py
  git commit -m "step 4: pass volts and amps from mock frame to FrameInput"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && timeout 3 python -m scripts.simulate_realtime --mode novice --output console --frames 50 2>&1 | tail -5`
  - **Pass:** No traceback

---

- [ ] 🟥 **Step 5: Wire get_session_alerts to pass volts and amps into FrameInput** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "fin = FrameInput" backend/routes/sessions.py` → 1 match

  **Self-Contained Rule:**

  ```python
  fin = FrameInput(
      frame_index=i,
      timestamp_ms=float(ts_ms),
      travel_angle_degrees=fd.get("travel_angle_degrees"),
      travel_speed_mm_per_min=fd.get("travel_speed_mm_per_min"),
      ns_asymmetry=ns,
      volts=fd.get("volts"),
      amps=fd.get("amps"),
  )
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/routes/sessions.py
  git commit -m "step 5: pass volts and amps from frame_data to FrameInput in get_session_alerts"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -m pytest tests/ -v -k "alert" 2>&1 | tail -15`
  - **Pass:** All alert-related tests pass

---

### Phase 2 — Buffers and Rules

**Goal:** VoltageSustainBuffer and CurrentRampDownBuffer exist; all seven defect rules implemented with correct suppression.

---

- [ ] 🟥 **Step 6: Add VoltageSustainBuffer (time-based)** — *Critical*

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "class SpeedFrameBuffer" backend/realtime/frame_buffer.py` → 1 match
  - `grep -n "from collections" backend/realtime/frame_buffer.py` → 1 match (deque already imported)

  **Self-Contained Rule:** Use `Optional[float]` for type hints (Python 3.8 compat). Add `from typing import Optional` at top of `backend/realtime/frame_buffer.py` if not present. Then add class:

  ```python
  from typing import Optional

  class VoltageSustainBuffer:
      """Tracks (timestamp_ms, voltage). Detects voltage < threshold sustained > duration_ms."""

      def __init__(self, threshold_V: float, duration_ms: float) -> None:
          self._threshold = threshold_V
          self._duration_ms = duration_ms
          self._low_since_ms: Optional[float] = None

      def push(self, timestamp_ms: float, voltage_V: Optional[float]) -> bool:
          """Record sample. Returns True if sustained low for >= duration_ms this frame."""
          if voltage_V is None or voltage_V >= self._threshold:
              self._low_since_ms = None
              return False
          if self._low_since_ms is None:
              self._low_since_ms = timestamp_ms
          elapsed = timestamp_ms - self._low_since_ms
          return elapsed >= self._duration_ms

      def reset(self) -> None:
          self._low_since_ms = None
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/frame_buffer.py
  git commit -m "step 6: add VoltageSustainBuffer for time-based voltage sustain detection"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -c "
  from realtime.frame_buffer import VoltageSustainBuffer
  buf = VoltageSustainBuffer(19.5, 500.0)
  assert buf.push(0, 22.0) is False
  assert buf.push(100, 18.0) is False
  assert buf.push(400, 18.0) is False
  assert buf.push(501, 18.0) is True
  buf.reset()
  assert buf.push(0, 18.0) is False
  print('OK')
  "`
  - **Pass:** Exit 0, prints OK

---

- [ ] 🟥 **Step 7: Add CurrentRampDownBuffer (time-based)** — *Critical*

  **Idempotent:** Yes.

  **Context:** Crater crack = abrupt drop to zero. Ramp-down = ≥30% decrease over ≥300ms before zero. **Arming:** Only evaluate when arc has been on (amps > 1.0) for at least 500ms. Prevents false positives from wire feed hiccups.

  **Pre-Read Gate:**
  - `grep -n "class VoltageSustainBuffer" backend/realtime/frame_buffer.py` → 1 match (confirms Step 6 landed)
  - `grep -n "from collections import deque" backend/realtime/frame_buffer.py` → 1 match

  **Self-Contained Rule:** Add class. Arc samples exclude zero-amp frames. Use `Optional[float]` for type hints. Arm only when arc on ≥ crater_arc_on_min_ms before dropout. `typing.Optional` already imported in Step 6.

  ```python
  class CurrentRampDownBuffer:
      """Detects abrupt current drop to zero. Arms only after arc on >= arc_on_min_ms."""

      def __init__(
          self,
          ramp_pct: float,
          ramp_min_ms: float,
          arc_on_min_ms: float,
          max_history_ms: float = 1000.0,
      ) -> None:
          self._ramp_pct = ramp_pct
          self._ramp_min_ms = ramp_min_ms
          self._arc_on_min_ms = arc_on_min_ms
          self._max_history_ms = max_history_ms
          self._samples: deque = deque()
          self._arc_on_since_ms: Optional[float] = None

      def push(self, timestamp_ms: float, amps: Optional[float]) -> Optional[bool]:
          """
          Returns True if abrupt (crater crack), False if controlled, None if arc on or not armed.
          Arms only after amps > 1.0 for >= arc_on_min_ms.
          """
          if amps is None:
              return None
          self._samples.append((timestamp_ms, amps))
          while self._samples and (timestamp_ms - self._samples[0][0]) > self._max_history_ms:
              self._samples.popleft()
          if amps > 1.0:
              if self._arc_on_since_ms is None:
                  self._arc_on_since_ms = timestamp_ms
              return None
          self._arc_on_since_ms = None
          arc = [(t, a) for t, a in self._samples if a > 1.0]
          if not arc:
              return None
          arc_duration = arc[-1][0] - arc[0][0]
          if arc_duration < self._arc_on_min_ms:
              return None
          for i, (t1, a1) in enumerate(arc):
              for t2, a2 in arc[i + 1:]:
                  if t2 - t1 >= self._ramp_min_ms and a2 <= a1 * (1 - self._ramp_pct / 100):
                      return False
          return True

      def reset(self) -> None:
          self._samples.clear()
          self._arc_on_since_ms = None
  ```

  **What it does:** Arms after 500ms arc-on; when amps drops to ≤1.0, checks for ramp-down in arc samples only (excludes zero-amp frame from pair scan). Returns None when not armed or arc still on.

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/frame_buffer.py
  git commit -m "step 7: add CurrentRampDownBuffer with arc-on arming for crater crack"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -c "
  from realtime.frame_buffer import CurrentRampDownBuffer
  b = CurrentRampDownBuffer(30, 300, 500, 1000)
  for i in range(60):
      b.push(i * 10, 150.0)
  assert b.push(610, 0.0) is True
  b.reset()
  for i in range(60):
      b.push(i * 10, 150.0)
  for i in range(36):
      t = 600 + i * 10
      a = 150.0 - (i / 35.0) * 50.0
      b.push(t, a)
  assert b.push(960, 0.0) is False
  b.reset()
  for i in range(5):
      b.push(i * 10, 150.0)
  assert b.push(50, 0.0) is None
  print('OK')
  "`
  - **Pass:** Exit 0, prints OK. Ramp spans 600–950ms (350ms) with 30%+ drop before zero at 960ms.
  - **Fail:** Logic error in ramp detection or arming

---

- [ ] 🟥 **Step 8: Implement porosity rule** — *Critical*

  **Idempotent:** Yes.

  **Re-Read Gate (mandatory before edit):**
  - `read backend/realtime/alert_engine.py` — capture current line count and exact position of "if not candidates"
  - `grep -n "Rule 3: Speed drop" backend/realtime/alert_engine.py` → 1 match
  - `grep -n "if not candidates" backend/realtime/alert_engine.py` → 1 match; confirm defect block inserts BEFORE this line

  **Self-Contained Rule:** Add `self._suppress_porosity_until = 0.0` in __init__. Insert Rule 4 block after Rule 3 block, before `if not candidates`. When porosity fires, also set `_suppress_oxide_until = now_ms + self._suppression_ms` so oxide does not fire simultaneously.

  ```python
  # In __init__, add:
  self._suppress_porosity_until = 0.0
  self._suppress_oxide_until = 0.0

  # Insert after Rule 3 block, before "if not candidates":
  # Rule 4: Porosity (spike)
  if now_ms >= self._suppress_porosity_until:
      if frame.travel_angle_degrees is not None and frame.travel_speed_mm_per_min is not None:
          if frame.travel_angle_degrees < 0 and frame.travel_speed_mm_per_min < self._cfg["porosity_speed_max_mm_per_min"]:
              candidates.append((4, "critical", AlertPayload(
                  frame_index=frame.frame_index,
                  rule_triggered="porosity",
                  severity="critical",
                  message="Porosity risk: drag angle and low speed",
                  correction="Increase travel angle to push and speed to 250+ mm/min",
                  timestamp_ms=now_ms,
              )))
              self._suppress_porosity_until = now_ms + self._suppression_ms
              self._suppress_oxide_until = now_ms + self._suppression_ms
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/alert_engine.py
  git commit -m "step 8: implement porosity defect rule"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -c "
  from realtime.alert_engine import AlertEngine
  from realtime.alert_models import FrameInput
  e = AlertEngine('config/alert_thresholds.json')
  a = e.push_frame(FrameInput(frame_index=0, travel_angle_degrees=-5, travel_speed_mm_per_min=200, ns_asymmetry=0, timestamp_ms=0))
  assert a is not None and a.rule_triggered == 'porosity'
  a2 = e.push_frame(FrameInput(frame_index=1, travel_angle_degrees=5, travel_speed_mm_per_min=200, ns_asymmetry=0, timestamp_ms=10))
  assert a2 is None or a2.rule_triggered != 'porosity'
  print('OK')
  "`
  - **Pass:** First frame fires porosity; second does not

---

- [ ] 🟥 **Step 9: Implement arc instability rule** — *Critical*

  **Idempotent:** Yes.

  **Re-Read Gate (mandatory before edit):**
  - `read backend/realtime/alert_engine.py` — confirm Rule 4 (porosity) block exists; capture line number of "if not candidates"
  - `grep -n 'rule_triggered="porosity"' backend/realtime/alert_engine.py` → 1 match
  - `grep -n "from realtime.frame_buffer import" backend/realtime/alert_engine.py` — if 1 match, extend that line; do not add duplicate import

  **Self-Contained Rule:** Add voltage buffer, suppression, and _warned_volts_missing (log once per session when volts is None). Extend existing frame_buffer import; do not add a second import line.

  ```python
  # In __init__, add:
  self._voltage_buffer = VoltageSustainBuffer(
      float(self._cfg["voltage_lo_V"]),
      float(self._cfg["voltage_sustain_ms"]),
  )
  self._suppress_arc_instability_until = 0.0
  self._warned_volts_missing = False

  # Extend import (or add if absent): from realtime.frame_buffer import SpeedFrameBuffer, VoltageSustainBuffer

  # Insert after Rule 4 block, before "if not candidates":
  # Rule 5: Arc instability (sustained) — push every frame (buffer handles None); warn when None
  sustained = self._voltage_buffer.push(now_ms, frame.volts)
  if frame.volts is None:
      if not self._warned_volts_missing:
          logger.warning("arc_instability requires volts; skipping (frame_index=%d)", frame.frame_index)
          self._warned_volts_missing = True
  elif sustained and now_ms >= self._suppress_arc_instability_until:
      candidates.append((5, "critical", AlertPayload(
          frame_index=frame.frame_index,
          rule_triggered="arc_instability",
          severity="critical",
          message="Arc instability: voltage < 19.5V sustained",
          correction="Check shielding gas and wire feed",
          timestamp_ms=now_ms,
      )))
      self._suppress_arc_instability_until = now_ms + self._cfg["sustained_repeat_ms"]
  ```

  **Note:** Push to buffer on every frame (including when suppressed) so sustain state is correct when condition clears and resurfaces.

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/alert_engine.py
  git commit -m "step 9: implement arc instability rule with time-based voltage sustain"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -c "
  from realtime.alert_engine import AlertEngine
  from realtime.alert_models import FrameInput
  import logging
  logging.basicConfig(level=logging.WARNING)
  e = AlertEngine('config/alert_thresholds.json')
  alerts = []
  for i in range(60):
      f = FrameInput(frame_index=i, volts=18.0, ns_asymmetry=0, travel_angle_degrees=12, travel_speed_mm_per_min=450, timestamp_ms=i*10)
      a = e.push_frame(f)
      if a:
          alerts.append(a)
  arc_alerts = [x for x in alerts if x.rule_triggered == 'arc_instability']
  assert len(arc_alerts) >= 1, 'arc_instability must fire after ~500ms low voltage'
  print('OK')
  "`
  - **Pass:** arc_alerts non-empty; rule fires after ~500ms

---

- [ ] 🟥 **Step 10: Implement crater crack rule** — *Critical*

  **Idempotent:** Yes.

  **Re-Read Gate (mandatory before edit):**
  - `grep -n 'rule_triggered="arc_instability"' backend/realtime/alert_engine.py` → 1 match (use single quotes around the grep pattern)
  - `grep -n "from realtime.frame_buffer import" backend/realtime/alert_engine.py` → 1 match; extend that line to add CurrentRampDownBuffer
  - `read backend/realtime/alert_engine.py` offset around Rule 5 — confirm structure before inserting Rule 6

  **Self-Contained Rule:** Add crater buffer and _warned_amps_missing in __init__. When amps is None: log warning once per session, skip. Extend existing import; do not add duplicate.

  ```python
  # In __init__, add:
  self._crater_buffer = CurrentRampDownBuffer(
      float(self._cfg["crater_ramp_pct"]),
      float(self._cfg["crater_ramp_min_ms"]),
      float(self._cfg["crater_arc_on_min_ms"]),
  )
  self._suppress_crater_until = 0.0
  self._warned_amps_missing_crater = False

  # Extend import: from realtime.frame_buffer import SpeedFrameBuffer, VoltageSustainBuffer, CurrentRampDownBuffer

  # Insert after Rule 5 block, before "if not candidates":
  # Rule 6: Crater crack (spike) — push every frame to maintain buffer history
  if frame.amps is None:
      if not self._warned_amps_missing_crater:
          logger.warning("crater_crack requires amps; skipping (frame_index=%d)", frame.frame_index)
          self._warned_amps_missing_crater = True
  else:
      abrupt = self._crater_buffer.push(now_ms, frame.amps)
      if abrupt is True and now_ms >= self._suppress_crater_until:
          candidates.append((6, "critical", AlertPayload(
              frame_index=frame.frame_index,
              rule_triggered="crater_crack",
              severity="critical",
              message="Crater crack risk: abrupt arc termination",
              correction="Use controlled ramp-down at bead end",
              timestamp_ms=now_ms,
          )))
          self._suppress_crater_until = now_ms + self._suppression_ms
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/alert_engine.py
  git commit -m "step 10: implement crater crack rule with arc-on arming"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -c "
  from realtime.alert_engine import AlertEngine
  from realtime.alert_models import FrameInput
  e = AlertEngine('config/alert_thresholds.json')
  for i in range(60):
      e.push_frame(FrameInput(frame_index=i, amps=150.0, ns_asymmetry=0, travel_angle_degrees=12, travel_speed_mm_per_min=450, timestamp_ms=i*10))
  a = e.push_frame(FrameInput(frame_index=60, amps=0.0, ns_asymmetry=0, travel_angle_degrees=12, travel_speed_mm_per_min=450, timestamp_ms=600))
  assert a is not None and a.rule_triggered == 'crater_crack', 'crater_crack must fire on abrupt 150A->0A after 600ms arc-on'
  print('OK')
  "`
  - **Pass:** Exit 0, prints OK
  - **Fail:** AssertionError or a is None → crater rule or arming logic broken

---

- [ ] 🟥 **Step 11: Implement oxide inclusion rule** — *Critical*

  **Idempotent:** Yes.

  **Re-Read Gate:**
  - `grep -n 'rule_triggered="crater_crack"' backend/realtime/alert_engine.py` → 1 match (use single quotes)
  - `grep -n '_suppress_oxide_until' backend/realtime/alert_engine.py` → 2 matches (one in __init__, one in Rule 4 block; confirms Step 8 landed)

  **Self-Contained Rule:** Oxide fires when travel_angle < 0 and not suppressed. When porosity fires, we already set _suppress_oxide_until. Oxide also needs its own suppression when it fires alone.

  ```python
  # Rule 7: Oxide inclusion (spike) — standalone negative angle
  if now_ms >= self._suppress_oxide_until:
      if frame.travel_angle_degrees is not None and frame.travel_angle_degrees < 0:
          candidates.append((7, "warning", AlertPayload(
              frame_index=frame.frame_index,
              rule_triggered="oxide_inclusion",
              severity="warning",
              message="Oxide inclusion risk: argon trailing (negative travel angle)",
              correction="Maintain push angle; avoid dragging torch",
              timestamp_ms=now_ms,
          )))
          self._suppress_oxide_until = now_ms + self._suppression_ms
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/alert_engine.py
  git commit -m "step 11: implement oxide inclusion rule"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -c "
  from realtime.alert_engine import AlertEngine
  from realtime.alert_models import FrameInput
  e = AlertEngine('config/alert_thresholds.json')
  a = e.push_frame(FrameInput(frame_index=0, travel_angle_degrees=-3, travel_speed_mm_per_min=300, ns_asymmetry=0, timestamp_ms=0))
  assert a is not None and a.rule_triggered == 'oxide_inclusion', 'oxide_inclusion must fire when travel_angle negative'
  print('OK')
  "`
  - **Pass:** Exit 0, prints OK
  - **Fail:** AssertionError → oxide rule or suppression broken

---

- [ ] 🟥 **Step 12: Implement undercut rule** — *Critical*

  **Idempotent:** Yes.

  **Re-Read Gate:**
  - `grep -n 'rule_triggered="oxide_inclusion"' backend/realtime/alert_engine.py` → 1 match

  **Known limitation:** Current mock peaks ~195A; undercut threshold 210A. Unit-test only. No mock scenario.

  **Self-Contained Rule:**

  ```python
  # In __init__: self._suppress_undercut_until = 0.0, self._warned_amps_missing_undercut = False

  # Rule 8: Undercut (spike)
  if frame.amps is None:
      if not self._warned_amps_missing_undercut:
          logger.warning("undercut requires amps; skipping (frame_index=%d)", frame.frame_index)
          self._warned_amps_missing_undercut = True
  elif now_ms >= self._suppress_undercut_until and frame.travel_speed_mm_per_min is not None:
      if frame.amps > self._cfg["undercut_amps_min"] and frame.travel_speed_mm_per_min > self._cfg["undercut_speed_min_mm_per_min"]:
          candidates.append((8, "critical", AlertPayload(
              frame_index=frame.frame_index,
              rule_triggered="undercut",
              severity="critical",
              message="Undercut risk: high current and high speed",
              correction="Reduce travel speed or current",
              timestamp_ms=now_ms,
          )))
          self._suppress_undercut_until = now_ms + self._suppression_ms
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/alert_engine.py
  git commit -m "step 12: implement undercut rule (unit-test only; mock does not reach threshold)"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -c "
  from realtime.alert_engine import AlertEngine
  from realtime.alert_models import FrameInput
  e = AlertEngine('config/alert_thresholds.json')
  a = e.push_frame(FrameInput(frame_index=0, amps=220.0, travel_speed_mm_per_min=550, ns_asymmetry=0, timestamp_ms=0))
  assert a is not None and a.rule_triggered == 'undercut', 'undercut must fire when amps>210 and speed>500'
  print('OK')
  "`
  - **Pass:** Exit 0, prints OK
  - **Fail:** AssertionError → undercut rule broken

---

- [ ] 🟥 **Step 13: Implement lack of fusion rule** — *Critical*

  **Idempotent:** Yes.

  **Re-Read Gate:**
  - `grep -n 'rule_triggered="undercut"' backend/realtime/alert_engine.py` → 1 match

  **Context:** Split behavior: low amps = sustained (re-fire every sustained_repeat_ms); high speed = spike (suppression_ms). Two independent conditions — use two `if` blocks, not if/elif, so both can fire on the same frame when novice runs cold AND fast. Use rule_triggered="lack_of_fusion_amps" and "lack_of_fusion_speed" for QA distinction.

  **Self-Contained Rule:**

  ```python
  # In __init__: self._suppress_lof_amps_until = 0.0, self._suppress_lof_speed_until = 0.0

  # Rule 9: Lack of fusion — low amps (sustained). Priority 9. Amps takes precedence when both fire.
  if frame.amps is not None and frame.amps < self._cfg["lack_of_fusion_amps_max"]:
      if now_ms >= self._suppress_lof_amps_until:
          candidates.append((9, "critical", AlertPayload(
              frame_index=frame.frame_index,
              rule_triggered="lack_of_fusion_amps",
              severity="critical",
              message="Lack of fusion risk: low current",
              correction="Increase current to 140+ A",
              timestamp_ms=now_ms,
          )))
          self._suppress_lof_amps_until = now_ms + self._cfg["sustained_repeat_ms"]
  # Rule 10: Lack of fusion — high speed (spike). Priority 10.
  if frame.travel_speed_mm_per_min is not None and frame.travel_speed_mm_per_min > self._cfg["lack_of_fusion_speed_max_mm_per_min"]:
      if now_ms >= self._suppress_lof_speed_until:
          candidates.append((10, "critical", AlertPayload(
              frame_index=frame.frame_index,
              rule_triggered="lack_of_fusion_speed",
              severity="critical",
              message="Lack of fusion risk: travel speed too high",
              correction="Reduce speed below 520 mm/min",
              timestamp_ms=now_ms,
          )))
          self._suppress_lof_speed_until = now_ms + self._suppression_ms
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/alert_engine.py
  git commit -m "step 13: implement lack of fusion rule (amps=sustained, speed=spike)"
  ```

  **✓ Verification Test:**
  - **Action:** amps=120 → lack_of_fusion_amps. speed=550 → lack_of_fusion_speed. Both branches fire independently; when both true on same frame, both can add candidates.
  - **Pass:** Both rule_triggered values fire with synthetic data

---

- [ ] 🟥 **Step 14: Implement burn-through rule** — *Critical*

  **Idempotent:** Yes.

  **Re-Read Gate:**
  - `grep -n 'rule_triggered="lack_of_fusion_' backend/realtime/alert_engine.py` → 2 matches (amps and speed)

  **Known limitation:** Mock peaks ~195A; threshold 220A. Unit-test only.

  **Self-Contained Rule:**

  ```python
  # In __init__: self._suppress_burn_through_until = 0.0, self._warned_amps_missing_burn_through = False

  # Rule 11: Burn-through (spike)
  if frame.amps is None:
      if not self._warned_amps_missing_burn_through:
          logger.warning("burn_through requires amps; skipping (frame_index=%d)", frame.frame_index)
          self._warned_amps_missing_burn_through = True
  elif frame.travel_speed_mm_per_min is not None:
      if now_ms >= self._suppress_burn_through_until:
          if frame.amps > self._cfg["burn_through_amps_min"] and frame.travel_speed_mm_per_min < self._cfg["burn_through_speed_max_mm_per_min"]:
              candidates.append((11, "critical", AlertPayload(
                  frame_index=frame.frame_index,
                  rule_triggered="burn_through",
                  severity="critical",
                  message="Burn-through risk: high current and low speed",
                  correction="Reduce current or increase travel speed",
                  timestamp_ms=now_ms,
              )))
              self._suppress_burn_through_until = now_ms + self._suppression_ms
  ```

  **Git Checkpoint:**
  ```bash
  git add backend/realtime/alert_engine.py
  git commit -m "step 14: implement burn-through rule (unit-test only; mock does not reach threshold)"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -c "
  from realtime.alert_engine import AlertEngine
  from realtime.alert_models import FrameInput
  e = AlertEngine('config/alert_thresholds.json')
  a = e.push_frame(FrameInput(frame_index=0, amps=230.0, travel_speed_mm_per_min=150, ns_asymmetry=0, timestamp_ms=0))
  assert a is not None and a.rule_triggered == 'burn_through', 'burn_through must fire when amps>220 and speed<200'
  print('OK')
  "`
  - **Pass:** Exit 0, prints OK
  - **Fail:** AssertionError → burn_through rule broken

---

### Phase 3 — Tests and Regression

**Goal:** Unit tests for defect rules; regression guard with defined partial-pass criteria.

---

- [ ] 🟥 **Step 15: Add unit tests for defect rules** — *Non-critical*

  **Idempotent:** Yes.

  **Self-Contained Rule:** Add tests to `backend/tests/test_alert_engine.py`:
  - test_porosity_fires_when_drag_and_low_speed
  - test_porosity_does_not_fire_when_angle_positive
  - test_arc_instability_skips_when_volts_none (caplog asserts exactly one warning, not per-frame)
  - test_crater_crack_fires_on_abrupt_drop (sequence: 60 frames 150A, then 0)
  - test_crater_crack_does_not_fire_when_not_armed (5 frames 150A then 0 → None)
  - test_oxide_inclusion_fires_when_angle_negative
  - test_oxide_suppressed_when_porosity_fires (angle<0 and speed<250 fires porosity; oxide does not fire same frame)
  - test_undercut_fires_when_high_amps_and_speed
  - test_lack_of_fusion_fires_on_low_amps (rule_triggered lack_of_fusion_amps)
  - test_lack_of_fusion_fires_on_high_speed (rule_triggered lack_of_fusion_speed)
  - test_burn_through_fires_when_high_amps_low_speed

  **Git Checkpoint:**
  ```bash
  git add backend/tests/test_alert_engine.py
  git commit -m "step 15: add unit tests for defect rules"
  ```

  **✓ Verification Test:**
  - **Action:** `cd backend && python -m pytest tests/test_alert_engine.py -v`
  - **Pass:** All tests pass

---

- [ ] 🟥 **Step 16: Regression guard** — *Non-critical*

  **Idempotent:** Yes.

  **Partial-pass criteria (current mock, before Session 1):**

  | Rule | Verifiable with current mock? | Fallback |
  |------|-------------------------------|----------|
  | Rule 1–3 | Yes | Existing tests pass |
  | Porosity | No (mock travel_angle ≥ 5) | Unit test with synthetic FrameInput |
  | Arc instability | Unlikely (mock ~22V) | Unit test |
  | Crater crack | Yes — novice 120ms arc-off; expert stitch boundaries | Expect false positives on expert stitch until Session 1 adds ramp-down. Do not treat expert crater_crack alerts as implementation failures. |
  | Oxide inclusion | No (same as porosity) | Unit test |
  | Undercut | No (mock < 210A) | Unit test only |
  | Lack of fusion | Speed branch may fire on expert (560 > 520) | Use 520 threshold; document if expert still fires |
  | Burn-through | No (mock < 220A) | Unit test only |

  **Action:**
  - Run `cd backend && python -m pytest tests/ -v` — test count ≥ pre-flight baseline
  - Run `cd backend && timeout 5 python -m scripts.simulate_realtime --mode novice --frames 200 --output console 2>&1` — no crash
  - Run `cd backend && timeout 5 python -m scripts.simulate_realtime --mode expert --frames 200 --output console 2>&1` — no crash

  **✓ Verification Test:**
  - **Pass:** All pytest pass; both simulate_realtime modes run without traceback
  - **Known:** Expert stitch boundaries may trigger crater_crack; lack_of_fusion speed may fire on expert 560 — document, do not block

---

## Regression Guard

**Systems at risk:**
- Alert engine: push_frame, candidate ordering, suppression
- get_session_alerts, simulate_realtime

**Regression verification:**

| System | Pre-change | Post-change |
|--------|------------|-------------|
| Rule 1–3 | Existing tests pass | test_rule1_*, test_frame_buffer pass |
| Defect rules | N/A | Unit tests pass per Step 15 |
| simulate_realtime | Runs | Runs without traceback |
| get_session_alerts | Returns alerts | Returns alerts; new rules may add more |

**Test count:** Must be ≥ pre-flight baseline.

---

## Rollback Procedure

Revert commits in reverse order (most recent first). Each revert creates a new commit that undoes one step.

**Guard:** Count commits since plan start before running. If you are mid-session, reverting 15 times will corrupt unrelated work.

```bash
# Record first plan commit before Step 1: <FIRST_PLAN_COMMIT>
# Before reverting, count: git log --oneline <FIRST_PLAN_COMMIT>..HEAD | wc -l
# Only revert that many: N=$(git log --oneline <FIRST_PLAN_COMMIT>..HEAD | wc -l)
# for i in $(seq 1 $N); do git revert --no-edit HEAD; done
```

Or, if all 15 steps are committed: `for i in $(seq 1 15); do git revert --no-edit HEAD; done`

Do not use `git revert HEAD~15..HEAD` — that reverts in forward order and causes conflicts.

---

## Pre-Flight Checklist

| Phase | Check | Status |
|-------|-------|--------|
| Pre-flight | Clarification Gate complete | ⬜ |
| | Baseline snapshot captured | ⬜ |
| | Lines after "if not candidates" confirmed | ⬜ |
| Phase 1 | Step 1–5 verifications pass | ⬜ |
| Phase 2 | Step 6–14 verifications pass | ⬜ |
| Phase 3 | Step 15–16 verifications pass | ⬜ |

---

## Risk Heatmap

| Step | Risk | Mitigation | Idempotent |
|------|------|------------|------------|
| 1–5 | Low | Additive only | Yes |
| 6–7 | Medium | Buffer logic; Step 7 confirms Step 6 | Yes |
| 8–14 | High (context drift) | Re-read gate before each edit | Yes |
| 15–16 | Low | Tests only | Yes |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Porosity | Fires when angle<0 and speed<250 | Unit test |
| Arc instability | Fires when V<19.5 sustained >500ms | Unit test |
| Crater crack | Fires on abrupt amps→0; arms after 500ms arc-on | Unit test; no fire on short arc |
| Oxide inclusion | Fires when angle<0; suppressed when porosity fires | Unit test |
| Undercut | Fires when amps>210 and speed>500 | Unit test (mock does not reach) |
| Lack of fusion | amps<140 sustained; speed>520 spike; rule_triggered lack_of_fusion_amps / lack_of_fusion_speed | Unit test; 520 avoids expert 380–560 |
| Burn-through | Fires when amps>220 and speed<200 | Unit test (mock does not reach) |
| Rule 1–3 | Unchanged | Existing tests pass |
| simulate_realtime | Runs with volts/amps | No crash |
| get_session_alerts | Passes volts/amps | No crash |
