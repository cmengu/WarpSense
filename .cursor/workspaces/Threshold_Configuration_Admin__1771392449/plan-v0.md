
The implementation plan is in `.cursor/issues/threshold-configuration-admin-ui-plan.md`. Summary:

---

## Plan Overview

**4 phases, 20 steps, ~22h total**

| Phase | Focus | Est. |
|-------|--------|------|
| **Phase 1** | Data model & backend (migration, process_type, weld_thresholds table, threshold service, GET/PUT API) | 6h |
| **Phase 2** | Scoring wiring (extract_features angle_target, score_session thresholds, active_threshold_spec in score API) | 5h |
| **Phase 3** | Admin UI (types, API, AngleArcDiagram, layout, tabs/form with validation) | 6h |
| **Phase 4** | Micro-feedback & callouts (generateMicroFeedback thresholds, Replay + WelderReport + ScorePanel + demo, tests) | 5h |

---

## Decisions Applied

- **process_type column** on sessions (default `mig`), backfilled in migration
- **TIG spec**: 75° ±10° (typo fix)
- **`heat_diss_consistency`** added to weld_thresholds model
- **Cache** invalidated on PUT
- **`active_threshold_spec`** in score API response
- **Micro-feedback** takes optional thresholds; Replay passes them from the score
- **Standalone** `/admin` route group

---

## Files

**Create:** `backend/models/thresholds.py`, `backend/services/threshold_service.py`, `backend/routes/thresholds.py`, `backend/alembic/versions/004_weld_thresholds_and_process_type.py`, `my-app/src/types/thresholds.ts`, `my-app/src/components/admin/AngleArcDiagram.tsx`, `my-app/src/app/admin/layout.tsx`, `my-app/src/app/admin/thresholds/page.tsx`

**Modify:** `backend/database/models.py`, `backend/models/session.py`, `backend/features/extractor.py`, `backend/scoring/rule_based.py`, `backend/routes/sessions.py`, `backend/main.py`, `my-app/src/lib/api.ts`, `my-app/src/lib/micro-feedback.ts`, `my-app/src/app/replay/[sessionId]/page.tsx`, `my-app/src/app/seagull/welder/[id]/page.tsx`, `my-app/src/components/welding/ScorePanel.tsx`, `my-app/src/app/demo/team/[welderId]/page.tsx`

---

The plan matches the create-plan-autonomous output structure: phases, steps with file/code/verification/dependencies, risk heatmap, pre-flight checklists, success criteria, and a progress tracker. All CRITICAL steps have full code; non-critical steps have concise snippets.
