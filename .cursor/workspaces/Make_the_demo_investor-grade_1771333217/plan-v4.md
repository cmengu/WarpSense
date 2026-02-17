
All five minor refinements from the critique are in place in the plan:

1. **Step 1.5** — Invalid welder check now uses `!DEMO_WELDERS.some((w) => w.id === welderId)` instead of `WELDER_MAP`.

2. **Pre-Flight** — Path convention updated for `src/` layout: use `src/app/demo/team/page.tsx` (prefix with `src/` for app, lib, and components).

3. **Step 2.3** — Verification clarifies how to spy/capture: use `jest.spyOn` on state setters, or pass mock callback props, or invoke the captured `onStepEnter` manually.

4. **Section 8 (Rollback)** — Rollback verification command is explicitly `cd my-app && npm test`.

5. **Step 3.1** — CTA placement is only “in header div after title” (the fixed top-right option removed).

The refined plan is saved at `.cursor/plans/investor-grade-demo-implementation-plan.md`.
