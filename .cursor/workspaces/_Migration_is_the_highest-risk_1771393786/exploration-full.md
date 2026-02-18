
Summary of the exploration:

---

## Exploration Summary

A technical exploration for the **Plan Critique Fixes** issue is in `.cursor/explore/plan-critique-fixes-exploration.md`. Findings:

### Complexity Classification
**Moderate** — Focused plan edits plus one threading change (invalidate_cache).

### Codebase Findings

| Finding | Location | Implication |
|--------|----------|-------------|
| Existing score test pattern | `test_get_session_score.py` | Reuse `generate_expert_session`, `SessionModel.from_pydantic`, in-memory SQLite |
| Session has no `process_type` | `models/session.py`, `database/models.py` | Fixture must add it after Step 1.3 via `model_copy(update={...})` |
| Replay fetches session and score in parallel | `replay/[sessionId]/page.tsx` | If score arrives after frames, micro-feedback recomputes and flickers |
| Micro-feedback has no thresholds param | `micro-feedback.ts` | Step 4.1 adds optional param; prototype confirms API shape |
| Migration chain | `alembic/versions/003_add_score_total.py` | 004 follows same pattern; pre-flight must cover partial failure |

### Prototype Results

1. **Cache lock:** `backend/scripts/prototype_cache_invalidate_lock.py` confirms `invalidate_cache` must hold `_load_lock` before setting `_cache_loaded = False`.
2. **parseFloat:** `parseFloat("") || 0` yields 0 and passes `Number.isFinite`; form should use `parseFloat(x)` without fallback and require `angle_target_degrees > 0`.
3. **session_factory:** Use `generate_expert_session` + `model_copy(update={"process_type": "mig"})`; fixture code included in the exploration.
4. **Micro-feedback gating:** Gate micro-feedback on both `sessionData?.frames` and `primaryScore` to avoid flicker.

### Recommended Approach: Minimal Plan Edits (Option A)

Apply edits directly in the plan: pre-flight bullets, corrected code blocks, explicit fixture, and a gating + verification step. No separate docs or scripts.

### Plan Edits Required

- **Step 1.2:** Add pre-flight for row count (>1000 → manual UPDATE first) and `alembic upgrade head --sql > migration_preview.sql`.
- **Step 1.4:** Wrap `invalidate_cache` in `with _load_lock` and document threading.
- **Step 1.5:** Note why validation is asymmetric (angle/thermal vs amps/volts).
- **Step 3.1:** Explain optional `ActiveThresholdSpec` fields for legacy API.
- **Step 3.4:** Remove `|| 0` from parseFloat; require `angle_target_degrees > 0`; backend rejects 0 with 422.
- **Step 4.2:** Gate micro-feedback on `sessionData?.frames && primaryScore`; add verification step.
- **Step 4.5:** Add comment about hardcoded fallback and MIG seed changes.
- **Step 4.6:** Add explicit `session_factory` fixture code; ensure `WeldThresholdModel` is imported before `create_all`.

### Blockers

None. Use `generate_expert_session`, reject `angle_target_degrees=0` with 422, and gate micro-feedback on both session and score.
