
Updated **CONTEXT.md** to document the investor-grade demo. Summary of changes:

## CONTEXT.md changes

1. **Current State** – Added: "Investor-grade demo (guided tour, team dashboard, Seagull path)"

2. **Implemented Features** – Documented:
   - **Investor-Grade Demo** – Guided tour, CTA to team, browser-only team path; locations, patterns, and integrations
   - **`computeMinMaxTemp`** – New utility in `utils/heatmapTempRange.ts`

3. **Patterns** – Added:
   - **Demo Config** – Single source of truth in `demo-config.ts`
   - **Demo Tour Overlay** – Custom overlay, debounced scrub, z-index

4. **Component APIs** – Documented DemoTour props and requirements

5. **File Structure** – Documented:
   - `app/demo/team/` – Team dashboard and welder reports
   - `app/seagull/` – Seagull pilot path
   - `components/demo/` – DemoTour
   - `lib/demo-config.ts`, `lib/demo-tour-config.ts`, `lib/seagull-demo-data.ts`
   - `utils/heatmapTempRange.ts`

6. **Last updated** – 2025-02-17

---

## Current investor-grade demo implementation

From the codebase, these pieces are in place:

| Component | Status |
|-----------|--------|
| **Demo Tour** | DemoTour with 4 steps (intro → expert → novice spike @ 2.4s → scores) |
| **CTA** | "See Team Management →" linking to `/demo/team` |
| **Team Dashboard** | `/demo/team` with Mike Chen (42) and Expert Benchmark (94) cards |
| **Welder Report** | `/demo/team/[welderId]` with HeatMap, FeedbackPanel, LineChart, PlaceholderHeatMap |
| **AppNav** | "Team" link to `/seagull` |
| **Config** | `demo-config.ts`, `demo-tour-config.ts`, `seagull-demo-data.ts` |

Run `npm test` in `my-app` to confirm the demo tests pass.
