
Here's a concise summary of the implementation plan and where it lives.

## Implementation Plan Summary

The plan is saved at **`.cursor/plans/wwad-macro-analytics-implementation-plan.md`** and follows the requested structure.

### Structure

1. **Pre-planning thinking (30 min)**
   - Synthesis of exploration: approach, components, data flow, risks, gaps
   - Dependency analysis: 21 work items, dependency graph, bottlenecks, parallelizable work
   - Risk-based planning: mitigation for each risk and failure-mode handling

2. **Phase breakdown**
   - **Phase 1 (6.5 h):** Score persistence — migration, `score_total`, lazy persistence in `get_session_score`, backfill
   - **Phase 2 (8.5 h):** Aggregate API — Pydantic models, `aggregate_service`, route, tests
   - **Phase 3 (8.25 h):** Supervisor dashboard — types, API client, CalendarHeatmap, `aggregateToDashboardData`, supervisor page
   - **Phase 4 (5.25 h):** Extensions — CSV export, date filter, empty/error states, accessibility

3. **32 atomic steps**
   - 9 critical steps with full code examples
   - Each step has subtasks, verification tests, pass criteria, and time estimates
   - Code examples for: migration, lazy persistence, backfill, aggregate service, aggregate route, `CalendarHeatmap`, `export.ts`, supervisor page

4. **Other sections**
   - Critical vs non‑critical step classification
   - Pre‑flight checklist per phase
   - Risk heatmap (20 risks)
   - 12 success criteria (P0/P1)
   - Progress table and common failure/fix notes
   - Definition of done

### Main technical decisions

- **Score persistence:** Add `score_total` and persist lazily in `get_session_score` plus backfill for existing sessions
- **Aggregate API:** `GET /api/sessions/aggregate?date_start=&date_end=`; metadata + `score_total` only (no frames)
- **Orthogonality:** No imports from TorchViz3D, HeatmapPlate3D, or micro‑feedback components
- **Route:** `/supervisor`

### Total estimate: ~28.5 hours

The plan is implementation-ready with concrete steps and verification tests for each phase.
