# Demo Page — Wire Investor UX to Compare Session APIs

**Type:** Feature  
**Priority:** Normal  
**Effort:** Medium  
**Labels:** `frontend` `demo` `compare` `api`

---

## TL;DR

Create a `/demo` page that reuses the compare-session APIs (`fetchSession`, `fetchSessionAlerts`, `fetchScore`) and replaces mock keyframes/ALERTS with real session data. The investor-polish UI (WQI gauges, parameter trends, bead diff, alert feed, playback bar) drives off live API responses.

---

## Current State vs Expected

| Area | Current (mock) | Expected (real) |
|------|----------------|-----------------|
| Keyframes | `KF_NOVICE`, `KF_EXPERT` (volt, amp, heat, angle, temp, wqi) | `Session.frames` → volts, amps, angle_degrees, heat_input, center temp |
| Alerts | `ALERTS` (t, severity, msg, detail, corrected, correctedIn) | `fetchSessionAlerts(sessionId)` → `AlertPayload[]` |
| WQI | Interpolated from keyframes | `Session.score_total` or `fetchScore()` |
| Duration | `DURATION = 15` | `firstTimestamp` → `lastTimestamp` from comparison deltas |

---

## Data Mapping

| Demo mock | Real API |
|-----------|----------|
| volt, amp, angle | `frame.volts`, `frame.amps`, `frame.angle_degrees` |
| heat (kJ/mm) | `frame.heat_input_kj_per_mm` (backend has it; add to frontend Frame type if needed) |
| temp | `extractCenterTemperatureWithCarryForward(frames, timestamp_ms)` |
| wqi | `session.score_total` or `fetchScore(sessionId).total` |
| Alerts t, msg, detail | `AlertPayload.timestamp_ms` → t (seconds), `message` → detail, `getRuleLabel(rule_triggered)` → msg |
| corrected / correctedIn | Not in API — use placeholder or infer from subsequent frames |

---

## Relevant Files

- `my-app/src/app/demo/page.tsx` — new demo page (or `demo/[sessionIdA]/[sessionIdB]/page.tsx`)
- `my-app/src/lib/api.ts` — `fetchSession`, `fetchSessionAlerts`, `fetchScore`
- `my-app/src/types/frame.ts` — add optional `heat_input_kj_per_mm` if missing
- `my-app/src/utils/frameUtils.ts` — `getFrameAtTimestamp`, `extractCenterTemperatureWithCarryForward`
- `my-app/src/lib/alert-labels.ts` — `getRuleLabel` for alert display
- `my-app/src/hooks/useSessionComparison.ts` — shared comparison logic

---

## Risks & Notes

- BeadDiff is "derived · not sensor-measured" — keep illustrative or derive from heat/amp variance.
- `corrected` / `correctedIn` are not in the API; placeholder or infer from subsequent frames.
- Default pair: `sess_expert_aluminium_001_001` / `sess_novice_aluminium_001_001` (matches compare quick demo).
