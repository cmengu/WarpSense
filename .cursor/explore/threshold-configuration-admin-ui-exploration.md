# Threshold Configuration Admin UI — Technical Exploration

## 1. Complexity Classification

**Moderate.** Adds a new DB table, CRUD API, admin UI with tabs and forms, and wires thresholds through 3 backend call sites and 2 frontend consumers. The weld_type semantic collision (metal vs process) requires a schema or mapping decision before implementation. No ML or heavy computation; mostly CRUD and wiring.

---

## 2. Risk Profile

| Axis | Level | Reason |
|------|-------|--------|
| Data loss risk | Low | New table append-only; session data untouched. |
| Service disruption risk | Medium | Score route refactor; cache invalidation on PUT can cause brief inconsistency. |
| Security risk | Medium | /admin currently unprotected; auth is deferred. |
| Dependency risk | Low | No new packages; uses existing FastAPI, SQLAlchemy, React. |
| Rollback complexity | Low | Migration reversible; code changes localized. |

---

## 3. Codebase Findings

**Search the codebase now.** Findings from real files:

| File path | What it does | Pattern used | Reuse | Avoid |
|-----------|--------------|--------------|-------|-------|
| `backend/scoring/rule_based.py` | 5 rule checks using module-level constants | Pure functions, `features.get(...)` | Refactor to `score_session(session, features, thresholds)`; keep rule structure | Do not remove fallback when thresholds missing |
| `backend/features/extractor.py` | Computes 5 features; line 55 `max(abs(a - 45) for a in angles)` | `statistics.stdev`, list comprehensions | Add `angle_target_deg: float = 45` param to `extract_features` | Don't break empty-list handling |
| `my-app/src/lib/micro-feedback.ts` | `generateMicroFeedback(frames)` — angle 45°, ±5°/±15°, thermal 20°C | Const at top, two generators | Add optional `thresholds?: WeldTypeThresholds` param; fallback to current consts | Don't change CAP_PER_TYPE or try-catch |
| `backend/routes/sessions.py` | `get_session_score` loads session, `extract_features(session)`, `score_session(session, features)` | `joinedload(frames)`, `model_dump()` | Add `get_thresholds(process_type)` before scoring; pass to extract/score | Don't add DB hit per request — use cache |
| `my-app/src/app/replay/[sessionId]/page.tsx` | `useMemo(() => generateMicroFeedback(sessionData?.frames ?? []), [...])` | Client fetch, useMemo | Pass thresholds from session metadata or score API response | Avoid extra fetch if score already loaded |
| `backend/database/models.py` | `SessionModel` with `weld_type` (String) | SQLAlchemy ORM | Add `process_type` column (nullable, default "mig") OR map weld_type→process | Don't reuse weld_type for process — semantic collision |
| `my-app/src/app/seagull/welder/[id]/page.tsx` | WelderReport: score, AI summary, heatmaps; no threshold callout | fetchSession + fetchScore, useState | Add callout below score; `active_threshold_spec` from score API | Don't change existing layout structure |
| `backend/alembic/versions/001_initial_schema.py` | Initial sessions/frames tables | `op.create_table`, indexes | New migration for `weld_thresholds`; seed 4 rows | Don't modify 001 |
| `my-app/src/components/welding/ScorePanel.tsx` | Fetches score, displays total + rules | useEffect fetch, loading/error states | No change; score API will include active_threshold_spec | — |
| `my-app/src/lib/api.ts` | fetchScore, fetchSession; no thresholds | buildUrl, apiFetch | Add `fetchThresholds()`, `updateThreshold(weldType, body)` | — |

**Similar implementations (admin / forms / tabs):**

- **Admin routes:** None exist. `/admin/*` does not exist. Closest: `(app)/dashboard`, `(app)/supervisor` — standard Next.js App Router pages.
- **Form with validation:** No existing form with inline validation. `FeedbackPanel` uses list rendering; form patterns will be new.
- **Tabs:** No tab UI. `my-app/src/data/mockData.ts` has chart data; no tab component. Build from scratch with `aria-selected`, `role="tablist"`.

