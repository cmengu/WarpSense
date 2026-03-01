# Demo Page — Wire Investor UX to Compare Session APIs (Refined)

**Type:** Feature  
**Priority:** Normal  
**Effort:** Medium  
**Labels:** `frontend` `demo` `compare` `api`

---

## TL;DR

Create a `/demo` page that reuses the compare-session APIs and replaces mock keyframes/ALERTS with real session data. The investor-polish UI (WQI gauges, parameter trends, bead diff, alert feed, playback bar) drives off live API responses.

---

## Data Mapping (Source of Truth)

| Demo mock | Real API |
|-----------|----------|
| volt | `frame.volts` |
| amp | `frame.amps` |
| angle | `frame.angle_degrees` |
| heat (kJ/mm) | `frame.heat_input_kj_per_mm` — backend has it; add optional field to frontend `Frame` type first (5‑min PR) |
| temp | `extractCenterTemperatureWithCarryForward(frames, timestamp_ms)` — use carry‑forward; temp has the most gaps/null in real data |
| wqi | **Use `session.score_total` only.** Remove `fetchScore` from the flow. Session is already fetched; avoid extra call. |
| Alerts t, msg, detail | `AlertPayload.timestamp_ms` → t (seconds), `message` → detail, `getRuleLabel(rule_triggered)` → msg |

---

## Corrected / correctedIn — Decision

**Decision:** UI shows alerts **without** correction status until the API supports it.

The alert feed currently leans on `corrected` and `correctedIn` for severity color, "✓ corrected in 1.2s", and "no correction". We will **not** infer from subsequent frames — that would require per-rule logic, spec definitions, and maintenance. Instead:

- Render all alerts with severity badge and message only.
- Omit "✓ corrected in X.Xs" and "✗ no correction" until backend adds `corrected` / `corrected_in_seconds` to `AlertPayload`.
- Track as follow-up: *Add correction status to AlertPayload and demo UI.*

---

## Duration — Edge Case

**Decision:** Truncate to the **shorter** session duration. Single shared timeline.

- `firstTimestamp` = max(sessionA first, sessionB first) — actually we align on overlapping timestamps; use `comparison.deltas[0].timestamp_ms` for start.
- `lastTimestamp` = `comparison.deltas[comparison.deltas.length - 1].timestamp_ms` (already aligned by `useSessionComparison`).
- The comparison hook only emits deltas for **shared** timestamps, so duration is inherently the overlap. No truncation logic needed — `deltas` define the playable range.
- If no overlap (`deltas.length === 0`), show "No overlapping frames" (same as compare page) and disable playback.

---

## Route Structure — Decision

**Decision:** Ship `/demo` with **hardcoded** default pair (`sess_expert_aluminium_001_001` / `sess_novice_aluminium_001_001`) for the investor demo. **Stub** `demo/[sessionIdA]/[sessionIdB]` as a TODO.

- Implement: `my-app/src/app/demo/page.tsx` → loads default pair, renders the demo UI.
- Stub: Add a comment in `demo/page.tsx` or a placeholder `demo/[sessionIdA]/[sessionIdB]/page.tsx` that redirects to compare for now. Document: *Future: Support dynamic session pair for supervisor sharing.*

---

## Loading & Error Handling

### Loading

- Show a **skeleton** until all fetches resolve: `fetchSession(A)`, `fetchSession(B)`, `fetchSessionAlerts(A)`, `fetchSessionAlerts(B)`.
- Skeleton matches layout: WQI placeholders (gray bars), chart placeholders, alert feed skeleton, playback bar disabled.
- No partial render — don't show 0 WQI or empty charts while loading. That reads as broken in a live demo.

### Errors

- **Both sessions fail:** Full-page error + "Back to dashboard" link.
- **One session fails:** Show error for the failed session only (e.g. left column "Session A: Failed to load") and render the successful session where possible. If comparison requires both, fall back to full-page error.
- **Alerts fail for one/both:** Log and render session data; show "Alerts unavailable" in that column. Don't block the rest of the demo.

---

## Implementation Sequence

Do in this order so something is showable at each step:

1. **Frames + charts** — Fetch sessions, drive MultiChart (heat, amp, angle) from real frames. Playback bar + seek. No WQI, no alerts yet.
2. **WQI** — Add `score_total` to gauges. Add BeadDiff (illustrative is fine for now).
3. **Alerts** — Wire alert feed to `fetchSessionAlerts`. No correction status. Add seek-on-click for alerts.

---

## Prereqs

1. Add `heat_input_kj_per_mm?: number | null` to `my-app/src/types/frame.ts`. Quick, unblocks charts.
2. Ensure backend `Frame` serialization includes it (verify mock sessions emit it).

---

## Relevant Files

| File | Action |
|------|--------|
| `my-app/src/types/frame.ts` | Add optional `heat_input_kj_per_mm` |
| `my-app/src/app/demo/page.tsx` | New demo page with default pair |
| `my-app/src/lib/api.ts` | Existing: `fetchSession`, `fetchSessionAlerts` |
| `my-app/src/utils/frameUtils.ts` | `getFrameAtTimestamp`, `extractCenterTemperatureWithCarryForward` |
| `my-app/src/lib/alert-labels.ts` | `getRuleLabel` |
| `my-app/src/hooks/useSessionComparison.ts` | Shared comparison |
