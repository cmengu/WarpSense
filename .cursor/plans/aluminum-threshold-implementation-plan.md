# Aluminum Threshold Implementation Plan

**Overall Progress:** `100%`

## TLDR

Wire the scoring layer to use dedicated aluminum thresholds. Frontend and physics exist; this is model constants, DB seeding, and verification. No new features — pure wiring. Expert score ≥ 85, novice 28–55.

---

## Critical Decisions

- **process_type vs weld_type:** Scoring uses `process_type`, not `weld_type`. Mock sessions must pass `process_type="aluminum"` when `is_aluminum_arc` so scoring picks aluminum thresholds.
- **Threshold values:** All values verified against mock generator output (extract_features). Stitch welding produces amps/volts/heat_diss variance by design; thresholds must bracket expert (pass) and fail novice on angle/thermal/amps.
- **volts_stability_warning = 25:** Stitch has volts 0 (arc off) and ~21 (arc on) → volts_range ≈ 21. 2.5 would fail both; 25 accommodates.
- **Seed approach:** New Alembic migration (010_add_aluminum_threshold) — production-ready. Alternative: extend dev seed to upsert aluminum row (dev-only).
- **Step 2 + 3 ordering:** Do not restart server between Step 2 (add aluminum to KNOWN_PROCESS_TYPES) and Step 3 (constants + seed). Step 2 makes missing row a crash; Step 3 prevents it.

---

## Tasks

### Phase 0 — Prerequisite

**Goal:** Aluminum sessions use aluminum thresholds when scored.

- [ ] 🟥 **Step 0: Set process_type in generate_session_for_welder**

  **Context:** Scoring calls `get_thresholds(db, session.process_type)`. Without this, aluminum sessions default to `process_type="mig"` and get MIG thresholds regardless of DB row.

  **Code snippet:**
  ```python
  # backend/data/mock_sessions.py — in generate_session_for_welder return Session(...)
  process_type="aluminum" if is_aluminum_arc else "mig",
  ```

  **What it does:** Adds process_type to Session; aluminum arcs get process_type="aluminum".

  **Why this approach:** Single change at session construction; flows through seed, API, scoring.

  **Assumptions:** WELDER_ARCHETYPES includes expert_aluminium_001, novice_aluminium_001 with arc stitch_expert/continuous_novice.

  **Risks:** None if archetypes exist; session model already has process_type field with default.

  **Subtasks:**
  - [ ] 🟥 Add `process_type="aluminum" if is_aluminum_arc else "mig"` to Session() in generate_session_for_welder
  - [ ] 🟥 Run `cd backend && python3 -m pytest tests/test_mock_welders.py tests/test_extract_features.py -x --tb=short`

  **✓ Verification Test:**

  **Action:** Run `cd backend && python3 -c "
  from data.mock_sessions import generate_session_for_welder
  s = generate_session_for_welder('expert_aluminium_001','stitch_expert',0,'sess_test')
  assert s.process_type == 'aluminum'
  print('OK')
  "`

  **Expected Result:** No AssertionError; prints OK.

  **Pass Criteria:** process_type is "aluminum" for stitch_expert sessions.

  **Common Failures:** AssertionError → Session() call missing process_type arg or wrong branch.

---

### Phase 1 — Model + Constants

**Goal:** WeldTypeThresholds allows aluminum thermal values; threshold service knows aluminum.

- [ ] 🟥 **Step 1: Raise thermal_symmetry cap in WeldTypeThresholds**

  **Subtasks:**
  - [ ] 🟥 In `backend/models/thresholds.py`, change `thermal_symmetry_warning_celsius` and `thermal_symmetry_critical_celsius` from `le=200` → `le=500`
  - [ ] 🟥 Run `cd backend && python3 -m pytest tests/ -x --tb=short`

  **✓ Verification Test:**

  **Action:** Run `cd backend && python3 -c "
  from models.thresholds import WeldTypeThresholds
  t = WeldTypeThresholds(weld_type='aluminum', angle_target_degrees=45.0, angle_warning_margin=20.0, angle_critical_margin=35.0, thermal_symmetry_warning_celsius=250.0, thermal_symmetry_critical_celsius=400.0, amps_stability_warning=18.0, volts_stability_warning=25.0, heat_diss_consistency=250.0)
  print('OK')
  "`

  **Pass Criteria:** No ValidationError; prints OK.

  **Common Failures:** ValidationError → le=200 still in place or wrong field.

