# Aluminum 6061 GMAW Mock Session Enhancement — Steps 0–14

> **Source:** `.cursor/plans/mock-session-enhancement-travel-speed-porosity-cyclogram.md`  
> **Status:** Implemented  
> **Purpose:** AI context — what was built for aluminum travel speed, porosity, cyclogram scoring.

---

## Overview

Adds aluminum 6061 GMAW mock session support: travel speed, porosity, cyclogram features, and scoring. Target: 3–6mm medium plate, real-time alert + post-session scoring.

**Key decisions:**
- Novice **decelerates** when hot (panic), not accelerates
- Porosity is **cause-gated** (angle, speed, CTWD), not flat random
- Two migrations: schema-only (A), then data population (B)
- 30-session calibration before threshold values
- Expert: 8 rules; MIG: 5 rules (unchanged)

---

## Step 0 — Pre-Flight

**Purpose:** Confirm baseline before edits.

**Checks:**
- `pytest tests/` — all pass
- `generate_expert_session`, `generate_frames_for_arc` — imports OK
- `_generate_stitch_expert_frames(0, 1500)`, `_generate_continuous_novice_frames(0, 1500)` — accept `(session_index, num_frames)`

---

## Step 1 — Frame Model

**File:** `backend/models/frame.py`

**Change:** Add optional `travel_speed_mm_per_min`, `travel_angle_degrees` after `heat_dissipation_rate_celsius_per_sec`.

**Bounds (post-review fix):** `travel_speed_mm_per_min` ge=0, le=2000; `travel_angle_degrees` ge=0, le=360.

---

## Step 2 — Constants

**File:** `backend/data/mock_sessions.py`

**Change:** Add/update 20 constants from Constants Reference: `AL_AMPS`, `AL_VOLTS`, `AL_*_NOISE_*`, `AL_TRAVEL_SPEED_*`, `AL_POROSITY_*`, `AL_AMBIENT_TEMP`, `AL_MELT_POINT`, etc.

---

## Step 3 — Thermal Physics

**File:** `backend/data/mock_sessions.py`

**Changes:**
1. `_step_thermal_state`: add `travel_speed_mm_per_min` param; scale heat by `AL_TRAVEL_SPEED_NOMINAL / travel_speed_mm_per_min`
2. `_compute_interpass_bias`: helper for stitch preheat (30s pause, τ=45s cooling)
3. Wire interpass into `_generate_stitch_expert_frames`: `prev_arc_active`, `last_arc_end_temp`, `stitch_count`; apply bias at arc False→True

---

## Step 4 — Porosity Model

**File:** `backend/data/mock_sessions.py`

**Change:** `_porosity_probability(angle, travel_speed, ctwd, base_prob)` — multipliers for angle deviation, speed >560/500, CTWD >19mm. Cap at 0.10.

Replace flat `rng.random() < AL_POROSITY_PROB_*` with cause-gated call in both generators.

---

## Step 5 — Generator: Expert Frames

**File:** `backend/data/mock_sessions.py` — `_generate_stitch_expert_frames`

**Changes:**
- Init: `travel_speed`, `travel_angle`, `porosity_frames_remaining`, `ctwd_mm`
- Loop: adaptive speed (temp-based target), ctwd/angle noise, porosity-aware volts/amps
- `_step_thermal_state(..., travel_speed)`; Frame with `travel_speed_mm_per_min`, `travel_angle_degrees`

**Verification:** Expert speed p2≥360, p98≤580; travel_angle 8–18°.

---

## Step 6 — Generator: Novice Frames

**File:** `backend/data/mock_sessions.py` — `_generate_continuous_novice_frames`

**Changes:**
- Init: same as expert + `ctwd_drift_rate`
- Loop: panic deceleration (6% slow, 1% speed-up when hot), CTWD drift with reversal, porosity block, amps spike 0.3%
- Frame with travel_speed/travel_angle on every frame

**Verification:** Novice dwells (speeds < expert min); amps/volts/speed ratio expert vs novice.

---

## Step 7 — Feature Extractor

**File:** `backend/features/extractor.py`

