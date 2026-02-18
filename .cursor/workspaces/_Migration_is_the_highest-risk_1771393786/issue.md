
Created the issue at `.cursor/issues/threshold-configuration-admin-ui-plan-critique-fixes.md`. Summary:

---

### Summary

**Title:** `[Improvement] Fix five main and three minor gaps in Threshold Admin UI plan before implementation`

**Main fixes:**

| Problem | Fix |
|--------|-----|
| **1. Migration pre-flight** | Add row-count check (>1000 rows → run manual UPDATE first) and `alembic upgrade head --sql > migration_preview.sql` for SQL preview |
| **2. Cache race** | `invalidate_cache` must take `_load_lock` before setting `_cache_loaded = False`; document threading model |
| **3. Form NaN bug** | Replace `parseFloat(...) \|\| 0` with `parseFloat(...)`; enforce `angle_target_degrees > 0`; backend rejects 0 |
| **4. Test fixture** | Specify `session_factory` that creates `SessionModel` with frames and process_type (e.g. `generate_expert_session` + patch) |
| **5. Micro-feedback flicker** | Ensure micro-feedback waits on both session data and score before computing; add verification step |

**Minor fixes:**

- Step 1.5: Comment on asymmetric validation (angle/thermal vs amps/volts/heat_diss)
- Step 3.1: Document optional `ActiveThresholdSpec` fields for legacy API
- Step 4.5: Note risk of hardcoded fallback when MIG seed changes

**Classification:** P1, S (4–8h), plan-only edits; no production code until the parent plan is executed.
