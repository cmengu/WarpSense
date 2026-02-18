# Plan Critique Fixes — Technical Exploration

**Issue:** Fix five main and three minor gaps in Threshold Admin UI plan before implementation  
**Scope:** Plan-only edits; no production code until parent plan executes  
**Exploration date:** 2025-02-18

---

## 1. Complexity Classification

**Moderate.** The fixes are localized plan edits (pre-flight additions, code-block corrections, fixture specs, verification steps) with no new algorithms or infrastructure. One fix (cache lock) requires careful threading reasoning; two (migration pre-flight, session_factory) require precise fixture/checklist wording. The micro-feedback flicker mitigation touches Replay page data-flow but is a small change (gate micro-feedback on both session and score).

---

## 2. Risk Profile

| Axis | Level | Reason |
|------|-------|--------|
| Data loss risk | **Low** | Plan edits only; no DB or file mutations |
| Service disruption risk | **Low** | No runtime changes |
| Security risk | **Low** | Documentation and validation rules only |
| Dependency risk | **Low** | No new dependencies; relies on existing generate_expert_session |
| Rollback complexity | **Low** | Revert plan doc; no deployed changes |

---

## 3. Codebase Findings

| File | What it does | Pattern | Reuse | Avoid |
|------|--------------|----------|-------|------|
| `backend/tests/test_get_session_score.py` | GET score for expert/novice; uses `seeded_client` with `generate_expert_session`, `generate_novice_session`, `SessionModel.from_pydantic` | In-memory SQLite, `Base.metadata.create_all`, override `get_db` | Same fixture layout for `test_thresholds_api.py`: `db_session`, `client`, `seeded_client`-like pattern. `generate_expert_session` produces valid Session with ~1500 frames. | No `process_type` today; fixture must add it via `model_copy` or `model_dump` + `model_validate` after Step 1.3 |
| `backend/database/models.py` | SessionModel, FrameModel; `from_pydantic`/`to_pydantic` | ORM models; `joinedload` for frames | `SessionModel.from_pydantic(session)` after session has `process_type`. Plan Step 1.3 adds `process_type` to Session and SessionModel. | Don't assume Session has `process_type` before Step 1.3 |
| `backend/data/mock_sessions.py` | `generate_expert_session(session_id, duration_ms)`, `generate_novice_session` | Returns `Session` Pydantic; includes frames, thermal data | Use `generate_expert_session(session_id="sess_test_001")` for session_factory; patch `process_type` via `session.model_copy(update={"process_type": "mig"})` once Session has the field (Step 1.3) | No `generate_session_for_welder` yet; don't depend on mock welders plan |
| `my-app/src/app/replay/[sessionId]/page.tsx` | Fetches session (useEffect) and score (separate useEffect); `microFeedback` useMemo depends only on `sessionData?.frames` | Parallel independent fetches; micro-feedback computed when frames available | Add `thresholdsForMicroFeedback` from `primaryScore?.active_threshold_spec`; gate micro-feedback until both `sessionData` and `primaryScore` ready to avoid flicker | Don't add thresholds to useMemo deps without gating—causes visible re-render when score arrives late |
| `my-app/src/lib/micro-feedback.ts` | `generateMicroFeedback(frames)`; hardcoded 45°/5°/15°/20° | No params | Step 4.1 adds optional `thresholds?`; prototype at `my-app/prototype/micro-feedback-thresholds-prototype.ts` validates API shape | N/A |
| `backend/alembic/versions/001_initial_schema.py`, `003_add_score_total.py` | Migration chain; 003 adds `score_total` | `op.add_column`, `op.alter_column` | Plan migration 004 follows same pattern. `alembic upgrade head --sql` emits SQL for offline inspection (standard Alembic feature). | Migration 004 splits UPDATE + ALTER; pre-flight must address partial-failure risk |
| `backend/alembic/env.py` | Loads `Base.metadata` from `database.base` | Models auto-register when imported | Ensure `WeldThresholdModel` imported (e.g. in `database/models.py`) before `create_all` so `weld_thresholds` table exists in test DB | SQLite in-memory: `Base.metadata.create_all` creates only registered tables |

