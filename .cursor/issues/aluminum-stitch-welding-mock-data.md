# Aluminum Stitch Welding Mock Data

**Type:** Feature | **Priority:** Normal | **Effort:** Medium

---

## TL;DR

Add two new welder archetypes (`stitch_expert`, `continuous_novice`) with aluminum 6061 physics, stitch welding (arc on/off) patterns, and thermal-reactive angle behavior. Uses existing `disable_sensor_continuity_checks` bypass for 0↔non-zero volts/amps transitions.

---

## Current State

- WELDER_ARCHETYPES has 10 welders with arc types: fast_learner, consistent_expert, plateaued, declining, new_hire, volatile
- All mock sessions use mild steel MIG physics (mock_sessions.py)
- No stitch welding (arc on/off) — continuity checks would reject 0↔non-zero transitions
- Angle has no thermal reactivity — purely time-based generators

---

## Expected Outcome

- Two new welders: Senior Welder A (stitch_expert), Trainee Welder B (continuous_novice)
- Aluminum 6061 thermal model with soft clamp (25–480°C)
- Stitch expert: arc on 1.5s / off 1.0s, angle reacts to thermal state (redirects heat when N-S asymmetry > 10°C)
- Continuous novice: arc always on (accidental breaks), angle drifts with no thermal awareness, asymmetry spikes correlate with angle drift
- All frames satisfy Frame schema (angle [0,360], thermal 5 readings, etc.)
- `disable_sensor_continuity_checks=True` on both session types

---

## Before Cursor Implements — Critical Instructions

1. **Thermal distances:** Use `THERMAL_DISTANCES_MM` ([10, 20, 30, 40, 50]) — same as existing mock_sessions. Scale aluminum temps across all 5 distances, not a single point.
2. **heat_dissipation_rate:** `max(0, (prev_center - curr_center) / 0.2)` — clamp at zero, never negative. When arc is on and temps rise, report 0.
3. **Verification script:** Create `backend/scripts/verify_aluminum_mock.py`; run with `python -m backend.scripts.verify_aluminum_mock`; must print JSON to stdout.

---

## Implementation Sequence — Do in This Order

1. **Fix heat_diss_consistency threshold** (Step 0) — **before** implementing mock data or seeding.
2. Implement plan (Steps 1–9); run `verify_aluminum_mock.py`.
3. Seed DB; run the four curl checks below.
4. If expert score still &lt; 85 after threshold fix, investigate which other rule is failing.

---

## Plan

### Step 0: Fix heat_diss_consistency Threshold (DO FIRST)

**Why:** Scoring was calibrated on mild steel. Stitch welding (arc on/off) produces highly variable dissipation rates *by design* — high when arc on, zero when off. Penalizing an expert for correct technique is a bad rule. Fix the rule before seeding.

**Where:** `backend/scoring/rule_based.py` (HEAT_DISS_CONSISTENCY_THRESHOLD) and `backend/services/threshold_service.py` (default heat_diss_consistency for mig).

**Quick MVP fix:** Double the threshold (e.g. 40 → 80) so stitch welding passes. Stitch experts will have higher heat_diss_stddev than continuous-arc mild steel experts; that's physically correct.

**Long-term (post-pilot):** Make the rule evaluate dissipation variance only during arc-on periods, ignoring arc-off cooling frames. Not in scope for this implementation.

**Action:** Raise `heat_diss_consistency` threshold significantly — at least double — before implementing Steps 1–9.

### Step 1: mock_welders.py

- Add two entries to WELDER_ARCHETYPES (do not modify existing):
  - `expert_aluminium_001` / "Senior Welder A" / stitch_expert / 4 sessions / base 85 / delta 4
  - `novice_aluminium_001` / "Trainee Welder B" / continuous_novice / 6 sessions / base 48 / delta -3

### Step 2: mock_sessions.py — Constants

Add at top of file (after existing constants):

```
AL_VOLTS = 21.0
AL_AMPS = 145.0
AL_AMBIENT_TEMP = 25.0
AL_DISSIPATION_COEFF = 0.09
AL_MAX_TEMP = 480.0
```

### Step 3: mock_sessions.py — Physics Helper

