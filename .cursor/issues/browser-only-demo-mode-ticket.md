# Browser-Only Demo Mode

**Type:** Feature  
**Priority:** High  
**Effort:** Medium  
**Labels:** `frontend` `demo` `replay` `zero-setup`  
**Status:** In progress — `demo-data.ts` done, demo page pending

---

## TL;DR
Self-contained demo at `/demo` — 100% in-browser, no backend/DB/seed. One link for prospects, any device, LinkedIn-ready.

## Current vs Expected

| | Current | Expected |
|---|--------|----------|
| **Flow** | Run uvicorn + Postgres → seed script → navigate to `/replay/sess_expert_001` → explain stack | Open `/demo` → side-by-side expert vs novice replays with scores |
| **Portability** | Laptop with backend + DB only | Any device (phone, tablet, laptop); shareable link |
| **Time to value** | Minutes (setup + navigation) | ~30 seconds (click link, see replay) |
| **Implemented** | `demo-data.ts` ✅, tests ✅ | `app/demo/page.tsx` not yet built |

## Relevant Files
- `my-app/src/lib/demo-data.ts` ✅ — done; port from `backend/data/mock_sessions.py`
- `my-app/src/app/demo/page.tsx` — **TODO** — layout + playback integration
- Reuse as-is: HeatMap, TorchViz3D, TorchAngleGraph, extractHeatmapData, extractAngleData, frameUtils

## Risks & Notes
- TS thermal model may diverge from Python; unit test parity recommended
- Bundle ~200KB acceptable
- ScorePanel fetches via API — use inline score blocks (94/100, 42/100) instead

## Vision
Replay + scoring with zero setup → prospects see value in ~30s. One URL to 100 prospects; works on any device. LinkedIn/social demos and ad-hoc customer demos on their machines.

---

*Full spec:* `browser-only-demo-mode.md`  
*Exploration notes:* `browser-only-demo-mode-exploration.md`
