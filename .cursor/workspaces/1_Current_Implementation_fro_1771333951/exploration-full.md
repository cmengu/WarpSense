
Summary of the WWAD exploration:

## Exploration output

**File:** `.cursor/explore/wwad-macro-analytics-exploration.md`

### Decisions and approach

1. **Score persistence** – Add a `score_total` column to sessions. Computing scores on the fly for many sessions (500 × ~1500 frames) would be too slow (tens of seconds); persistence keeps aggregate responses under 3s.

2. **Aggregate API** – Use `GET /api/sessions/aggregate?date_start=&date_end=` to query metadata and `score_total` only (no frames).

3. **Route** – `/supervisor` as the supervisor dashboard route.

4. **Calendar heatmap** – Custom GitHub-style grid (sessions per day for Phase 1). The existing `HeatMap` is for thermal data; a separate component is needed.

5. **KPIs** – avg_score, session_count, top_performer, rework_count (score &lt; 60).

6. **Orthogonality** – No imports from TorchViz3D, HeatmapPlate3D, HeatMap (thermal), or micro-feedback in the supervisor module.

### Prototype

**File:** `backend/scripts/prototype_aggregate_perf.py`

Tests metadata-only queries vs batch scoring with frames. Run:

```bash
cd backend && python scripts/prototype_aggregate_perf.py
```

(Requires seeded DB; e.g. `curl -X POST http://localhost:8000/api/dev/seed-mock-sessions`)

### Files to add/modify

| Action | Path |
|--------|------|
| **New** | `backend/routes/aggregate.py` |
| **New** | `backend/services/aggregate_service.py` |
| **New** | `backend/alembic/versions/003_add_score_total.py` |
| **New** | `my-app/src/app/(app)/supervisor/page.tsx` |
| **New** | `my-app/src/components/dashboard/CalendarHeatmap.tsx` |
| **New** | `my-app/src/lib/export.ts` |
| **New** | `my-app/src/types/aggregate.ts` |
| **New** | `backend/scripts/backfill_score_total.py` |
| **Modify** | `backend/main.py`, `my-app/src/lib/api.ts` |

### Effort estimate

24–32 hours total (backend 10–14h, frontend 10–12h, testing 4–6h).

---

The exploration doc covers scope, approaches, constraints, risks, architectural decisions, edge cases, and a readiness check. You can move to Phase 3: **Create Plan** using this exploration as the base.
