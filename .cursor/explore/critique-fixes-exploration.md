# Exploration: Critique Fixes for 10 Mock Welders Plan

**Issue:** 10-mock-welders-plan-critique-fixes  
**Date:** 2026-02-18  
**Source:** `.cursor/issues/10-mock-welders-plan-critique-fixes.md` + plan critique

---

## 1. Complexity Classification

**State: Simple**

Justification: All fixes are incremental plan amendments and small code changes—no new features, no schema changes. Tuning guide and pre-flight are documentation; spot-check and loading state are localized edits; last-slot test is ~15 lines in an existing test file. The parent plan (10 mock welders) remains the primary effort; these fixes reduce demo-day failure risk.

---

## 2. Risk Profile

| Axis | Level | Reason |
|------|-------|--------|
| Data loss risk | Low | No data migration; mock data only |
| Service disruption risk | Low | Changes are additive; seed/wipe logic clarified, not replaced |
| Security risk | Low | No new endpoints or auth changes |
| Dependency risk | Low | No new packages; optional `typing.Tuple` for Python 3.8 |
| Rollback complexity | Low | Revert plan doc + code edits; no schema or deploy impact |

---

## 3. Codebase Findings

Searched for prototype, seed_demo_data, seagull pages, ai-feedback, mock_sessions, dev routes.

| File | What it does | Pattern | Reuse | Avoid |
|------|--------------|---------|-------|-------|
| `backend/scripts/prototype_arc_scoring.py` | Validates arc→score ranges via `make_session_for_arc` | Duplicate frame logic (arc_angle_tight, arc_angle_drift, etc.) inside prototype | Replace `make_session_for_arc` with `generate_session_for_welder` from mock_sessions | Do not keep duplicate signal generators; prototype must use production path |
| `backend/scripts/seed_demo_data.py` | Seeds sess_expert_001, sess_novice_001; idempotent on `existing > 0` | Skip if any exist | Change to `existing == expected_count`; add spot-check using `session_ids[0]` + first archetype | Do not use hardcoded sess_mike-chen_001 for spot-check |
| `my-app/src/app/seagull/page.tsx` | 2 welders; `Promise.allSettled(fetchScore)`; `loading` shows "Loading scores..." | Text loading state | Already has `loading`; add skeleton/card placeholders per critique | Do not show empty score values during load |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | WELDER_MAP (2 entries), MOCK_HISTORICAL [68,72,75], `generateAIFeedback(s, sc, [68,72,75])` | Hardcoded historical; no last-slot fix | Add `if i === lastIdx && sc != null` when building historicalScores | Do not use 0 for last slot when sc.total is available |
| `my-app/src/lib/ai-feedback.ts` | `generateAIFeedback(session, score, historicalScores)`; trend = last vs prev | `historicalScores[length-1]` vs `[length-2]` | Pure; no changes needed | Caller must pass correct last slot |
| `my-app/src/__tests__/lib/ai-feedback.test.ts` | Tests trend improving/declining/stable, empty guard, feedback_items | mockSession(), mockScore(), generateAIFeedback | Add test: `[72, 0]` → "declining" to document pitfall | No changes to lib |
| `backend/data/mock_sessions.py` | generate_expert_session, generate_novice_session, generate_frames, THERMAL_* | No `generate_frames_for_arc` yet | Plan adds it; prototype will call `generate_session_for_welder` | Ensure `tuple` vs `Tuple` for Python 3.8 if needed |
| `backend/routes/dev.py` | Seed/wipe for 2 sessions; loop delete; no `import random` | Uses `db.delete(existing)` in loop for seed; wipe uses `.delete(synchronize_session=False)` | Fold `import random` into seed step; note wipe vs seed delete inconsistency | Do not change delete semantics |

**Closest implementations (3+):**

1. **prototype_arc_scoring.py** — Uses `make_session_for_arc` (duplicate). Critique fix: use `generate_session_for_welder`; add tuning guide; seed before each PASS_BAND or fresh process.
2. **seed_demo_data.py** — Idempotent on `existing > 0` (wrong per plan). Critique fix: `existing == expected_count`; spot-check with `session_ids[0]` and `WELDER_ARCHETYPES[0]["welder_id"]` in both skip and re-seed paths.
3. **ai-feedback.test.ts** — Has trend tests. Critique fix: add "trend is declining when last slot is 0 and prev is higher" to document caller contract.

---

## 4. Known Constraints