**Similar implementations:** test_get_session_score.py (fixture pattern), mock_sessions generate_expert/novice (session with frames), replay page (parallel fetch + useMemo). The gap: no existing threshold cache or admin form; plan code blocks are the only reference. The critique fixes correct those blocks.

---

## 4. Known Constraints

- **Plan-only scope:** All fixes are edits to `.cursor/issues/threshold-configuration-admin-ui-plan.md` (or plan-critique-fixes issue). No backend/frontend code until parent plan runs.
- **Step ordering:** session_factory in Step 4.6 runs after Step 1.3 (Session has process_type), Step 1.2 (weld_thresholds table), Step 1.4 (threshold_service). Fixture must not assume generate_session_for_welder exists.
- **Pydantic:** Session will have `process_type: str = "mig"` after Step 1.3. `WeldTypeThresholds` uses `ge=0` for angle_target_degrees—backend must add explicit validator rejecting 0 for angle_target.
- **React:** useMemo deps drive re-renders. Adding `primaryScore?.active_threshold_spec` to micro-feedback deps causes recompute when score loads; if frames loaded first, markers jump—visible flicker.
- **Alembic:** `alembic upgrade head --sql` writes SQL to stdout; operator captures to file. Requires DATABASE_URL; offline mode works.
- **SQLite in-memory tests:** `Base.metadata.create_all` creates tables for all models in metadata. WeldThresholdModel must be imported (e.g. in database/models.py) so weld_thresholds exists.
- **Form validation:** `parseFloat("")` returns NaN; `parseFloat("") || 0` returns 0. Plan Step 3.4 uses `|| 0`—clearing a field yields 0, passes isCompleteForm (0 is finite).

---

## 5. Approach Options

### A. Minimal Plan Edits (Inline Fixes)
Add pre-flight bullets, correct code blocks in-place, add fixture snippet, add verification step. No new files.

- **Pros:** Smallest delta; reviewer sees exact fix; no structural change  
- **Cons:** Plan doc grows; some fixes span multiple locations  
- **Key risk:** One fix missed in review  
- **Complexity:** Low  

### B. Separate Fixes Document + Plan References
Create `plan-critique-fixes.md` with each fix as a section; add "See plan-critique-fixes" references in plan steps.

- **Pros:** Fixes grouped; single source for critique responses  
- **Cons:** Two docs to maintain; implementer must cross-reference  
- **Key risk:** Implementer misses a reference  
- **Complexity:** Medium  

### C. Fork Plan with Fixes Inlined
Produce `threshold-configuration-admin-ui-plan-fixed.md` as the implementation source; original plan deprecated.

- **Pros:** Single document; no cross-ref  
- **Cons:** Duplication; merge conflicts if plan evolves  
- **Key risk:** Wrong doc used  
- **Complexity:** Medium  

### D. Patch Script
Script that applies fixes to plan (sed/replace, structured edits).

- **Pros:** Reproducible; audit trail  
- **Cons:** Overkill for 9 edits; script maintenance  
- **Key risk:** Script bugs  
- **Complexity:** High  

**Recommendation:** A (Minimal Plan Edits). Fixes are localized; inline edits keep context; effort stays S.

---

## 6. Prototype Results

### Prototype 1: invalidate_cache under lock

**What was tested:** Correct pattern for `invalidate_cache` to avoid race with `_load_all`.

