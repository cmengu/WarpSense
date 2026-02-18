# Threshold Configuration Admin UI — Plan Critique Fixes

## 1. Title

`[Improvement] Fix five main and three minor gaps in Threshold Admin UI plan before implementation`

---

## 2. TL;DR

The Threshold Configuration Admin UI implementation plan has five correctness/risk gaps and three minor omissions that would cause rework, broken migrations, or silent bugs if implemented as written. Root cause: plan was written without adversarial review of migration atomicity, concurrent cache semantics, form validation edge cases, test fixture completeness, and load-order UX. This issue captures fixes so the exploration phase produces an implementation-ready plan. Effort: S (4–8h) of plan updates and verification steps—no production code changes until the parent plan is executed.

---

## 3. Root Cause Analysis

**Level 1:** Migration Step 1.2 pre-flight is insufficient for staging/prod.  
**Level 2:** Plan treats all environments alike; no row-count or SQL-preview checks.  
**Level 3:** Plan author assumed "run during maintenance window" covers large-table risk; pre-flight checklist wasn't environment-aware.  
**Level 4:** Plan verification focused on happy path; no adversarial review of partial migration failure or concurrent request races.  
**Level 5:** Root cause: plan verification was surface-level; migration atomicity, cache threading, form edge cases, and fixture completeness were not stress-tested.

---

## 4. Current State

**What exists today:**
| File / Component | Description |
|------------------|-------------|
| `.cursor/issues/threshold-configuration-admin-ui-plan.md` | 20-step plan (Phases 1–4) for weld_thresholds, admin UI, scoring, micro-feedback |
| `backend/alembic/versions/001_initial_schema.py`, `002_*.py`, `003_add_score_total.py` | Current migration chain; 003 is head |
| `backend/database/models.py` | `SessionModel`, `FrameModel`; no `process_type`, no `WeldThresholdModel` |
| `backend/data/mock_sessions.py` | `generate_expert_session`, `generate_novice_session`; no `generate_session_for_welder` (mock welders plan) |
| `backend/tests/test_get_session_score.py` | Uses `seeded_client` with expert/novice via `SessionModel.from_pydantic`; no thresholds or process_type |
| `my-app/src/app/replay/[sessionId]/page.tsx` | `sessionData` and `primaryScore` load independently; `generateMicroFeedback(frames)` — no thresholds yet |
| `my-app/src/lib/micro-feedback.ts` | `generateMicroFeedback(frames)` only; no thresholds param |
| Plan Step 1.4 code block | `invalidate_cache()` sets `_cache_loaded = False` without acquiring `_load_lock` |
| Plan Step 3.4 code block | `parseFloat(e.target.value) \|\| 0` for all numeric inputs; `isCompleteForm` checks `Number.isFinite(v)` |
| Plan Step 4.6 | References `session_factory` fixture; no implementation provided |

**What's broken or missing:**

1. **Migration pre-flight (Step 1.2):** User running on DB with 100k+ rows gets same checklist as fresh dev DB. Single `UPDATE` + `ALTER COLUMN` is two-step; if UPDATE succeeds but ALTER fails (timeout, connection drop), `sessions.process_type` stays nullable with data, and next `alembic upgrade` fails because revision is partially applied. Plan says "run during maintenance window" but doesn't add pre-flight: row-count check, or `alembic upgrade head --sql > migration_preview.sql` for inspection.
2. **Cache correctness (Step 1.4):** `invalidate_cache()` writes `_cache_loaded = False` without holding `_load_lock`. A request in `_load_all` (holds lock, building `_threshold_cache`) can be interrupted by `invalidate_cache` setting `_cache_loaded = False`; next request sees False, enters `_load_all` again. Harmless for load but violates single-responsibility of lock; future changes could introduce real races.
3. **Form NaN bug (Step 3.4):** `parseFloat("") \|\| 0` yields 0; clearing a field submits 0. `isCompleteForm` allows `angle_target_degrees = 0` (finite). Backend accepts 0 (Pydantic `ge=0`). With `angle_target_degrees=0` and `angle_warning_margin=0`, every weld angle >0 triggers a warning—scoring useless. User expects invalid or blocked save.
4. **Test fixture underspec (Step 4.6):** `test_put_threshold_invalidates_cache` depends on `session_factory(process_type="mig")`. Fixture not defined. Implementer may create minimal session without frames; `get_session_score` could 404 before threshold logic. Test passes for wrong reason.
5. **Micro-feedback flicker (Phase 4 / Step 4.2):** `thresholdsForMicroFeedback` depends on `primaryScore?.active_threshold_spec`; `microFeedback` depends on `sessionData?.frames` and `thresholdsForMicroFeedback`. If frames load fast and score slow, micro-feedback runs twice: once with default thresholds, once with TIG. Visual flicker on replay timeline. Plan verification doesn't check "micro-feedback doesn't re-render visibly when score loads after frames."

---

