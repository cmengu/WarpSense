
Refined plan is updated. Summary of changes:

**Step 1.2 — Migration**
- Post-migration smoke check: assert seed values (tig=75, stick=20, flux_core=45, mig=45)
- Added `preflight_migration.py` for DB writability and row-count checks
- Verification updated with concrete seed checks

**Step 1.3**
- Verification: concrete Python snippet for `process_type` round-trip

**Step 1.4 — Threshold service**
- Fail loudly when tig/stick/flux_core row is missing (no silent MIG fallback)
- Per-row try/except in `_load_all` to handle corrupt rows
- Verification: `get_thresholds("tig")` returns 75; missing tig row raises

**Step 2.3**
- Reject sessions with &lt;10 frames; return 400 and clear message
- Phase 2 ordering: 2.1 → 2.2 → 2.3

**Step 3.4**
- Save button: loading state during PUT, error state on failure, re-enable Save for retry

**Step 4.2**
- Thermal fallback set to 60/80 to match seed (was 20/40)

**Step 4.5**
- Demo callout: fetch `GET /api/thresholds` and use mig row when `mockScore` has no spec; no hardcoded 45° ±5°

**Step 4.6**
- Conftest: import `WeldThresholdModel` before `create_all`
- Comments about dependency override keys for tests

**Step 3.2**
- Numeric verification for arc path (correct angle formula)

**Rollback**
- Procedure for "code reverted but migration not reverted"

**Notes & Risk Heatmap**
- Pre-flight script, seed verification, health check option
- New entries for zero-frames and missing-row cases
