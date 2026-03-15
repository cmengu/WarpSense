# PANEL_MOCK_SCORES Fallback — Implementation Plan

**Overall Progress:** 0%

## TLDR

Add `PANEL_MOCK_SCORES` to page.tsx as a hardcoded fallback map (panel ID → score). Apply it in the Promise.allSettled handler so panels with no seeded session show realistic scores instead of "Score unavailable". Real API scores always take precedence — the fallback only fires when fetchScoreWithTimeout returns null (404 / network failure). Two edits, one file, zero architecture changes.

---

## Critical Decisions

| Decision | Choice |
|----------|--------|
| **1** | Scores live in page.tsx as `Record<string, number>`, not in panel.ts or the PANELS array. Panel type stays a descriptor; scores are a result. |
| **2** | Fallback fires only when `r.value == null`. Real seeded session scores always win. |
| **3** | Values match inspection decision tiers — clear → ≥ 85 (green), needs-dpi → 60–84 (amber), needs-xray → < 60 (red). PANEL-4C=45 and PANEL-7A=72 are fixed to match existing sort test expectations. |
| **4** | Once panel sessions are seeded in the backend, PANEL_MOCK_SCORES has zero effect and can be deleted cleanly. |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → STOP. Output full contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Clarification Gate

| Unknown | Required | Source | Blocking |
|---------|----------|--------|----------|
| Score values per panel | See constant below | Human | Resolved |
| Fallback priority | Real API score wins; mock only when null | Human | Resolved |
| File to edit | `my-app/src/app/(app)/dashboard/page.tsx` | Codebase | Resolved |

---

## Pre-Flight — Run Before Any Code Changes

```bash
# 1. Confirm PANEL_MOCK_SCORES does not already exist
grep -n "PANEL_MOCK_SCORES" my-app/src/app/\(app\)/dashboard/page.tsx
# Expected: no output

# 2. Confirm insertion anchor exists (caret anchors to line start — excludes comment matches)
grep -n "^const PANELS" my-app/src/app/\(app\)/dashboard/page.tsx
# Expected: exactly 1 match

# 3. Confirm replacement target exists (unique to panel block; expert block uses expertVal)
grep -n "const score =" my-app/src/app/\(app\)/dashboard/page.tsx
# Expected: exactly 1 match — this is the panel loop block

# 4. Baseline TypeScript check
cd my-app && npx tsc --noEmit
# Expected: exit 0

# 5. Baseline test check
cd my-app && npx jest src/__tests__/app/\(app\)/dashboard/page.test.tsx --passWithNoTests 2>&1 | tail -5
# Expected: exit 0 — record pass count
```

**Baseline Snapshot (agent fills during pre-flight):**
```
PANEL_MOCK_SCORES already exists : no (must be no to proceed)
const PANELS matches              : 1
const score = matches             : 1 (panel block anchor)
TSC exit code                    : ____
Test pass count                  : ____
```

**If TSC exit code is non-zero at baseline → stop and report before making any changes. If test baseline exits non-zero → stop and report before making any changes. This plan assumes a clean baseline.**

---

## Tasks

### Phase 1 — Add Constant

#### Step 1: Add PANEL_MOCK_SCORES constant

**Idempotent:** Yes — adding a new constant; re-run produces the same file state.

**Pre-Read Gate:**
- `grep -n "PANEL_MOCK_SCORES" my-app/src/app/\(app\)/dashboard/page.tsx` → must return 0 matches. If any match → already added; skip to Step 2.
- `grep -n "^const PANELS" my-app/src/app/\(app\)/dashboard/page.tsx` → must return exactly 1 match. Insert immediately above that line.

**Insert** immediately above `const PANELS`:

```typescript
const PANEL_MOCK_SCORES: Record<string, number> = {
  "PANEL-4C": 45,  // red   — X-ray inspection required
  "PANEL-7A": 72,  // amber — Dye penetrant inspection required
  "PANEL-2B": 63,  // amber — Dye penetrant inspection required
  "PANEL-1A": 91,  // green — Surveyor-ready
  "PANEL-9D": 88,  // green — Surveyor-ready
  "PANEL-3F": 94,  // green — Surveyor-ready
};
```

**Git Checkpoint:**
```bash
git add my-app/src/app/\(app\)/dashboard/page.tsx
git commit -m "step 1: add PANEL_MOCK_SCORES fallback constant"
```

**Verification:**
- Action: `cd my-app && npx tsc --noEmit`
- Expected: Exit 0, no errors
- Fail: TypeScript error on new constant → check `Record<string, number>` spelling and that the constant is at module scope (not inside a function)

---

### Phase 2 — Apply Fallback

#### Step 2: Apply fallback in Promise.allSettled handler

