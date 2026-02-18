
The refined plan is saved in `.cursor/issues/threshold-configuration-admin-ui-plan.md`. Summary of changes applied:

**Critical fixes (Standard + Adversarial):**

1. **Step 1.3**  
   - `from_pydantic` / `to_pydantic` use `(getattr(session, "process_type", None) or "mig")` to handle `process_type=None`.

2. **Step 1.4**  
   - Implemented `get_all_thresholds()` that ensures cache is loaded before returning values.  
   - Added `threading.Lock` around `_load_all` to avoid race conditions under concurrent load.

3. **Step 1.5**  
   - PUT response is built directly from the updated row instead of calling `get_thresholds` after commit, avoiding 500s on connection problems.

4. **Step 1.8** (new)  
   - Added step to update `backfill_score_total.py` to use `get_thresholds`, `angle_target_deg`, and `score_session(thresholds=...)` per session `process_type`.

5. **Step 3.4**  
   - `isCompleteForm` checks `Number.isFinite()` to block NaN from cleared fields.  
   - Replaced placeholder with full Thermal/Amps/Volts/Heat Diss input section.  
   - Number inputs use `parseFloat(...) || 0` to avoid NaN.

6. **Step 4.5**  
   - Callout uses `mockScore?.active_threshold_spec` when present, with a fallback to the MIG spec.

7. **Step 4.6**  
   - Added `seeded_weld_thresholds` fixture so tests run against seeded `weld_thresholds`.  
   - `test_get_thresholds_returns_four` and `test_put_threshold_invalidates_cache` depend on this fixture.

**Other updates:**

- Migration note for large tables in Known Issues.  
- Phase 1 estimate updated to 6.25h.  
- Phase 2 prerequisites include `get_all_thresholds` and running `test_put_threshold_invalidates_cache`.  
- SQLAlchemy 2.0 note added for `db.query()`.  
- Notes clarified for `backfill_score_total.py` and Step 1.8.
