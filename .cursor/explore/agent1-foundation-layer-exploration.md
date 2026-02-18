# Agent 1 Foundation Layer — Technical Exploration

---

## 1. Complexity Classification

**Moderate.** Six distinct deliverables (shared enums, schemas, TS types, migration stubs, welders router, ReportLayout) across backend and frontend, with coordination requirements (no circular imports, unchanged visual output). Each piece is individually trivial; the coordination and slot-contract stability raise complexity.

---

## 2. Risk Profile

| Axis | Level | Reason |
|------|-------|--------|
| Data loss risk | Low | No schema changes to existing tables; migration stubs are no-op |
| Service disruption risk | Low | Additive only: new router, new files; existing routes unchanged |
| Security risk | Low | Health endpoint returns static JSON; no auth/PII |
| Dependency risk | Low | No new npm/pip packages; uses existing Pydantic, React, TypeScript |
| Rollback complexity | Low | Delete new files, revert main.py and page.tsx; alembic downgrade 005–009 is no-op |

---

## 3. Codebase Findings

| File | What it does | Pattern | Reuse | Avoid |
|------|--------------|---------|-------|-------|
| `backend/models/scoring.py` | ScoreRule/SessionScore Pydantic models with `rule_id: str` | Pydantic BaseModel, `rule_id` as string | MetricScore can mirror ScoreRule shape (metric, value, label) | Do not replace rule_id with enum in scoring yet — that's a later migration |
| `backend/models/thresholds.py` | WeldTypeThresholds, WeldThresholdUpdate | Pydantic Field validation | Pydantic style for MetricScore | — |
| `backend/scoring/rule_based.py` | 5 rules with hardcoded `rule_id` strings | Literal strings: `amps_stability`, `angle_consistency`, etc. | WeldMetric enum values must match exactly | Do not refactor rule_based.py to use enum in this batch — enums are for shared reference only |
| `my-app/src/lib/ai-feedback.ts` | RULE_TEMPLATES keyed by rule_id; FeedbackSeverity `info \| warning \| critical` | Record<string, fn> for templates | METRIC_LABELS align with RULE_TEMPLATES semantics; FeedbackSeverity in shared.ts re-exports or aliases ai-feedback | Avoid duplicate FeedbackSeverity — shared.ts should re-export from ai-feedback or be the single source |
| `my-app/src/lib/seagull-demo-data.ts` | RULE_IDS array, createMockScore | `as const` arrays for rule IDs | WeldMetric union in shared.ts must match RULE_IDS | — |
| `backend/routes/sessions.py` | APIRouter, get_db dependency, prefix="/api" in main | FastAPI APIRouter + include_router(prefix="/api") | Welders router: prefix="/api/welders", route="/health" → GET /api/welders/health | sessions defines routes like `/sessions/{id}`; welders should use `/health` under prefix `/api/welders` |
| `backend/routes/aggregate.py` | Router with `/sessions/aggregate` under prefix `/api` | Same include pattern | — | — |
| `backend/alembic/versions/004_weld_thresholds_and_process_type.py` | revision="004_weld_thresholds_process_type", down_revision="003_add_score_total" | revision = descriptive ID; down_revision = prior revision ID | Chain: 005 down_revision="004_weld_thresholds_process_type", 006→005, 007→006, 008→007, 009→008 | Use revision ID string, not filename |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | Inline layout: header card, Thermal Comparison (HeatMap×2 or 1), Detailed Feedback (FeedbackPanel), Progress chart, action buttons | Ad-hoc div structure with Tailwind | Move HeatMap/FeedbackPanel JSX into ReportLayout slots; preserve same section order and styling | Do not change HeatMap/FeedbackPanel props or behavior |
| `my-app/src/types/ai-feedback.ts` | FeedbackSeverity, FeedbackItem, AIFeedbackResult | Type unions, interfaces | shared.ts: re-export FeedbackSeverity or define identical type; avoid divergence | — |
| `backend/models/__init__.py` | Imports from models.py, comparison, frame, scoring, session, thermal; exports __all__ | Dynamic import for models_root; direct imports for submodules | Add `from .shared_enums import ...` and extend __all__ | models/__init__ imports models.py; shared_enums must not import models.py to avoid cycles |
| `my-app/src/__tests__/app/seagull/welder/[id]/page.test.tsx` | Asserts: score header, AI summary, Thermal Comparison, Detailed Feedback, Progress Over Time, back link | screen.getByText, waitFor | Tests must still pass after ReportLayout refactor — same text selectors | — |

**Closest existing implementations:**