- **Python:** Project specifies 3.10+; `tuple[List[Frame], bool]` requires 3.9+. Use `typing.Tuple` or `from __future__ import annotations` for 3.8 if required.
- **Next.js:** Client components; `params` can be Promise; hooks run unconditionally.
- **Loading state:** Must appear within ~200ms; cards should show skeleton, not "Score unavailable" during fetch.
- **generateAIFeedback:** Takes `historicalScores: number[]`; trend from last 2 elements. Caller (welder page) must pass `sc.total` for last slot when it's the current session—never 0.
- **Seed reproducibility:** `random.seed(42)` in seed route advances RNG; prototype run after seed (or in same process) sees different state. Fix: fresh process or seed inside prototype loop.
- **Badge flicker:** `score > secondScore` vs `score < secondScore` with ±2 noise causes plateaued/volatile to flip. Document or add ±2 dead zone.

---

## 5. Approach Options

### Option A: Apply all fixes to plan doc + code in single pass
- **Description:** Update plan-10-mock-welders-refined.md with tuning guide, pre-flight, Step 2.3 fold, wipe/seed note, badge flicker note; update prototype, seed_demo_data, Step 3.2 loading spec, Step 5.3 concrete test; add ai-feedback test.
- **Pros:** Single PR; all mitigations in one place; planner has complete picture.
- **Cons:** Larger diff; depends on parent plan being the source of edits.
- **Key risk:** Plan file may be regenerated; fixes could be overwritten.
- **Complexity:** Low

### Option B: Create separate critique-fixes plan
- **Description:** New document `critique-fixes-plan.md` with only the 5 main + 4 minor fixes, cross-referencing parent plan steps.
- **Pros:** Isolated; can merge independently; survives plan regeneration.
- **Cons:** Two documents to maintain; possible drift.
- **Key risk:** Planner might miss cross-refs.
- **Complexity:** Low

### Option C: Fixes-only branch (no plan doc changes)
- **Description:** Implement only code fixes (prototype, seed_demo_data, loading state, last-slot, ai-feedback test); leave plan doc for manual update.
- **Pros:** Delivers executable mitigations fast.
- **Cons:** Tuning guide and pre-flight live only in issue spec; implementers may not see them.
- **Key risk:** Plan stays vague; tuning guidance lost.
- **Complexity:** Low

### Option D: Plan doc first, code when parent plan executes
- **Description:** Update plan doc with all critique fixes now; defer code changes until parent 10-mock-welders plan is executed (prototype/seed/loading/test are part of parent steps).
- **Pros:** Plan is correct for next executor; no double work.
- **Cons:** seed_demo_data and prototype exist today with wrong logic; fixing only at execution delays mitigation.
- **Key risk:** Executor might skip or miss critique fixes in long plan.
- **Complexity:** Low

---

## 6. Prototype Results

### Prototype 1: last-slot ai-feedback behavior
- **What was tested:** `generateAIFeedback` trend when last slot is 0 vs real score.
- **Code:** `generateAIFeedback(mockSession(), mockScore({total: 78}), [72, 0])` and `generateAIFeedback(..., [72, 78])`.
- **Result:** From `ai-feedback.ts` (lines 62–71): trend compares `historicalScores[last]` vs `historicalScores[last-1]`. `[72, 0]` → 0 < 72 → "declining"; `[72, 78]` → 78 > 72 → "improving". Confirmed.
- **Decision:** Proceed. Add test for `[72, 0]` → "declining" to document contract; welder page must use `sc.total` for last slot.

### Prototype 2: seed_demo_data spot-check derivation
- **What was tested:** Whether `session_ids[0]` and `WELDER_ARCHETYPES[0]["welder_id"]` are always valid.
- **Result:** `session_ids` is built by looping archetypes and appending `sess_{welder_id}_{i:03d}`. First ID is `sess_{first_arch["welder_id"]}_001`. So `session_ids[0]` and `WELDER_ARCHETYPES[0]["welder_id"]` are always aligned. Valid regardless of which welders exist.
- **Decision:** Proceed. Use `session_ids[0]` and first archetype for spot-check.

### Prototype 3: Prototype uses duplicate logic
- **What was tested:** Does prototype use `make_session_for_arc` (duplicate) or `generate_session_for_welder` (production)?
- **Result:** `prototype_arc_scoring.py` defines `arc_angle_tight`, `arc_angle_drift`, `arc_amps_stable`, etc., and `make_session_for_arc`. It does NOT import `generate_session_for_welder` (which does not exist yet). Confirms critique: prototype validates a different code path.
- **Decision:** Proceed. Parent plan creates `generate_session_for_welder`; critique fix requires prototype to replace `make_session_for_arc` with that.

---

## 7. Recommended Approach

**Chosen approach:** Option A (apply all fixes to plan doc + code in single pass)

