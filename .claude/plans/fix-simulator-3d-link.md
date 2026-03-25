# Fix "View 3D Comparison" Link in Simulator

**Overall Progress:** `0%` (0/1 steps done)

---

## Architecture Overview

**The problem:** `my-app/src/app/(app)/simulator/page.tsx` line 271 generates a dynamic `/compare/{matchResult.session_id}/sess_expert_aluminium_001_001` URL from the closest-match result. The `/compare` route uses seeded DB sessions, so it breaks if the matched corpus session (e.g. `sess_al_angled_001_015`) was never seeded or has no report. The `/demo` route is hardcoded for the two aluminium demo welders and always works.

**Pattern applied:** Hardcoded constant — the demo comparison target is fixed by design, not computed from simulator state.

**What stays unchanged:** All backend files, `ClosestMatchResult` type, `getClosestMatch()` API call, match card display logic.

**Critical decision:** Hard-code `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001` rather than derive from `matchResult.session_id`. Alternative (route to `/compare/{matched}/expert`) rejected because `/compare` requires seeded DB sessions with reports; corpus sessions don't have them.

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every modified file. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight

- Read `my-app/src/app/(app)/simulator/page.tsx` in full.
- Run `grep -n "compare.*matchResult.session_id" "my-app/src/app/(app)/simulator/page.tsx"` → must return exactly 1 match. Record the exact line. If 0 → already patched, stop. If 2+ → STOP and report.
- Run `grep -n "demo/sess_expert_aluminium" "my-app/src/app/(app)/simulator/page.tsx"` → must return 0 matches (confirms new string not yet present).

---

## Step 1: Fix "View 3D Comparison" href — *Non-critical: single string replacement*

**Step Architecture Thinking:**

**Pattern applied:** Hardcoded constant replaces dynamic string interpolation.

**Why this step exists:** The current href interpolates `matchResult.session_id` which is a corpus ID (e.g. `sess_al_angled_001_015`) — a session that exists analytically but has no DB row or report. `/demo` is the correct route because it's hardcoded for the two aluminium demo welders and always renders.

**Why this file:** This is the only file rendering the "View 3D Comparison" button.

**Alternative rejected:** Routing to `/compare/${matchResult.session_id}/sess_expert_aluminium_001_001` with the matched corpus session — rejected because corpus sessions have no seeded DB rows or quality reports, causing a 404 or blank compare page.

**What breaks if deviated:** If the URL remains dynamic, clicking "View 3D Comparison" after a bad-weld simulation routes to a `/compare` page for a session that doesn't exist in the DB.

---

**Idempotent:** Yes — string replace is safe to re-run.

**Pre-Read Gate:**
- `grep -n "compare.*matchResult.session_id" "my-app/src/app/(app)/simulator/page.tsx"` → must return exactly 1 match. If 0 → already patched, skip step. If 2+ → STOP and report.

**Replace:**

Old:
```tsx
              href={`/compare/${matchResult.session_id}/sess_expert_aluminium_001_001`}
```

New:
```tsx
              href="/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001"
```

**Git Checkpoint:**
```bash
git add "my-app/src/app/(app)/simulator/page.tsx"
git commit -m "fix: hardcode View 3D Comparison link to /demo expert vs novice sessions"
```

**✓ Verification:**

**Type:** Integration + E2E

**Action (run in order):**

1. Confirm old string is **gone**:
   `grep -n "compare.*matchResult.session_id" "my-app/src/app/(app)/simulator/page.tsx"` → must return **0 matches**. If 1+ → edit was not applied → re-apply and recheck.

2. Confirm new string is **present**:
   `grep -n "demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001" "my-app/src/app/(app)/simulator/page.tsx"` → must return **exactly 1 match**.

3. E2E: Navigate to `/simulator`, run a simulation, click "View 3D Comparison →" — browser URL must be `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001`.

**Pass:** Steps 1 and 2 both return correct match counts AND browser URL matches target.

**Fail:**
- Step 1 returns 1 match → old href still present → Edit tool did not apply — re-read file, re-apply edit
- Step 2 returns 0 matches → new href not written — check file path has correct `(app)` parentheses
- Link not visible in browser → `matchResult` is null → run a simulation first (debounce fires after slider move or button click)

---

## Success Criteria

| Feature | Target | Verification |
|---|---|---|
| View 3D Comparison link | Always routes to `/demo/sess_expert_aluminium_001_001/sess_novice_aluminium_001_001` | Click button after any simulation → URL must match exactly |
| Match card still renders | Unchanged | `matchResult` display, stats grid, rework cost all still visible |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not batch multiple steps into one git commit.**
