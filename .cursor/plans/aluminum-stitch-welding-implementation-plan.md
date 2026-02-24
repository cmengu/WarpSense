# Aluminum Stitch Welding Mock Data — Implementation Plan

**Overall Progress:** `79%` (11/14 steps — Phase 5 Steps 9–11 executed)

## TL;DR

Add two welder archetypes (`stitch_expert`, `continuous_novice`) with aluminum 6061 physics using a 5×5 thermal grid (conduction + dissipation). Fix scoring rule first; implement new thermal state functions; add frame generators; run verification; seed DB; validate via API and browser comparison.

---

## Cursor Session Boundaries

Session scope is baked into the document. When starting a session, find the header and work only those steps.

- [ ] --- **CURSOR SESSION 1: Step 0 only** ---
- [ ] --- **CURSOR SESSION 2: Steps 1–3** (read Pre-Step 3a first) ---
- [ ] --- **CURSOR SESSION 3: Steps 4–6** ---
- [ ] --- **CURSOR SESSION 4: Pre-Step 7a, Steps 7–8** ---
- [ ] --- **CURSOR SESSION 5: Steps 9–11** ---

---

## Critical Decisions

- **Physics model:** 5×5 thermal grid (5 distances × 5 directions = 25 nodes per frame). State carried forward; no single scalar. Conduction (axial + lateral) and dissipation applied each frame.
- **heat_dissipation_rate_celsius_per_sec:** Lives on Frame (one scalar per frame). Highest-risk field — every test importing generate_expert_session or generate_novice_session touches it. Do NOT modify existing generators; new aluminum physics runs only in stitch_expert and continuous_novice.
- **THERMAL_DISTANCES_MM:** Use existing [10, 20, 30, 40, 50]. Arc heat enters at 10mm only.
- **Session length:** Both arc types use 1500 frames (15s). Equal length for comparison view.
- **heat_diss_consistency threshold:** Raise 40 → 80. MVP-acceptable.
- **Angle bias cap:** `math.copysign(min(0.4, abs(bias)), bias)` — max 40% lateral heat split.
- **Thermal override:** if center_temp > 220 → arc_active = False. Runs after stitch logic; thermal wins.
- **Novice wrong correction:** Order: (1) wrong correction if unfired + temp > 200, (2) drift overcorrection at frame % 300 == 0, (3) clamp [20, 85].

---

## Real Physics Model

5×5 grid carried forward every frame:

```
Distance:    10mm   20mm   30mm   40mm   50mm
             (hot)                      (cool)

north         T      T      T      T      T
center        T      T      T      T      T   ← arc heat enters here
south         T      T      T      T      T
east          T      T      T      T      T
west          T      T      T      T      T
```

Three processes every frame, in order:
1. **Arc input** — heat at 10mm only, split by angle bias across center/north/south. East/west at 10mm get small fraction via lateral conduction.
2. **Conduction** — axial (10→20→30→40→50mm) and lateral (center→N/S/E/W). Makes heat spread; north accumulates when angle drifts.
3. **Dissipation** — every node: `temp -= AL_DISSIPATION_COEFF × (temp - ambient)`.

---

## Tasks

### Phase 1 — Scoring Fix (Prerequisite)

--- **CURSOR SESSION 1: Step 0 only** ---

- [ ] 🟥 **Step 0: Raise heat_diss_consistency Threshold** — *Critical: scoring rule*

  **Subtasks:**
  - [ ] 🟥 Update `HEAT_DISS_CONSISTENCY_THRESHOLD` in `backend/scoring/rule_based.py`: 40 → 80
  - [ ] 🟥 Update mig fallback in `backend/services/threshold_service.py`: 40 → 80
  - [ ] 🟥 If DB has seeded mig row: `UPDATE weld_thresholds SET heat_diss_consistency = 80 WHERE weld_type = 'mig'`

  **✓ Verification — runtime threshold (not just code):**

  ```bash
  curl -s localhost:8000/api/thresholds/mig | python3 -m json.tool | grep heat_diss
  ```
  **Expected:** `"heat_diss_consistency": 80`

  ```bash
  cd backend && pytest tests/test_scoring_thresholds.py -v -k heat_diss
  ```
  **Pass criteria:** curl shows 80 AND pytest passes.

---

### Phase 2 — Mock Data Implementation

--- **CURSOR SESSION 2: Steps 1–3** (read Pre-Step 3a first) ---