**Justification:** The critique fixes are tightly coupled to the parent plan steps. Folding them into the plan ensures the executor sees tuning guidance, pre-flight, and loading-state spec in context. The code changes (prototype, seed_demo_data, ai-feedback test) are small and can be delivered as part of the same work. A separate document (Option B) risks being overlooked; code-only (Option C) loses tuning and pre-flight; deferring (Option D) leaves prototype and seed_demo_data with known bugs until execution. Option A gives a single source of truth: updated plan with embedded critique mitigations, and code that matches. Trade-off: plan doc gets longer; we accept that for completeness.

**Trade-offs accepted:**
- Plan doc grows; some steps gain 2–4 lines (tuning guide, pre-flight).
- Spot-check runs on every seed (full and re-seed); adds ~1 DB query.
- ai-feedback test documents pitfall rather than asserting caller behavior (caller test would be in welder page).

**Fallback approach:** Option B. If plan doc is auto-generated or locked, create `critique-fixes-plan.md` and implement code fixes independently.

---

## 8. Architecture Decisions

**Decision: Prototype uses production path**
- Options: Keep `make_session_for_arc`, add `generate_session_for_welder` alongside, use `generate_session_for_welder` only
- Chosen: Use `generate_session_for_welder` only; remove duplicate logic from prototype
- Reason: Single code path; prototype validates what seed produces
- Reversibility: Easy
- Downstream impact: Prototype must run after Step 1.3; pass-band assertions validate real implementation

**Decision: Tuning guide content**
- Options: Generic "tune angle/amps/volts", symptom→param mapping, external doc
- Chosen: Add to Step 1.4: "fast_learner scores low → tighten _arc_angle_tight stddev; declining scores high → increase _arc_angle_drift drift_factor"
- Reason: Actionable; implementer knows what to change
- Reversibility: Easy
- Downstream impact: None

**Decision: Spot-check sample**
- Options: Hardcoded sess_mike-chen_001, session_ids[0], random sample
- Chosen: session_ids[0] and WELDER_ARCHETYPES[0]["welder_id"]
- Reason: Always valid; survives archetype reorder/removal
- Reversibility: Easy
- Downstream impact: Spot-check runs in both skip and re-seed branches

**Decision: Loading state spec**
- Options: No spec, "Loading...", skeleton/spinner
- Chosen: Cards show skeleton/spinner during load; setWelderScores once after Promise.allSettled
- Reason: Avoids "Score unavailable" flash; explicit in Step 3.2
- Reversibility: Easy
- Downstream impact: May need simple Skeleton or placeholder component

**Decision: Last-slot test location**
- Options: ai-feedback.test.ts, welder page test, manual only
- Chosen: ai-feedback.test.ts — "trend is declining when last slot is 0 and prev is higher"
- Reason: Documents contract; low cost; same pattern as existing tests
- Reversibility: Easy
- Downstream impact: None

**Decision: Python type annotation**
- Options: tuple[...], Tuple[...], from __future__ import annotations
- Chosen: `typing.Tuple` or `from __future__ import annotations` if Python 3.8 support needed
- Reason: Project uses 3.10+; defensive for CI or legacy envs
- Reversibility: Easy
- Downstream impact: None

---

## 9. Edge Cases

| Category | Scenario | How chosen approach handles | Graceful? |
|----------|----------|------------------------------|-----------|
| Empty/missing | archetypes list empty | Spot-check would fail; WELDER_ARCHETYPES has 10 entries | N/A (invariant) |
| Empty/missing | historicalScores = [] | generateAIFeedback returns "insufficient_data" | Graceful |
| Empty/missing | One fetchScore returns null | Promise.allSettled; card shows "Score unavailable" | Graceful |
| Empty/missing | session_ids[0] not in DB after partial seed | Spot-check catches; re-seed triggered | Graceful |
| Max scale | 20 fetchScore calls | 5s timeout; allSettled; single setWelderScores | Graceful |
| Max scale | 10 welders × 2 scores = 20 fetches | Same | Graceful |
| Concurrent | User navigates away during fetch | mounted check; no setState after unmount | Graceful |
| Concurrent | Rapid refresh of /seagull | Each run has own mounted; previous aborted | Partial (no abort controller) |
| Network | All 20 fetches timeout | Cards show "Score unavailable"; no crash | Graceful |
| Network | Backend cold start 4s | Skeleton visible; then scores populate | Graceful |
| Network | Expert fetch 404 | Promise.allSettled; welder report shows without expert | Graceful |
| Browser | React 18 batching | setWelderScores once → 1 re-render | Graceful |
| Browser | Slow device | Skeleton appears; 5s timeout limits hang | Partial |
| Session | ENV≠development, seed called | 403; no seed | Graceful |
| Session | Partial seed 44/45, run seed_demo_data | Re-seed branch; spot-check on session_ids[0] | Graceful |
| Tuning | fast_learner scores 38 | Tuning guide: tighten _arc_angle_tight | Partial (manual) |
| Tuning | Prototype run after seed in same process | Plan note: fresh process or seed before each PASS_BAND | Partial (documented) |