---

- [ ] 🟥 **Step 2: Add aluminum to KNOWN_PROCESS_TYPES**

  **Context:** get_thresholds treats unknown process_type as fallback-to-MIG; known-but-missing as crash. Adding aluminum makes missing row a crash until Step 3 seeds it.

  **Code snippet:**
  ```python
  # backend/services/threshold_service.py
  KNOWN_PROCESS_TYPES = frozenset({"mig", "tig", "stick", "flux_core", "aluminum"})
  ```

  **What it does:** Aluminum is now a known type; missing DB row will raise ValueError instead of silently using MIG.

  **Why this approach:** Fail-fast; prevents silent fallback to wrong thresholds.

  **Risks:** Any aluminum route/score request crashes until Step 3+4 complete. **Do not restart server between Step 2 and Step 3.**

  **Subtasks:**
  - [ ] 🟥 Add `"aluminum"` to KNOWN_PROCESS_TYPES
  - [ ] 🟥 Run `cd backend && python3 -m pytest tests/ -x --tb=short`

  **✓ Verification Test:**

  **Action:** Run `cd backend && python3 -c "
  from services.threshold_service import KNOWN_PROCESS_TYPES
  assert 'aluminum' in KNOWN_PROCESS_TYPES
  print('OK')
  "`

  **Pass Criteria:** "aluminum" in frozenset.

---

### Phase 2 — Seeding

**Goal:** Aluminum row exists in weld_thresholds; GET /api/thresholds/aluminum returns aluminum values.

- [ ] 🟥 **Step 3a: Pre-Step 3 threshold verification**

  **Subtasks:**
  - [ ] 🟥 Run `extract_features` on aluminum expert + novice sessions (angle_target=45)
  - [ ] 🟥 Confirm: expert features ≤ proposed thresholds; novice at least one of angle/thermal/amps exceeds
  - [ ] 🟥 Optionally extend `verify_aluminum_mock.py` to assert this

  **✓ Verification Test:**

  **Action:** Run backend with venv, then:
  ```python
  from data.mock_sessions import generate_session_for_welder
  from features.extractor import extract_features
  expert = generate_session_for_welder('expert_aluminium_001','stitch_expert',0,'s1')
  expert = expert.model_copy(update={'process_type':'aluminum'})
  novice = generate_session_for_welder('novice_aluminium_001','continuous_novice',0,'s2')
  novice = novice.model_copy(update={'process_type':'aluminum'})
  ef, nf = extract_features(expert, 45), extract_features(novice, 45)
  # Expert: all <= thresh; Novice: angle or thermal or amps > thresh
  thresh = {'amps':18,'angle':20,'thermal':15,'heat_diss':250,'volts':25}
  assert ef['amps_stddev']<=18 and ef['volts_range']<=25 and ef['heat_diss_stddev']<=250
  assert nf['angle_max_deviation']>20 or nf['north_south_delta_avg']>15 or nf['amps_stddev']>18
  print('OK')
  ```

  **Pass Criteria:** No assertion failures.

---

