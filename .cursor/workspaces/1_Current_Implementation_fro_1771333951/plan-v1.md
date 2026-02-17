
All critical and minor changes from the critique are now applied in the plan. Summary:

## Refinements applied

### Critical fixes (P0)

1. **Step 2.2 – date_end inclusivity**  
   Replaced `start_time <= date_end` with `start_time < (date_end + 1 day)` so sessions later on `date_end` are included.

2. **Step 2.3 – route registration order**  
   Documented that `aggregate_router` must be registered before `sessions_router` so `/api/sessions/aggregate` is not matched by `/api/sessions/{session_id}`.

3. **Step 1.5 – backfill batching**  
   Switched from `.all()` to a `limit(BATCH_SIZE)` loop to avoid OOM on large datasets.

4. **Step 2.3 – `get_db` reuse**  
   Aggregate route now imports `get_db` from `routes.sessions` instead of defining its own.

### Minor fixes

5. **Step 1.2 – pre-migration backup**  
   Added a pg_dump backup step and noted to verify downgrade on staging.

6. **Step 3.4 – ChartData shape**  
   Specified the LineChart payload: `{ id: 'trend-1', type: 'line', title: 'Score Trend', data: trend.map(t => ({ date: t.date, value: t.value })) }`.

7. **Step 3.5 – AbortController**  
   Supervisor fetch now uses `AbortController` plus a cancelled flag to avoid setState-after-unmount and redundant requests. `fetchAggregateKPIs` accepts an optional `AbortSignal`.

8. **Step 1.7 – ordering**  
   Moved from after Phase 2 header to its correct place after Step 1.6.

9. **Steps 2.7 / 2.8 – test file paths**  
   Explicit paths: `backend/tests/test_aggregate_service.py`, `backend/tests/test_aggregate_api.py`.

10. **Common Failures**  
    Documented: aggregate 404 (router order), backfill OOM, and date range exclusion.
