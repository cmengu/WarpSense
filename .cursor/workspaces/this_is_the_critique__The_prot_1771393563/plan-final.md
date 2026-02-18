
The refined plan is complete. Summary of changes from both critiques:

## Refined Plan – Summary of Changes

### Critical changes (adversarial + standard)

1. **Pre-flight structure assertion** – Pre-flight now checks:
   - `WELDER_ARCHETYPES` is non-empty
   - Each archetype has `welder_id` and `sessions`
   - All archetypes have `sessions >= 1` (avoids `sessionCount` KeyError and empty skip)

2. **Plan file resolution** – Canonical order:
   - `docs/plan-10-mock-welders.md` first (for CI)
   - `.cursor/issues/10-mock-welders-plan.md` (implementation plan, not the issue)
   - `.cursor/taskspace/*/plan-10-mock-welders-refined.md` last
   - Step 1.2 explicitly states: do not edit `10-mock-welders-with-skill-arcs.md` (that is the issue)

3. **Empty `session_ids`** – Step 2.1: if `expected_count == 0`, return 1 and fail fast; do not skip with “Demo data already complete.”

4. **Step 4.3 gate** – If E2E is not set up: require PR checklist item or a verification doc; merge is blocked until manual Step 4.4 is completed and documented.

5. **Step 2.2 partial-seed verification** – Added a concrete Python snippet for the “delete one session” check instead of a manual SQL note.

### Other changes

- **Step 1.1 tuning guide grep** – Specified `backend/data/mock_sessions.py` and exact grep command
- **Step 1.4 PYTHONPATH** – `PYTHONPATH=backend` from project root (aligned with pre-flight)
- **Step 4.1 sc-null test** – Added a test describing the contract when `sc` is null; uses a concrete `[...histScores, 0]` example instead of passing `null`.
- **Risk heatmap** – New rows for: empty `WELDER_ARCHETYPES`, wrong plan file (issue vs plan), manual fallback drift, `sessionCount` KeyError, version control conflicts
- **Success criteria** – Added checks for structure assertion, empty `expected_count` fail-fast, plan resolution, and manual gate enforcement
- **Known issues** – Clarified spot-check limitation and skeleton verification; added manual gate requirement
- **Rollback** – Plan conflict mitigation noted