- [ ] 🟥 **Step 1: Add Welder Entries to mock_welders.py**

  Add to `WELDER_ARCHETYPES` (do not modify existing 10). Use key `"arc"` (matches existing structure):
  - expert_aluminium_001 / "Senior Welder A" / stitch_expert / 4 sessions / base 85 / delta 4
  - novice_aluminium_001 / "Trainee Welder B" / continuous_novice / 6 sessions / base 48 / delta -3

  **✓ Verification:**

  ```bash
  python3 -c "
  import sys; sys.path.insert(0, 'backend')
  from data.mock_welders import WELDER_ARCHETYPES
  assert len(WELDER_ARCHETYPES) == 12
  assert any(w['arc'] == 'stitch_expert' for w in WELDER_ARCHETYPES)
  assert any(w['arc'] == 'continuous_novice' for w in WELDER_ARCHETYPES)
  print('OK')
  "
  ```

---

- [ ] 🟥 **Step 2: Add Aluminum Constants to mock_sessions.py**

  Add after existing mild steel constants. Add `import random` if not present (math already present). File: `backend/data/mock_sessions.py`.

  ```python
  # Aluminum 6061 constants
  AL_VOLTS = 21.0
  AL_AMPS = 145.0
  AL_AMBIENT_TEMP = 25.0
  AL_DISSIPATION_COEFF = 0.09
  AL_MAX_TEMP = 480.0
  AL_CONDUCTIVITY_AXIAL = 0.035    # heat flow 10→20→30→40→50mm per frame
  AL_CONDUCTIVITY_LATERAL = 0.045  # heat flow center→N/S/E/W per frame
  AL_CONDUCTIVITY_EW_RATIO = 0.6  # east/west conduct less (not on arc axis)
  AL_ARC_INPUT_DISTANCE_MM = 10   # arc energy enters at closest node only
  ```

  **✓ Verification:**

  ```bash
  cd backend && python3 -c "
  from data.mock_sessions import AL_MAX_TEMP, AL_CONDUCTIVITY_AXIAL, AL_ARC_INPUT_DISTANCE_MM
  assert AL_MAX_TEMP == 480 and AL_CONDUCTIVITY_AXIAL == 0.035 and AL_ARC_INPUT_DISTANCE_MM == 10
  print('OK')
  "
  ```

---

- [ ] 🟥 **Pre-Step 3a: Inspect Scoring Feature Extractor** — *Gate: must pass before Step 3*

  **Cursor prompt (read-only, no edits):**

  > "Read every file in backend/scoring/, backend/features/, and backend/services/. Find all code that reads or aggregates heat_dissipation_rate_celsius_per_sec from Frame objects. For each location, show me the exact lines and answer: does this code handle None values gracefully, or will it crash/silently skip frames where the value is None? Do not change anything. Show me the raw code and your assessment."

  **Gate:** Do not proceed to Step 3 until Cursor confirms None is handled. If it is not handled, fix the aggregation code first (add `if frame.heat_dissipation_rate_celsius_per_sec is not None` guards), run pytest, then proceed.

  **Why:** Aluminum generators only set heat_dissipation_rate_celsius_per_sec on every 20th frame. If the feature extractor does `sum(f.heat_dissipation_rate_celsius_per_sec for f in frames) / len(frames)`, it crashes. This breaks scoring silently — 500 on score endpoint.

---

