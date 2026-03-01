# Plan: Remove 2D Heatmaps from Compare Page

**Overall Progress:** `100%`

## TLDR

Remove the three 2D heatmap columns (Session A, Delta, Session B) from the compare page. The page will retain: 3D Torch visualizations, timeline slider, alert feed, and summary text. This simplifies the UI and avoids redundant thermal representation (3D already shows temperature).

---

## Critical Decisions

- **Decision 1:** Remove only the 2D `HeatMap` grid components, not the 3D `TorchWithHeatmap3D` visualizations — 3D torches stay.
- **Decision 2:** Delete compare-specific heatmap data extraction (`heatmapDataA`, `heatmapDataB`, `deltaHeatmapData`, `compareColorFn`) from the compare page only — `HeatMap`, `extractHeatmapData`, `extractDeltaHeatmapData` stay in the codebase for demo, replay, and seagull pages.
- **Decision 3:** Update compare landing page copy from "heatmaps" to "3D torch views" or similar to avoid misleading users.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| (none) | — | — | — | ✅ |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping, output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx in full. Capture and output:
(1) Every import (lines 1–19), in order
(2) Every useMemo/state that references heatmapDataA, heatmapDataB, deltaHeatmapData, compareColorFn
(3) Exact line range of the grid containing the three HeatMap components
(4) Run: cd my-app && npm test -- --testPathPattern="compare" --passWithNoTests 2>&1 | tail -20
(5) Run: wc -l my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx my-app/src/app/compare/page.tsx

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____
Line count compare/[sessionIdA]/[sessionIdB]/page.tsx: ____
Line count compare/page.tsx: ____
```

**Automated checks (all must pass before Step 1):**
- [ ] Compare page tests pass. Document output.
- [ ] `HeatMap` import exists at line 6
- [ ] `extractHeatmapData`, `extractDeltaHeatmapData` imports exist
- [ ] Grid with three `HeatMap` components exists (lines ~535–565)
- [ ] No in-progress migrations or uncommitted schema changes

---

## Environment Matrix

| Step | Dev | Staging | Prod | Notes |
|------|-----|---------|------|-------|
| Step 1 | ✅ | ✅ | ✅ | Compare page only, no env-specific code |
| Step 2 | ✅ | ✅ | ✅ | Compare landing page copy only |

---

## Tasks

### Phase 1 — Remove Heatmaps from Compare View

**Goal:** Compare view shows only 3D torches, timeline, and alert feed. No 2D heatmap grid.

---

- [x] 🟩 **Step 1: Remove 2D heatmaps and related code from compare view** — *Non-critical: UI simplification only*

  **Idempotent:** Yes — removing already-removed code is a no-op.

  **Context:** The compare page currently renders three `HeatMap` components (Session A, Delta, Session B) plus explanatory text. These are redundant with the 3D TorchWithHeatmap3D visualizations. Removing them simplifies the page.

  **Pre-Read Gate:**
  Before any edit:
  - Run `grep -n 'HeatMap\|heatmapDataA\|heatmapDataB\|deltaHeatmapData\|compareColorFn' my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`. Capture all matches.
  - Confirm `HeatMap` is imported from `@/components/welding/HeatMap`.
  - Confirm the three HeatMap components are inside a `grid grid-cols-1 md:grid-cols-3` div.

  **Self-Contained Rule:** All edits below are complete. No references to other steps.

  **Edits (apply in order):**

  1. **Remove imports** (lines 6, 11, 12):
     - Remove: `import HeatMap from '@/components/welding/HeatMap';`
     - Remove: `extractHeatmapData, tempToColorRange` from `@/utils/heatmapData` import (delete entire import if it becomes empty; if heatmapData has other exports used, keep the import and remove only those two).
     - Remove: `import { extractDeltaHeatmapData, deltaTempToColor } from '@/utils/deltaHeatmapData';`
     - Check: `heatmapData.ts` exports only `extractHeatmapData`, `tempToColorRange`, `tempToColor` — if page uses none after removal, delete the heatmapData import line entirely. Same for deltaHeatmapData.

  2. **Remove heatmap data and color logic** (delete these blocks entirely):
     - `heatmapDataA` useMemo/assignment (lines ~99–104)
     - `heatmapDataB` useMemo/assignment (lines ~103–107)
     - `deltaHeatmapData` useMemo/assignment (lines ~106–109)
     - `compareColorFn` useMemo (lines ~111–129)

  3. **Remove the explanatory paragraph:**
     - Delete the block: `{heatmapDataA?.point_count && heatmapDataB?.point_count && ( <p className="text-xs ...">Session A and B use a shared temperature scale...</p> )}`

  4. **Remove the HeatMap grid section:**
     - Delete the entire `<div className="grid grid-cols-1 md:grid-cols-3 gap-6">` block containing the three `<HeatMap>` components and their wrapping `<ErrorBoundary>` elements (lines ~534–566).

  **What it does:** Removes 2D heatmap visualization and all code that supports it from the compare page. The 3D TorchWithHeatmap3D, timeline, alerts, and summary remain.

  **Assumptions:**
  - `sharedMinTemp`, `sharedMaxTemp` are still used by TorchWithHeatmap3D — do NOT remove them.
  - `useSessionComparison` and `comparison` are still used for timeline bounds, frame counts, and summary — do NOT remove.
  - `frameDataA`, `frameDataB` are still used by TorchWithHeatmap3D — do NOT remove.

  **Risks:**
  - Accidentally removing `frameDataA`/`frameDataB` → mitigation: only remove heatmap-specific vars and HeatMap JSX.
  - Breaking import if heatmapData has other exports → mitigation: verify imports; if `heatmapData` import becomes empty, remove the entire line.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx
  git commit -m "remove 2D heatmaps from compare page"
  ```

  **Subtasks:**
  - [ ] 🟥 Remove HeatMap, extractHeatmapData, extractDeltaHeatmapData, tempToColorRange, deltaTempToColor imports
  - [ ] 🟥 Remove heatmapDataA, heatmapDataB, deltaHeatmapData, compareColorFn
  - [ ] 🟥 Remove explanatory paragraph
  - [ ] 🟥 Remove HeatMap grid section (three HeatMap components)

  **✓ Verification Test:**

  **Type:** Unit (Jest)

  **Action:** `cd my-app && npm test -- --testPathPattern="compare" --passWithNoTests`

  **Expected:** All compare page tests pass.

  **Observe:** Jest output; no "HeatMap" or "heatmapDataA" in compare page file (`grep` to confirm).

  **Pass:** Tests pass; `grep -c HeatMap my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` returns 0.

  **Fail:**
  - If tests fail → check for leftover references to removed variables or broken imports
  - If HeatMap still in file → Step 1 incomplete

