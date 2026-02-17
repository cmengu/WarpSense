
`CONTEXT.md` is updated to match the implemented WWAD macro-analytics feature. Summary of changes:

## Updates

### Project Overview
- Added “WWAD macro-analytics (supervisor dashboard, aggregate API, score_total persistence)” to **Current State**.

### Implemented Features
- New **WWAD Macro-Analytics (Supervisor Dashboard)** section covering:
  - Team KPIs, trend chart, calendar heatmap, CSV export  
  - Orthogonality rules (no 3D/micro-feedback imports)  
  - Integration: `fetchAggregateKPIs`, `aggregateToDashboardData`, export flow  

### Utilities
- `aggregateToDashboardData`, `generateCSV`, `downloadCSV` documented.

### Data Models
- **Session** now includes `score_total` and backfill notes.

### Patterns
- New **WWAD Orthogonality** pattern (no 3D/micro-feedback in supervisor code, ESLint enforcement).

### API Contracts
- Added **GET /api/sessions/aggregate** (params, response shape, usage).
- Updated **GET /api/sessions/:id/score** with lazy score persistence.

### Integration Points
- Added **Aggregate Data Flow** (`fetchAggregateKPIs` → `aggregateToDashboardData` → DashboardLayout + CalendarHeatmap).
- Added **CalendarHeatmap** to key components.

### Component APIs
- **CalendarHeatmap** props and usage.

### Constraints
- **Aggregate Limits**: 90-day range, 1000-session cap, truncation alert.

### File Structure
- `supervisor/` route, `dashboard/` components, `aggregate-transform.ts`, `export.ts`, `types/aggregate`.
- Backend: `aggregate.py`, `aggregate_service.py`, `aggregate.py` models, backfill and verify scripts.

### Related Docs
- Links to the WWAD plan and key facts.

`CONTEXT.md` now reflects the WWAD implementation and can be used by AI tools and contributors.