**Code:** See `backend/scripts/prototype_cache_invalidate_lock.py`. Key snippet:
```python
# Prototype: cache invalidation with lock
import threading

_cache = {}
_loaded = False
_lock = threading.Lock()

def _load():
    global _cache, _loaded
    with _lock:
        if _loaded:
            return
        _cache = {"mig": 45}  # simulate load
        _loaded = True

def invalidate_wrong():
    """Original: no lock — race with _load."""
    global _loaded
    _loaded = False

def invalidate_fixed():
    """Fixed: acquire lock before clearing."""
    global _loaded
    with _lock:
        _loaded = False

def get():
    global _loaded
    if not _loaded:
        _load()
    return _cache.get("mig")
```

**Result:** With `invalidate_fixed`, `invalidate` and `_load` serialize under `_load_lock`. With `invalidate_wrong`, a thread in `_load` (holding lock, building _cache) could have `_loaded` set False by another thread; next `get` triggers redundant _load. Harmless for correctness but violates lock discipline. Fix: `invalidate_cache` must acquire `_load_lock` before setting `_cache_loaded = False`. Run: `cd backend && python scripts/prototype_cache_invalidate_lock.py`.

**Decision:** Proceed. Plan Step 1.4 code block: change `invalidate_cache` to:
```python
def invalidate_cache() -> None:
    global _cache_loaded
    with _load_lock:
        _cache_loaded = False
```
Add docstring: "Threading: _load_lock protects both _load_all and invalidate_cache. Acquire before read/write of _cache_loaded."

---

### Prototype 2: parseFloat edge cases

**What was tested:** `parseFloat("") || 0` vs `parseFloat("")` for form validation.

**Code (browser or Node):**
```javascript
// parseFloat("") || 0 → 0 (cleared field becomes 0)
// parseFloat("0") || 0 → 0 (valid)
// parseFloat("45") || 0 → 45
// parseFloat("") → NaN; isCompleteForm checks Number.isFinite → false
console.log(parseFloat("") || 0);      // 0
console.log(Number.isFinite(parseFloat("") || 0));  // true (!)
console.log(Number.isFinite(parseFloat("")));        // false
```

**Result:** Confirmed. Clearing a field: `parseFloat("") || 0` = 0; `Number.isFinite(0)` = true; form passes; backend receives angle_target_degrees=0. Fix: use `parseFloat(e.target.value)` (no `|| 0`), store NaN in state; `isCompleteForm` requires `typeof v === 'number' && Number.isFinite(v) && v >= 0` and add `angle_target_degrees > 0`. Backend: reject `angle_target_degrees === 0` with 422.

**Decision:** Proceed.

---

### Prototype 3: session_factory with generate_expert_session

**What was tested:** Can we create a session with process_type using existing mock_sessions?

**Code (conceptual—Session has no process_type today):**
```python
# After Step 1.3, Session has process_type
session = generate_expert_session(session_id="sess_test_001")
session = session.model_copy(update={"process_type": "mig"})
model = SessionModel.from_pydantic(session)
# model has frames via relationship; process_type on SessionModel
```

**Result:** `model_copy(update={"process_type": "mig"})` requires Session to define `process_type`. After Step 1.3 it will. `SessionModel.from_pydantic` will need to pass `process_type` (plan Step 1.3 adds this). Fixture pattern is valid.

**Decision:** Proceed. Provide explicit session_factory code in Step 4.6. Full fixture:

```python
@pytest.fixture
def session_factory(db, seeded_weld_thresholds):
    """Creates SessionModel with frames and process_type for score endpoint tests.
    Requires Step 1.3 (Session has process_type). Uses generate_expert_session.
    """
    from data.mock_sessions import generate_expert_session
    from database.models import SessionModel
    from models.session import Session

    def _create(process_type: str = "mig", session_id: str = "sess_test_001"):
        session = generate_expert_session(session_id=session_id)
        session = session.model_copy(update={"process_type": process_type})
        model = SessionModel.from_pydantic(session)
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    return _create
```

Ensure `WeldThresholdModel` is imported (e.g. in conftest or before `create_all`) so `weld_thresholds` table exists.

---

### Prototype 4: Micro-feedback gating

