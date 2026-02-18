# Plan Critique Fixes — 10 Mock Welders With Skill Arcs

**Type:** Improvement  
**Priority:** P1  
**Effort:** M (8–12h)  
**Status:** Open  
**Parent:** 10-mock-welders-with-skill-arcs  

---

## 1. Title

`[Improvement] Add critique mitigations to 10 Mock Welders plan — tuning guide, archetype sync, spot-check fix, loading state, last-slot test`

---

## 2. TL;DR

The 10 Mock Welders implementation plan has five substantive gaps identified by critique: (1) Step 1.4 prototype has no tuning guide—implementers thrash blindly when scores drift; (2) WELDER_ARCHETYPES is duplicated in three files with no drift check; (3) seed_demo_data.py spot-check uses a hardcoded welder ID and runs only on the happy path; (4) Phase 3 fetches 20 scores with no loading-state spec; (5) Step 5.3 last-slot historicalScores test is underspecified and covers a critical bug. Root cause: plan optimizes for completeness over operational robustness. Desired outcome: every critique fix applied so implementers have deterministic guidance and regression safety. Effort: ~10h (mostly folded into plan execution).

---

## 3. Root Cause Analysis

1. **Surface:** Plan passes verification but implementers hit hidden failures at demo time.
2. **Why:** Mitigations are vague ("tune angle/amps/volts") or deferred ("Follow-up: GET /api/dev/welders").
3. **Why that:** Plan was written for a green-field run; edge cases and tuning were under-specified.
4. **Why that:** Critique surfaced latent risks only after plan completion; no adversarial review loop.
5. **Root cause:** Plan treats prototype as a pass/fail gate without actionable remediation steps; treats data-source duplication as acceptable tech debt without a 2-minute pre-flight check.

---

## 4. Current State

**What exists today:**

| File / Component | Description |
|-----------------|-------------|
| `.cursor/issues/10-mock-welders-with-skill-arcs.md` | Original feature issue for 10 welders + skill arcs |
| `.cursor/taskspace/20260218_130707/plan-10-mock-welders-refined.md` | Refined implementation plan (or equivalent in workspaces) |
| `backend/scripts/prototype_arc_scoring.py` | Prototype using `make_session_for_arc` (duplicate logic; NOT `generate_session_for_welder`) — validates arcs but not production path |
| `backend/data/mock_sessions.py` | `generate_frames`, `generate_expert_session`, `generate_novice_session`; no `generate_frames_for_arc` yet |
| `backend/data/mock_welders.py` | Does not exist; plan creates it in Step 1.1 |
| `backend/routes/dev.py` | Seed/wipe for 2 sessions only; no `import random`; uses loop delete |
| `backend/scripts/seed_demo_data.py` | Seeds `sess_expert_001`, `sess_novice_001`; idempotent on `existing > 0`; no spot-check |
| `my-app/src/app/seagull/page.tsx` | WELDERS = 2 entries; has loading state; fetches 2 scores |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | WELDER_MAP, WELDER_DISPLAY_NAMES = 2 entries; MOCK_HISTORICAL hardcoded; no historical fetch |
| `my-app/src/lib/ai-feedback.ts` | `generateAIFeedback(session, score, historicalScores)` — trend from last 2 elements; treats 0 as real score |
| `my-app/src/__tests__/lib/ai-feedback.test.ts` | Tests trend improving/declining/stable; no last-slot 0 vs sc.total test |
| `backend/tests/test_dev_routes.py` | Expects 2 sessions; seed/wipe assertions hardcoded |

**What's broken or missing:**

