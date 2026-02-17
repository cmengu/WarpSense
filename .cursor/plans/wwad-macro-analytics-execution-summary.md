# WWAD Macro Analytics — Execution Summary

## Steps
1. File: `backend/scripts/verify_backfill.py` — Create; exit 1 if COMPLETE+frames have null score_total. Key: `SELECT ... score_total IS NULL`
2. File: `backend/services/aggregate_service.py` — Guard len(scored)==0; cap 1000 sessions; sessions_truncated. Key: `avg_score = None if not scored else total/len(scored)`
3. File: `backend/tests/test_aggregate_service.py` — Add test for all-null avg_score, invalid date 400. Key: assert avg_score is None; assert 400
4. File: `my-app/src/lib/api.ts` — Document NEXT_PUBLIC_API_URL for env switching. Key: `process.env.NEXT_PUBLIC_API_URL || localhost:8000`
5. File: `my-app/src/components/dashboard/CalendarHeatmap.tsx` — Use UTC: setUTCDate, Date.UTC. Key: `dte.setUTCDate(...)`; `toISOString().slice(0,10)`
6. File: `my-app/src/lib/aggregate-transform.ts` — Guards for null trend/calendar; [] fallbacks. Key: `Array.isArray(res.trend) ? res.trend : []`
7. File: `my-app/src/__tests__/lib/aggregate-transform.test.ts` — Tests: empty, null, all-zero trend; malformed. Key: no throw; charts[0].data === []
8. File: `my-app/.eslintrc*` — no-restricted-imports for supervisor/CalendarHeatmap/aggregate-transform. Key: disallow TorchViz3D, HeatmapPlate3D
9. File: `my-app/src/app/(app)/supervisor/page.tsx` — Mandatory alert when sessions_truncated. Key: "Export limited to 1000 sessions..."
10. File: `my-app/e2e/supervisor-export.spec.ts` — Playwright: date filter + CSV export. Key: Last 30 days; Export CSV; filename *.csv
11. File: `backend/routes/aggregate.py` — Log requests: date_start, date_end, duration_ms, sessions_truncated. Key: logger.info("aggregate", extra={...})
12. File: `my-app/src/app/(app)/supervisor/page.tsx` (export handler) — Log export failures; log truncation. Key: console.error; log sessions_truncated

## Critical Details
- avg_score only when len(scored) > 0
- sessions_truncated → mandatory UI alert
- aggregate_router BEFORE sessions_router
- UTC for API + CalendarHeatmap
- ESLint no-restricted-imports in CI
- 90-day limit; 1000-session cap
