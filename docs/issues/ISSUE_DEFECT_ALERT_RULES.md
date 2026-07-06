# Issue: Session 2 — Implement Defect Alert Rules

**Type:** Feature  
**Priority:** Normal  
**Effort:** Medium–Large  
**Labels:** `backend` `alerts` `defect-signatures` `realtime`

---

## TL;DR

Implement seven defect-signature rules in the alert engine module: porosity, arc instability, crater crack, oxide inclusion, undercut, lack of fusion, burn-through. Keep existing three proxy rules (thermal asymmetry, travel angle deviation, speed drop). New rules run alongside as named defect alerts. Scope: alert engine only — no mock data, scoring, or UI changes.

---

## Current State vs Expected Outcome

### Current State

- **Alert engine** ([`backend/realtime/alert_engine.py`](backend/realtime/alert_engine.py)) has three rules:
  - Rule 1: NS thermal asymmetry
  - Rule 2: Travel angle deviation from nominal
  - Rule 3: Speed drop (percent change vs 10 frames ago)
- **FrameInput** ([`backend/realtime/alert_models.py`](backend/realtime/alert_models.py)) has: `frame_index`, `timestamp_ms`, `travel_angle_degrees`, `travel_speed_mm_per_min`, `ns_asymmetry` — no `volts` or `amps`
- **simulate_realtime** and **get_session_alerts** build `FrameInput` from frames but do not pass `volts` or `amps`; mock frames have both
- **alert_thresholds.json** holds only thermal/angle/speed thresholds; no defect-rule thresholds yet

### Expected Outcome

- Seven named defect rules implemented as real-time alerts with severity, message, and correction
- Spike rules (undercut, burn-through, porosity spike) use time-based suppression; sustained rules (arc instability, lack of fusion) re-fire on a longer interval or remain active until the condition clears (see Suppression Policy below)
- `FrameInput` extended with optional `volts`, `amps` for rules that need them
- All callers (simulate_realtime, sessions.get_session_alerts) pass volts/amps when available
- **Missing volts/amps:** If a rule requires `volts` or `amps` and the field is `None`, log a warning and skip that rule — never silently fail (per `.cursorrules`)
- **Buffer state:** All stateful buffers (voltage sustain, current ramp-down) must reset on session start — otherwise state carries over and produces phantom alerts at the start of a new session

---

## Defect Signature Library (Priority Order)

| Priority | Defect | Condition |
|----------|--------|-----------|
| 1 | Porosity | `travel_angle < 0°` (drag) AND `travel_speed < 250 mm/min` simultaneously |
| 2 | Arc instability / contamination | `voltage < 19.5V` sustained for > 500ms |
| 3 | Crater crack | Current drops to zero in < 300ms with no prior ramp-down phase |
| 4 | Oxide inclusion | `travel_angle` goes negative (argon trailing) — standalone, separate from porosity |
| 5 | Undercut | `current > 210A` AND `travel_speed > 500 mm/min` |
| 6 | Lack of fusion | `current < 140A` OR `travel_speed > 480 mm/min` |
| 7 | Burn-through | `current > 220A` AND `travel_speed < 200 mm/min` |

---

## Suppression Policy

Do **not** apply the same suppression pattern to all rules.

- **Spike rules** (undercut, burn-through, porosity, oxide inclusion, crater crack): One-time or brief events. Use time-based suppression — after firing, suppress for `suppression_ms` before allowing another fire.
- **Sustained rules** (arc instability, lack of fusion): The condition persists. If you suppress after first fire, you miss the rest of the sustained event. Re-fire on a longer interval (e.g. every 2–3 seconds while condition holds) or remain active until the condition clears.

---

## Crater Crack: Ramp-Down Definition

**Concrete threshold — do not leave vague.** "Ramp-down" means:

> Current decreases by at least 30% over a minimum of 300ms before reaching zero.

- **Abrupt (crater crack):** Current goes from > 70% of prior value to zero in < 300ms without a sustained decrease phase.
- **Controlled (no alert):** Current shows ≥30% decrease over ≥300ms before reaching zero.

Calculate from `timestamp_ms` and buffered amps; do not assume frame rate.

---

## Arc Instability: Time-Based Buffer

**Do not assume frame rate.** The "sustained > 500ms" condition must be calculated from `timestamp_ms`, not frame count.

- At 100Hz, 500ms = 50 frames; at 10Hz, 500ms = 5 frames. Hardcoding 50 frames breaks at different rates.
- Buffer entries as `(timestamp_ms, voltage)`; compute elapsed time as `timestamp_ms - first_low_voltage_timestamp_ms`.
- Same approach for crater crack: use `timestamp_ms` to detect < 300ms window, not "N frames".

---

## Relevant Files

