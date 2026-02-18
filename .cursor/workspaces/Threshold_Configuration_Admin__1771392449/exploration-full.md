
Technical exploration is complete. Deliverables:

---

**Exploration document:** `.cursor/explore/threshold-configuration-admin-ui-exploration.md`

**Prototypes:**
- `my-app/prototype/threshold-injection-prototype.py` — `angle_target_deg` injection into `extract_features`
- `my-app/prototype/micro-feedback-thresholds-prototype.ts` — Optional `thresholds` for `generateMicroFeedback`

---

## 1. Complexity Classification

**Moderate.** Adds a DB table, CRUD API, admin UI with tabs, and wires thresholds through three backend call sites and two frontend consumers. The `weld_type` vs `process_type` mismatch must be decided before implementation.

---

## 2. Risk Profile

| Axis | Level | Reason |
|------|-------|--------|
| Data loss risk | Low | New table; existing session data unchanged |
| Service disruption risk | Medium | Score route refactor; cache invalidation on PUT |
| Security risk | Medium | `/admin` has no auth (deferred) |
| Dependency risk | Low | No new packages |
| Rollback complexity | Low | Migration reversible; changes localized |

---

## 3. Codebase Findings

| File | Purpose | Pattern | Reuse / Avoid |
|------|---------|---------|---------------|
| `backend/scoring/rule_based.py` | Five rules with module-level constants | Pure functions | Refactor to `score_session(..., thresholds)`; keep fallbacks |
| `backend/features/extractor.py` | Line 55: `max(abs(a - 45) for a in angles)` | List comprehensions | Add `angle_target_deg` param |
| `my-app/src/lib/micro-feedback.ts` | Angle 45°, ±5°/±15°, thermal 20°C | Top-level constants | Optional `thresholds` with fallbacks |
| `backend/routes/sessions.py` | Score route: `extract_features` → `score_session` | joinedload, `model_dump` | Add `get_thresholds(process_type)`, cache |
| `my-app/src/app/replay/[sessionId]/page.tsx` | `generateMicroFeedback(frames)` in `useMemo` | Client fetch | Pass thresholds from score/session |
| `backend/database/models.py` | `SessionModel.weld_type` (metal IDs) | SQLAlchemy ORM | Add `process_type`; do not overload `weld_type` |

**Similar implementations:** None for admin or thresholds. `/admin` does not exist; no tab components. Supervisor page uses a similar fetch pattern for aggregate data.

---

## 4. Known Constraints

- **Session semantics:** `weld_type` = metal (e.g. `mild_steel`); thresholds use process (mig/tig/stick/flux_core).
- **Missing `heat_diss`:** Spec defines 4 thresholds; `rule_based` has 5 (including `heat_diss`).
- **Admin auth:** Not implemented; assumed deferred.
- **Performance:** Thresholds cached; no DB hit per score request.
- **Accessibility:** WCAG 2.1 AA for admin form.

---

## 5. Approach Options

| Name | Description | Pros | Cons | Key risk |
|------|-------------|------|------|----------|
| A. Add `process_type` | New session column, default `"mig"` | Clear semantics, backward compatible | Extra column + backfill | Incomplete backfill |
| B. Repurpose weld_type | Switch to process semantics | No new column | Breaking; `mild_steel` incompatible | Data migration |
| C. Mapping table | weld_type → process mapping | No session schema change | Indirect, mapping maintenance | Stale mappings |
| D. Default fallback | Use `process_type or weld_type or "mig"` | Minimal migration surface | Fallback behavior in code | Inconsistent behavior |

---

## 6. Prototype Results

1. **extract_features:** `angle_max_deviation` with `target_deg` — simple refactor; proceed.
2. **generateMicroFeedback:** Optional `thresholds` — non-breaking; proceed.
3. **Inline arc SVG:** Standard SVG arc; no prototype; proceed.
4. **Threshold caching:** In-memory cache + clear on PUT; proceed.

---

## 7. Recommended Approach

**Approach A (add `process_type` column)**

Clean separation between metal (`weld_type`) and process (`process_type`). One migration adds both `weld_thresholds` and `process_type`; backfill sets `process_type = "mig"`. Scoring, extractor, and micro-feedback all use thresholds keyed by `process_type`.

**Trade-offs:** Extra column and backfill vs repurposing `weld_type`. Auth deferred.

**Fallback:** D if a new column is rejected — map `mild_steel` → `mig` and document as temporary.

---

## 8. Architecture Decisions (Summary)

- Process type source: New `process_type` column
- Threshold storage: DB table with migration seed
- Cache strategy: Invalidate on PUT
- Score API: Include `active_threshold_spec` in score response
- Micro-feedback thresholds: From score API or session
- Admin layout: Standalone `/admin` route group
- `heat_diss`: Add to thresholds model for consistency

---

## 9. Edge Cases (15+)

Covered in the document for: empty/null data, scale, concurrency, network, browser, permissions, and validation.

---

## 10. Risk Analysis

**CRITICAL:** `Session.weld_type` vs process semantics — add `process_type` and resolve before coding.

Other risks: incomplete backfill, cache invalidation, signature changes, Replay not passing thresholds.

---

## 11. Exploration Summary

- **Files to create:** 9 (models, service, routes, migration, admin page, layout, types, components, API)
- **Files to modify:** 9 (extractor, rule_based, sessions route, main, micro-feedback, replay, WelderReport pages, api.ts)
- **New dependencies:** none
- **Bundle impact:** ~2–3 KB (code-split admin)
- **Effort:** Frontend 8h + Backend 8h + Testing 4h + Review 2h ≈ **22h**, 75% confidence

**Blockers:**
1. Confirm `process_type` vs mapping for process type.
2. Confirm TIG spec: "75°10°" vs "75° ±10°".
3. Decide whether to include `heat_diss` in thresholds.
4. Decide when to add admin auth (now vs later).
