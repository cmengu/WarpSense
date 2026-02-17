# WWAD Macro Analytics — Key Facts

## Key Files

- `backend/routes/aggregate.py` — GET /api/sessions/aggregate endpoint
- `backend/services/aggregate_service.py` — aggregation logic
- `backend/alembic/versions/003_add_score_total.py` — add score_total column
- `backend/scripts/backfill_score_total.py` — backfill existing sessions
- `backend/scripts/prototype_aggregate_perf.py` — perf prototype (run before impl)
- `my-app/src/app/(app)/supervisor/page.tsx` — supervisor dashboard route
- `my-app/src/components/dashboard/CalendarHeatmap.tsx` — GitHub-style sessions/day grid
- `my-app/src/lib/export.ts` — CSV generate + download
- `my-app/src/types/aggregate.ts` — AggregateKPIResponse types
- Modify: `backend/main.py`, `my-app/src/lib/api.ts`

## Architecture

- **Score persistence:** Add `score_total` to sessions; compute on COMPLETE. Batch scoring 500 sessions = 25–100s → must persist.
- **Aggregate API:** `GET /api/sessions/aggregate?date_start=&date_end=` — metadata + score_total only, no frames.
- **Pattern:** Reuse DashboardLayout, MetricCard, ChartCard, LineChart, BarChart. Calendar is custom (7×N grid).
- **Orthogonality:** Zero imports from TorchViz3D, HeatmapPlate3D, HeatMap (thermal), micro-feedback.
- **Route:** `/supervisor`. Filter: COMPLETE only.
- **KPIs:** avg_score, session_count, top_performer, rework_count (score < 60).

## Dependencies / Integration

- Reuse: extract_features, score_session
- Index on start_time for date range queries
- Client CSV: Blob → URL.createObjectURL → download (no lib)

## Risks

- Batch scoring on request → OOM/slow; mitigated by persistence
- Coupling to 3D/micro-feedback → code review, no imports in supervisor
- Migration/backfill failure → test on dev, batch backfill
- Wrong KPIs → validate with stakeholder first
