
The implementation plan is in `.cursor/issues/10-mock-welders-plan-critique-fixes-plan.md`. Summary:

## Implementation Plan: Critique Fixes for 10 Mock Welders

**Estimate:** 9h | **Steps:** 12 across 4 phases

### Phase 1 — Prototype & plan doc (2.5h)

| Step | Fix | Classification |
|------|-----|----------------|
| 1.1 | Replace `make_session_for_arc` with `generate_session_for_welder`; add tuning guide to script output | CRITICAL |
| 1.2 | Add tuning guide and fresh-process note to plan Step 1.4 | NON-CRITICAL |
| 1.3 | Add Phase 3 pre-flight: verify WELDERS matches WELDER_ARCHETYPES | NON-CRITICAL |
| 1.4 | Use `Tuple` for `generate_frames_for_arc` (Python 3.8) | NON-CRITICAL |
| 1.5 | Fold Step 2.3 into 2.1; document wipe vs seed delete | NON-CRITICAL |

### Phase 2 — Seed & spot-check (1.5h)

| Step | Fix | Classification |
|------|-----|----------------|
| 2.1 | Spot-check uses `session_ids[0]` + `WELDER_ARCHETYPES[0]["welder_id"]`; run in skip and re-seed branches | CRITICAL |
| 2.2 | Idempotent only on `existing == expected_count`; partial seed triggers re-seed | CRITICAL |

### Phase 3 — Dashboard & welder report (2h)

| Step | Fix | Classification |
|------|-----|----------------|
| 3.1 | Skeleton cards during load; single `setWelderScores` after `Promise.allSettled` | CRITICAL |
| 3.2 | Use `sc.total` for last slot in `historicalScores` | CRITICAL |
| 3.3 | Document badge flicker; optional ±2 dead zone | NON-CRITICAL |

### Phase 4 — Tests (1.5h)

| Step | Fix | Classification |
|------|-----|----------------|
| 4.1 | Add last-slot tests in `ai-feedback.test.ts` | CRITICAL |
| 4.2 | Update plan Step 5.3 with concrete test reference or manual-only note | NON-CRITICAL |

### Coverage of critique

- **P1:** Tuning guide + fresh-process note (Steps 1.1, 1.2)
- **P2:** Phase 3 pre-flight archetype sync (Step 1.3)
- **P3:** Spot-check logic and idempotency (Steps 2.1, 2.2)
- **P4:** Loading state spec (Step 3.1)
- **P5:** Last-slot fix and tests (Steps 3.2, 4.1, 4.2)
- **Minor:** `Tuple`, fold 2.3, wipe/seed note, badge flicker (Steps 1.4, 1.5, 3.3)

The plan includes verification steps, pass criteria, a risk heatmap, pre-flight checks, and success criteria. It can be run after the parent plan or folded into it as a single pass.
