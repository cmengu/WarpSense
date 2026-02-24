# Aluminum Threshold Plan

**Type:** Feature | **Priority:** Normal | **Effort:** Small

---

## TL;DR

Wire the scoring layer to use dedicated aluminum thresholds. Frontend and physics are ready; this is model constants + DB seeding + verification. No new features — pure wiring.

---

## Current State

- Aluminum mock sessions exist (`sess_expert_aluminium_001_001`, `sess_novice_aluminium_001_001`) with weld_type="aluminum"
- Scoring uses `session.process_type` → `get_thresholds(db, process_type)` → weld_thresholds row
- `KNOWN_PROCESS_TYPES` = mig, tig, stick, flux_core — unknown types fall back to MIG
- `WeldTypeThresholds` thermal_symmetry caps are le=200
- No aluminum row in weld_thresholds — aluminum sessions get MIG thresholds (expert penalized for stitch variance)

---

## Expected Outcome

- Aluminum row in weld_thresholds with stitch-appropriate values (heat_diss_consistency 250, angle margins 20/35, etc.)
- Expert score ≥ 85 (achieved 100); novice 28–55 (achieved 60 — mock variance limits; see LEARNING_LOG)
- Replay label shows "Aluminum"; ScorePanel shows "ALUMINUM" spec
- Narrative not generic for novice

---

## Prerequisite: process_type on Aluminum Sessions

**Critical:** Scoring uses `process_type`, not `weld_type`. Mock sessions default to `process_type="mig"`.

Before any scoring verification will pass, **`generate_session_for_welder`** in `backend/data/mock_sessions.py` must set `process_type="aluminum"` when `is_aluminum_arc`:

```python
process_type="aluminum" if is_aluminum_arc else "mig",
```

Without this, aluminum sessions are scored against MIG thresholds regardless of the new row.

---

## Threshold Verification (Before Step 3)

**Do not use dummy thresholds.** Each value must bracket the actual variance produced by the aluminum mock generators. Cross-check against:

| Threshold | Rule (rule_based.py) | Feature (extractor.py) | Source of variance (mock_sessions.py) | Verification |
|-----------|----------------------|------------------------|---------------------------------------|--------------|
| `angle_warning_margin` | _check_angle_consistency | angle_max_deviation | Expert: reactive 35/45/90° + gauss(0,1.2) L209; Novice: drift L286 + overcorrection L283 | Expert should pass; novice fail |
| `thermal_symmetry_warning_celsius` | _check_thermal_symmetry | north_south_delta_avg | verify_aluminum_mock: expert 95th N-S < 12°C; novice max > 20°C | 15°C: expert pass; novice fail |
| `heat_diss_consistency` | _check_heat_diss_consistency | heat_diss_stddev | Stitch arc on/off: cooling = (prev−curr)/0.2, 0 when heating L221–227 | ~165 expected; 250 gives headroom |
| `amps_stability_warning` | _check_amps_stability | amps_stddev | Expert: gauss(0,3) when on, 0 when off L215; Novice: gauss(0,5) L296 | 18: expert pass; novice fail |
| `volts_stability_warning` | _check_volts_stability | volts_range | Stitch: 0 (arc off) to AL_VOLTS+noise (~21) when on L214 | range ≈ 21; threshold must be ≥ 22 |

**Pre-Step 3 check:** Run `extract_features` on aluminum expert + novice sessions (with `process_type="aluminum"`), compare each feature to the proposed threshold. Expert: all features ≤ thresholds. Novice: at least angle, thermal_symmetry, or amps should exceed thresholds. Optionally extend `verify_aluminum_mock.py` to assert this.

---

## Implementation — 4 Cursor Sessions

### CURSOR SESSION 1: Model + Constants

#### Step 1: Raise thermal_symmetry cap in WeldTypeThresholds

- **File:** `backend/models/thresholds.py`
- Change `thermal_symmetry_warning_celsius` and `thermal_symmetry_critical_celsius` from `le=200` → `le=500`
- Change nothing else
- **Verify:** `cd backend && python3 -m pytest tests/ -x --tb=short`
- **Verify:** `python3 -c "from models.thresholds import WeldTypeThresholds; t = WeldTypeThresholds(weld_type='aluminum', ..., thermal_symmetry_warning_celsius=250.0, thermal_symmetry_critical_celsius=400.0, ...); print('OK')"` — no ValidationError

#### Step 2: Add aluminum to KNOWN_PROCESS_TYPES

- **File:** `backend/services/threshold_service.py`
- Add `'aluminum'` to the `KNOWN_PROCESS_TYPES` frozenset
- Change nothing else
- **Verify:** `cd backend && python3 -m pytest tests/ -x --tb=short`

**⚠️ After Step 2:** Any request to the aluminum threshold route will **crash** until Step 3 seeds the DB row. **Do not restart the server between Step 2 and Step 3.**

---

### CURSOR SESSION 2: Seeding

#### Step 3: Add ALUMINUM_THRESHOLDS constants

- **File:** `backend/services/threshold_service.py`
- Add after existing MIG constants (fallback dict):

```python
ALUMINUM_THRESHOLDS = {
    "weld_type": "aluminum",
    "angle_target_degrees": 45.0,
    "angle_warning_margin": 20.0,       # wider — reactive correction is correct expert behavior
    "angle_critical_margin": 35.0,
    "thermal_symmetry_warning_celsius": 15.0,
    "thermal_symmetry_critical_celsius": 35.0,
    "amps_stability_warning": 18.0,     # wider — stitch on/off creates variance by design
    "volts_stability_warning": 25.0,    # stitch: volts 0 (arc off) to ~21 (arc on) → range ~21
    "heat_diss_consistency": 250.0,      # stitch stddev ~165 expected; 250 gives headroom
}
```

