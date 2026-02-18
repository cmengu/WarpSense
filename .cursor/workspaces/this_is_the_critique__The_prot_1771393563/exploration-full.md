
Technical exploration is done and written to `.cursor/explore/critique-fixes-exploration.md`.

## Summary

**Complexity:** Simple — small plan tweaks plus localized code edits.

**Findings:**

1. **prototype_arc_scoring.py** (`backend/scripts/prototype_arc_scoring.py`) — Uses `make_session_for_arc` with its own signal logic, not the planned `generate_session_for_welder`. Should switch to the production path.

2. **seed_demo_data.py** (`backend/scripts/seed_demo_data.py`) — Skips when `existing > 0` instead of `existing == expected_count`. No spot-check; needs one using `session_ids[0]` and the first archetype.

3. **seagull/page.tsx** — Already shows “Loading scores...” while fetching; needs explicit skeleton/card placeholders instead of empty scores during load.

4. **ai-feedback.ts** — Trend logic is fine. Caller must pass `sc.total` for the last slot when building `historicalScores`; passing 0 yields incorrect “declining” for fast_learner.

5. **ai-feedback.test.ts** — Add a test: when historicalScores is `[72, 0]`, trend is `"declining"`, documenting the contract.

**Recommendation:** Option A — apply all fixes in a single pass, in both the plan doc and the code.

**Effort:** ~7h (plan updates ~1.5h, prototype + seed_demo_data ~1.5h, loading state ~0.5h, last-slot + tests ~1h, review ~2h).

**Blockers:** None. Assumptions: plan doc is editable; skeleton can be simple pulse/placeholders.

The exploration doc includes full Codebase Findings, Edge Cases, Risk Analysis, and an Exploration Summary (Section 11) for direct use in planning.