---

- [x] 🟩 **Step 2: Update compare landing page copy** — *Non-critical*

  **Idempotent:** Yes.

  **Context:** The compare landing page (`/compare`) says "Enter two session IDs to view side-by-side heatmaps and the temperature delta (A − B)." After removing heatmaps, this is inaccurate. Update to describe 3D torch comparison instead.

  **Pre-Read Gate:**
  - Run `grep -n "heatmap" my-app/src/app/compare/page.tsx`. Must return the line with the description text.

  **Edit:**

  In `my-app/src/app/compare/page.tsx`, replace:
  ```
  Enter two session IDs to view side-by-side heatmaps and the temperature delta (A − B).
  ```
  with:
  ```
  Enter two session IDs to compare 3D torch visualizations and session alerts.
  ```

  **What it does:** Updates landing page copy to match the new compare experience (no heatmaps, 3D torches + alerts).

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/compare/page.tsx
  git commit -m "update compare landing copy: 3D torches instead of heatmaps"
  ```

  **Subtasks:**
  - [ ] 🟥 Replace heatmap description with 3D torch description

  **✓ Verification Test:**

  **Type:** Unit (grep)

  **Action:** `grep -n "heatmap" my-app/src/app/compare/page.tsx`

  **Expected:** No matches (or only in comments if any).

  **Pass:** Zero matches for "heatmap" in compare landing page.

  **Fail:** If "heatmap" still in user-facing text → Step 2 incomplete.

---

- [x] 🟩 **Step 3: Remove HeatMap mock from compare page test** — *Non-critical*

  **Idempotent:** Yes.

  **Context:** The compare page test mocks `HeatMap` because the page used to render it. After removal, the mock is unused and can be deleted to reduce noise.

  **Pre-Read Gate:**
  - Run `grep -n "HeatMap" my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx`. Confirm the mock block exists.

  **Edit:**

  In `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx`, remove the entire block:
  ```javascript
  jest.mock('@/components/welding/HeatMap', () => ({
    __esModule: true,
    default: () => <div data-testid="heatmap" />,
  }));
  ```

  **What it does:** Removes obsolete mock. Tests do not assert on HeatMap, so no test logic changes.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx
  git commit -m "remove HeatMap mock from compare page test"
  ```

  **Subtasks:**
  - [ ] 🟥 Remove jest.mock for HeatMap

  **✓ Verification Test:**

  **Type:** Unit (Jest)

  **Action:** `cd my-app && npm test -- --testPathPattern="compare" --passWithNoTests`

  **Expected:** All compare tests pass.

  **Pass:** Tests pass.

  **Fail:** If tests fail → possible dynamic import or module resolution issue; check for other HeatMap references in test file.

