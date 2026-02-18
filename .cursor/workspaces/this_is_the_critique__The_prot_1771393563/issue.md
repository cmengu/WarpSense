
Created the issue specification at `.cursor/issues/10-mock-welders-plan-critique-fixes.md`. Summary:

## Summary

**Title:** `[Improvement] Add critique mitigations to 10 Mock Welders plan — tuning guide, archetype sync, spot-check fix, loading state, last-slot test`

**Scope:** All 5 main critique items plus 4 minor ones, mapped to concrete fixes.

| Critique | Fix |
|----------|-----|
| **P1** Prototype lacks tuning guidance | Add tuning guide to Step 1.4 (e.g. fast_learner low → tighten `_arc_angle_tight` stddev). Add note to run prototype in a fresh Python process or re-seed before each `PASS_BAND` check. |
| **P2** WELDER_ARCHETYPES duplicated in 3 files | Add Phase 3 pre-flight: “Verify WELDERS in page.tsx matches WELDER_ARCHETYPES.” |
| **P3** seed_demo_data spot-check flaw | Use `session_ids[0]` and first archetype’s `operator_id` instead of hardcoded `sess_mike-chen_001`; run spot-check in both full-seed and re-seed branches. |
| **P4** Phase 3 no loading state | Update Step 3.2: cards show skeleton/spinner while loading; `setWelderScores` only after `Promise.allSettled`. |
| **P5** Step 5.3 underspecified | Add tests in `ai-feedback.test.ts` for the last-slot behavior (0 vs `sc.total`), or state clearly that verification is manual-only. |
| Minor | Use `typing.Tuple` for Python 3.8; fold Step 2.3 into Step 2.1; document wipe vs seed delete behavior; document badge flicker with ±2 noise. |

**Classification:** Improvement, P1, ~9h effort.

**Relevant files:**

- `backend/scripts/prototype_arc_scoring.py` — currently uses `make_session_for_arc` (non-production path)
- `backend/scripts/seed_demo_data.py` — still seeds 2 sessions only
- `my-app/src/app/seagull/page.tsx` — WELDERS = 2 entries, has loading state
- `my-app/src/app/seagull/welder/[id]/page.tsx` — WELDER_MAP, MOCK_HISTORICAL hardcoded
- `my-app/src/__tests__/lib/ai-feedback.test.ts` — target for last-slot tests