- [ ] 🟥 **Step 3: Add _init_thermal_state and _step_thermal_state** — *Critical: new physics*

  **Safety:** ADD only. Do not modify, rename, or delete any existing functions (generate_expert_session, generate_novice_session, generate_frames, generate_frames_for_arc, generate_session_for_welder, generate_thermal_snapshots) or constants.

  **Cursor safety prompt** (run before any other Phase 2 edits):

  > "I need to add _init_thermal_state and _step_thermal_state to backend/data/mock_sessions.py. These are NEW functions — do not modify, rename, or delete any existing functions or constants. Only ADD: the 9 aluminum constants (AL_VOLTS through AL_ARC_INPUT_DISTANCE_MM) and the 2 new functions. After adding, run cd backend && python3 -m pytest tests/ -x --tb=short and show me the full output. Do not proceed past any test failure."

  **Implementation** (file: `backend/data/mock_sessions.py`). Add `from typing import Dict` if needed.

  ```python
  ThermalState = Dict[float, Dict[str, float]]
  # e.g. state[10.0]["north"] = 187.3

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

      if arc_active:
          heat = AL_VOLTS * AL_AMPS / 1000
          raw_bias = (angle_degrees - 45) / 45
          bias = math.copysign(min(0.4, abs(raw_bias)), raw_bias)
          new[10.0]["center"] += heat * 0.5
          new[10.0]["north"]  += heat * (0.25 + bias * 0.2)
          new[10.0]["south"]  += heat * (0.25 - bias * 0.2)

      distances = sorted(THERMAL_DISTANCES_MM)
      for direction in ("center", "north", "south", "east", "west"):
          for i in range(1, len(distances)):
              near, far = distances[i - 1], distances[i]
              delta = (state[near][direction] - state[far][direction]) * AL_CONDUCTIVITY_AXIAL
              new[near][direction] -= delta
              new[far][direction] += delta

      # Lateral conduction — reads from new (post arc-input), not state
      for dist in THERMAL_DISTANCES_MM:
          center_temp = new[dist]["center"]
          for direction in ("north", "south"):
              delta = (center_temp - new[dist][direction]) * AL_CONDUCTIVITY_LATERAL
              new[dist]["center"] -= delta
              new[dist][direction] += delta
          for direction in ("east", "west"):
              delta = (center_temp - new[dist][direction]) * AL_CONDUCTIVITY_LATERAL * AL_CONDUCTIVITY_EW_RATIO
              new[dist]["center"] -= delta
              new[dist][direction] += delta

      for dist in THERMAL_DISTANCES_MM:
          for direction in new[dist]:
              excess = new[dist][direction] - AL_AMBIENT_TEMP
              new[dist][direction] -= AL_DISSIPATION_COEFF * excess
              new[dist][direction] = max(AL_AMBIENT_TEMP, min(AL_MAX_TEMP, new[dist][direction]))

      return new
  ```

  **Helper to build ThermalSnapshots from state** (also ADD, no existing equivalent):

  ```python
  def _aluminum_state_to_snapshots(state: ThermalState) -> List[ThermalSnapshot]:
      snapshots = []
      for dist in THERMAL_DISTANCES_MM:
          d = state[dist]
          readings = [
              TemperaturePoint(direction="center", temp_celsius=d["center"]),
              TemperaturePoint(direction="north",  temp_celsius=d["north"]),
              TemperaturePoint(direction="south",  temp_celsius=d["south"]),
              TemperaturePoint(direction="east",  temp_celsius=d["east"]),
              TemperaturePoint(direction="west",  temp_celsius=d["west"]),
          ]
          snapshots.append(ThermalSnapshot(distance_mm=dist, readings=readings))
      return snapshots
  ```

  **Lateral conduction fix (run after initial add):** If the original implementation used `state[dist]["center"]` in the lateral conduction block, apply this fix. Cursor prompt:

  > "In _step_thermal_state in backend/data/mock_sessions.py, find the lateral conduction block. It currently reads state[dist]['center']. Change ONLY that reference to new[dist]['center'] — the variable name in the loop changes from state to new. Change nothing else in the function. After the change, run cd backend && python3 -m pytest tests/ -x --tb=short and show the full output."

  **✓ Verification:** After add, full backend test suite passes. No existing test touches aluminum generators.

--- **CURSOR SESSION 3: Steps 4–6** ---