## 5. Desired Outcome

**User flow after fix:**

1. **Operator runs migration pre-flight:** Operator runs `alembic upgrade head --sql > migration_preview.sql`, inspects SQL. If `sessions` has >1000 rows, runs manual `UPDATE sessions SET process_type = 'mig' WHERE process_type IS NULL` and verifies row count before `alembic upgrade head`.
2. **Implementer writes cache service:** `invalidate_cache` acquires `_load_lock` before setting `_cache_loaded = False`; threading model documented in service docstring.
3. **Admin uses form:** Admin clears angle target; form shows invalid state; Save disabled. Admin sets `angle_target_degrees=0`; backend or form rejects. No silent 0.
4. **Implementer runs cache-invalidation test:** `session_factory` explicitly defined (e.g. uses `generate_expert_session` with process_type patched, or inline SessionModel+frames); test asserts PUT then GET score yields new `active_threshold_spec.angle_target`.
5. **Replay page avoids flicker:** Either wait for both `sessionData` and `primaryScore` before computing micro-feedback, or show skeleton until both ready. Verification step: "Micro-feedback doesn't re-render visibly when score loads after frames."

**Edge flows:**
- **Large DB, migration fails mid-way:** Pre-flight caught row count; operator ran manual UPDATE first; ALTER succeeds.
- **Concurrent PUT + GET score:** `invalidate_cache` under lock; no interleaving with `_load_all`.
- **Admin submits angle_target=0:** Backend validation rejects or form blocks; explicit error.

**Acceptance criteria:**

1. Step 1.2 pre-flight includes: "If `sessions` has >1000 rows, run manual UPDATE first; verify row count; then alembic upgrade."
2. Step 1.2 pre-flight includes: "Run `alembic upgrade head --sql > migration_preview.sql`; inspect SQL before applying."
3. Step 1.4 `invalidate_cache` acquires `_load_lock` before setting `_cache_loaded = False`; service docstring documents threading model.
4. Step 3.4 form: no `parseFloat(...) \|\| 0`; use `parseFloat(...)` (no fallback); `isCompleteForm` requires `angle_target_degrees > 0` or backend rejects `angle_target_degrees === 0`.
5. Step 4.6 provides explicit `session_factory` fixture code (or equivalent) that produces SessionModel with frames + process_type; test asserts score endpoint returns 200 with `active_threshold_spec`.
6. Step 4.2 verification includes: "Micro-feedback doesn't re-render visibly when score loads after frames" with mitigation (wait for both, or skeleton).
7. Step 1.5: Add comment explaining asymmetric validation (angle/thermal have warning≤critical; amps/volts/heat_diss have no ordering).
8. Step 3.1: Document that `ActiveThresholdSpec` optional fields exist for legacy API callers returning old 4-field spec.
9. Step 4.5: Add comment that hardcoded fallback "MIG spec — Target 45° ±5°" can be wrong if admin changes MIG seed.

**Out of scope:**

1. Implementing the parent plan—this issue updates the plan document only.
2. Changing migration strategy (e.g. batched UPDATE)—that remains a Known Issue; pre-flight is the mitigation.
3. Redis/shared cache for multi-worker—documented backlog item, not part of critique fixes.

---

## 6. Constraints

- Plan updates only; no backend or frontend code changes.
- Fixes must be backward-compatible with existing plan structure (step numbering, phases).
- Effort must stay S (4–8h) for plan author / reviewer.
- Blocked by: none. Blocks: clean execution of Threshold Configuration Admin UI implementation.

---

## 7. Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Plan author misses one of nine fixes | Low | Med | Checklist: verify each acceptance criterion maps to a plan edit |
| generate_session_for_welder doesn't exist when Step 4.6 runs | Med | Med | Use `generate_expert_session` + process_type patch, or inline SessionModel+frames; don't depend on mock welders plan |
| Fix 3 (angle_target=0) conflicts with Pydantic ge=0 | Low | Low | Add backend validation rejecting angle_target_degrees===0 explicitly; or keep ge=0.01 |
| Flicker mitigation requires larger Replay refactor | Low | Med | Mitigation: skeleton or "loading" state until both ready; minimal code change |

---

## 8. Open Questions

| Question | Current assumption | Confidence | Resolver |
|----------|--------------------|------------|----------|
| Should session_factory use generate_expert_session or wait for generate_session_for_welder? | Use generate_expert_session + add process_type to Session before from_pydantic | Med | Eng |
| Backend: reject angle_target_degrees=0 or add ge=0.01? | Reject with 422 and explicit message | High | Eng |
| Flicker: wait for both vs skeleton? | Wait for both before computing micro-feedback | Med | Eng |

---

## 9. Classification

- **Type:** improvement
- **Priority:** P1 (high impact—prevents migration failures, cache races, silent form bugs)
- **Effort:** S (4–8h)
- **Effort breakdown:** Plan edits 3h + Verification 2h + Review 1h = Total 6h