| Gap | User wants | Current behavior | Why |
|-----|------------|------------------|-----|
| Prototype tuning | When fast_learner scores 38 instead of 58, know what to change | Plan says "tune angle/amps/volts" — no mapping from symptom to param | No tuning guide in Step 1.4 |
| Prototype reproducibility | Run prototype and seed and get same scores | Both use `random.seed(42)`; seed route advances RNG; prototype run after mock_sessions advances state | Shared global random state; no fresh-process or per-check seed |
| Archetype sync | Add archetype once, all UIs correct | Must edit `mock_welders.py`, `seagull/page.tsx`, `welder/[id]/page.tsx` — miss one → 404 or wrong badge | No pre-flight verification |
| Spot-check validity | Partial seed triggers re-seed and we validate data | Spot-check uses `sess_mike-chen_001`; if mike-chen removed, passes incorrectly | Hardcoded welder ID; runs only when existing == expected_count |
| Dashboard loading | See skeleton during 20 fetchScore calls | Plan does not specify loading UI | Step 3.2 omits loading-state spec |
| Last-slot test | Regress-proof historicalScores last-slot fix | Step 5.3 is pseudocode; no concrete test | Test classified P1 but optional; no file specified |
| Badge flicker | Plateaued welder shows stable neutral | With ±2 noise, score > secondScore vs score < secondScore flips across runs | No dead zone or documented expected behavior |
| Python 3.8 compat | Run on older envs | `tuple[List[Frame], bool]` requires Python 3.9+ | Plan uses lowercase `tuple` |
| Step granularity | Minimal step count | Step 2.3 "Add import random" is 1 line, 0.1h | Should fold into Step 2.1 |
| Delete consistency | Reviewer understands seed vs wipe | Wipe uses `.delete(synchronize_session=False)`; seed uses loop `db.delete(existing)` | Inconsistent; no note in plan |

---

## 5. Desired Outcome

**User flow after fix:**

1. **Primary flow — implementer hits prototype failure:** Implementer runs `prototype_arc_scoring.py`; fast_learner session 0 scores 38. Opens Step 1.4 tuning guide: "If fast_learner scores low → tighten `_arc_angle_tight` stddev (reduce looseness). If declining scores high → increase `_arc_angle_drift` drift_factor." Adjusts params; re-runs prototype; exits 0.
2. **Edge — prototype run after seed:** Implementer runs seed via API, then runs prototype in same Python process. Plan states: "Prototype must run with fresh Python process, or call `random.seed(42)` immediately before each PASS_BAND check inside the loop." Prototype yields correct results.
3. **Edge — archetype change:** Implementer adds 11th welder to WELDER_ARCHETYPES. Phase 3 pre-flight: "Verify WELDERS in page.tsx matches WELDER_ARCHETYPES." Script or manual check catches mismatch before demo.
4. **Edge — partial seed + spot-check:** DB has 44/45 sessions. seed_demo_data re-seeds; spot-check uses `session_ids[0]` and first archetype's expected `operator_id` — valid regardless of which welders exist.
5. **Edge — slow dashboard:** Backend cold start; 20 fetches take 4s. Cards show skeleton/spinner until `setWelderScores` called once after Promise.allSettled.

**Acceptance criteria:**

1. Step 1.4 includes a tuning guide: "If fast_learner scores low → tighten _arc_angle_tight stddev. If declining scores high → increase _arc_angle_drift drift_factor."
2. Step 1.4 explicitly notes: prototype must run with a fresh Python process (not after mock_sessions), or set `random.seed(42)` immediately before each PASS_BAND check inside the loop.
3. Phase 3 pre-flight includes: "Verify WELDERS in page.tsx matches WELDER_ARCHETYPES: compare welder IDs and sessionCounts manually or with a quick script."
4. seed_demo_data.py spot-check uses `session_ids[0]` and `WELDER_ARCHETYPES[0]["welder_id"]` (or equivalent first archetype) for operator_id validation — not hardcoded `sess_mike-chen_001`.
5. Spot-check runs in both full-seed (existing == expected_count) and re-seed (existing > 0) branches — not only when skipping.
6. Step 3.2 specifies: cards show skeleton/spinner during load, not empty score values; `setWelderScores` called once after Promise.allSettled resolves.
7. Step 5.3 has concrete test: `my-app/src/__tests__/lib/ai-feedback.test.ts` — "trend is declining when last slot is 0 and prev is higher" and "trend is improving when last slot has real score" — OR plan explicitly states "manual verification only; owner must run Step 4.4 verification before every demo."
8. Step 3.3 documents: plateaued/volatile with ±2 noise may flicker between on_track and needs_attention; add ±2 dead zone OR document as expected behavior.
9. `generate_frames_for_arc` uses `Tuple[List[Frame], bool]` from `typing` (or `from __future__ import annotations`) for Python 3.8 compat.
10. Step 2.3 folded into Step 2.1; plan notes wipe vs seed delete inconsistency (loop vs bulk) for reviewer clarity.

