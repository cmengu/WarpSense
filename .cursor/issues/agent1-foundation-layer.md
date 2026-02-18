# Agent 1 — Foundation Layer

---

### 1. Title
`[Feature] Agent 1 Foundation Layer: shared enums, schemas, migration stubs, welders router, ReportLayout`

---

### 2. TL;DR
This issue lays pure infrastructure so future batches (sites/teams, session narratives, annotations, coaching, certifications) can work in parallel without conflicts. Today there are no shared enums for weld metrics or risk levels, no welders API, no ReportLayout slot component, and no migration stubs for upcoming tables. The root cause is phased development — the MVP shipped with hardcoded rule IDs and inline page layout. After this fix: canonical enums live in backend and frontend, migration chain 005→009 is reserved, GET /api/welders/health exists, welder report uses ReportLayout slots, and the page looks identical. Effort: S (4–8h).

---

### 3. Root Cause Analysis
1. **Surface:** Future batches will conflict — no reserved migrations, no shared types, no welders router.
2. **Cause:** MVP was built feature-first; shared types were deferred.
3. **Cause:** Scoring rules use string IDs (`amps_stability`, etc.) scattered across `rule_based.py`, `ai-feedback.ts`, `seagull-demo-data.ts` — no single source.
4. **Cause:** Welder report page has inline layout; no slot-based abstraction for adding narrative, trajectory, coaching later.
5. **Root cause:** No foundation layer was delivered before batch-parallel work started; enums, schemas, and layout contracts were never introduced.

---

### 4. Current State

**What exists today:**
- `backend/models/__init__.py` — exports Session, Frame, ScoreRule, SessionScore, etc.; no shared enums
- `backend/models/scoring.py` — `ScoreRule` with `rule_id: str`; no WeldMetric enum
- `backend/models/thresholds.py` — WeldTypeThresholds; no shared RiskLevel
- `backend/scoring/rule_based.py` — rule IDs `amps_stability`, `angle_consistency`, `thermal_symmetry`, `heat_diss_consistency`, `volts_stability` as literals
- `backend/routes/sessions.py`, `thresholds.py`, `aggregate.py`, `dashboard.py`, `dev.py` — no welders router
- `backend/main.py` — registers dashboard, aggregate, sessions, thresholds, dev; no welders
- `backend/alembic/versions/001_*.py` through `004_weld_thresholds_and_process_type.py` — last revision: `004_weld_thresholds_process_type`, down_revision `003_add_score_total`
- `my-app/src/types/ai-feedback.ts` — FeedbackSeverity `info | warning | critical`; no shared RiskLevel
- `my-app/src/types/session.ts`, `thresholds.ts`, etc. — no shared.ts with ID types or WeldMetric
- `my-app/src/app/seagull/welder/[id]/page.tsx` — inline layout; HeatMap and FeedbackPanel in ad-hoc divs; no ReportLayout
- `my-app/src/components/welding/HeatMap.tsx` — used by welder report for thermal comparison
- `my-app/src/components/welding/FeedbackPanel.tsx` — used by welder report for feedback items