1. **Shared Python enums** — None. `SessionStatus` in `models/session.py` is a str literal union in Pydantic. We introduce `shared_enums.py` as the first enum module.
2. **Pydantic schemas in dedicated directory** — None. `backend/schemas/` does not exist. Pydantic models live in `models/` (e.g. `scoring.py`, `thresholds.py`). We create `backend/schemas/shared.py` as the first schema module.
3. **Slot-based layout** — None. Welder page uses inline divs. We introduce ReportLayout with optional ReactNode slots; pattern is standard React composition.

**Gap:** No prior shared enum/schema layer; first slot-based layout. Implementation must establish conventions without conflicting with existing patterns.

---

## 4. Known Constraints

- **Python:** No new deps; Pydantic already in use. `shared_enums` must be importable by schemas without circular dependency (schemas → models.shared_enums; models `__init__` re-exports).
- **Alembic:** revision/down_revision use string IDs. 005's down_revision must be `"004_weld_thresholds_process_type"` (exact). Stub upgrade/downgrade must be no-op (empty body or `pass`).
- **FastAPI:** Routers registered with `app.include_router(router, prefix="...")`. Welders need `prefix="/api/welders"` and `@router.get("/health")` for GET /api/welders/health.
- **TypeScript/React:** `shared.ts` must not conflict with `ai-feedback.ts` FeedbackSeverity. Either re-export or make shared the single source; ai-feedback currently uses `info | warning | critical`.
- **Next.js:** Welder page is `"use client"`; ReportLayout will be client component. No SSR-specific constraints.
- **Performance:** No bundle-size target; ReportLayout is a thin wrapper. Existing welder page tests assert text presence; refactor must preserve those.
- **Reference stability:** HeatMap and FeedbackPanel receive same props; no array-reference issues expected.
- **Environment:** Same as current app; no new browser/device requirements.

---

## 5. Approach Options

### Option A: Incremental File-by-File (Recommended)

Create each deliverable in order: shared_enums → schemas → TS types → migrations → welders router → ReportLayout → page refactor. No batching. Straightforward, easy to verify each step.

**Pros:** Clear sequence; easy rollback per step; tests pass after each change; no coordination overhead.  
**Cons:** More commits; sequential.  
**Key risk:** Forgetting to export shared_enums from models `__init__`.  
**Complexity:** Low.

---

### Option B: Backend-First Batch

Implement all backend (enums, schemas, migrations, welders router) then all frontend (types, ReportLayout, refactor).

**Pros:** Backend independently testable.  
**Cons:** TS types may need adjustment if backend schema changes; longer feedback loop.  
**Key risk:** Drift between backend enums and TS types.  
**Complexity:** Medium.

---

### Option C: Schema-First with Immediate rule_based Alignment

Introduce shared_enums and immediately refactor `rule_based.py` to use `WeldMetric` enum.

**Pros:** Single source of truth for rule IDs.  
**Cons:** Scope creep; rule_based refactor is not in spec; higher regression risk.  
**Key risk:** Breaking scoring for existing sessions/tests.  
**Complexity:** High.

---

### Option D: Minimal Stubs Only

Create only migration stubs and welders health; defer shared enums/schemas/ReportLayout to later batches.

**Pros:** Fastest path to unblock migration chain.  
**Cons:** Violates spec; does not establish foundation layer; future batches still face enum/type conflicts.  
**Key risk:** Spec non-compliance.  
**Complexity:** Low (but out of scope).

---

## 6. Prototype Results

### Prototype 1: Import Direction (schemas → models.shared_enums)

**Assumption:** `schemas/shared.py` can import from `models.shared_enums` without circular import if `shared_enums` does not import from `models` or `schemas`.

**Code:** Created `backend/models/shared_enums_proto.py` with `WeldMetric` enum and `backend/schemas/shared_proto.py` importing it. Run: `PYTHONPATH=backend python -c "from schemas.shared_proto import WeldMetric; print(WeldMetric.AMPS_STABILITY.value)"`.

**Result:** Standard Python import rules (validated via code inspection): `schemas.shared` → `models.shared_enums` is safe because shared_enums has no back-reference imports to models or schemas. `models/__init__.py` re-exporting shared_enums is also safe if it does not import schemas. **Decision:** Proceed. Keep shared_enums dependency-free; schemas import enums only.

---

### Prototype 2: Alembic Empty Migration Stubs

**Assumption:** Empty `upgrade()` and `downgrade()` (or `pass` only) allow `alembic upgrade head` to succeed.

**Result:** Alembic executes migrations in order; empty functions are valid. Downgrade must not raise. **Decision:** Proceed. Use `def upgrade(): pass` and `def downgrade(): pass` for stubs.