- [ ] 🟥 **Step 3b: Add ALUMINUM_THRESHOLDS constants**

  **Context:** Fallback and seed source. Must match threshold verification table.

  **Code snippet:**
  ```python
  # backend/services/threshold_service.py — after MIG fallback dict
  ALUMINUM_THRESHOLDS = {
      "weld_type": "aluminum",
      "angle_target_degrees": 45.0,
      "angle_warning_margin": 20.0,
      "angle_critical_margin": 35.0,
      "thermal_symmetry_warning_celsius": 15.0,
      "thermal_symmetry_critical_celsius": 35.0,
      "amps_stability_warning": 18.0,
      "volts_stability_warning": 25.0,
      "heat_diss_consistency": 250.0,
  }
  ```

  **What it does:** Defines aluminum threshold values; used by fallback and seed.

  **Assumptions:** Step 3a verified values bracket mock output.

  **Subtasks:**
  - [ ] 🟥 Add ALUMINUM_THRESHOLDS after MIG constants
  - [ ] 🟥 Wire ALUMINUM_THRESHOLDS into _load_all fallback (when cache empty and no rows) if desired — or rely on migration seed

  **✓ Verification Test:**

  **Action:** Import and check dict exists with weld_type="aluminum", heat_diss_consistency=250, volts_stability_warning=25.

  **Pass Criteria:** Dict present, values match.

---

- [ ] 🟥 **Step 4: Seed aluminum row into weld_thresholds**

  **Context:** Database must have aluminum row. Migration is production-ready; dev seed upsert is alternative.

  **Code snippet (Alembic migration):**
  ```python
  # backend/alembic/versions/010_add_aluminum_threshold.py
  revision = "010_add_aluminum_threshold"
  down_revision = "009_certifications"

  def upgrade():
      op.execute(sa.text(
          "INSERT INTO weld_thresholds (weld_type, angle_target_degrees, angle_warning_margin, "
          "angle_critical_margin, thermal_symmetry_warning_celsius, thermal_symmetry_critical_celsius, "
          "amps_stability_warning, volts_stability_warning, heat_diss_consistency) "
          "VALUES ('aluminum', 45, 20, 35, 15, 35, 18, 25, 250)"
      ))

  def downgrade():
      op.execute(sa.text("DELETE FROM weld_thresholds WHERE weld_type = 'aluminum'"))
  ```

  **What it does:** Adds aluminum row to weld_thresholds.

  **Why this approach:** Replicable, versioned, production-safe.

  **Risks:** If DB already ran migrations, must run `alembic upgrade head`. Fresh DB gets it on initial migrate.

  **Subtasks:**
  - [ ] 🟥 Create `010_add_aluminum_threshold.py`
  - [ ] 🟥 Run `alembic upgrade head` (or ensure migrations applied)
  - [ ] 🟥 Run `POST /api/dev/seed-mock-sessions` (backend with ENV=development)
  - [ ] 🟥 Run curl verification (Step 4 verify block from issue)

  **✓ Verification Test:**

  **Action:**
  1. Start backend (ENV=development)
  2. `curl -s localhost:8000/api/thresholds/aluminum | python3 -m json.tool`
  3. `curl -s localhost:8000/api/thresholds/aluminum | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['weld_type']=='aluminum' and d['heat_diss_consistency']==250.0; print('OK')"`

  **Expected Result:** JSON with weld_type aluminum, heat_diss_consistency 250, angle_warning_margin 20, volts_stability_warning 25.

  **Pass Criteria:** All assertions pass. If MIG values returned, row didn't seed — check migration ran.

  **Common Failures:** MIG values → fallback; migration not run or aluminum row missing. 404/500 → server not running or route misconfigured.

---

### Phase 3 — Score Verification

**Goal:** Expert ≥ 85, novice 28–55; narrative not generic.

- [ ] 🟥 **Step 5: Verify scores**

  **Subtasks:**
  - [ ] 🟥 `curl -s localhost:8000/api/sessions/sess_expert_aluminium_001_001/score` → total ≥ 85
  - [ ] 🟥 `curl -s localhost:8000/api/sessions/sess_novice_aluminium_001_001/score` → 28 ≤ total ≤ 55
  - [ ] 🟥 If expert < 85: inspect rule_results, adjust failing rule threshold only, re-seed, re-check
  - [ ] 🟥 If novice > 55: thresholds too loose; tighten angle or thermal

  **✓ Verification Test:**

  **Action:** Call score endpoints; parse JSON for `total` and `rule_results`.

  **Pass Criteria:** Expert total ≥ 85; novice total in [28, 55].

  **Common Failures:** Expert < 85 → check which rule failed (heat_diss, amps, volts, angle, thermal). Novice > 55 → angle/thermal thresholds too loose.

