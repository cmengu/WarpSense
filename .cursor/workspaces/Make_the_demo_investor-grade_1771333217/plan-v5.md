
Refinements from the critique are applied. The plan at `.cursor/plans/investor-grade-demo-implementation-plan.md` is updated as follows:

**1. Path convention (`src/` prefix)**  
All step-level `Files` lines and verification test paths now use the `src/` layout:
- `src/lib/seagull-demo-data.ts`
- `src/app/demo/team/page.tsx`
- `src/app/demo/team/[welderId]/page.tsx`
- `src/lib/demo-tour-config.ts`
- `src/components/demo/DemoTour.tsx`
- `src/components/AppNav.tsx`
- `src/__tests__/...` for all test files  
Rollback, failure-mode hints, Risk Heatmap, and “404” notes use the same paths.

**2. Viewport alignment (375px)**  
All 320px references are updated to 375px:
- Risk #5, Gap #2, C. Risk-Based Planning, Risk Heatmap (3.3), Step 3.3 subtasks

**3. Step 3.3 verification (viewport + keyboard)**  
- New subtask: at 375px, overlay visible, no horizontal overflow, buttons accessible  
- New verification: render at 375px and assert overlay visibility, title/body, and buttons in DOM and usable

**4. Optional documentation step (Step 3.4)**  
- New optional step: if investor-facing docs exist (README, docs/), add a short “Investor Demo” section describing `/demo`, tour, CTA, and `/demo/team`  
- Phase 3 time estimate set to ~2.5–3h to cover optional Step 3.4

**5. Step 2.2 Files line**  
- Added `**Files:** Create `src/components/demo/DemoTour.tsx`` for consistency