**What was tested:** Does gating micro-feedback on both sessionData and primaryScore prevent flicker?

**Analysis:** Current: `microFeedback = useMemo(() => generateMicroFeedback(sessionData?.frames ?? []), [sessionData?.frames])`. Score loads in parallel. Plan Step 4.2 adds `thresholdsForMicroFeedback` from `primaryScore?.active_threshold_spec` and adds it to useMemo deps. When frames load first, microFeedback runs with undefined thresholds (fallback constants). When score loads, useMemo re-runs with TIG thresholds → markers change → flicker.

**Mitigation:** Compute micro-feedback only when both are ready: `(sessionData?.frames && primaryScore)`. If either missing, return [] or don't render markers. Result: single paint with correct thresholds.

**Decision:** Proceed. Add to Step 4.2: gate with `sessionData?.frames && primaryScore`; verification: "Micro-feedback does not re-render visibly when score loads after frames."

---

## 7. Recommended Approach

**Chosen approach:** A (Minimal Plan Edits)

**Justification:** The nine fixes are small, localized changes to a single plan document. Inline edits keep each fix next to the step it affects, reducing the chance an implementer misses one. The cache fix is a 3-line change (add `with _load_lock` in invalidate_cache). The form fix is a pattern replacement (`parseFloat(x) || 0` → `parseFloat(x)`) plus validation. The session_factory is a ~15-line fixture block. The migration pre-flight is two checklist bullets. The micro-feedback fix is a conditional gate and one verification step. Creating a separate fixes document adds indirection; a patch script is unnecessary for this scope. The prototype validated that the cache fix is correct, the parseFloat behavior is as stated, and the session_factory/gating patterns are sound. Trade-off: we accept that the plan document will have more content in a few steps.

**Trade-offs accepted:**
- Plan doc length increases slightly.
- session_factory depends on Step 1.3 being done first (already true—4.6 runs after 1.3).
- Micro-feedback shows nothing until both session and score load (acceptable; avoids flicker).

**Fallback approach:** B (Separate fixes document) if the plan author prefers to keep the main plan minimal and reference a fixes appendix. Trigger: review feedback that inline edits make the plan too dense.

---

## 8. Architecture Decisions

| Decision | Options | Chosen | Reason | Reversibility | Impact |
|----------|---------|--------|--------|---------------|--------|
| invalidate_cache locking | No lock, lock in invalidate only, single RWLock | Lock in invalidate | Eliminates race with _load_all; matches _load_lock | Easy | Documents threading contract |
| Form NaN handling | parseFloat\|\|0, parseFloat only, controlled input | parseFloat only + validation | Prevents silent 0 on cleared field; angle_target>0 | Easy | Form validation logic |
| angle_target_degrees=0 | Allow (ge=0), Reject 422 | Reject 422 | 0 makes scoring useless (every angle>0 warns) | Easy | Backend validation |
| session_factory source | generate_session_for_welder, generate_expert_session, inline | generate_expert_session | Exists today; mock welders not required | Easy | Test fixture |
| Micro-feedback gating | Wait both, skeleton, no gate | Wait both | Single paint; no flicker; minimal code | Easy | Replay page |
| Migration pre-flight location | Inline step, checklist, runbook | Step 1.2 pre-flight | Operator sees it before upgrade | Easy | Pre-flight process |
| SQL preview | Optional note, required step | Required: alembic upgrade head --sql | Operator inspects before applying | Easy | Operator workflow |

---

## 9. Edge Cases