**Gap:** No prior admin or threshold CRUD pattern. Supervisor page (`my-app/src/app/(app)/supervisor/page.tsx`) fetches aggregate KPIs; similar fetch pattern for GET thresholds. No PUT/form precedent.

---

## 4. Known Constraints

- **Locked:** FastAPI, SQLAlchemy, PostgreSQL, React, Next.js, Tailwind. No new frameworks.
- **SSR / Hydration:** Admin page can be client-only; no frame/3D, so no WebGL constraints.
- **Hook rules:** React 19; `use` for params; `useState`/`useEffect`/`useMemo` as today.
- **Performance:** Threshold cache in backend — no DB hit per score. Target: score latency unchanged.
- **Scale:** 4 weld types; small table. No pagination.
- **Reference stability:** Thresholds cached; invalidation on PUT. Client re-fetches after save.
- **Session.weld_type:** Currently `"mild_steel"` (metal). Thresholds expect `mig`|`tig`|`stick`|`flux_core` (process). Must add `process_type` or mapping.
- **Rule_based heat_diss:** `HEAT_DISS_CONSISTENCY_THRESHOLD=40` exists; task spec interface omits it. Add to thresholds or keep hardcoded.
- **Accessibility:** WCAG 2.1 AA for admin form — labels, focus, errors.
- **Environment:** Same as MVP — Chrome, Firefox, Safari recent.

---

## 5. Approach Options

### A. Add `process_type` column; separate from weld_type

- **Description:** Add `process_type` (nullable, default `"mig"`) to sessions. Backfill existing with `"mig"`. Scoring uses `process_type` for thresholds; `weld_type` stays as metal.
- **Pros:** Clear semantics; no collision; both retained for future. **Cons:** Migration + backfill; two concepts.
- **Key risk:** Backfill must run before scoring uses it. **Complexity:** Medium.

### B. Repurpose weld_type for process (breaking)

- **Description:** Change weld_type semantic to process (mig/tig/stick/flux_core). Metal becomes separate or dropped.
- **Pros:** No new column. **Cons:** Breaking; existing `mild_steel` data incompatible.
- **Key risk:** Data migration and API contract change. **Complexity:** High.

### C. Mapping table: weld_type → process_type

- **Description:** Config table mapping metal codes to process. `mild_steel` → `mig`, etc. No session schema change.
- **Pros:** No migration to sessions. **Cons:** Indirect; mapping maintenance.
- **Key risk:** Stale mappings. **Complexity:** Medium.

### D. Default process_type when absent; add column later

- **Description:** Scoring uses `process_type or weld_type or "mig"`. Add column in same migration as weld_thresholds; backfill in same migration.
- **Pros:** Single migration; backward compatible. **Cons:** Fallback logic in code.
- **Key risk:** Inconsistent behavior during rollout. **Complexity:** Low–Medium.

**Recommended:** A or D. A is cleaner long-term; D minimizes migration surface. Plan should pick one and document.

---

## 6. Prototype Results

### Prototype 1: extract_features angle_target injection

**What was tested:** `angle_max_deviation` computed from configurable target.

**Code:** `my-app/prototype/threshold-injection-prototype.py`:
```python
def _angle_max_deviation_param(angles: list[float], target_deg: float = 45) -> float:
    return max(abs(a - target_deg) for a in angles) if angles else 0.0
```

**Result:** Straightforward; one extra param; backward compatible with default 45. **Decision:** Proceed.

### Prototype 2: generateMicroFeedback with optional thresholds

**What was tested:** Optional `thresholds?: WeldTypeThresholds`; fallback to current constants.

**Code:** `my-app/prototype/micro-feedback-thresholds-prototype.ts` — `getAngleFeedback(angle, t)` with DEFAULT vs TIG (75°, ±10°).

**Result:** API extension is non-breaking; call sites pass `undefined` to keep current behavior. **Decision:** Proceed.

### Prototype 3: Inline arc diagram (SVG)

**What was tested:** Not coded; spec says ~20 lines SVG. Semicircle with target angle arc is standard SVG arc (`path` with `A` command). **Decision:** Well-understood; no prototype needed. Proceed.

### Prototype 4: Threshold caching