| File | Action |
|------|--------|
| [`backend/realtime/alert_models.py`](backend/realtime/alert_models.py) | Extend `FrameInput` with optional `volts`, `amps`; extend `AlertPayload.rule_triggered` to support new rule names |
| [`backend/realtime/alert_engine.py`](backend/realtime/alert_engine.py) | Add seven defect rules; add buffers for voltage sustain (500ms from timestamp_ms), current ramp-down detection (30% over 300ms); config extension for new thresholds |
| [`backend/config/alert_thresholds.json`](backend/config/alert_thresholds.json) | Add defect thresholds (voltage_lo_V, crater_ramp_ms, undercut_amps, etc.) |
| [`backend/scripts/simulate_realtime.py`](backend/scripts/simulate_realtime.py) | Pass `volts`, `amps` from mock frame into `FrameInput` |
| [`backend/routes/sessions.py`](backend/routes/sessions.py) | Pass `volts`, `amps` from `frame_data` into `FrameInput` in `get_session_alerts` |

---

## Architecture Notes

- **Stateful buffers:** Voltage sustain buffer, current ramp-down detector. **All stateful buffers must reset on session start.** AlertEngine is called per session; if state is not cleared, phantom alerts occur at the start of a new session.
- **Missing data:** If a rule requires `volts` or `amps` and the field is `None`, log a warning (e.g. `logger.warning("Rule X requires volts; skipping (frame_index=%d)", frame.frame_index)`) and skip that rule. Never silently fail.

---

## Implementation Order

1. **Porosity** — compound: `travel_angle < 0` AND `travel_speed < 250`
2. **Arc instability** — voltage sustain buffer (500ms from timestamp_ms), threshold 19.5V
3. **Crater crack** — current ramp-down detector (30% decrease over ≥300ms = no alert; else abrupt = alert)
4. **Oxide inclusion** — travel_angle < 0 standalone
5. **Undercut** — current > 210 AND travel_speed > 500
6. **Lack of fusion** — current < 140 OR travel_speed > 480
7. **Burn-through** — current > 220 AND travel_speed < 200

---

## Done When

### Automatically verifiable (with current mock)

- **Porosity:** Novice mock triggers when travel_angle < 0 AND speed < 250. (Requires Session 1 for negative angle; until then, rule is implemented but mock may not produce it.)
- **Arc instability:** Novice triggers when voltage < 19.5V sustained > 500ms. (Current mock: AL_VOLTS=22; may need Session 1 short-circuit drops to reliably trigger.)
- **Crater crack:** Novice triggers at abrupt arc terminations; expert does not trigger (Session 1 adds expert ramp-down; until then, expert stitch boundaries may fire — document as known limitation).

### Rules without automatic mock verification (until Session 1)

These rules are implemented and unit-testable with synthetic FrameInput, but **current mock may not produce the conditions**. Verify manually or add synthetic test cases:

- **Undercut:** current > 210 AND travel_speed > 500 — both expert and novice stay in different bands; mock would need injected spike.
- **Lack of fusion:** current < 140 OR travel_speed > 480 — expert rarely hits; novice can hit speed > 480.
- **Burn-through:** current > 220 AND travel_speed < 200 — mock would need injected spike.
- **Oxide inclusion:** travel_angle < 0 — requires Session 1 (novice negative angle).

Add to implementation notes: which rules can be validated with current mock vs. require Session 1 or synthetic tests.

---

## Risk / Notes

- **Mock dependency:** Full "Done when" for porosity, oxide, crater crack assumes [ISSUE_MOCK_DATA_FOUNDATION.md](ISSUE_MOCK_DATA_FOUNDATION.md) (Session 1) is complete. Implement rules as specified; verify with current mock where possible.
- **Frame schema:** `Frame.travel_angle_degrees` is currently `ge=0, le=360`. Session 1 will allow negative; rule implementation should handle < 0 when present.
- **Expert stitch:** Expert mock has abrupt arc-off at stitch boundaries. Crater-crack rule will fire on these until Session 1 adds expert ramp-down. Document as known limitation.
- **Rule collision:** Porosity and oxide inclusion both key on negative travel_angle; porosity is compound (angle + speed), oxide is standalone. Order evaluation so both can fire when appropriate.

---

## Cursor Prompt to Open With

```
I need to add defect alert rules to the alert engine module only. Do not touch mock data, scoring, or UI. Here are the seven defect signatures I need implemented [paste the defect signature library]. Before writing any code, show me the current alert engine structure and confirm where new rules should be added. Then implement them one rule at a time, starting with porosity.

Critical constraints:
- Arc instability: Use timestamp_ms for sustain duration (500ms), not frame count. Buffer by time.
- Crater crack: Ramp-down = current decreases by ≥30% over ≥300ms before zero. Abrupt = no such ramp.
- Spike rules (undercut, burn-through, porosity, oxide, crater) use suppression; sustained rules (arc instability, lack of fusion) re-fire on interval or until condition clears.
- If volts or amps is None and a rule requires it: log warning, skip rule — never silently fail.
- All stateful buffers reset on session start.
```

---

## Vision Alignment

From `.cursorrules`: *"Never silently fail"*, *"Validation everywhere"*, *"Exact replays"*. Defect alerts are deterministic, rule-based, and auditable. Adding named defect signatures makes alerts more actionable and ties them to known weld defects in aluminum GMAW.