| Category | Scenario | Handling | Graceful? |
|----------|----------|-----------|-----------|
| Empty data | sessions table empty | migration backfill: UPDATE affects 0 rows; ALTER proceeds | Yes |
| Empty data | weld_thresholds table empty | _load_all fallback to hardcoded MIG; no 500 | Yes |
| Empty data | Cleared form field | parseFloat("")=NaN; isCompleteForm false; Save disabled | Yes |
| Max scale | sessions has 100k+ rows | Pre-flight: run manual UPDATE first; then alembic | Partial (operator must follow) |
| Max scale | Large payload GET /thresholds | 4 rows; trivial | Yes |
| Concurrent | PUT threshold + GET score | invalidate_cache under lock; no interleaving | Yes |
| Concurrent | Two GET score during _load_all | Double-check lock; second waits for first | Yes |
| Network | Score fetch fails, frames load | primaryScore null; gate: no micro-feedback until both | Partial (no markers until score) |
| Network | Frames fetch fails | sessionData null; gate: no micro-feedback | Yes |
| Browser | Slow score API | Micro-feedback delayed until score arrives; no flicker | Yes |
| Browser | Session without process_type | Backfill gives mig; get_thresholds falls back to mig | Yes |
| Permission | Admin saves angle_target=0 | Backend 422 | Yes |
| Session | Session not found for score | 404; primaryScore null; gate yields no micro-feedback | Yes |
| Fixture | DB has no weld_thresholds in test | seeded_weld_thresholds fixture seeds; create_all needs WeldThresholdModel | Yes (fixture) |
| Legacy API | active_threshold_spec has only 4 fields | Optional thermal/amps/volts/heat_diss; fallback constants | Yes |

---

## 10. Risk Analysis

| Risk | Prob | Impact | Early warning | Mitigation |
|------|------|--------|---------------|------------|
| Plan author omits a fix | Low | Med | Checklist verification | Map each acceptance criterion to a plan edit |
| generate_expert_session lacks process_type | N/A | — | — | Step 1.3 adds it; fixture runs after |
| session_factory creates session without frames | Med | High | test_put_threshold_invalidates_cache passes but score 404 | Explicit fixture: use generate_expert_session (has frames) |
| Flicker mitigation over-delays UI | Low | Low | Users wait longer for markers | Gate is minimal; both fetches typically complete within ms |
| Backend ge=0 conflicts with angle_target>0 | Low | Low | Validation fails | Add explicit 422 for angle_target_degrees==0 |
| Pre-flight not run in prod | Med | High | Migration fails mid-way | Make pre-flight bullets prominent; add to runbook |
| **CRITICAL** WeldThresholdModel not imported in test | Med | High | weld_thresholds table missing; GET/PUT 404 | Step 4.6: "Ensure WeldThresholdModel imported before Base.metadata.create_all" |
| Invalid downgrade after partial upgrade | Low | High | alembic downgrade fails | Document: if upgrade fails, fix schema manually before retry |

---

## 11. Exploration Summary

**Files to create:** None (plan edits only)

**Files to modify:**
- `.cursor/issues/threshold-configuration-admin-ui-plan.md` — Add Step 1.2 pre-flight (row count, SQL preview); Step 1.4 invalidate_cache under lock + docstring; Step 1.5 validation comment; Step 3.4 parseFloat/no-fallback, isCompleteForm angle_target>0; Step 4.2 gating + verification; Step 4.5 fallback comment; Step 4.6 session_factory fixture code + WeldThresholdModel import note
- `.cursor/issues/threshold-configuration-admin-ui-plan-critique-fixes.md` — Optional: add "Fixes applied" checklist referencing plan edits

**New dependencies:** None

**Bundle impact:** 0 KB

**Critical path order:**
1. Edit Step 1.2 pre-flight
2. Edit Step 1.4 invalidate_cache
3. Edit Step 1.5 comment
4. Edit Step 3.1 ActiveThresholdSpec doc
5. Edit Step 3.4 form logic
6. Edit Step 4.2 gating + verification
7. Edit Step 4.5 comment
8. Edit Step 4.6 session_factory

**Effort estimate:** Plan edits 2h + Verification 1.5h + Review 1h = Total 4.5h, confidence 85%

**Blockers for planning:** None. Open questions resolved: use generate_expert_session; reject angle_target=0 with 422; gate micro-feedback on both session and score.