**What was tested:** In-memory dict with TTL or invalidation on PUT. Standard pattern. **Decision:** Well-understood; use `@lru_cache` or module-level dict + `cache_clear()` on PUT. Proceed.

---

## 7. Recommended Approach

**Chosen approach:** A (Add `process_type` column) + full threshold wiring as specified.

**Justification:** Option A resolves the weld_type semantic collision cleanly. `weld_type` remains metal (`mild_steel`); `process_type` is process (`mig`, `tig`, etc.). Scoring, extractor, and micro-feedback all consume thresholds keyed by `process_type`. The migration adds both `weld_thresholds` and `process_type`; backfill sets `process_type = 'mig'` for existing sessions. Admin UI at `/admin/thresholds` with tabs is straightforward; no existing admin pattern to conflict with. Cache invalidation on PUT keeps scores consistent. Micro-feedback receives thresholds via score API response or session metadata — one extra field, no extra round-trip when score is already fetched. Trade-off: one extra column and backfill, but semantics stay clear and future extensions (e.g. metal-specific overrides) remain possible.

**Trade-offs accepted:**
- Extra `process_type` column and backfill vs. repurposing weld_type (cleaner long-term).
- Admin auth deferred to infra (document as constraint).
- `heat_diss_consistency` not in task spec — add to thresholds model for consistency or keep hardcoded and document.

**Fallback approach:** D (default process_type when absent). Trigger: Product rejects new column. Mitigation: Use `weld_type` with mapping `mild_steel`→`mig` and document as temporary.

---

## 8. Architecture Decisions

| Decision | Options | Chosen | Reason | Reversibility | Downstream impact |
|----------|---------|--------|--------|---------------|-------------------|
| Process type source | A: new column, B: repurpose weld_type, C: mapping | A | Clear semantics, no breaking change | Easy (drop column) | All scoring/feedback uses process_type |
| Threshold storage | DB table, env vars, config file | DB table | Admin-editable, auditable | Easy | API + migration |
| Cache strategy | None, TTL, invalidation on PUT | Invalidation on PUT | Fresh after edit; simple | Easy | PUT must call cache_clear |
| Score API response | Add active_threshold_spec, separate endpoint | Add to score response | One fetch for report; no extra call | Easy | Frontend reads new field |
| Micro-feedback thresholds | Fetch separately, from score, from session | From score API or session | Replay/Report already fetch score/session | Easy | Extend score response |
| Admin layout | Nested under /app, standalone | Standalone /admin | No auth coupling to (app) | Easy | New route group |
| heat_diss in thresholds | Include, omit | Include | 5 rules in rule_based; spec has 4 | Easy | Add column to weld_thresholds |

---

## 9. Edge Cases

| Category | Scenario | Handling | Graceful? |
|----------|----------|----------|-----------|
| Empty/null | No thresholds in DB | Seed from migration; defaults always present | Yes |
| Empty/null | Session has no process_type (legacy) | Default "mig" in scoring | Yes |
| Empty/null | Frames empty | extract_features returns 0; score computed | Yes |
| Scale | 10k sessions scored/min | Cached thresholds; no N+1 | Yes |
| Scale | Large payload on GET thresholds | 4 rows; trivial | Yes |
| Concurrent | Admin saves while score computed | Cache cleared after commit; next score gets fresh | Partial (brief stale window) |
| Concurrent | Two admins edit same weld type | Last write wins; no conflict resolution | Partial |
| Network | PUT fails | Form shows error; no partial save | Yes |
| Network | GET thresholds fails on admin load | Show error state; retry | Yes |
| Browser | No JS | Form won't work; acceptable for admin | Partial |
| Permissions | Unauthenticated /admin | No auth today; document | Partial |
| Permissions | Session from another tenant | N/A for single-tenant MVP | N/A |
| Validation | warning > critical | Backend 422; inline error | Yes |
| Validation | Negative values | Backend validation | Yes |
| Validation | Unknown weld_type in PUT | 404 or 422 | Yes |
| Missing data | Session has weld_type "mild_steel", no process_type | Backfill gives "mig"; or mapping | Yes |

---

## 10. Risk Analysis

