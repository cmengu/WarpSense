
Refined plan is in place. Summary of changes:

**Critical updates**
1. **Automated tests (per .cursorrules)** – Every step now has Jest/RTL tests:
   - Step 1.2: `__tests__/app/demo/team/page.test.tsx` — 2 cards, scores 42/94, correct links
   - Step 1.3: `__tests__/app/demo/team/[welderId]/page.test.tsx` — report render with mocked data
   - Step 1.5: Invalid welderId covered in the same test file
   - Step 2.1: `__tests__/lib/demo-tour-config.test.ts`
   - Step 2.2: `__tests__/components/demo/DemoTour.test.tsx` — step advance, skip dismisses
   - Step 2.3: Extended `demo/page.test.tsx` — onStepEnter scrub, tour dismiss
   - Steps 3.1–3.3: CTA, AppNav, keyboard tests

2. **onStepEnter useCallback (Step 2.3)** – Step 2.3 now requires wrapping `onStepEnter` in `useCallback` and notes the fix in Common Failures and the Red team section.

3. **Step 1.2 code skeleton** – Full team dashboard code skeleton added, mirroring the Seagull grid layout, `DEMO_WELDERS`, and links to `/demo/team/[welderId]`.

**Minor updates**
- **Step 3.1:** CTA placement set to “in header div after title” with a specific code pattern.
- **Step 2.3:** `showTour` state location documented (DemoPageContent, with `playing`/`currentTimestamp`).
- **Phase times:** Phase headers aligned with totals (~7.5h, ~5h, ~2.5h).
- **Step 3.2:** AppNav Team link insertion point: “after Demo, before closing `</div>`” with code.
- **Step 1.3:** HeatMap empty-state behavior added to Common Failures (extractHeatmapData/thermal_snapshots).
