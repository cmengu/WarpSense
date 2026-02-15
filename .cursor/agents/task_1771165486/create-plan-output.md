
Summary of the plan document:

## Plan Document Created

**Location:** `.cursor/plans/browser-only-demo-mode-plan.md`

### High-level summary

Self-contained demo at `/demo`, fully in the browser: side-by-side expert vs novice welding replays with scores. No backend, DB, or seed; single shareable link.

### Architecture decisions (no code)

1. **Simplified TypeScript thermal model** — `150 + arc_power/50`, `exp(-distance_mm/100)`; no Python parity yet.
2. **Hardcoded scores** — 94/100 (expert), 42/100 (novice); no ScorePanel API changes.
3. **Separate `/demo` route** — no `/replay?demo=1`.
4. **Responsive grid** — `grid-cols-1 md:grid-cols-2` for mobile.
5. **Playback end behavior** — Reset to 0 and stop; user clicks Play to restart.

### Step status

| Step | Status | Description |
|------|--------|-------------|
| 1 | Done | `demo-data.ts` — thermal model, expert/novice generators |
| 2 | To Do | Demo page — layout, playback, component integration |
| 3 | Done | Unit tests — `demo-data.test.ts` |
| 4 | To Do | Responsive layout |
| 5 | To Do | ErrorBoundary and edge cases |
| 6 | To Do | Zero-API verification |

**Progress:** 33% (2/6 steps)

### Code review placement

- **Step 1** — Critical: data generation, thermal model (full review with code, risks, verification).
- **Step 2** — Critical: new route, state, component wiring (full review with code, risks, verification).
- **Steps 3–6** — Non-critical: verification tests only.

### Verification tests

Each step includes:

- **Action** — What to run or do
- **Expected** — Expected result
- **How to observe** — Where to look (UI, Network, Jest)
- **Pass** — Success criteria
- **Fail** — Typical causes and fixes

### Extra sections

- Pre-flight checklist (dependencies per phase)
- Risk heatmap (thermal model, frame shape, WebGL)
- Success criteria for end-to-end checks

The plan matches `browser-only-demo-mode.md` and the existing codebase. `demo-data.ts` and its tests are present; the demo page (`app/demo/page.tsx`) still needs to be implemented.
