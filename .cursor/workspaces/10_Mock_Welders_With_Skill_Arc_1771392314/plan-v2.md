
The refined plan is saved at `.cursor/taskspace/20260218_130707/plan-10-mock-welders-refined.md`.

Summary of changes from both critiques:

**Adversarial (critical)**
1. **Step 4.4 – last-slot trend fix:** For the last historical score slot, use `sc.total` when the historical fetch fails instead of 0, so `generateAIFeedback` does not infer a wrong “declining” trend.
2. **Phase 2 – session ID migration:** Documented that deployment replaces `sess_expert_001`/`sess_novice_001` and that existing references must be updated.
3. **Step 1.4 – PASS_BANDS:** Capped `consistent_expert` at 100 (no 73–103 or 78–108).
4. **Step 5.1 – arc coverage:** Added `test_mock_sessions_declining_session4_in_band` and `test_mock_sessions_volatile_session2_in_band`.
5. **Prototype in CI:** Added `test_prototype_arc_scoring_exits_zero` that runs the prototype as a subprocess and fails the build on non‑zero exit.

**Adversarial (other)**
6. **Step 2.4 – spot check:** When `existing == expected_count`, verify that `operator_id` matches for a sample row and re-seed if it does not.
7. **Step 2.1 – DB pre-flight:** Added `db.execute(text("SELECT 1"))` to fail fast when the DB is unreachable.
8. **Step 5.3 – last-slot regression test:** Added a test step for the Step 4.4 fix.
9. **Step 3.3 – automated badge check:** Added `data-testid` for automated badge verification.

**Standard critique**
10. **Pre-flight:** Document that if the prototype exits 1, run it before Phase 2.
11. **Step 4.2 verification:** Corrected the typo `[2]` → `[ ]`.
12. **Step 3.2 verification:** Matched wording to implementation (5s timeout via `Promise.race` with `setTimeout`).