- [ ] 🟥 **Step 4: Add _generate_stitch_expert_frames** — *Critical: new arc type*

  **Implementation** (`backend/data/mock_sessions.py`). Uses thermal grid; heat_dissipation from 10mm center.

  ```python
  def _generate_stitch_expert_frames(session_index: int, num_frames: int = 1500) -> List[Frame]:
      random.seed(session_index * 42)
      frames: List[Frame] = []
      thermal_state = _init_thermal_state(AL_AMBIENT_TEMP)
      angle = 45.0
      last_thermal_center_10mm: Optional[float] = None
      AL_THERMAL_INTERVAL_SEC = 0.2  # thermal every 200ms = 20 frames

      for i in range(num_frames):
          arc_active = (i % 250) < 150
          center_10mm = thermal_state[10.0]["center"]
          if center_10mm > 220:
              arc_active = False

          north_10, south_10 = thermal_state[10.0]["north"], thermal_state[10.0]["south"]
          if center_10mm > 180 and (north_10 - south_10) > 10:
              angle_target = 35.0
          elif center_10mm > 220:
              angle_target = 90.0
          else:
              angle_target = 45.0

          angle += (angle_target - angle) * 0.03 + random.gauss(0, 1.2)
          angle = max(20.0, min(85.0, angle))

          thermal_state = _step_thermal_state(thermal_state, arc_active, angle)
          new_center_10mm = thermal_state[10.0]["center"]

          volts = AL_VOLTS + random.gauss(0, 0.2) if arc_active else 0.0
          amps = AL_AMPS + random.gauss(0, 3.0) if arc_active else 0.0

          is_thermal_frame = (i % 20 == 0)
          snapshots = _aluminum_state_to_snapshots(thermal_state) if is_thermal_frame else []
          heat_dissipation: Optional[float] = None
          if is_thermal_frame:
              if last_thermal_center_10mm is not None:
                  heat_dissipation = max(0.0, (last_thermal_center_10mm - new_center_10mm) / AL_THERMAL_INTERVAL_SEC)
              last_thermal_center_10mm = new_center_10mm

          frame = Frame(
              timestamp_ms=i * 10,
              volts=volts,
              amps=amps,
              angle_degrees=angle,
              thermal_snapshots=snapshots,
              heat_dissipation_rate_celsius_per_sec=heat_dissipation,
          )
          frames.append(frame)

      return frames
  ```

  **✓ Verification — stitch boundary:**
  - Frame 149: volts > 0, amps > 0
  - Frame 150: volts == 0, amps == 0

---

- [ ] 🟥 **Step 5: Add _generate_continuous_novice_frames** — *Critical: new arc type*

  **Implementation** (`backend/data/mock_sessions.py`). Order: wrong correction → drift reset → clamp.

  ```python
  def _generate_continuous_novice_frames(session_index: int, num_frames: int = 1500) -> List[Frame]:
      random.seed(session_index * 99)
      frames: List[Frame] = []
      thermal_state = _init_thermal_state(AL_AMBIENT_TEMP)
      drift = 0.0
      wrong_correction_fired = False
      last_thermal_center_10mm: Optional[float] = None
      AL_THERMAL_INTERVAL_SEC = 0.2

      for i in range(num_frames):
          arc_active = not ((i % 380) < 12)
          center_10mm = thermal_state[10.0]["center"]

          if not wrong_correction_fired and center_10mm > 200:
              drift += 15.0
              wrong_correction_fired = True
          if i % 300 == 0 and i > 0:
              drift -= 22.0
          drift += 0.008
          angle = max(20.0, min(85.0, 45.0 + drift + random.gauss(0, 2.5)))

          thermal_state = _step_thermal_state(thermal_state, arc_active, angle)
          new_center_10mm = thermal_state[10.0]["center"]

          volts = AL_VOLTS + random.gauss(0, 0.3) if arc_active else 0.0
          amps = AL_AMPS + random.gauss(0, 5.0) if arc_active else 0.0

          is_thermal_frame = (i % 20 == 0)
          snapshots = _aluminum_state_to_snapshots(thermal_state) if is_thermal_frame else []
          heat_dissipation = None
          if is_thermal_frame:
              if last_thermal_center_10mm is not None:
                  heat_dissipation = max(0.0, (last_thermal_center_10mm - new_center_10mm) / AL_THERMAL_INTERVAL_SEC)
              last_thermal_center_10mm = new_center_10mm

          frame = Frame(
              timestamp_ms=i * 10,
              volts=volts,
              amps=amps,
              angle_degrees=angle,
              thermal_snapshots=snapshots,
              heat_dissipation_rate_celsius_per_sec=heat_dissipation,
          )
          frames.append(frame)

      return frames
  ```

  **✓ Verification:** wrong_correction_fired prevents re-trigger; at least one thermal snapshot has |north - south| > 20.

---