---

- [ ] 🟥 **Step 6: Narrative check**

  **Subtasks:**
  - [ ] 🟥 `curl -X POST localhost:8000/api/sessions/sess_novice_aluminium_001_001/narrative -H "Content-Type: application/json" -d '{}'`
  - [ ] 🟥 Assert narrative_text does not contain "Strong performance" (generic)

  **✓ Verification Test:**

  **Action:** POST narrative; read narrative_text.

  **Pass Criteria:** Narrative present; not generic positive template.

---

### Phase 4 — Frontend Spot Check

**Goal:** Replay and compare UI show correct labels and scores.

- [ ] 🟥 **Step 7: Browser verification**

  **Subtasks:**
  - [ ] 🟥 Open `http://localhost:3000/replay/sess_expert_aluminium_001_001` → weld type label "Aluminum"
  - [ ] 🟥 Open `http://localhost:3000/replay/sess_novice_aluminium_001_001` → Compare → select expert → ScorePanel shows "ALUMINUM" spec, scores visible

  **✓ Verification Test:**

  **Action:** Load pages, inspect metadata label and ScorePanel.

  **Pass Criteria:** "Aluminum" (not "ALUMINUM" or blank) in replay metadata; ScorePanel shows "ALUMINUM" spec when comparing.

  **Common Failures:** Blank label → session.weld_type missing or getWeldTypeLabel not used. Wrong spec → process_type not aluminum or threshold lookup failing.

---

## Pre-Flight Checklist

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| Phase 0 | mock_sessions, mock_welders | expert_aluminium_001, novice_aluminium_001 in WELDER_ARCHETYPES | ⬜ |
| Phase 1 | models.thresholds, threshold_service | Import WeldTypeThresholds, KNOWN_PROCESS_TYPES | ⬜ |
| Phase 2 | DB + migrations | `alembic current` shows 010; weld_thresholds has aluminum row | ⬜ |
| Phase 3 | Backend running, sessions seeded | GET /api/sessions/sess_expert_aluminium_001_001 returns 200 | ⬜ |
| Phase 4 | Frontend running | localhost:3000 loads | ⬜ |

---

## Risk Heatmap

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|----------------------|
| Phase 0 | 🟢 **10%** | process_type typo | Step 0 verification fails |
| Phase 1 | 🟢 **10%** | le=200 not updated | WeldTypeThresholds ValidationError |
| Phase 2 | 🟡 **40%** | Server restart between Step 2 and 3 → crash on aluminum request | GET /thresholds/aluminum returns 500 |
| Phase 2 | 🟡 **30%** | Migration not run, row missing | curl returns MIG values |
| Phase 3 | 🟡 **35%** | Expert < 85 (wrong threshold) | Score curl shows rule_results with failures |
| Phase 4 | 🟢 **5%** | Label mismatch | Visual check |

---

## Success Criteria (End-to-End)

| Feature | Target Behavior | Verification Method |
|---------|-----------------|----------------------|
| Aluminum thresholds | GET /api/thresholds/aluminum returns aluminum row | **Test:** curl endpoint → **Expect:** weld_type=aluminum, heat_diss=250, angle_warning=20 | **Location:** API response |
| Expert score | ≥ 85 | **Test:** curl score endpoint for sess_expert_aluminium_001_001 → **Expect:** total ≥ 85 | **Location:** API response |
| Novice score | 28–55 | **Test:** curl score endpoint for sess_novice_aluminium_001_001 → **Expect:** 28 ≤ total ≤ 55 | **Location:** API response |
| Replay label | "Aluminum" | **Test:** Load replay page → **Expect:** metadata shows "Aluminum" | **Location:** Browser |
| Narrative | Not generic | **Test:** POST narrative for novice → **Expect:** narrative_text ≠ "Strong performance" template | **Location:** API response |

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.**
