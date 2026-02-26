# Issue: Session 1 — Fix Mock Data (Foundation)

**Type:** Improvement  
**Priority:** High  
**Effort:** Large  
**Labels:** `backend` `mock-data` `aluminum` `expert-profile` `novice-profile` `foundation`

---

## TL;DR

Aluminum expert and novice mock data in `backend/data/mock_sessions.py` does not accurately represent real welder profiles. Fix expert mock (current range, arc-start spike, corner drop, travel speed, heat input) and novice mock (travel angle into drag, hot-start/cold-mid pattern, arc terminations, porosity cause, interpass) so every future session can be tested against realistic data. Do not touch alerts, scoring, or UI.

---

## Current State vs Expected Outcome

### Current State
- Expert mock: 155A center, no arc-start spike, no corner drop, travel speed 380–560 mm/min, no heat input
- Novice mock: travel angle clamped 5–90° (never negative/drag), no hot-start/cold-mid pattern, abrupt 120ms arc-off without ramp-down label
- Porosity: uses work angle + high speed; ignores drag angle + low speed compound
- No interpass timer or plate temperature state
- Heat input not computed

### Expected Outcome
- **Expert:** 160–200A mean, slow drift ±5–8A; 20–30A arc-start spike for ~200ms; ~10–15A drop at corners; travel speed 350–450 mm/min with ~15% decel at start/end; heat input stored per frame
- **Novice:** Travel angle allowed negative (drag); hot-start/cold-mid current pattern; abrupt dropout labeled for crater rule; porosity when travel_angle negative AND speed <250 mm/min; interpass timer + plate temp state
- Visible difference between expert and novice on current trace, travel angle (including negative), arc starts, arc terminations, and travel speed profile when mock is run

---

## What to Fix

### Expert Mock (`_generate_stitch_expert_frames`)
| Parameter | Current | Target |
|-----------|---------|--------|
| Current | 155A ±4, no pattern | Pick target (e.g. 178A) at session start; drift ±5–8A around that. Do not roam the full 160–200A band — operating envelope is session-level, not bead variance. |
| Arc-start spike | None | 20–30A spike for ~200ms at bead start, then settle |
| Corner drop | None | ~10–15A reduction. **Trigger:** Define corner: e.g. every N-th stitch boundary, or positional flag. Not every stitch boundary is a corner — specify in implementation. |
| Voltage | 22V flat | Correlated with current (±0.5V variance). When current drifts up, voltage follows slightly. Never <20V. Required for correct heat input. |
| Travel speed | 380–560 mm/min, no decel | 350–450 mm/min, ~15% decel at start and end |
| Heat input | Not computed | `(Amps × Volts × 60) / travel_speed_mm_per_min / 1000` → **kJ/mm**. At 180A, 22V, 400 mm/min = 0.594 kJ/mm. Target 1.0–1.4 kJ/mm. Store per frame. |

### Novice Mock (`_generate_continuous_novice_frames`)
| Parameter | Current | Target |
|-----------|---------|--------|
| Travel angle | Clamped 5–90° (never negative) | Remove 5° floor — allow negative (drag territory) |
| Current | 155 ±10 + occasional spike | Hot-start (overcorrect high at start), cold mid-bead pattern |
| Voltage | 22 ±0.3/1.8 | ±2–3V variance; **short-circuit drops below 19V** — distinct electrical event, key differentiator for scoring. Model crudely (periodic dips). |
| Arc terminations | 120ms abrupt dropout | Keep abrupt 120ms for novice; add label so crater crack rule can check |
| Porosity cause | Work angle + speed >500/560 | Replace with: travel_angle negative AND speed <250 mm/min |
| Interpass | None (continuous) | Add timer between arc-off and arc-on; store plate temp state |

### Expert Arc Terminations (for contrast)
- Add controlled ramp-down model so expert has proper crater fill; novice keeps abrupt dropout — explicit difference for crater rule.

---

## Relevant Files

| File | Action |
|------|--------|
| `backend/data/mock_sessions.py` | All mock changes — constants, `_generate_stitch_expert_frames`, `_generate_continuous_novice_frames`, porosity logic, interpass state |
| `backend/models/frame.py` | Add optional `heat_input_kj_per_mm: Optional[float]`; add optional `arc_termination_type: Optional[Literal["controlled_ramp_down", "abrupt_dropout"]]` — **decided before session:** use explicit enum field, not metadata dict |
| `backend/scripts/verify_aluminum_mock.py` | Update travel speed assertions (350–450 expert); **add heat input assertion:** expert arc-on frames must have heat_input_kj_per_mm in 1.0–1.4 kJ/mm |
| `backend/tests/test_mock_sessions.py` | Adjust expectations for stitch/continuous aluminum if tests assert on specific values |

---

## Risk / Notes