Add `_compute_aluminum_thermals(prev_center, arc_active, angle_degrees, frame_index)`:

- Heat input: `(AL_VOLTS * AL_AMPS / 1000)` when arc active, else 0
- Angle bias: `(angle_degrees - 45) / 45` → north/south heat split
- Temp update: dissipation = coeff × (center - ambient); center += heat - dissipation
- North/south from center + asymmetry; east/west = center - gaussian noise
- Clamp all temps: `max(AL_AMBIENT_TEMP, min(AL_MAX_TEMP, temp))`
- Return: center, north, south, east, west (float) **per distance** — scale across THERMAL_DISTANCES_MM (e.g. 10mm = hottest, 50mm = coolest, conduction drop)
- **heat_dissipation_rate** = `max(0, (prev_center - curr_center) / 0.2)` — clamp at zero
- `import random` for east/west gaussian

### Step 4: mock_sessions.py — stitch_expert Generator

Add `_generate_stitch_expert_frames(session_index, num_frames)`:

- **Stitch pattern:** arc_active = (frame_index % 250) < 150 (1.5s on, 1.0s off)
- **Angle reactive:** if center_temp > 180 and (north - south) > 10 → target 35°; if center_temp > 220 → force arc off, target 90°; else target 45°
- **Smoothing:** angle += (target - angle) * 0.03 + random.gauss(0, 1.2)
- **Soft clamp:** angle = max(20, min(85, angle)) — stays within [0,360]
- **Machine:** volts/amps = AL_* + noise when arc on; 0 when arc off
- **Thermal:** only on frame_index % 20 == 0
- **Return:** List[Frame] with thermal snapshots at **all 5 distances** (THERMAL_DISTANCES_MM), scaled temps per distance — 5 readings per snapshot
- **disable_continuity:** True

### Step 5: mock_sessions.py — continuous_novice Generator

Add `_generate_continuous_novice_frames(session_index, num_frames)`:

- **Arc:** always on except (frame_index % 380) < 12 (accidental breaks)
- **Angle:** drift += 0.008/frame; overcorrection snap every 300 frames (drift -= 22); wrong correction when center_temp > 200 (drift += 0.06)
- **Soft clamp:** angle = max(20, min(85, angle))
- **Machine:** AL_* + noise when on; 0 when break
- **Thermal:** only on frame_index % 20 == 0
- **Return:** List[Frame]
- **disable_continuity:** True

### Step 6: mock_sessions.py — Routing

Update `generate_frames_for_arc()`:

- If arc_type == "stitch_expert": call `_generate_stitch_expert_frames(session_index, num_frames)`; return (frames, True)
- Elif arc_type == "continuous_novice": call `_generate_continuous_novice_frames(...)`; return (frames, True)
- Else: existing logic unchanged

### Step 7: mock_sessions.py — Session Builder

Update `generate_session_for_welder()`:

- When arc_type in (stitch_expert, continuous_novice): use new generators
- Pass `disable_sensor_continuity_checks=disable` from generate_frames_for_arc (already True for these)
- Set `thermal_sample_interval_ms=200` for aluminum (thermal every 20 frames)
- **Default num_frames:** 1500 for stitch_expert (15s), 1800 for continuous_novice (18s) — if not explicitly set by archetype definition. Prevents wrong/zero default from existing archetype flow.

### Step 8: Thermal Snapshot Structure

- New generators must produce exactly 5 readings: center, north, south, east, west
- **Use THERMAL_DISTANCES_MM** (`[10.0, 20.0, 30.0, 40.0, 50.0]`) — same as existing mock_sessions — with scaled temperature values across all 5 distances, not a single point. This keeps Session thermal-distance validator happy and matches the mild-steel pattern.
- **heat_dissipation_rate** = `max(0, (prev_center - curr_center) / 0.2)` — clamp at zero, never negative. When arc is on and temps rise, (prev - curr) is negative; physically we report 0 dissipation (no cooling), not a negative value. (200ms between thermal frames.)

### Step 9: Verification (pre-seed)

**IMPORTANT:** Write the verification as a standalone Python script at `backend/scripts/verify_aluminum_mock.py` that can be run with:

```
python -m backend.scripts.verify_aluminum_mock
```

The script must print JSON directly to terminal (stdout). Otherwise it will be written somewhere random or skipped.

Before reseeding DB, run that script. It must:

1. Generates sess_expert_aluminium_001_001 → output first 30 frames as JSON (verify stitch: volts/amps → 0 on arc-off, angle reacting to temp)
2. Generates sess_novice_aluminium_001_001 → output first 30 frames as JSON (verify continuous arc, angle drifting)
3. Output frames 200–220 of novice (first overcorrection snap)
4. Assert: no frame has angle_degrees outside [20, 85] (soft clamp)

---

## Verification After Seeding — Run in Order

Before touching the frontend, run these four checks:

```bash
# 1. Sessions exist
curl localhost:8000/api/sessions/sess_expert_aluminium_001_001

# 2. Expert score is in expected range (85+)
curl localhost:8000/api/sessions/sess_expert_aluminium_001_001/score

# 3. Novice score is in expected range (28–55)
curl localhost:8000/api/sessions/sess_novice_aluminium_001_001/score

# 4. Narrative generates without error
curl -X POST localhost:8000/api/sessions/sess_novice_aluminium_001_001/narrative \
  -H "Content-Type: application/json" -d '{}'
```

**Diagnostics:** If check 2 fails (expert &lt; 85), `heat_diss_consistency` is the likely culprit — verify Step 0 was done and threshold was raised. If check 1 returns 404, session builder routing failed.

---

## Files to Touch

| File | Changes |
|------|---------|
| `backend/scoring/rule_based.py` | Step 0: Raise HEAT_DISS_CONSISTENCY_THRESHOLD (e.g. 40 → 80) |
| `backend/services/threshold_service.py` | Step 0: Raise default heat_diss_consistency for mig |
| `backend/data/mock_welders.py` | Add 2 welder entries |
| `backend/data/mock_sessions.py` | Al constants, _compute_aluminum_thermals, 2 new generators, routing, session builder |
| `backend/scripts/verify_aluminum_mock.py` | **NEW** — standalone script runnable via `python -m backend.scripts.verify_aluminum_mock`; prints JSON to stdout |
| `backend/scripts/seed_demo_data.py` | No change — disable flag comes from generate_session_for_welder |

---

## Risks / Notes

- **Thermal distance consistency:** Use full THERMAL_DISTANCES_MM [10,20,30,40,50] with scaled temps — matches existing mild-steel pattern, passes Session validator.
- **heat_dissipation:** Use `max(0, (prev_center - curr_center) / 0.2)`. When arc is on and temps rise, raw value is negative; clamp at 0 (physically: no cooling, not "negative dissipation").
- **Scoring — heat_diss_consistency:** Stitch welding produces variable dissipation by design (arc on/off). The rule checks heat_diss_stddev — stitch experts will have higher variance. **Step 0 fixes this** by raising the threshold. If expert score still comes in below 85 after seeding, this rule is the likely culprit; verify threshold was raised and consider further tuning.
- **Scoring — other rules:** thermal_symmetry (asymmetry &lt; 20°C) — novice designed to spike 25–45°C (fails correctly). Expert designed to stay &lt; 12°C (should pass). Aluminum thermal profiles differ from mild steel; if unexpected rule failures occur, check thresholds.
- **Seagull / supervisor dashboards:** After reseeding, 10 new aluminum sessions mix with mild steel. Aggregate KPIs, trajectory charts, rankings will include aluminum scored against mild steel thresholds. For demo day (individual welder reports) this is fine; fleet analytics will be blended.
- **Warp risk ONNX:** Model trained on mild steel. Predictions on aluminum sessions are meaningless — different physical system. Gauge still renders; acceptable for demo (“warp risk” not “aluminum warp risk”).
- **Narrative service:** Uses scores and rule results; doesn’t know metal type. Should be fine since rules/numbers are correct.

---

## Vision Alignment

- Enables aluminum weld training scenarios (common in shipbuilding)
- Stitch welding is a real technique for thin materials — demo value
- Thermal-reactive angle models expert behavior (redirect heat to balance N-S)
- No changes to ingestion pipeline or Frame/Session contracts