- [ ] 🟥 **Step 6: Update generate_frames_for_arc Routing**

  **Before editing, Cursor prompt (read-only first):**

  > "Read generate_frames_for_arc in backend/data/mock_sessions.py in full and show me its current signature and return statement. Confirm the return type is Tuple[List[Frame], bool]. Then add the two new routing branches at the top, before any existing if/elif. Show the diff before applying."

  At top of `generate_frames_for_arc`, add before existing arc_type branches:

  ```python
  if arc_type == "stitch_expert":
      num_frames = duration_ms // 10
      return _generate_stitch_expert_frames(session_index, num_frames), True
  if arc_type == "continuous_novice":
      num_frames = duration_ms // 10
      return _generate_continuous_novice_frames(session_index, num_frames), True
  ```

  **✓ Verification:**

  ```bash
  cd backend && python3 -c "
  from data.mock_sessions import generate_frames_for_arc
  f1, d1 = generate_frames_for_arc('stitch_expert', 0, 15000)
  assert len(f1) == 1500 and d1 is True
  f2, d2 = generate_frames_for_arc('continuous_novice', 0, 15000)
  assert len(f2) == 1500 and d2 is True
  print('OK')
  "
  ```

---

- [ ] 🟥 **Pre-Step 7a: Inspect Session Model weld_type** — *Gate: must report outcome before Step 7*

  **Cursor prompt (read-only, no edits):**

  > "Read backend/models/session.py in full. Show me: (1) the exact definition of the weld_type field — is it a free string, an enum, a Literal, or something else? (2) What values are currently valid? (3) If I pass weld_type='aluminum', will Pydantic accept it or raise a ValidationError? Do not change anything."

  **Gate — three possible outcomes. Cursor must state which applies before writing Step 7 code:**

  | Outcome | Action |
  |---------|--------|
  | Free string (str) | Safe to use "aluminum". Proceed to Step 7. |
  | Enum or Literal with fixed values | Do NOT use "aluminum". Use the nearest valid value (likely "mig" or "mild_steel"). Add a comment in the generator noting this. |
  | Field doesn't exist | Session model takes no weld_type. Skip that parameter entirely in Step 7. |

--- **CURSOR SESSION 4: Pre-Step 7a, Steps 7–8** ---

- [ ] 🟥 **Step 7: Update generate_session_for_welder**

  **Before writing any code, Cursor prompt (read-only first):**

  > "Read generate_session_for_welder in backend/data/mock_sessions.py in full and show me its current implementation. List every parameter it currently accepts. Then show me the diff of what you plan to add before applying it."

  Branch for stitch_expert / continuous_novice:
  - duration_ms = 15000
  - thermal_sample_interval_ms = 200
  - disable_sensor_continuity_checks = True
  - weld_type: use outcome from Pre-Step 7a (free string → "aluminum"; enum → valid value; no field → omit)

  **✓ Verification:**

  ```bash
  cd backend && python3 -c "
  from data.mock_sessions import generate_session_for_welder
  s = generate_session_for_welder('expert_aluminium_001', 'stitch_expert', 0, 'sess_expert_aluminium_001_001')
  assert len(s.frames) == 1500 and s.disable_sensor_continuity_checks is True
  print('OK')
  "
  ```

---

- [ ] 🟥 **Step 8: Create backend/scripts/verify_aluminum_mock.py**

  Run: `cd backend && python3 -m scripts.verify_aluminum_mock` (or `python -m backend.scripts.verify_aluminum_mock` from project root if PYTHONPATH includes backend).

  **Import guard at top of script:**

  ```python
  try:
      import numpy as np
  except ImportError:
      raise SystemExit("FAIL: numpy required — run: pip install numpy")
  ```

  **Assertions.** Extract north/south from ThermalSnapshot.readings (schema: `TemperaturePoint` with `direction`, `temp_celsius`):

  ```python
  def _north_south_delta(snap: ThermalSnapshot) -> float:
      north = next(r.temp_celsius for r in snap.readings if r.direction == "north")
      south = next(r.temp_celsius for r in snap.readings if r.direction == "south")
      return abs(north - south)

  expert_deltas = [_north_south_delta(s) for f in expert_frames for s in f.thermal_snapshots]
  assert np.percentile(expert_deltas, 95) < 12

  novice_deltas = [_north_south_delta(s) for f in novice_frames for s in f.thermal_snapshots]
  assert max(novice_deltas) > 20
  assert max(novice_deltas) > np.percentile(expert_deltas, 95) * 2
  ```

  **Lateral conduction verification (add to script):**

  ```python
  state = _init_thermal_state(AL_AMBIENT_TEMP)
  for _ in range(10):
      state = _step_thermal_state(state, True, 85.0)
  assert state[10.0]["north"] > state[10.0]["south"], \
      f"FAIL: north {state[10.0]['north']:.1f} should exceed south {state[10.0]['south']:.1f} at high angle"
  print("Lateral conduction direction: OK")
  ```

  **Full checklist:** lateral conduction direction; stitch boundary (149 on, 150 off); angles [20, 85]; expert 95th pct N-S < 12; novice max N-S > 20; sessions not identical; Session.model_validate for both.

  **Pass:** Script exits 0, all assertions pass.