**Changes:**
- `_compute_cyclogram_area(volts, amps)`: ellipse area π×σ_v×σ_a×√(1-r²)
- Add `travel_speed_stddev`, `cyclogram_area`, `porosity_event_count` to `extract_features`
- `POROSITY_SIGMA_THRESHOLD = 0.8` at module level (Step 8 calibration)

---

## Step 8 — Calibration

**Action:** Run 30 sessions expert + 30 novice; human gates before Step 9.

**Output:** Suggested thresholds from (e_p95 + n_p5)/2:
- `cyclogram_area_max`: 16.21
- `travel_speed_consistency`: 67.68
- `porosity_event_max`: 7.5

---

## Step 9 — Database Migration

**Files:** `backend/alembic/versions/012_*.py`, `013_*.py`

**Migration A (012):** Add nullable columns to `weld_thresholds`: `travel_speed_consistency`, `cyclogram_area_max`, `porosity_event_max`.

**Migration B (013):** `UPDATE weld_thresholds SET ... WHERE weld_type = 'aluminum'` with Step 8 values.

**Models:** `backend/models/thresholds.py`, `backend/database/models.py` — add optional fields/columns.

---

## Step 10 — Threshold Service

**File:** `backend/services/threshold_service.py`

**Changes:**
- `_load_all`: map new columns into `WeldTypeThresholds` via `getattr`
- `ALUMINUM_THRESHOLDS`: add `travel_speed_consistency`, `cyclogram_area_max`, `porosity_event_max`

---

## Step 11 — No Action

Placeholder. Proceed to Step 12.

---

## Step 12 — Scoring Rules

**File:** `backend/scoring/rule_based.py`

**Changes:**
- Add `_check_travel_speed_consistency`, `_check_cyclogram_area`, `_check_porosity_events`
- Append rules only when threshold fields are non-None
- `total = int(round(100 * passed_count / len(rules)))`

**Verification:** Aluminum 8 rules, expert ≥75; MIG 5 rules unchanged.

---

## Step 13 — Final Integration Test

**Commands:**
- `curl -X POST .../api/dev/wipe-mock-sessions`
- `curl -X POST .../api/dev/seed-mock-sessions`
- Session existence: `sess_expert_aluminium_001_001`, `sess_novice_aluminium_001_001` (use `?limit=1500` for full frames)
- Score: expert ≥75, novice 15–55, MIG 5 rules

---

## Step 14 — Verify Script

**File:** `backend/scripts/verify_aluminum_mock.py`

**Additions:**
- Travel speed assertions (expert p2≥360, p98≤580)
- Voltage variance ratio (novice/expert σ > 1.5)
- Cyclogram + porosity via `extract_features`

**Run:** `cd backend && python3 -m scripts.verify_aluminum_mock`

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/models/frame.py` | travel_speed_mm_per_min, travel_angle_degrees |
| `backend/data/mock_sessions.py` | Generators, thermal physics, porosity |
| `backend/features/extractor.py` | cyclogram_area, travel_speed_stddev, porosity_event_count |
| `backend/models/thresholds.py` | WeldTypeThresholds, WeldThresholdUpdate (optional new fields) |
| `backend/services/threshold_service.py` | Load new cols, ALUMINUM_THRESHOLDS |
| `backend/scoring/rule_based.py` | 5 base + 3 aluminum rules |
| `backend/scripts/verify_aluminum_mock.py` | Behavioral assertions |
| `backend/alembic/versions/012_*.py`, `013_*.py` | Schema + data migrations |

---

## Post-Implementation Fixes (Code Review)

- **MEDIUM 1:** `POROSITY_SIGMA_THRESHOLD` moved to module level in extractor
- **MEDIUM 2:** Frame `travel_speed_mm_per_min` ge=0/le=2000, `travel_angle_degrees` ge=0/le=360
- **LOW 1:** verify_aluminum_mock uses `_percentile` + `statistics.stdev` (no NumPy)
- **LOW 2:** rule_based docstring updated
- **LOW 3:** WeldThresholdUpdate + routes support new optional fields
- **LOW 4:** `math.isnan(r_val)` in _compute_cyclogram_area
