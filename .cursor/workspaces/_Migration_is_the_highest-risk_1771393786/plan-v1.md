
The refined plan is at `.cursor/issues/threshold-configuration-admin-ui-plan-refined.md` and includes all fixes from both the standard and adversarial critiques.

**Addressed issues:**
- **Step 1.1:** `angle_target_degrees` changed to `gt=0` in Pydantic models (aligned with PUT)
- **Step 1.2:** DB writability check, post-migration smoke check, CI migration step
- **Step 1.7:** `process_type` validation in `create_session` (reject non-mig/tig/stick/flux_core)
- **Step 1.9 (new):** Update `prototype_arc_scoring.py` and `prototype_aggregate_perf.py` to use thresholds, or document the limitation
- **Step 4.1:** Per-generator try/catch in `generateMicroFeedback` to return partial results instead of empty output
- **Step 4.2:** `scoreFetchError` state and "Score unavailable" message when score fetch fails
- **Step 4.6:** Explicit dependency overrides for `routes.thresholds.get_db` and `routes.sessions.get_db`, and `len(session.frames) >= 10` assertion in `session_factory`
