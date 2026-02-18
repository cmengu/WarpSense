
Refined plan is in place. Summary of changes that address both critiques:

**Critical fixes**
1. **Pre-flight automation** — Added `PYTHONPATH=backend python -c "from data.mock_sessions import generate_session_for_welder; from data.mock_welders import WELDER_ARCHETYPES"` at the top so missing dependencies fail fast.
2. **Step 2.1 `session_ids` undefined** — Defined `session_ids` and `expected_count` at the very start of `main()` and included the full `main()` flow so the skip path cannot see them undefined. Added an invariant note on ordering.
3. **Step 3.2 `sc` null** — When `fetchScore` fails, avoid appending 0 to the last slot; added a guard and requirement to use `insufficient_data` or not render the trend.
4. **Step 1.2 plan file path** — Defined a resolution order (taskspace → `.cursor/issues` → create `docs/`), plus an abort path if nothing exists.
5. **Step 4.3 integration test** — New Step 4.3 to verify the welder report caller passes `sc.total` for the last slot, with a manual fallback if E2E is not set up.

**Other improvements**
- **Terminology** — Switched "sessionCounts" to "sessions" to match `WELDER_ARCHETYPES`.
- **Step 1.4 verification** — Replaced `python3.8` with `python` for 3.10+.
- **Tuning guide validation** — Step 1.1 verification includes a grep check that the tuning guide params exist in `mock_sessions`.
- **Orphan sessions** — Documented in Step 2.2 that orphan sessions may remain.
- **Risk heatmap** — Added a row for "session_ids undefined in skip path".
- **Success criteria** — Added checks for the pre-flight, `sc` null handling, and integration test.
- **Rollback & known issues** — Added sections to match the template.