---

## 10. Risk Analysis

| Risk | Prob | Impact | Early warning | Mitigation |
|------|------|--------|---------------|------------|
| Tuning guide wrong for actual scoring rules | Med | Med | Scores still out of band after tuning | Guide is heuristic; prototype + test catch drift; iterate |
| Pre-flight not run before demo | Med | High | Archetype mismatch at demo | Add to Pre-Flight Checklist; remind in deploy runbook |
| Spot-check passes incorrectly for edge archetype order | Low | Med | Wrong operator_id in DB | Use session_ids[0] + first archetype; always aligned |
| Last-slot test fragile if generateAIFeedback semantics change | Low | Low | Test fails on refactor | Update test with semantic change; doc contract |
| ±2 dead zone changes badge semantics | Low | Med | Product disagrees with "stable" range | Document first; dead zone optional; product approves |
| Python 3.8 not in use | Low | Low | CI fails on 3.8 | Project uses 3.10+; Tuple fix defensive |
| Prototype still uses wrong path after fix | Low | High | Seed scores ≠ prototype scores | Verification step: prototype must import from mock_sessions |
| Loading skeleton delays perceived performance | Low | Low | User sees skeleton >2s | 5s timeout; backend perf separate concern |
| Plan doc overwritten by regeneration | Med | Med | Critique fixes disappear | Option B fallback: separate critique-fixes doc |
| seed_demo_data idempotent logic wrong | Low | High | Skip when should re-seed | Test: 44/45 exists → re-seed; 45/45 → skip |
| **CRITICAL:** Badge shows wrong state (e.g. declining for fast_learner) | Med | High | Demo-day failure | Last-slot fix + test; pre-flight archetype sync |

---

## 11. Exploration Summary

**Files to create:**
- None (all edits to existing files)

**Files to modify:**
- `.cursor/taskspace/20260218_130707/plan-10-mock-welders-refined.md` — Add tuning guide to Step 1.4; add fresh-process/seed note; add Phase 3 pre-flight; fold Step 2.3 into 2.1; note wipe vs seed delete; note badge flicker in Step 3.3; add loading state spec to Step 3.2; add concrete Step 5.3 test or "manual only"; fix tuple→Tuple for Python 3.8 if applicable
- `backend/scripts/prototype_arc_scoring.py` — Replace `make_session_for_arc` with `generate_session_for_welder`; add `random.seed(42)` before each PASS_BAND or document fresh process
- `backend/scripts/seed_demo_data.py` — Switch to WELDER_ARCHETYPES loop; `existing == expected_count` for skip; spot-check with `session_ids[0]` and first archetype in both branches; re-seed when partial
- `my-app/src/app/seagull/page.tsx` — Add skeleton/card placeholder during load (when parent plan adds 10 welders); ensure setWelderScores once after allSettled
- `my-app/src/app/seagull/welder/[id]/page.tsx` — Use `sc.total` for last slot when building historicalScores (when parent plan adds historical fetch)
- `my-app/src/__tests__/lib/ai-feedback.test.ts` — Add test: "trend is declining when last slot is 0 and prev is higher"

**New dependencies:** none

**Bundle impact:** 0 KB (no new packages)

**Critical path order:**
1. Parent plan Step 1.1–1.3 (mock_welders, generate_frames_for_arc, generate_session_for_welder)
2. Update prototype to use generate_session_for_welder + tuning guide + seed note
3. Parent plan Step 2.1–2.2 (seed/wipe routes)
4. Update seed_demo_data (archetypes, idempotent, spot-check)
5. Parent plan Step 3.1–3.3 (dashboard)
6. Add loading state spec + skeleton to Step 3.2
7. Parent plan Step 4.x (welder report)
8. Add last-slot fix (sc.total for last index) + ai-feedback test
9. Parent plan Step 5.x; add concrete Step 5.3 test

**Effort estimate:** Plan doc 1.5h + prototype update 0.5h + seed_demo_data 1h + loading state 0.5h + last-slot + ai-feedback test 1h + Python/comments 0.5h + Review 2h = **Total ~7h**, confidence 80%

**Blockers for planning:**
- None. Issue spec and critique mapping are complete.
- Assumption: Plan doc is editable; if not, use Option B (separate critique-fixes doc).
- Assumption: Skeleton can be simple (e.g. div with animate-pulse or existing Loading text); no new component required if "Loading scores..." in card layout is acceptable per critique.
