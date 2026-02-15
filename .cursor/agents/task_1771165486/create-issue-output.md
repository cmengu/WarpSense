---
name: create-issue-output
model: composer-1.5
---


Updated the **browser-only-demo-mode-ticket** and synced it with the full spec in `browser-only-demo-mode.md`.

**Changes made:**
- Set **Status** to: `In progress — demo-data.ts done, demo page pending`
- Added an **Implemented** row in the Current vs Expected table
- Marked `demo-data.ts` as done and `app/demo/page.tsx` as **TODO**

**Summary:**
- **TL;DR:** Self-contained demo at `/demo` — 100% in-browser, no backend/DB/seed.
- **Next step:** Add `my-app/src/app/demo/page.tsx` (layout + side-by-side playback).
- **Labels:** feature, high priority, medium effort; frontend, demo, replay, zero-setup.
- **Risks:** TS thermal model may diverge from Python; use inline scores (avoid ScorePanel API).

Full implementation details are in `browser-only-demo-mode.md`.