- ADD only — do not modify existing constants or functions
- **Before applying:** Run threshold verification (see **Threshold Verification** section below) to confirm values bracket actual mock output

#### Step 4: Seed aluminum row into DB

- **Seed location:** `backend/alembic/versions/004_weld_thresholds_and_process_type.py` seeds mig/tig/stick/flux_core. Add aluminum via either:
  - New Alembic migration (e.g. `0xx_add_aluminum_threshold.py`) — preferred for production
  - Or extend dev seed route to upsert aluminum row when seeding (dev-only)
- Use exact same INSERT pattern as 004; values from ALUMINUM_THRESHOLDS
- **Seed:** `curl -X POST localhost:8000/api/dev/seed-mock-sessions`
- **Verify (immediate):**
  ```bash
  curl -s localhost:8000/api/thresholds/aluminum | python3 -m json.tool
  # Must return aluminum values. MIG values = fallback = row didn't seed.

  curl -s localhost:8000/api/thresholds/aluminum | python3 -c "
  import sys, json
  d = json.load(sys.stdin)
  assert d['heat_diss_consistency'] == 250.0, f'FAIL: got {d[\"heat_diss_consistency\"]}'
  assert d['angle_warning_margin'] == 20.0, f'FAIL: got {d[\"angle_warning_margin\"]}'
  assert d['weld_type'] == 'aluminum', 'FAIL: wrong weld_type returned'
  print('OK — aluminum threshold row confirmed')
  "
  ```

---

### CURSOR SESSION 3: Score Verification

#### Step 5: Verify scores

```bash
# Expert must be ≥ 85
curl -s localhost:8000/api/sessions/sess_expert_aluminium_001_001/score | \
  python3 -c "import sys,json; d=json.load(sys.stdin); s=d['total']; print(f'Expert: {s}'); assert s >= 85, f'FAIL: {s}'"

# Novice must be 28–55
curl -s localhost:8000/api/sessions/sess_novice_aluminium_001_001/score | \
  python3 -c "import sys,json; d=json.load(sys.stdin); s=d['total']; print(f'Novice: {s}'); assert 28 <= s <= 55, f'FAIL: {s}'"
```

**If expert < 85:** Inspect per-rule breakdown. Adjust the failing rule's threshold, re-seed, re-check. Do not raise all thresholds blindly.

**If novice > 55:** Aluminum thresholds are too loose; novice should still fail on angle drift and thermal asymmetry.

#### Step 6: Narrative check

```bash
curl -s -X POST localhost:8000/api/sessions/sess_novice_aluminium_001_001/narrative \
  -H "Content-Type: application/json" -d '{}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
t = d.get('narrative_text', '')
print(t[:300])
assert 'Strong performance' not in t, 'FAIL: narrative is generic'
print('OK')
"
```

---

### CURSOR SESSION 4: Frontend Spot Check

#### Step 7: Browser verification

1. Open `http://localhost:3000/replay/sess_expert_aluminium_001_001` — weld type label shows "Aluminum" not "ALUMINUM" or blank
2. Open `http://localhost:3000/replay/sess_novice_aluminium_001_001` — Compare → select expert — ScorePanel shows "ALUMINUM" as threshold spec; scores visible and separated

---

## Success Criteria

| Check | Target | How |
|-------|--------|-----|
| Threshold row exists | aluminum row returned | `curl .../api/thresholds/aluminum` |
| Expert score | ≥ 85 | `curl` score endpoint |
| Novice score | 28–55 | `curl` score endpoint |
| Replay label | "Aluminum" | Browser |
| Narrative | Not generic | `curl` narrative endpoint |

---

## Files to Touch

| File | Changes |
|------|---------|
| `backend/models/thresholds.py` | Step 1: thermal_symmetry le=200 → le=500 |
| `backend/services/threshold_service.py` | Step 2: add aluminum to KNOWN_PROCESS_TYPES; Step 3: ALUMINUM_THRESHOLDS; Step 4: seed (or seed script) |
| `backend/data/mock_sessions.py` | **Prerequisite:** `process_type="aluminum"` when `is_aluminum_arc` |
| Seed location | Step 4: add aluminum row (e.g. new Alembic migration or dev seed) |

---

## Risks / Notes

- **Steps 2 and 3 must happen in the same server session without restart.** Step 2 makes missing aluminum row a crash; Step 3 prevents it.
- **volts_stability_warning:** Stitch welding has volts 0 (arc off) and ~21 (arc on) → volts_range ≈ 21. Original 2.5 would fail both expert and novice. Use 25.0 (or ≥ 22).
- **VALID_PROCESS_TYPES** in `backend/routes/sessions.py` is for API validation on session create. If seed/mock flow creates sessions directly, it bypasses that. No change needed for seed flow.
- If expert < 85 after thresholds and process_type fix, inspect `rule_results` in the score response. Each failing rule maps to one threshold — tune that one only.
- ScorePanel shows `active_threshold_spec.weld_type.toUpperCase()` — comes from backend; will show "ALUMINUM" once aluminum thresholds are used. Replay `weld_type_label` uses `getWeldTypeLabel` (metals.ts) — "aluminum" → "Aluminum" ✓

---

## Vision Alignment

- Aluminum weld training is common in shipbuilding; dedicated thresholds align scoring with physical reality
- Stitch welding (arc on/off) produces different variance profiles — heat_diss_consistency=250 accommodates this
- No new UI or ingestion logic — pure data-layer wiring