**Out of scope:**

1. **GET /api/dev/welders** — Single source of truth deferred; pre-flight check is mitigation.
2. **Batch score endpoint** — 20 fetches acceptable for MVP; no new API.
3. **Automated archetype sync script** — Manual or quick ad-hoc script sufficient for demo.

---

## 6. Constraints

- **Tech stack:** Backend Python 3.10+ (project rule); if support for 3.8 needed, use `typing.Tuple` or `from __future__ import annotations`.
- **Performance:** Dashboard loading state must appear within 200ms; skeleton until fetches complete.
- **Blocked by:** 10 Mock Welders plan existence (plan-10-mock-welders-refined or equivalent).
- **Blocks:** Clean demo execution; prevents 404s and wrong badges from archetype drift.
- **Approval:** Plan author or tech lead for tuning guide and pre-flight additions.

---

## 7. Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Tuning guide wrong for actual scoring rules | Med | Med | Guide is heuristic; implementer can iterate; prototype + test catch drift |
| Pre-flight script not run before demo | Med | High | Add to Pre-Flight Checklist; CI or deploy hook if feasible |
| Spot-check logic still wrong for edge archetype order | Low | Med | Use `session_ids[0]` and `WELDER_ARCHETYPES[0]` — first derived ID and first archetype always aligned |
| Last-slot test fragile across generateAIFeedback changes | Low | Low | Test documents contract; if semantics change, update test and doc |
| ±2 dead zone changes badge semantics | Low | Med | Document first; dead zone is optional; product can decide |
| Python 3.8 not in use | Low | Low | Project specifies 3.10+; Tuple fix is defensive |

---

## 8. Open Questions

| Question | Assumption | Confidence | Resolver |
|----------|------------|------------|----------|
| Is Python 3.8 in any target environment? | No; project uses 3.10+ | Med | DevOps / env docs |
| Should badge use ±2 dead zone for plateaued? | Document as expected; optional dead zone | Low | Product |
| Step 5.3: concrete test vs manual-only? | Concrete test in ai-feedback.test.ts (~20 lines) | High | Tech lead |
| Who runs Phase 3 pre-flight before demo? | Implementer / demo owner | High | Process |

---

## 9. Classification

- **Type:** improvement
- **Priority:** P1 (high impact — prevents demo failures)
- **Effort:** M (8–12h)
- **Effort breakdown:** Plan updates 2h + seed_demo_data spot-check 1h + loading state 1h + ai-feedback test 2h + Python compat + fold Step 2.3 + doc 1h + Review 2h = **~9h**

---

## Appendix: Critique Problem → Fix Mapping

| Critique problem | Fix |
|------------------|-----|
| P1: Prototype weakest mitigation; no tuning guide | Add tuning guide + fresh-process/seed note to Step 1.4 |
| P2: WELDER_ARCHETYPES duplicated, no enforcement | Phase 3 pre-flight: verify WELDERS matches WELDER_ARCHETYPES |
| P3: seed_demo_data spot-check logic flaw | Use session_ids[0] + first archetype; run in re-seed branch too |
| P4: Phase 3 no loading state | Step 3.2: skeleton/spinner spec; setWelderScores once |
| P5: Step 5.3 underspecified | Concrete test in ai-feedback.test.ts or "manual only" explicit |
| Minor: tuple Python 3.9+ | Tuple from typing or __future__ annotations |
| Minor: Step 2.3 fold | Merge into Step 2.1 |
| Minor: wipe vs seed delete | Document inconsistency |
| Minor: badge flicker ±2 | Document or add dead zone |