---

### Phase 2 — Regression Guard

**Goal:** Confirm no regression in compare flow and related pages.

---

**Regression verification:**

| System | Pre-change behavior | Post-change verification |
|--------|---------------------|---------------------------|
| Compare view | Renders Session A, Delta, Session B heatmaps + 3D torches | Renders only 3D torches, timeline, alerts; no HeatMap |
| Compare landing | Copy mentions "heatmaps" | Copy mentions "3D torch visualizations" |
| Replay page | Uses HeatMap | Unchanged — `grep HeatMap my-app/src/app/replay` still finds usage |
| Demo page | Uses HeatMap | Unchanged — `grep HeatMap my-app/src/app/demo` still finds usage |

**Test count regression check:**
- Tests before plan: from Pre-Flight baseline
- Tests after plan: `cd my-app && npm test 2>&1 | tail -5` — must pass, count must not decrease
- If count decreased → a test was deleted — STOP and report

---

## Rollback Procedure

```bash
# Reverse order: Step 3, Step 2, Step 1
git revert HEAD~2..HEAD   # if Steps 1–3 are the last 3 commits
# or individually:
git revert <step3-commit-hash>
git revert <step2-commit-hash>
git revert <step1-commit-hash>

# Confirm:
cd my-app && npm test -- --testPathPattern="compare" --passWithNoTests
grep -c HeatMap my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx  # should be > 0 again
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| **Pre-flight** | Baseline snapshot captured | Test output + line counts | ⬜ |
| **Phase 1** | Compare page tests pass | `npm test -- --testPathPattern="compare"` | ⬜ |
| | HeatMap imported in compare page | grep returns 1 | ⬜ |
| | Three HeatMap components in grid | grep HeatMap returns 3 | ⬜ |
| **Phase 2** | All Phase 1 steps complete | Verifications passed | ⬜ |

---

## Risk Heatmap

| Step | Risk Level | What Could Go Wrong | Early Detection | Idempotent |
|------|------------|---------------------|------------------|------------|
| Step 1 | 🟢 **Low** | Accidentally remove frameData or comparison | Tests fail; 3D block missing | Yes |
| Step 2 | 🟢 **Low** | Typo in copy | Manual read of page | Yes |
| Step 3 | 🟢 **Low** | Test fails without mock | Jest output | Yes |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Compare view | No 2D heatmaps | **Do:** Open /compare/sess_expert_001/sess_novice_001 → **Expect:** Only 3D torches, timeline, alerts → **Look:** No grid with "Session A", "Delta", "Session B" heatmap columns |
| Compare landing | Updated copy | **Do:** Open /compare → **Expect:** "3D torch visualizations" not "heatmaps" |
| Replay / Demo / Seagull | Unchanged | **Do:** grep HeatMap in those pages → **Expect:** Still used |
| Test count | ≥ pre-plan | **Do:** npm test → **Expect:** Same or more passing |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not batch multiple steps into one git commit.**
