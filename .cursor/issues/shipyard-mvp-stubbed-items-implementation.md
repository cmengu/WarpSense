# Implement Shipyard MVP Stubbed Items

**Type:** Feature  
**Priority:** High  
**Effort:** Large  
**Status:** Ready  
**Reference:** `SHIPYARD_WELDING_MVP_PLAN.md` (lines 31–44, Implementation Plans)

---

## TL;DR

Implement all 10 stubbed items: wire Recharts to HeatMap and TorchAngleGraph, add replay controls, scoring system (extract_features + score_session + ScorePanel), GET /score endpoint, /compare page, WebSocket streaming, and comparison UI. Data pipeline is complete; charts and scoring currently show placeholders.

---

## Current State vs Expected

| Item | Current | Expected |
|------|---------|----------|
| HeatMap | Placeholder "coming soon" | Recharts grid: time × distance × temp, blue→red scale, tooltip |
| TorchAngleGraph | Placeholder "coming soon" | LineChart with angle over time, ref line 45°, tooltip |
| GET /api/sessions/{id}/score | 501 Not Implemented | JSON: `{total, rules}` from extract_features + score_session |
| extract_features | Returns `{}` | `{amps_stddev, angle_max_deviation, north_south_delta_avg, heat_diss_stddev, volts_range}` |
| score_session | Returns `total=0, rules=[]` | 5 rules; total = passed × 20 (max 100) |
| ScorePanel | "Coming soon" | Fetch score; total + per-rule ✓/✗ + threshold vs actual |
| /compare page | Does not exist | `app/compare/[a]/[b]` — Expert \| Delta \| Novice heatmaps, synced slider |
| Phase 2: Replay controls | None | currentTimestamp, slider, play/pause, speed 1×–10×, activeTimestamp on charts |
| Phase 4: WebSocket | Not started | `GET /ws/sessions/{id}/stream`; push on POST /frames |
| Phase 5: Comparison UI | Not started | Same as /compare; "Compare with…" link from replay page |

---

## Relevant Files

| Area | Files |
|------|-------|
| **Frontend — Charts** | `my-app/src/components/welding/HeatMap.tsx`, `TorchAngleGraph.tsx` |
| **Frontend — Replay** | `my-app/src/app/replay/[sessionId]/page.tsx` |
| **Frontend — API** | `my-app/src/lib/api.ts` (add `fetchScore`) |
| **Frontend — Score** | `my-app/src/components/welding/ScorePanel.tsx` |
| **Frontend — Compare** | `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` (new) |
| **Backend — Scoring** | `backend/features/extractor.py`, `backend/scoring/rule_based.py` |
| **Backend — Routes** | `backend/routes/sessions.py` (GET /score) |

---

## Implementation Order (by dependency)

1. **Phase 1:** HeatMap + TorchAngleGraph (after seed verified)
2. **Phase 2:** Replay controls (slider, play/pause, speed, keyboard)
3. **Phase 3:** extract_features → score_session → GET /score → ScorePanel *(blocked until domain expert sign-off on thresholds)*
4. **Phase 4:** WebSocket backend + frontend hook
5. **Phase 5:** /compare page + delta heatmap + synced playback

---

## Risks & Notes

- **Scoring thresholds:** Do not implement `extract_features` / `score_session` with guessed values. Roadmap rules: amps <15%, angle <5°, thermal <20°C, heat_diss <30, volts <2V — **validate with domain expert first.**
- **Recharts heatmap:** Use `ScatterChart` + `Scatter` + `Cell` with `tempToColor()` for heatmap; Recharts has no native heatmap. Alternative: grid of divs if scatter doesn’t fit.
- **WebSocket:** Needs session-specific fan-out; handle client disconnect without crashing ingestion.

---

## How This Furthers the Product

- **Charts:** Product becomes demoable — stakeholders see real heatmap and angle graphs.
- **Replay controls:** Operators can scrub and play sessions at variable speed for training review.
- **Scoring:** Trainees get actionable feedback (pass/fail per rule) instead of “coming soon.”
- **Comparison:** Trainers see expert vs novice side-by-side with delta overlay.
- **Live streaming:** Supervisors can watch welds in real time (Phase 4).