**Idempotent:** Yes — single string replacement; re-run produces same state. If already applied, Pre-Read Gate skips to verification.

**Pre-Read Gate:**
- `grep -n "PANEL_MOCK_SCORES" my-app/src/app/\(app\)/dashboard/page.tsx` → must return exactly 1 match (from Step 1). If 0 → Step 1 incomplete; stop.
- `grep -n "PANEL_MOCK_SCORES\[f\.panel" my-app/src/app/\(app\)/dashboard/page.tsx` → if 1 match exists, replacement is already applied; skip to verification.
- `grep -n "const score =" my-app/src/app/\(app\)/dashboard/page.tsx` → must return exactly 1 match. If 0 or 2+ → stop and report.

**Anchor lookup (grep-anchored, self-correcting after Step 1 line shift):** Before constructing the replacement, run `grep -n "const score =" my-app/src/app/\(app\)/dashboard/page.tsx`, take the returned line number N, and read lines N through N+4 verbatim so the anchor matches the actual whitespace, line breaks, and formatting.

**Anchor block** (inside `panelFetches.map`, exactly once):

```typescript
const score =
  r.status === "fulfilled" && r.value != null
    ? (r.value as SessionScore).total
    : null;
```

**Replace with:**

```typescript
const score =
  r.status === "fulfilled" && r.value != null
    ? (r.value as SessionScore).total           // real seeded score wins
    : (PANEL_MOCK_SCORES[f.panel.id] ?? null); // fallback only when API returns null
```

**Note:** Use `f.panel.id` (no non-null assertion). `f.panel` in panelFetches is `Panel`, never null.

**Git Checkpoint:**
```bash
git add my-app/src/app/\(app\)/dashboard/page.tsx
git commit -m "step 2: apply PANEL_MOCK_SCORES fallback in allSettled handler"
```

**Verification:**
- Action:
  ```bash
  cd my-app && npx tsc --noEmit
  grep -n "PANEL_MOCK_SCORES\[f\.panel" my-app/src/app/\(app\)/dashboard/page.tsx
  cd my-app && npx jest src/__tests__/app/\(app\)/dashboard/page.test.tsx --passWithNoTests 2>&1 | tail -5
  ```
- Expected:
  1. TSC exits 0
  2. `PANEL_MOCK_SCORES[f.panel` returns exactly 1 match
  3. Tests pass at same count as pre-flight baseline

- Fail (concrete recovery for grep returns 0):
  - TSC error on `f.panel.id` → check panelFetches declaration shape
  - Grep returns 0 for `PANEL_MOCK_SCORES[f.panel` → run `grep -n "r.value != null" my-app/src/app/\(app\)/dashboard/page.tsx` to confirm whether the original anchor is still present. If present → the str_replace did not apply; read the exact surrounding lines (run `grep -n "const score ="` to get line N, then read N through N+4) and retry with matching whitespace. If absent → the block was modified by another change; stop and report.
  - Test count decreased → a test was deleted unintentionally; check git diff before committing

---

## Regression Guard

| System | Pre-change | Post-change |
|--------|------------|-------------|
| Panel scores (no seed) | "Score unavailable" on all 6 cards | Numeric scores from PANEL_MOCK_SCORES |
| Panel scores (seeded) | Real score from API | Real score from API — fallback never fires |
| Expert Benchmark | Unchanged | Unchanged — separate expertScore state, untouched |
| Sort order | PANEL-4C first (lowest), PANEL-7A second | Identical — mock values match sort test expectations |
| Test suite | All passing | All passing, same count |

---

## Rollback

```bash
git revert HEAD    # reverts Step 2
git revert HEAD~1  # reverts Step 1
cd my-app && npx tsc --noEmit  # confirm clean
```

---

## Success Criteria

| Feature | Target | Verification |
|---------|-------|--------------|
| No "Score unavailable" | All 6 panels show numeric scores | Load dashboard; no "Score unavailable" visible |
| Correct risk tiers | PANEL-4C red, PANEL-7A/2B amber, PANEL-1A/9D/3F green | Visual check against inspection decision labels |
| Real scores win | Seeded session overrides mock | Seed sess_PANEL-4C_005; confirm card shows seeded value, not 45 |
| TypeScript clean | Zero errors | `npx tsc --noEmit` exits 0 |
| Tests unchanged | Same pass count as baseline | `npx jest .../dashboard/page.test.tsx` exits 0 |

---

⚠️ Do not mark a step 🟩 Done until its verification test passes.  
⚠️ Do not batch Steps 1 and 2 into one commit.  
⚠️ If blocked, output full current file state before stopping.  
⚠️ When panel sessions are seeded in the backend, delete PANEL_MOCK_SCORES entirely.