- **Schema (decided):** Add `heat_input_kj_per_mm: Optional[float]` and `arc_termination_type: Optional[Literal["controlled_ramp_down", "abrupt_dropout"]]` to `frame.py`. Do not use metadata dict — explicit enum allows crater rule to query directly.
- **Verification script:** `verify_aluminum_mock.py` asserts travel speed p2≥360, p98≤580; expert target 350–450 changes this. Add heat input validation.
- **Porosity scoring:** `extract_features` uses voltage σ in rolling window; mock porosity cause change affects *when* porosity events fire, not necessarily the extractor logic. Scoring should still discriminate expert vs novice.
- **Stitch pattern:** Expert stitch (150 on / 100 off) — corner trigger must be explicit (e.g. every 3rd stitch, or flag). Not every boundary is a corner.
- **Determinism:** Use a seeded `random.Random(seed)` instance, **not** global `random.seed()`. Per `LEARNING_LOG.md`. Add this to Cursor prompt explicitly.

---

## Vision Alignment

From `.cursorrules`: *"Exact replays: Frontend shows exactly what happened (no guessing)"* and *"Verification to be done by adding and running automated tests."* Realistic mock data is the foundation for all downstream testing — alerts, scoring, compare page, and future defect-signature rules depend on expert vs novice being physically credible. Without correct mock behavior, calibration and demo value are compromised.

---

## Done When

1. Run mock (`python -m scripts.simulate_realtime --mode expert` and `--mode novice`) and observe visible difference between expert and novice on:
   - Current trace (expert: stable around target, arc-start spike, corner drop; novice: hot-start, cold mid)
   - Travel angle (novice includes negative values; expert holds 10–15°)
   - Arc starts (expert: brief spike then settle; novice: extended hesitation)
   - Arc terminations (expert: ramp-down; novice: abrupt dropout)
   - Travel speed profile (expert: 350–450, start/end decel; novice: 200–320, erratic)
2. `verify_aluminum_mock.py` passes with updated thresholds:
   - Travel speed p2/p98 for 350–450 expert
   - **Heat input:** expert arc-on frames have `heat_input_kj_per_mm` in 1.0–1.4 kJ/mm range
3. Porosity events occur when travel_angle negative AND speed <250 (novice); expert rarely/never.
4. Interpass timer and plate temp state modeled between arc-off and arc-on.

---

## Cursor Prompt to Open With

```
I need to update the mock data module only. Do not touch alerts, scoring, or UI. Use a seeded random.Random(seed) instance for all randomness — never use global random.seed(). Here is the expert welder profile and novice welder profile I'm targeting [paste both profiles]. Audit the current mock against these profiles and list every parameter that doesn't match before making any changes. Then fix them one parameter at a time and confirm each one.

Schema decisions (already made):
- Add heat_input_kj_per_mm: Optional[float] to Frame — formula: (Amps × Volts × 60) / travel_speed_mm_per_min / 1000 → kJ/mm.
- Add arc_termination_type: Optional[Literal["controlled_ramp_down", "abrupt_dropout"]] to Frame — expert gets controlled_ramp_down, novice gets abrupt_dropout.
- Corner drop trigger: every 3rd stitch boundary is a corner (or define explicitly in code).
```

**Expert profile (for paste):**
- Current: Pick target (e.g. 178A) at session start; drift ±5–8A around that. Operating envelope 160–200A is session-level, not bead variance. Arc starts: brief 20–30A spike for ~200ms then settle. At corners (every 3rd stitch): current drops ~10–15A.
- Voltage: 21–24V, variance ±0.5V, **correlated with current** — when current drifts up, voltage follows slightly. Never <20V.
- Wire feed: 450–550 IPM (not modeled; skip).
- Travel speed: 350–450 mm/min, variance <8%. ~15% decel at start and end. Smooth.
- Push angle: 10–15° from vertical, held ±3° over bead.
- Work angle: 45° ±5° on fillets.
- Arc length/CTWD: 15–20mm, stable.
- Heat input: 1.0–1.4 kJ/mm. Formula: (Amps × Volts × 60) / travel_speed_mm_per_min / 1000. Validate in verify_aluminum_mock.
- Arc terminations: controlled ramp-down with crater fill; set arc_termination_type="controlled_ramp_down".
- Interpass: waits until plate <60°C; model as timer between sessions.

**Novice profile (for paste):**
- Current: Same target range but wanders ±20–30A. Hot at start (overcorrect), cold mid-bead. Frequent small spikes from torch movement.
- Voltage: ±2–3V variance; **short-circuit drops below 19V** — distinct electrical event. Model periodically.
- Travel speed: 200–320 mm/min, ±25%. Pauses at tacks. Sudden changes not gradual.
- Push angle: Drifts 5–25°; sometimes negative (drag) — contaminates weld. Key novice differentiator.
- Work angle: ±15–20°.
- Arc starts: 0.5–2s hesitation, 30–50A spike on commit.
- Arc terminations: Abrupt, no crater fill — sudden dropout = crater defect risk. Set arc_termination_type="abrupt_dropout".
- Porosity: travel angle into drag AND speed <250 mm/min simultaneously.
- Interpass: Doesn't wait; next pass on plate still 80–100°C.