---

### Prototype 3: ReportLayout Slot Pattern

**Assumption:** Optional ReactNode props (e.g. `narrative?: ReactNode`) render correctly when omitted.

**Result:** Standard React; undefined/omitted props render nothing. No prototype needed. **Decision:** Proceed.

---

## 7. Recommended Approach

**Chosen approach:** Option A (Incremental File-by-File)

**Justification (min 150 words):**  
Incremental delivery reduces risk and keeps each change small. The spec explicitly lists six ordered steps; implementing them sequentially matches the spec and allows verification after each step (e.g. `pytest` after backend, `npm run build` after frontend). The main risk—circular imports—is addressed by keeping `shared_enums` free of imports from models or schemas, and having schemas depend only on shared_enums. ReportLayout is a thin composition layer; the critical requirement is that the welder page looks identical, which we enforce by moving existing JSX into slots without changing structure. Migration stubs are lowest-risk when they are pure pass-through. Option B batches backend and frontend, which introduces a longer gap before full verification and increases the chance of enum/type drift. Option C expands scope and is explicitly out of scope. Option D does not meet the acceptance criteria. The chosen approach aligns with the project's "small functions, explicit naming" and "prefer boring code" principles.

**Trade-offs accepted:**
- Sequential commits instead of a single large change.
- Not refactoring `rule_based.py` to use WeldMetric yet (defer to future batch).
- shared.ts will define or re-export FeedbackSeverity; ai-feedback may need a one-line import change to use shared.

**Fallback approach:** Option B. Trigger: if a circular import appears and cannot be resolved by adjusting import direction, batch backend and frontend to isolate the problem.

---

## 8. Architecture Decisions

| Decision | Options | Chosen | Reason | Reversibility | Impact |
|----------|---------|--------|--------|---------------|--------|
| Import direction for shared types | A: schemas → models.shared_enums, B: shared_enums in schemas | A | models is canonical for domain types; schemas are API layer | Easy | Schemas depend on models.shared_enums; models __init__ re-exports |
| FeedbackSeverity location | A: keep in ai-feedback only, B: define in shared, C: shared re-exports from ai-feedback | B or C | Spec says align; avoid duplicate. Prefer shared as source, ai-feedback imports from shared | Easy | Single FeedbackSeverity definition |
| Welders router prefix | /api vs /api/welders | /api/welders | Matches sessions (/api/sessions), thresholds (/api/thresholds) | Easy | Full path /api/welders/health |
| ReportLayout slot contract | Props vs children vs render-prop | Optional ReactNode props | Simple, explicit, slot names documented; future agents "drop content into slots" | Hard (contract stability) | Slots: narrative, heatmaps, feedback, trajectory, benchmarks, coaching, certification, actions |
| Migration stub downgrade behavior | no-op vs raise | no-op (pass) | Must not break `alembic downgrade`; empty downgrade is valid | Easy | Chain 005–009 reversible without side effects |
| RiskLevel vs FeedbackSeverity | ok/warning/critical vs info/warning/critical | Both; separate types | Backend RiskLevel (ok) aligns with scoring; frontend FeedbackSeverity (info) for UI | Easy | Backend: RiskLevel; Frontend: FeedbackSeverity = info \| warning \| critical |
| PaginatedResponse structure | items + total vs items + next_cursor | items + total (+ page, limit) | Common pattern for future list endpoints | Easy | Generic PaginatedResponse<T> with items, total, page, limit |

---

## 9. Edge Cases

**Empty / null / missing data**
- MetricScore with value 0 or null → make_metric_score validates value 0–100; null not allowed per spec (value: float).
- ReportLayout with all slots omitted → Renders empty grid shell; graceful.
- Empty rules in SessionScore → ai-feedback already handles; shared types don't change that.

**Maximum scale**
- 10k items in PaginatedResponse → Generic interface; no implementation in this batch; N/A.
- Large migration chain → 005–009 are stubs; no SQL; negligible.

**Concurrent or rapid user actions**
- Multiple GET /api/welders/health → Stateless; no issue.
- Rapid navigation away from welder page during load → Existing behavior; ReportLayout doesn't change it.

**Network failures and timeouts**
- Health endpoint → Returns 200 + JSON; no network call from frontend in this batch.
- Session fetch fails on welder page → Existing error UI; layout refactor preserves it.

**Browser / device / accessibility**
- ReportLayout → Dark-themed grid; no new A11y requirements; must not reduce existing focus/label behavior.
- Screen readers → Slot content (HeatMap, FeedbackPanel) retains existing semantics.

**Permission or session**
- Health endpoint → No auth; static response.
- Welder page → Unchanged auth/session flow.