**What's broken or missing:**
- **Shared enums:** No `shared_enums.py` or `shared.ts` — future batches would define their own enum values, causing drift.
- **Metric labels:** Human-readable labels for the 5 metrics are implicit in `ai-feedback.ts` RULE_TEMPLATES; no METRIC_LABELS dict.
- **Migration stubs:** Tables for sites/teams, session_narratives, annotations, coaching_drills, certifications require migrations; chain not reserved.
- **Welders router:** No `/api/welders/*` routes; future batches need a welders API.
- **ReportLayout:** Page layout is inline; no slot contract for narrative, heatmaps, feedback, trajectory, benchmarks, coaching, certification, actions.
- **backend/schemas/** — directory does not exist; Pydantic schemas live in models or inline.

---

### 5. Desired Outcome

**User flow after fix:**
1. **Primary:** User visits `/seagull/welder/[id]` → page renders with identical visual layout (header, Thermal Comparison with HeatMap×2, Detailed Feedback with FeedbackPanel, Progress chart, PDF/Email buttons). Only internal structure changes (ReportLayout slots).
2. **API health:** Developer calls GET `/api/welders/health` → `{ "status": "ok", "router": "welders" }`.
3. **Edge — empty thermal:** Expert session absent → single HeatMap for welder; layout unchanged.
4. **Edge — error:** Session fetch fails → error state unchanged; layout shell still uses ReportLayout.

**Acceptance criteria:**
1. `GET /api/welders/health` returns `{ "status": "ok", "router": "welders" }`.
2. No circular import errors when importing `backend.models.shared_enums` or `backend.schemas.shared`.
3. `my-app/src/types/shared.ts` has zero TypeScript errors; `npm run build` passes.
4. Welder report page at `/seagull/welder/[id]` renders HeatMap(s) and FeedbackPanel in the same positions as before (visual regression: identical).
5. `backend/alembic/versions/005_sites_teams.py` exists with `down_revision = "004_weld_thresholds_process_type"`, empty upgrade()/downgrade().
6. `backend/alembic/versions/006_session_narratives.py` exists with `down_revision` pointing to 005.
7. `backend/alembic/versions/007_session_annotations.py` exists with `down_revision` pointing to 006.
8. `backend/alembic/versions/008_coaching_drills.py` exists with `down_revision` pointing to 007.
9. `backend/alembic/versions/009_certifications.py` exists with `down_revision` pointing to 008.
10. `ReportLayout` exposes slots: narrative, heatmaps, feedback, trajectory, benchmarks, coaching, certification, actions.
11. `pytest backend/tests/ -x` passes.

**Out of scope:**
- Implementing SQL in migrations 005–009 — stubs only; future batches fill SQL.
- Adding real welder CRUD routes — health check only.
- Changing HeatMap or FeedbackPanel component APIs — same props, same behaviour.
- Migrating other pages (replay, demo, compare) to ReportLayout — welder report only.

---

### 6. Constraints
- **Tech stack:** Python + FastAPI backend; React + Next.js + TypeScript frontend. Must use Pydantic for `MetricScore`; must not add new runtime deps.
- **Performance:** No regressions; layout refactor must not increase bundle size materially.
- **Browser:** Same as existing app; no new device support.
- **Accessibility:** No new A11y requirements; ReportLayout must not reduce existing focus/label behaviour.
- **Blocked by:** None.
- **Blocks:** Batch 1 (sites/teams), Batch 2 (annotations), Batch 3 (coaching, certifications).
- **Approval:** N/A.

---

### 7. Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Circular import between models and schemas | Med | High | Keep shared_enums in models; schemas import enums only; models __init__ re-exports. |
| Migration stub chain breaks `alembic upgrade` | Low | High | Stub downgrade() must be no-op; upgrade() empty. Run `alembic upgrade head` in CI. |
| ReportLayout slot contract changes later | Med | High | Make contract explicit (prop types, slot names); document "never modify slot contract" in component. |
| shared.ts conflicts with existing ai-feedback.ts FeedbackSeverity | Low | Med | Align FeedbackSeverity in shared.ts with ai-feedback.ts (`info \| warning \| critical`); avoid duplicate types. |
| Welders router prefix wrong (e.g. /api/welders vs /welders) | Low | Med | Register with `prefix="/api/welders"` and ensure health at `/api/welders/health`. |
| Refactor introduces subtle layout shift | Med | Med | Use existing welder report tests; add visual snapshot or selector assertions for HeatMap/FeedbackPanel presence. |

---

### 8. Open Questions
| Question | Assumption | Confidence | Resolver |
|----------|------------|------------|----------|
| Exact WeldMetric values from plan | Use `amps_stability`, `angle_consistency`, `thermal_symmetry`, `heat_diss_consistency`, `volts_stability` (from rule_based.py, seagull-demo-data.ts) | High | Implementation agent |
| METRIC_LABELS human-readable strings | E.g. "Amps Stability", "Angle Consistency", etc. — align with RULE_TEMPLATES in ai-feedback.ts | Med | Implementation agent |
| ReportLayout grid layout (columns/rows) | Dark-themed grid; slot order: narrative, heatmaps, feedback, trajectory, benchmarks, coaching, certification, actions | Med | Implementation agent |

---

### 9. Classification
- **Type:** feature
- **Priority:** P2 (standard — unblocks future batches)
- **Effort:** S (4–8h)
- **Effort breakdown:** Frontend 2h + Backend 2h + Testing 1.5h + Review 0.5h = Total 6h