| Risk | Prob | Impact | Early warning | Mitigation |
|------|------|-------|---------------|------------|
| process_type backfill incomplete | Med | High | Scores use wrong thresholds for old sessions | Backfill in same migration as column; verify count |
| Cache not invalidated on PUT | Low | Med | Stale scores after admin edit | Call cache_clear in PUT handler; test |
| extract_features/score_session signature change breaks callers | Low | Med | Import errors, test failures | Add optional params; fallbacks; update tests |
| Micro-feedback thresholds not passed from Replay | Med | Low | Replay uses default 45° | Pass thresholds from score when available |
| Admin form validation bypass | Low | Low | Invalid values in DB | Backend validation mandatory |
| TIG spec typo ("75°10°") misinterpreted | Low | Low | Wrong defaults | Document as 75° ±10°; confirm with task author |
| heat_diss missing from spec | Low | Low | Inconsistent 5th rule | Add to weld_thresholds or document as fixed |
| **CRITICAL: Session.weld_type semantic collision** | High | High | Scoring uses wrong process for metal-typed sessions | Resolve with process_type column before build |
| Tab UI accessibility | Low | Med | Fails audit | Use aria roles, keyboard nav |
| Bundle size (admin page) | Low | Low | Large chunk | Code-split; admin not on critical path |

---

## 11. Exploration Summary

**Files to create:**
- `backend/database/models.py` — add `WeldThresholdModel` (or new file `models/thresholds.py`)
- `backend/models/thresholds.py` — Pydantic `WeldTypeThresholds`
- `backend/services/threshold_service.py` — `get_thresholds(process_type)`, cache, `invalidate_cache()`
- `backend/routes/thresholds.py` — `GET /api/thresholds`, `PUT /api/thresholds/:weld_type`
- `backend/alembic/versions/004_weld_thresholds_and_process_type.py` — table + seed + process_type column
- `my-app/src/app/admin/thresholds/page.tsx` — Admin UI
- `my-app/src/app/admin/layout.tsx` — Admin layout (minimal)
- `my-app/src/types/thresholds.ts` — `WeldTypeThresholds` interface
- `my-app/src/components/admin/AngleArcDiagram.tsx` — Inline SVG arc
- `my-app/src/lib/api.ts` — `fetchThresholds`, `updateThreshold`

**Files to modify:**
- `backend/features/extractor.py` — Add `angle_target_deg` param
- `backend/scoring/rule_based.py` — Accept thresholds dict; use in rules
- `backend/routes/sessions.py` — Load thresholds by process_type; pass to extract/score; add `active_threshold_spec` to score response
- `backend/main.py` — Register thresholds router
- `my-app/src/lib/micro-feedback.ts` — Optional `thresholds` param
- `my-app/src/app/replay/[sessionId]/page.tsx` — Pass thresholds to generateMicroFeedback
- `my-app/src/app/seagull/welder/[id]/page.tsx` — Threshold callout below score
- `my-app/src/app/demo/team/[welderId]/page.tsx` — Same callout (or use mock spec for demo)
- `my-app/src/lib/api.ts` — Extend SessionScore type with `active_threshold_spec`

**New dependencies:** none

**Bundle impact:** ~2–3 KB (admin page + small form components); code-split from main.

**Critical path order:**
1. Migration: weld_thresholds table + process_type column + seed
2. Backend: threshold_service + routes
3. Backend: Wire thresholds into extract_features, score_session
4. Backend: Extend score API response
5. Frontend: fetchThresholds, updateThreshold, types
6. Frontend: Admin page (tabs, form, arc diagram)
7. Frontend: Micro-feedback thresholds param
8. Frontend: WelderReport callout
9. Tests: API, scoring, callout

**Effort estimate:** Frontend 8h + Backend 8h + Testing 4h + Review 2h = **Total 22h**, confidence 75%

**Blockers for planning:**
1. **process_type vs weld_type:** Confirm product decision — add column (A) or mapping (C). Assumption: add `process_type`, default "mig".
2. **TIG spec typo:** Confirm "75°10°" → "75° ±10°". Assumption: 75° target, ±10° warning.
3. **heat_diss_consistency:** Add to thresholds or keep hardcoded? Assumption: add for consistency.
4. **Admin auth:** Implement now or stub? Assumption: stub; document for production.