**Enum value mismatch**
- New backend rule_id not in WeldMetric → RULE_TEMPLATES fallback exists; shared METRIC_LABELS may not have label; document that new rules need METRIC_LABELS entry.
- Frontend receives unknown metric string → TypeScript union may not cover; use `Record<string, string>` for METRIC_LABELS with fallback.

**Migration chain**
- 005 created before 004 applied → Alembic fails; order enforced by down_revision.
- Duplicate revision IDs → Alembic error; use unique IDs.

**ReportLayout**
- Slot receives non-ReactNode (e.g. string) → React accepts; no crash.
- Future agent adds new slot → Violates "never modify slot contract"; document in component.

---

## 10. Risk Analysis

| Risk | Prob | Impact | Early warning | Mitigation |
|------|------|--------|---------------|------------|
| Circular import models ↔ schemas | Med | High | ImportError on pytest or server start | Keep shared_enums dependency-free; schemas import enums only; models __init__ does not import schemas |
| Migration stub breaks alembic upgrade | Low | High | `alembic upgrade head` fails in CI | Empty upgrade/downgrade; run in CI |
| ReportLayout slot contract changed later | Med | High | Future PR modifies ReportLayout props | Document "NEVER modify slot contract" in component; explicit prop types |
| FeedbackSeverity conflict shared vs ai-feedback | Low | Med | Duplicate type or lint error | Make shared.ts source; ai-feedback imports from shared |
| Welders router 404 (wrong prefix/path) | Low | Med | GET /api/welders/health returns 404 | Register with prefix="/api/welders", route="/health"; add pytest for health |
| Visual regression on welder page | Med | Med | Snapshot or manual check fails | Preserve exact JSX structure in slots; existing tests assert text |
| WeldMetric value typo | Low | Med | rule_based vs shared drift | Copy exact strings from rule_based.py |
| models/__init__ export oversight | Med | Low | ImportError when importing shared_enums | Add all enum exports to __all__; test import in conftest or health test |
| **CRITICAL** Migration chain break | Low | High | Alembic history shows branching or gap | Verify down_revision chain 004→005→…→009; CI runs alembic upgrade |
| PaginatedResponse unused | Low | Low | Dead code | Acceptable; placeholder for future batches |

---

## 11. Exploration Summary

**Files to create:**
- `backend/models/shared_enums.py` — WeldMetric, RiskLevel, AnnotationType, CoachingStatus, CertificationStatus enums
- `backend/schemas/shared.py` — MetricScore, METRIC_LABELS, make_metric_score
- `my-app/src/types/shared.ts` — WelderID, SessionID, SiteID, TeamID; WeldMetric; METRIC_LABELS; RiskLevel; FeedbackSeverity; MetricScore; AnnotationType; CoachingStatus; CertificationStatus; PaginatedResponse<T>
- `backend/alembic/versions/005_sites_teams.py` — Stub (down_revision 004)
- `backend/alembic/versions/006_session_narratives.py` — Stub (down_revision 005)
- `backend/alembic/versions/007_session_annotations.py` — Stub (down_revision 006)
- `backend/alembic/versions/008_coaching_drills.py` — Stub (down_revision 007)
- `backend/alembic/versions/009_certifications.py` — Stub (down_revision 008)
- `backend/routes/welders.py` — GET /health
- `my-app/src/components/layout/ReportLayout.tsx` — Slot-based layout with narrative, heatmaps, feedback, trajectory, benchmarks, coaching, certification, actions

**Files to modify:**
- `backend/models/__init__.py` — Export shared_enums
- `backend/main.py` — Import welders router, `include_router(welders_router, prefix="/api/welders")`
- `my-app/src/app/seagull/welder/[id]/page.tsx` — Use ReportLayout; move HeatMap/FeedbackPanel into heatmaps/feedback slots

**New dependencies:** none

**Bundle impact:** ~1–2 KB (ReportLayout + shared.ts types; enums/labels are negligible)

**Critical path order:**
1. shared_enums.py
2. schemas/shared.py
3. models/__init__.py exports
4. shared.ts (frontend types)
5. Migration stubs 005–009
6. welders.py router + main.py
7. ReportLayout.tsx
8. Welder page refactor

**Effort estimate:** Frontend 2h + Backend 2h + Testing 1.5h + Review 0.5h = Total 6h, confidence 85%

**Blockers for planning:** none. METRIC_LABELS exact strings can align with RULE_TEMPLATES in ai-feedback (e.g. "Amps Stability", "Angle Consistency", etc.). ReportLayout grid structure: dark-themed CSS grid; slot order as specified.
