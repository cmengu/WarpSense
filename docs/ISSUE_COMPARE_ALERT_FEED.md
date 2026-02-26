# Issue: Compare Page Alert Feed — Pre-Computed Alerts API + Timeline UI

**Type:** Feature  
**Priority:** Normal  
**Effort:** Medium  
**Labels:** `backend` `frontend` `compare` `alerts` `replay` `demo`

---

## TL;DR

Add a `GET /sessions/{session_id}/alerts` endpoint that runs stored frames through `AlertEngine` and returns pre-computed alerts. On the compare page, fetch alerts for both sessions in parallel, and render a two-column alert feed below the heatmap grid that advances with timeline playback—expert column stays mostly empty, novice column populates with rule-triggered alerts. Alert count summary visible above the feed (dynamic as playback advances). Critical alerts trigger a brief full-column highlight for demo visibility. Clickable alert cards seek the timeline to that moment and pause. Add a hardcoded "Expert vs Novice" button on the compare landing page for self-serve demo entry.

---

## Current State vs Expected Outcome

### Current State
- Compare page shows side-by-side heatmaps + delta; timeline slider drives playback
- Alerts only exist live via WebSocket (`/ws/realtime-alerts`) and `simulate_realtime` script
- No way to see what alerts would have fired for a stored session during replay
- `fetchSession` returns frames only; no alert data
- Compare landing has two raw text inputs; an investor with a forwarded link must know session IDs to type in
- No way to recover a missed critical flash during playback

### Expected Outcome
- **Backend:** `GET /api/sessions/{session_id}/alerts` returns `{ alerts: AlertPayload[] }`
- **Frontend:** Compare page fetches `alertsA` and `alertsB` alongside sessions; shows alert feed below heatmaps
- **Expert vs Novice demo button:** On compare landing (`my-app/src/app/compare/page.tsx`), add a prominent "Expert vs Novice" button that navigates to `/compare/sess_expert_001/sess_novice_001`. Hardcoded IDs match seeded mock sessions. Makes the demo self-serve—one click from a shared link.
- **Alert count summary:** Above the feed, two columns show "Alerts: N" per session. N = count of alerts where `alert.timestamp_ms <= currentTimestamp`. Visible immediately on load (N may be 0); updates dynamically as `currentTimestamp` advances during playback
- Alert feed: two columns (Session A | Session B), filtered by `currentTimestamp`; only alerts where `alert.timestamp_ms <= currentTimestamp`, newest first
- **Clickable alert cards:** Each card is clickable. `onClick` sets `currentTimestamp` to `alert.timestamp_ms` and `setIsPlaying(false)`. Allows recovery if someone missed the critical flash; enables demo flow: "watch this one" → click → seek → column flashes (if critical) → explain the haptic
- Each alert card: human label (rule1→"Thermal asymmetry", rule2→"Torch angle", rule3→"Travel speed"), severity badge (warning=amber, critical=red), message
- **Critical alert highlight:** When a new critical alert enters the visible list during playback (or when seeking via card click), apply a brief full-column highlight (e.g. 0.5–1s red/amber glow on the entire column container, not just the card). Makes the moment unmissable in a live demo with someone watching
- Non-critical new alert entering list: brief card highlight
- Hardcoded tag `"⚡ Haptic → gun"` on each card
- Expert session column: nearly empty; novice column: populated with alerts

---

## Relevant Files

| File | Action |
|------|--------|
| `backend/routes/sessions.py` | Add `GET /sessions/{session_id}/alerts` handler; load up to 2000 frames (same cap as compare page), run AlertEngine, return `{ alerts: AlertPayload[] }` |
| `my-app/src/lib/api.ts` | Add `fetchSessionAlerts(sessionId)` using same `buildUrl` / `apiFetch` pattern as `fetchSession` |
| `my-app/src/app/compare/page.tsx` | Add "Expert vs Novice" button that links to `/compare/sess_expert_001/sess_novice_001`; place prominently above or beside the form |
| `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` | Parallel fetch alerts; add `alertsA`, `alertsB` state; add alert count summary above feed; add AlertFeed with clickable cards (onClick seeks + pauses), full-column critical highlight |
| `my-app/src/types/` | Optional: add `AlertPayload` / `SessionAlertsResponse` types to mirror backend (or inline in page) |

---

## Implementation Notes

### Backend
- Use existing `FrameModel` query ordered by `timestamp_ms` ascending (same pattern as `get_session`)
- **Apply explicit 2000-frame cap** — same limit as the compare page uses when fetching sessions. Do not default to all frames; without this cap, large sessions (e.g. 30k frames) will be slow and the demo won't noticeably improve.
- Convert each frame to `FrameInput`: `frame_index` = loop index; `timestamp_ms` = `frame.timestamp_ms` (from frame data); `ns_asymmetry` = north−south at 10mm (reuse logic from `simulate_realtime._ns_asymmetry_from_frame`); `travel_angle_degrees` / `travel_speed_mm_per_min` from frame (may be `null`—AlertEngine skips rules 2/3 when null)
- Run `AlertEngine.push_frame(fin)` for each frame; collect all `AlertPayload`; return `{ "alerts": [...] }`
- Router: sessions router (same prefix as `/sessions/{session_id}`)
- **Do not** modify `AlertEngine` or `alert_models.py`

### Frontend

