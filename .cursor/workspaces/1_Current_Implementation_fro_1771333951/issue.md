
An issue document for the WWAD (Macro-Level Multi-Session Analytics Dashboard) is at:

**`.cursor/issues/wwad-macro-analytics-dashboard.md`**

It follows the Deep Capture Mode structure and includes:

---

## Summary of the issue

### Title
**[Feature] WWAD: Macro-Level Multi-Session Analytics Dashboard for Supervisors**

### TL;DR
Supervisors cannot see team-level welding performance. The MVP only gives per-session, per-frame views (replay, 3D heatmaps, micro-feedback). WWAD adds macro analytics: KPI tiles, trend charts, calendar heatmap, and CSV export, using only aggregated session data and without touching TorchViz3D, HeatmapPlate3D, or micro-feedback.

### Main points captured

1. **Current state audit**
   - Main dashboard uses generic mock data; Seagull is per-welder with no aggregation
   - `GET /api/sessions` is 501; scores are computed per-session on demand
   - Session model has `operator_id`, `weld_type`, `start_time` (no line/shift/project)

2. **Desired outcome**
   - New backend aggregate endpoint: `/api/sessions/aggregate` (or similar)
   - Supervisor dashboard with KPI tiles, trend chart, calendar heatmap
   - Date range filter and CSV export
   - No use of frame-level data or 3D components

3. **Scope boundaries**
   - **In scope:** Aggregate API, supervisor page, date filter, CSV export, aggregation by `operator_id` / `weld_type`
   - **Out of scope:** PDF export, line/shift metadata, `GET /api/sessions`, score persistence, drill-down in Phase 1

4. **Risks**
   - Performance of batch scoring (loading frames for many sessions)
   - No line/shift metadata in schema
   - Keeping WWAD orthogonal to 3D and micro-feedback

5. **Open questions (10+)**
   - Persist session scores for aggregation?
   - Which metric for the calendar heatmap?
   - Exact KPI set
   - Routing: `/supervisor` vs `/analytics` vs replacing `/dashboard`

6. **Effort estimate**
   - Medium (24–40 hours)
   - Priority: P2 (Normal)

---

**Next steps (from the issue):**

1. Validate KPI set with a stakeholder  
2. Answer questions #2 (calendar metric) and #6 (full KPI list)  
3. Run Phase 2: **Explore Feature** (45–90 min technical exploration)  
4. Create an implementation plan from the exploration