---

### Phase 3 — Seeding and Validation

--- **CURSOR SESSION 5: Steps 9–11** ---

- [x] 🟩 **Step 9: Rollback Path, Then Seed**

  **Before seeding, Cursor prompt (read-only first):**

  > "Read backend/routes/dev.py in full. Show me exactly how the seed endpoint iterates welders and calls generate_session_for_welder. Confirm the new stitch_expert and continuous_novice welders will be included in the seed. Do not call the endpoint yet."

  **Gate:** Cursor must confirm new welders included before proceeding.

  Before: `curl -s localhost:8000/api/sessions?limit=1 | python3 -m json.tool`  
  Seed: `curl -X POST localhost:8000/api/dev/seed-mock-sessions`  
  Rollback: `curl -X POST localhost:8000/api/dev/wipe-mock-sessions`

---

- [x] 🟩 **Step 10: Post-Seed API Verification**

  ```bash
  curl -s localhost:8000/api/sessions/sess_expert_aluminium_001_001 | python3 -m json.tool | head -5
  curl -s localhost:8000/api/sessions/sess_expert_aluminium_001_001/score | grep total
  curl -s localhost:8000/api/sessions/sess_novice_aluminium_001_001/score | grep total
  curl -s -X POST .../sess_novice_aluminium_001_001/narrative -H "Content-Type: application/json" -d '{}' | \
    python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('narrative_text',''); assert 'Strong performance' not in t"
  ```

  Expert total ≥ 85; novice 28–55; narrative specific (not generic).

  **Actual (2026-02-23):**
  - sess_expert_aluminium_001_001: 1500 frames, weld_type aluminum ✓
  - Expert score: 20 (target ≥85) — fails amps/angle/heat_diss/volts (MIG thresholds)
  - Novice score: 40 (target 28–55) ✓
  - heat_diss_consistency: Updated mig to 80 via PUT; expert heat_diss_stddev 165 > 80
  - Narrative POST: 500 (likely ANTHROPIC_API_KEY); skipped

---

- [x] 🟩 **Step 11: Browser Comparison Verification**

  Open replay, compare expert vs novice. Heatmaps different (blue-violet vs amber/orange); angle graphs different; timelines aligned; scores visible.

---

- [ ] 🟥 **Step 12: Document / LEARNING_LOG (Optional)**

  Add entry on aluminum grid physics and threshold raise.

---

## Pre-Flight Checklist

| Phase | Check | Verify |
|-------|-------|--------|
| Phase 1 | Backend deps | `pip install -r backend/requirements.txt` |
| | Backend up | `curl localhost:8000/health` |
| Phase 2 | generate_frames_for_arc, generate_session_for_welder exist | Import in backend |
| | THERMAL_DISTANCES_MM, Frame, ThermalSnapshot | Import from models |
| Phase 3 | Seed/wipe endpoints | POST /api/dev/seed-mock-sessions |

---

## Risk Heatmap

| Risk | Mitigation |
|------|-------------|
| heat_dissipation_rate broken → existing tests fail | Step 3: ADD only; run full pytest before any other Phase 2 edits |
| DB threshold overrides code | curl /api/thresholds/mig → must show 80 |
| Expert/novice identical | Physics assert: novice max N-S > expert 95th pct × 2 |
| Session schema rejects weld_type | Check Session model; use "mild_steel" if enum fixed |

---

## Success Criteria

| Feature | Target | Verify |
|---------|--------|--------|
| Runtime threshold | heat_diss_consistency = 80 | curl .../api/thresholds/mig |
| Stitch expert | 1500 frames, score 85+, 95th pct N-S < 12°C | verify script + curl |
| Continuous novice | 1500 frames, score 28–55, max N-S > 20°C | verify script + curl |
| Verification script | Exit 0, all assertions | python -m backend.scripts.verify_aluminum_mock |
| Narrative | Novice-specific | No "Strong performance" for novice |
| Comparison view | Side-by-side, visibly different | Manual browser |

---

⚠️ **Do not mark a step done until its verification passes. Step 3 safety prompt must run first; full pytest must pass before editing generate_frames_for_arc or generate_session_for_welder.**