**Expert vs Novice demo button (compare landing)**
- In `my-app/src/app/compare/page.tsx`, add a `<Link href="/compare/sess_expert_001/sess_novice_001">` button
- Label: "Expert vs Novice" (or "Quick demo: Expert vs Novice")
- Place above the form or as a primary CTA; investor with `/compare` link sees it immediately
- IDs: `sess_expert_001` (expert), `sess_novice_001` (novice) — match `backend/routes/dev.py` seed and `backend/data/mock_sessions.py`

**Alert count summary (above feed)**
- Render before the alert feed, above the two-column grid
- Per column: "Session A: X alerts" / "Session B: X alerts"
- X = `alerts.filter(a => a.timestamp_ms <= currentTimestamp).length`
- Visible on load (X = 0 if timeline at start); updates when `currentTimestamp` changes (slider, playback, card click)

**Alert feed**
- `fetchSessionAlerts` follows `fetchSession` pattern: `buildUrl`, `apiFetch`, error handling
- Combine with session fetch: `Promise.all([fetchSession(A), fetchSession(B), fetchSessionAlerts(A), fetchSessionAlerts(B)])` or equivalent
- Filter alerts: `alerts.filter(a => a.timestamp_ms <= currentTimestamp)`; sort newest first
- Rule label map: `rule1` → `"Thermal asymmetry"`, `rule2` → `"Torch angle"`, `rule3` → `"Travel speed"`

**Clickable alert cards**
- Each card: `onClick={() => { setCurrentTimestamp(alert.timestamp_ms); setIsPlaying(false); }}`
- Callbacks `setCurrentTimestamp` and `setIsPlaying` must be passed into the AlertFeed / column component from the compare page (they already exist)
- Add `cursor-pointer` and hover state (e.g. `hover:bg-zinc-100 dark:hover:bg-zinc-800`) so cards are clearly interactive
- When user clicks, timeline seeks; if the clicked alert is critical, full-column flash still triggers (visibility change from seek)

**Critical alert full-column highlight**
- Track previous set of visible alert IDs (or `timestamp_ms` of last-seen alerts) per column
- When `visibleAlerts` changes: if any new alert has `severity === "critical"`, set a state flag e.g. `columnACriticalFlash: true` or `columnBCriticalFlash: true`
- Apply a CSS class to the entire column container: e.g. `ring-4 ring-red-500 bg-red-50 dark:bg-red-950/30 animate-pulse` or similar, with `transition` and `duration-500`–`duration-1000`
- Clear the flag after 500–1000ms (e.g. `setTimeout` or CSS animation end)
- Full-column = the `<div>` wrapping that session's alert cards, not individual cards
- Must also trigger when seeking via card click (user clicks critical alert → seek → that alert becomes visible → flash)

**Other**
- Non-critical new alert: brief card-level highlight (e.g. `animate-pulse` on the card for 1–2s)
- Hardcoded tag `"⚡ Haptic → gun"` on each card
- **Do not** add WebSocket; this is pre-computed
- **Max 1–2 Canvases:** HeatMap uses Canvas; AlertFeed is DOM-only (no new Canvas)

### Frame Data Mapping
DB frames may lack `travel_angle_degrees` / `travel_speed_mm_per_min` for older sessions. AlertEngine handles null (rules 2 and 3 skip). `ns_asymmetry` must be computed from `thermal_snapshots`; 0 when no thermal data.

---

## Verification

1. **Backend:** `GET /api/sessions/{session_id}/alerts` returns JSON with `alerts` array. For mock novice session (`sess_novice_001`), `alerts.length` > 0; for mock expert session (`sess_expert_001`), `alerts.length` is small or 0. Response time acceptable for 2000 frames (< ~5s).
2. **Expert vs Novice button:** From `/compare`, click "Expert vs Novice" → navigates to `/compare/sess_expert_001/sess_novice_001`. Sessions load; alert feed populates for novice column.
3. **Alert count summary:** On load with `currentTimestamp` at first frame, both columns show "0 alerts" (or correct filtered count). Scrubbing timeline forward increases count for novice column; expert stays low.
4. **Clickable alert cards:** Click an alert card → timeline seeks to `alert.timestamp_ms`, playback pauses. Heatmaps update to that timestamp. If clicked alert is critical, full-column flash triggers.
5. **Full-column critical highlight:** During playback, when a critical alert first appears in novice column, the entire column flashes (red/amber). Same behavior when seeking via card click to a critical alert. Flash lasts 0.5–1s.
6. **No new Canvas:** Page still uses existing HeatMap Canvas instances; no additional WebGL/Canvas contexts.

---

## Risk & Notes

- **Session size:** 2000-frame cap is mandatory (see Backend notes). Uncapped runs on large sessions would be slow without noticeable demo improvement.
- **Rule labels:** Hardcoded string map; future rule expansion (rule4+) would need mapping update.
- **Haptic tag:** Placeholder; no backend wiring yet.
- **Expert vs Novice IDs:** If seed changes, update the button href. Document dependency: `POST /api/dev/seed-mock-sessions` must be run for sessions to exist.

---

## How This Furthers the Product Vision

From [vision.md](.cursor/product/vision.md): *"Alerts that catch real technique deviations before they become defects"* and *"Comparison that makes expert technique legible"*. This brings rule-based alerts into the compare flow, so stakeholders see exactly when and why the novice session triggered alerts during playback—making the expert vs novice story tangible. The alert count summary, full-column critical highlight, and clickable cards make the demo legible and navigable at a glance. The "Expert vs Novice" button turns a shared `/compare` link into a self-serve demo—no need for the presenter to drive it every time.
