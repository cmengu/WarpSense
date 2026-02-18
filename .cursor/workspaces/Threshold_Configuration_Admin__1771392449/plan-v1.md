
The refined plan has been written to `.cursor/issues/threshold-configuration-admin-ui-plan.md`. It now includes:

**Critical fixes:**
- **Step 1.2**: Pre-migration check for `down_revision` and `sa.text()` for raw SQL
- **Step 1.4**: Fallback for empty `weld_thresholds` (no KeyError), plus multi-worker limitation documented
- **Step 1.5**: `invalidate_cache()` in `finally`; PUT returns a single object
- **Step 2.3**: Explicit dependency on 1.3; `active_threshold_spec` extended with thermal, amps, volts, heat_diss
- **Step 3.4**: `isCompleteForm` + `canSave` so save is disabled until fetch succeeds and form is complete
- **Step 4.2**: Uses thermal/amps/volts/heat_diss from `active_threshold_spec` when present
- **Step 4.6**: Test `test_put_threshold_invalidates_cache` asserts GET score returns updated values after PUT

**Other updates:**
- Notes for `backfill_score_total.py`
- Pre-flight check for `down_revision`
- Rollback section
- Known issues (multi-worker, migration compatibility)
