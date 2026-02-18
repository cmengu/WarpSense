
Applied all critique fixes to the Threshold Configuration Admin UI plan. Summary:

## Critique fixes applied

### Problem 1 — Migration pre-flight (Step 1.2)
- **Pre-migration verification** now includes:
  1. `alembic upgrade head --sql > migration_preview.sql` for SQL preview
  2. Row-count check: if `sessions` > 1000 rows, run manual `UPDATE sessions SET process_type = 'mig' WHERE process_type IS NULL` and verify before running `alembic upgrade head`
- **Phase 1 prerequisites** updated with these two checks

### Problem 2 — Cache race (Step 1.4)
- `invalidate_cache()` now acquires `_load_lock` before setting `_cache_loaded = False`
- Service docstring documents threading: `_load_lock` protects both `_load_all` and `invalidate_cache`

### Problem 3 — Form NaN bug (Step 3.4)
- Removed `|| 0` fallback: uses `parseFloat(e.target.value)` only
- `isCompleteForm` now requires `angle_target_degrees > 0`
- `handleSave` validates `angle_target_degrees > 0` before submit
- Step 1.5: backend rejects `angle_target_degrees=0` with 422 and a clear message
- Verification extended to cover cleared fields and `angle_target_degrees=0`

### Problem 4 — Test fixture (Step 4.6)
- Added explicit `session_factory` fixture using:
  - `generate_expert_session`
  - `session.model_copy(update={"process_type": process_type})`
  - `SessionModel.from_pydantic(session)`
  - 10+ frames for valid score
- Added note that `WeldThresholdModel` must be imported before `Base.metadata.create_all`

### Problem 5 — Micro-feedback flicker (Step 4.2)
- Micro-feedback computed only when both `sessionData?.frames` and `primaryScore` are present: `if (!sessionData?.frames || !primaryScore) return []`
- Verification updated: “Micro-feedback doesn’t visibly re-render when score loads after frames”; throttle score API to confirm

### Minor changes
- **Step 1.5:** Comment added for validation asymmetry (angle/thermal vs amps/volts/heat_diss)
- **Step 3.1:** Documented optional `ActiveThresholdSpec` fields for legacy API
- **Step 4.5:** Note added that hardcoded “MIG spec — Target 45° ±5°” can be wrong if admin changes MIG seed

### Risk heatmap & checklist
- 1.2 risk merged to cover partial migration
- 1.4 risk added for `invalidate_cache` race
- 4.2 risk added for micro-feedback flicker
- 4.6 risk added for `session_factory` without frames
- Phase 1 prerequisites updated with environment-aware checks

### Success criteria
- #4: Validation includes rejection of `angle_target_degrees=0`
- #8: Micro-feedback uses configured thresholds and does not visibly flicker

Plan file updated: `threshold-configuration-admin-ui-plan.md`
