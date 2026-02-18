
Refined plan is saved. Summary of changes:

## Summary of Refinements

### Critical issues fixed

1. **Step 1.4 – Prototype validates production path**  
   - Replaced `make_session_for_arc` with `generate_session_for_welder` from `mock_sessions`  
   - Added explicit pass bands with `sys.exit(1)` when out of range  
   - Added `random.seed(42)` in prototype for volatile  
   - Ensures prototype uses the same path as seed/Phase 2  

2. **Step 2.4 – Correct idempotent logic**  
   - Skip only when `existing == expected_count`  
   - When `existing > 0` but partial, re-seed (delete and regenerate)

3. **Step 4.4 – Preserve historicalScores order**  
   - Build `historicalScores` with `histResults.map((r, i) => ...)` instead of `filter(fulfilled).map`  
   - Use 0 for failed fetches so index order stays correct for `generateAIFeedback`

4. **Step 4.2/4.3 – Expert fetch handling**  
   - Use `Promise.allSettled` for expert session so 404 does not break the page  
   - Fallback behavior when expert session is missing  

5. **Step 3.2 – Fetch timeout**  
   - Added 5s timeout via `Promise.race` to avoid long hangs  

### Other changes

- **Step 1.3:** Clarified signature includes `arc_type`  
- **Step 1.2 verification:** Added check that declining returns `disable=True`  
- **Step 2.2:** Documented wipe limitation for orphan sessions  
- **Step 2.1:** Added DB reachability check to pre-flight  
- **Phases 3 & 4:** Documented “run seed before opening dashboard/welder report”  
- **Step 5.1:** Added `test_mock_sessions_fast_learner_session0_in_band`  
- **Step 5.2:** Use `EXPECTED_SESSION_COUNT` from `WELDER_ARCHETYPES`; wipe asserts via derived IDs instead of `like(sess_*)`  
- **Risk heatmap:** Expanded with new risks and mitigations  
- **Success criteria:** Added P0 for prototype and test validation of mock_sessions score bands  
- **Known issues:** Orphan sessions, WELDERS duplication, batch scores OOS
