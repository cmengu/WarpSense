# Compare Page HUD + Torch Y — Execution Plan

**Overall Progress:** `100%`

## TLDR

Fix two Compare page issues: (1) Move Session A's HUD (label, torch angle, weld pool temp) outside the 3D canvas so it no longer blocks the view; Session B keeps the overlay inside. (2) Reduce the gap between the welding gun tip and metal so the tip visually touches the workpiece. After execution: Compare page shows an unobstructed 3D view for Session A and a physically plausible torch–metal contact in both columns.

---

## Critical Decisions

- **labelPosition prop:** Use `labelPosition?: 'inside' | 'outside'` (default `'inside'`) in TorchWithHeatmap3D. `'outside'` renders HUD above the canvas, as a sibling of the canvas wrapper — not inside the `overflow-hidden` root.
- **Layout fix:** The root div has `overflow-hidden`. The "outside" HUD must be a sibling of the canvas wrapper div, not a child of it. Wrap both in an outer container with no `overflow-hidden`.
- **Y-position fix:** Change only `METAL_TO_TORCH_GAP` from `0.15` to `0.02`. Do not touch `TORCH_GROUP_Y`.
- **Test order:** Update welding3d test assertion first (Step 3), then change constant (Step 4). Every commit leaves tests green.
- **MAX_THERMAL_DISPLACEMENT:** Assumed 0.5 (from welding3d.ts). Pre-flight must confirm. If different, flag before Step 4—arithmetic and Step 5 expectation depend on it.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| None | — | — | — | ✅ |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping, output the full current contents of every file modified in this step. Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) current state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

Read the following files in full. Capture and output:

1. **TorchWithHeatmap3D.tsx** — Every prop in `TorchWithHeatmap3DProps` (lines 53–74). Exact line where `{label && (` appears (HUD block). Confirm root div has `overflow-hidden`.
2. **welding3d.ts** — Exact line containing `METAL_TO_TORCH_GAP = 0.15`. Exact line containing `WORKPIECE_BASE_Y =`. Run `grep -n "MAX_THERMAL_DISPLACEMENT" my-app/src/constants/welding3d.ts` and record the value.
3. **Arithmetic verification:** `WORKPIECE_BASE_Y = WELD_POOL_CENTER_Y - MAX_THERMAL_DISPLACEMENT - METAL_TO_TORCH_GAP`. With METAL_TO_TORCH_GAP = 0.02: `= -0.2 - [recorded value] - 0.02 = [computed]`. Confirm WORKPIECE_GROUP_Y === WORKPIECE_BASE_Y in TorchWithHeatmap3D.tsx.
4. **compare page** — Exact lines of the two `<TorchWithHeatmap3D` usages (Session A and Session B).
5. **welding3d.test.ts** — Exact line with `expect(gap).toBeGreaterThanOrEqual(0.1)`.
6. **TorchWithHeatmap3D.test.tsx** — Exact line with `expect(WORKPIECE_GROUP_Y).toBe(-0.85)`.
7. Run `cd /Users/ngchenmeng/test/my-app && npm test -- --passWithNoTests --verbose 2>&1 | tail -40` — record passing test count. Store exact number.
8. Run `cd /Users/ngchenmeng/test/my-app && npx tsc --noEmit 2>&1` — must exit 0.
9. Run `wc -l my-app/src/components/welding/TorchWithHeatmap3D.tsx my-app/src/constants/welding3d.ts "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` — record line counts.

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____ (exact number; final count must equal this)
MAX_THERMAL_DISPLACEMENT: ____
Line count TorchWithHeatmap3D.tsx:    ____
Line count welding3d.ts:              ____
Line count compare page:              ____
```

**Automated checks (all must pass before Step 1):**
- [ ] Existing test suite passes. Document test count: `____`
- [ ] `npx tsc --noEmit` exits 0.
- [ ] `grep -c "labelPosition" my-app/src/components/welding/TorchWithHeatmap3D.tsx` returns 0 (step not yet applied).
- [ ] `METAL_TO_TORCH_GAP = 0.15` appears exactly once in welding3d.ts.
- [ ] `grep -c "labelPosition" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` returns 0 (Step 2 not yet applied).

---

## Environment Matrix

| Step | Dev | Staging | Prod | Notes |
|------|-----|---------|------|-------|
| All | ✅ | ✅ | ✅ | Frontend-only changes |

---

## Tasks

### Phase 1 — HUD labelPosition

**Goal:** TorchWithHeatmap3D supports `labelPosition: 'inside' | 'outside'`; outside HUD renders above canvas (not clipped by overflow-hidden); Compare page passes `labelPosition="outside"` for Session A.

---

- [ ] 🟥 **Step 1: Add labelPosition to TorchWithHeatmap3D** — *Critical: shared component used by compare, replay, demo*

  **Idempotent:** No — re-running would duplicate the prop, logic, or test. **Skip if:** `grep -c "labelPosition" my-app/src/components/welding/TorchWithHeatmap3D.tsx` returns >0, **or** `grep -c "renders HUD above canvas when labelPosition=outside" my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx` returns >0.

  **Context:** The HUD is currently always an `absolute` overlay inside a root div with `overflow-hidden`. For `labelPosition="outside"`, the HUD must render above the canvas. Placing it as a child of `overflow-hidden` would clip it. The HUD and canvas wrapper must be siblings inside an outer wrapper; only the inner div (canvas + overlay) keeps `overflow-hidden`.

  **Pre-Read Gate:**
  - `grep -n "labelPosition" my-app/src/components/welding/TorchWithHeatmap3D.tsx` → must return 0 matches.
  - `grep -n "overflow-hidden" my-app/src/components/welding/TorchWithHeatmap3D.tsx` → confirm root div has it.
  - `grep -n "label &&" my-app/src/components/welding/TorchWithHeatmap3D.tsx` → exactly 1 match.
  - `grep -n "absolute top-4 left-4" my-app/src/components/welding/TorchWithHeatmap3D.tsx` → exactly 1 match.

  **Edits:**

  A. In `TorchWithHeatmap3DProps` interface (after `label?: string;`), add:
  ```ts
  /** Where to render the HUD: 'inside' = overlay on canvas, 'outside' = above canvas in flow. Default 'inside'. */
  labelPosition?: 'inside' | 'outside';
  ```

  B. In the function destructuring (after `label = DEFAULT_LABEL`), add:
  ```ts
  labelPosition = 'inside',
  ```

  C. Restructure the return. The "outside" HUD must not be a child of `overflow-hidden`. Wrap in an outer div; put `overflow-hidden` only on the inner canvas container.

  Current structure (simplified):
  ```tsx
  return (
    <div className="relative w-full h-64 min-h-64 rounded-xl overflow-hidden border-2 ...">
      {label && (<div className="absolute ...">HUD</div>)}
      <div className="relative h-64 w-full isolate">{Canvas}</div>
      <div className="absolute bottom-4 right-4">temp scale</div>
    </div>
  );
  ```

  New structure:
  ```tsx
  const hudContent = label ? (
    <div className="backdrop-blur-md bg-black/50 border border-blue-400/40 rounded-lg px-4 py-3 shadow-[0_0_20px_rgba(59,130,246,0.2)]">
      <div className="flex items-center gap-2 mb-1">
        <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" aria-hidden />
        <p className={`text-sm font-bold tracking-widest uppercase text-blue-400 ${orbitron.className}`}>{label}</p>
      </div>
      <div className="space-y-0.5">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] uppercase tracking-wider text-blue-400/80 ${orbitron.className}`}>Torch angle</span>
          <span className={`text-xs text-blue-300 ${jetbrainsMono.className}`}>{angle.toFixed(1)}°</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] uppercase tracking-wider text-blue-400/80 ${orbitron.className}`}>Weld pool temp</span>
          <span className={`text-xs text-blue-300 ${jetbrainsMono.className}`}>{temp.toFixed(0)}°C</span>
        </div>
      </div>
    </div>
  ) : null;

  return (
    <div className="w-full">
      {labelPosition === 'outside' && hudContent && <div data-testid="hud-outside" className="mb-2">{hudContent}</div>}
      <div className="relative w-full h-64 min-h-64 rounded-xl overflow-hidden border-2 border-blue-400/80 bg-neutral-950 shadow-[0_0_30px_rgba(59,130,246,0.15)]">
        {labelPosition === 'inside' && hudContent && <div data-testid="hud-inside" className="absolute top-4 left-4 z-10">{hudContent}</div>}
        <div className="relative h-64 w-full isolate">
          {/* existing Canvas + context-lost overlay — unchanged */}
        </div>
        <div className="absolute bottom-4 right-4 z-10">{/* temp scale — unchanged */}</div>
      </div>
    </div>
  );
  ```

  **Anchor Uniqueness Check:** The block `{label && (` appears exactly once. Replace it and the surrounding structure with the above. Preserve all Canvas, context-lost overlay, and temp scale markup exactly.

  **What it does:** Adds `labelPosition` prop. When `'outside'`, HUD renders as first child of outer wrapper (no overflow-hidden). When `'inside'`, HUD overlays the canvas inside the inner div. Same HUD content in both cases.

  **Assumptions:** `labelPosition` default `'inside'` preserves existing behavior for replay/demo.

  **Risks:** Layout shift when `outside` → mitigation: `mb-2` gives consistent spacing.

  **Git Checkpoint:**
  ```bash
  cd /Users/ngchenmeng/test && git add my-app/src/components/welding/TorchWithHeatmap3D.tsx && git commit -m "step 1: add labelPosition prop to TorchWithHeatmap3D"
  ```

  **Subtasks:**
  - [ ] 🟥 Add `labelPosition` to interface and destructuring
  - [ ] 🟥 Restructure return with outer wrapper; HUD outside vs inside conditional
  - [ ] 🟥 Add new test for labelPosition='outside'

  **✓ Verification Test (Step 1):**

  D. Add this test to `TorchWithHeatmap3D.test.tsx` (inside the describe block):

  ```tsx
  it('renders HUD above canvas when labelPosition=outside', () => {
    render(
      <TorchWithHeatmap3D
        angle={45}
        temp={400}
        label="Session A"
        labelPosition="outside"
        frames={[]}
      />
    );
    expect(screen.getByTestId('hud-outside')).toBeInTheDocument();
    expect(screen.queryByTestId('hud-inside')).not.toBeInTheDocument();
  });
  ```

  **Type:** Unit

  **Action:** `cd /Users/ngchenmeng/test/my-app && npm test -- TorchWithHeatmap3D --passWithNoTests 2>&1`

  **Expected:** All TorchWithHeatmap3D tests pass, including the new test.

  **Pass:** `hud-outside` exists and `hud-inside` is absent when labelPosition='outside'.

  **Fail:** If `hud-outside` absent or `hud-inside` present → structure or data-testid placement is wrong.

  **Post-Step 1 Commands (all must succeed):**
  ```bash
  cd /Users/ngchenmeng/test/my-app && npx tsc --noEmit 2>&1
  cd /Users/ngchenmeng/test/my-app && npm run build 2>&1
  ```

---

- [ ] 🟥 **Step 2: Pass labelPosition=outside for Session A on Compare page** — *Non-critical*

  **Idempotent:** Yes. If `labelPosition` already on Session A, skip.

  **Pre-Read Gate:**
  - `grep -n "TorchWithHeatmap3D" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` → 2 matches.
  - `grep -n "labelPosition" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx"` → 0 matches before Step 2.
  - `grep -n 'data-testid="torch-3d"' "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx"` → exactly 1 match (confirm mock structure).
  - Second TorchWithHeatmap3D (Session B) must not have `labelPosition` — verify it is absent.

  **Edit:** In the first `<TorchWithHeatmap3D` block (Session A), add `labelPosition="outside"` after `label={...}`.

  **Edit (compare page test):** Update the mock to capture and expose `labelPosition`, and add assertion. **Uniqueness check:** The mock `default: ({ label }` pattern must appear exactly once. If the mock uses a spread `({ ...props })` or different signature, locate the exact line and adapt the replacement accordingly.

  In `page.test.tsx`, change the mock from:
  ```tsx
  default: ({ label }: { label?: string }) => (
    <div data-testid="torch-3d" data-label={label ?? ''} />
  ),
  ```
  to:
  ```tsx
  default: ({ label, labelPosition }: { label?: string; labelPosition?: string }) => (
    <div data-testid="torch-3d" data-label={label ?? ''} data-label-position={labelPosition ?? ''} />
  ),
  ```

  Add this test:
  ```tsx
  it('session A torch receives labelPosition=outside', async () => {
    fetchSession
      .mockResolvedValueOnce(SESSION_A)
      .mockResolvedValueOnce(SESSION_B);
    renderComparePage('sess_expert_001', 'sess_novice_001');
    await waitForLoad();
    await waitFor(() => {
      const torches = screen.getAllByTestId('torch-3d');
      expect(torches).toHaveLength(2);
      expect(torches[0].getAttribute('data-label-position')).toBe('outside');
      expect(torches[1].getAttribute('data-label-position')).toBe('');
    });
  });
  ```

  **What it does:** Session A passes `labelPosition="outside"`; test asserts the prop is forwarded.

  **Git Checkpoint:**
  ```bash
  cd /Users/ngchenmeng/test && git add "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx" "my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx" && git commit -m "step 2: pass labelPosition=outside for Session A on compare page"
  ```

  **Subtasks:**
  - [ ] 🟥 Add `labelPosition="outside"` to Session A TorchWithHeatmap3D
  - [ ] 🟥 Update compare page mock and add labelPosition assertion test

  **✓ Verification Test:**

  **Type:** Integration

  **Action:** `cd /Users/ngchenmeng/test/my-app && npm test -- "compare" --passWithNoTests 2>&1`

  **Expected:** All compare page tests pass, including the new `labelPosition=outside` test.

  **Pass:** `torches[0].getAttribute('data-label-position') === 'outside'`.

  **Fail:** If `data-label-position` is not 'outside' → prop not passed on Session A.

  **Post-Step 2:** `cd /Users/ngchenmeng/test/my-app && npx tsc --noEmit 2>&1`

---

### Phase 2 — Torch Y (METAL_TO_TORCH_GAP)

**Goal:** Welding gun tip visually touches the metal. Change `METAL_TO_TORCH_GAP` from 0.15 to 0.02. Update tests first so every commit is green.

---

- [ ] 🟥 **Step 3: Update welding3d.test.ts assertion** — *Non-critical*

  **Idempotent:** Yes. If assertion already updated, skip.

  **Context:** Replace the "gap at least 0.1" test with an assertion tied to the constant: `expect(gap).toBeCloseTo(METAL_TO_TORCH_GAP)`. This keeps the test meaningful. With current constant 0.15, test passes. After Step 4 changes the constant to 0.02, same assertion validates the new value.

  **Pre-Read Gate:**
  - `grep -n "toBeGreaterThanOrEqual(0.1)" my-app/src/__tests__/constants/welding3d.test.ts` → exactly 1 match.

  **Edit:** Replace the entire "gap between metal max and weld pool" test body. Change:
  ```ts
  it('gap between metal max and weld pool is at least 0.1 (safety margin)', () => {
    const metal_surface_max_Y = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT;
    const gap = WELD_POOL_CENTER_Y - metal_surface_max_Y;
    expect(gap).toBeGreaterThanOrEqual(0.1);
  });
  ```
  with:
  ```ts
  it('gap between metal max and weld pool equals METAL_TO_TORCH_GAP', () => {
    const metal_surface_max_Y = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT;
    const gap = WELD_POOL_CENTER_Y - metal_surface_max_Y;
    // toBeCloseTo default: 2 decimal places (within ~0.005); 0.02 is exact
    expect(gap).toBeCloseTo(METAL_TO_TORCH_GAP);
  });
  ```

  **Git Checkpoint:**
  ```bash
  cd /Users/ngchenmeng/test && git add my-app/src/__tests__/constants/welding3d.test.ts && git commit -m "step 3: tie welding3d gap assertion to METAL_TO_TORCH_GAP"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:** `cd /Users/ngchenmeng/test/my-app && npm test -- welding3d 2>&1`

  **Expected:** All welding3d tests pass (constant still 0.15; gap = 0.15).

  **Pass:** All welding3d tests pass (count ≥ baseline for this file).

  **Post-Step 3:** `cd /Users/ngchenmeng/test/my-app && npx tsc --noEmit 2>&1`

---

- [ ] 🟥 **Step 4: Change METAL_TO_TORCH_GAP in welding3d.ts** — *Critical*

  **Idempotent:** Yes.

  **Context:** Reduce gap so torch tip reads as touching metal. `WORKPIECE_BASE_Y` derives automatically. With MAX_THERMAL_DISPLACEMENT = 0.5: WORKPIECE_BASE_Y = -0.2 - 0.5 - 0.02 = -0.72.

  **Pre-Read Gate:**
  - `grep -n "METAL_TO_TORCH_GAP = 0.15" my-app/src/constants/welding3d.ts` → exactly 1 match.

  **Edit:** Replace `0.15` with `0.02`:
  ```ts
  export const METAL_TO_TORCH_GAP = 0.02;
  ```

  **Git Checkpoint:**
  ```bash
  cd /Users/ngchenmeng/test && git add my-app/src/constants/welding3d.ts && git commit -m "step 4: set METAL_TO_TORCH_GAP to 0.02 for torch-metal contact"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:** `cd /Users/ngchenmeng/test/my-app && npm test -- welding3d 2>&1`

  **Expected:** All welding3d tests pass. Step 3's `toBeCloseTo(METAL_TO_TORCH_GAP)` now validates 0.02.

  **Pass:** All tests pass.

  **Post-Step 4 Commands (all must succeed):**
  ```bash
  cd /Users/ngchenmeng/test/my-app && npx tsc --noEmit 2>&1
  cd /Users/ngchenmeng/test/my-app && npm run build 2>&1
  ```

---

- [ ] 🟥 **Step 5: Update TorchWithHeatmap3D.test.tsx WORKPIECE_GROUP_Y expectation** — *Non-critical*

  **Idempotent:** Yes. **If `grep -c "toBeCloseTo(expected)" my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx` returns >0, step already applied — skip.**

  **Context:** WORKPIECE_GROUP_Y === WORKPIECE_BASE_Y. WORKPIECE_BASE_Y is derived from `WELD_POOL_CENTER_Y - MAX_THERMAL_DISPLACEMENT - METAL_TO_TORCH_GAP`. Use a computed expected value and `toBeCloseTo` to avoid magic numbers and floating-point mismatch (e.g. -0.7199999999999999 vs -0.72).

  **Pre-Read Gate:**
  - `grep -n "toBe(-0.85)" my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx` → exactly 1 match before edit (or 0 if already updated).
  - `grep -n "WORKPIECE_BASE_Y" my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx` → confirm import from welding3d.

  **Edit:** Add constants to the welding3d import; replace hardcoded assertion with computed expectation.

  A. Update import: change `import { WORKPIECE_BASE_Y } from '@/constants/welding3d';` to:
  ```ts
  import { WORKPIECE_BASE_Y, WELD_POOL_CENTER_Y, MAX_THERMAL_DISPLACEMENT, METAL_TO_TORCH_GAP } from '@/constants/welding3d';
  ```

  B. Replace the entire test body. Current:
  ```ts
  it('workpiece group uses WORKPIECE_BASE_Y from welding3d', () => {
    expect(WORKPIECE_GROUP_Y).toBe(WORKPIECE_BASE_Y);
    expect(WORKPIECE_GROUP_Y).toBe(-0.85);
  });
  ```
  New:
  ```ts
  it('workpiece group uses WORKPIECE_BASE_Y from welding3d', () => {
    const expected = WELD_POOL_CENTER_Y - MAX_THERMAL_DISPLACEMENT - METAL_TO_TORCH_GAP;
    expect(WORKPIECE_GROUP_Y).toBe(WORKPIECE_BASE_Y);
    expect(WORKPIECE_GROUP_Y).toBeCloseTo(expected);
  });
  ```
  This makes the test self-consistent and immune to arithmetic errors or floating-point differences.

  **Git Checkpoint:**
  ```bash
  cd /Users/ngchenmeng/test && git add my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx && git commit -m "step 5: update WORKPIECE_GROUP_Y expectation to -0.72"
  ```

  **✓ Verification Test:**

  **Type:** Unit

  **Action:** `cd /Users/ngchenmeng/test/my-app && npm test -- TorchWithHeatmap3D 2>&1`

  **Expected:** All TorchWithHeatmap3D tests pass.

  **Pass:** Tests pass.

  **Post-Step 5:** `cd /Users/ngchenmeng/test/my-app && npx tsc --noEmit 2>&1`

---

## Regression Guard

**Systems at risk:** Replay page, demo page (TorchWithHeatmap3D with default labelPosition), welding3d derivation.

**Regression verification commands (run after all steps):**

```bash
cd /Users/ngchenmeng/test/my-app
npx tsc --noEmit 2>&1
npm run build 2>&1
npm test -- --passWithNoTests --verbose 2>&1 | tail -50
```

**Test count gate:** The number of passed tests must equal the Pre-Flight baseline exactly. If a test was deleted or skipped, this fails.

**Explicit regression tests:**
```bash
npm test -- replay --passWithNoTests 2>&1
npm test -- demo --passWithNoTests 2>&1
```

**Note:** Replay and demo page tests exist. They mock TorchWithHeatmap3D; default `labelPosition='inside'` is implied. These tests confirm the pages still render; they do not assert labelPosition. If these tests are absent in future, document that gap.

---

## Rollback Procedure

```bash
cd /Users/ngchenmeng/test
# Use range revert — avoids HEAD~N shifting after each revert
git revert HEAD~5..HEAD --no-commit
git commit -m "Rollback: compare page HUD and torch Y fixes"

# Confirm:
cd my-app && npm test -- --passWithNoTests --verbose 2>&1
# Test count must equal Pre-Flight baseline
```

If reverting individual steps, use explicit hashes from `git log --oneline -6` (captured during execution) and revert in reverse order.

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| Pre-flight | Clarification Gate complete | All unknowns resolved | ⬜ |
| | Baseline snapshot | Test count + line counts + MAX_THERMAL_DISPLACEMENT recorded | ⬜ |
| | tsc --noEmit passes | Exit 0 | ⬜ |
| Phase 1 | labelPosition does not exist | grep returns 0 | ⬜ |
| | METAL_TO_TORCH_GAP = 0.15 | grep confirms | ⬜ |
| | labelPosition not in compare page | grep returns 0 | ⬜ |
| Phase 2 | Phase 1 complete | Steps 1–2 verified | ⬜ |
| | METAL_TO_TORCH_GAP = 0.02 | Step 4 applied | ⬜ |

---

## Risk Heatmap

| Step | Risk Level | What Could Go Wrong | Early Detection | Idempotent |
|------|-----------|---------------------|-----------------|------------|
| Step 1 | 🟡 Medium | overflow-hidden clips outside HUD | New test asserts HUD not absolute | No |
| Step 2 | 🟢 Low | Wrong column gets outside | labelPosition assertion on torches[0] | Yes |
| Step 3 | 🟢 Low | Assertion change breaks test | welding3d tests pass before Step 4 | Yes |
| Step 4 | 🟡 Medium | Z-fighting if gap too small | Visual check; tests pass | Yes |
| Step 5 | 🟢 Low | Wrong expectation | Test fails immediately | Yes |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| Session A HUD outside | Label + stats above 3D canvas, not clipped | TorchWithHeatmap3D test: hud-outside exists, hud-inside absent when labelPosition='outside'. Compare test: torches[0] has data-label-position='outside'. |
| Session B HUD inside | Overlay on canvas | Compare test: torches[1] has data-label-position='' (default). |
| Torch touches metal | Tip ~0.02 units above metal max | welding3d tests assert gap === METAL_TO_TORCH_GAP. Visual check on compare page. |
| Replay unchanged | HUD overlay | `npm test -- replay` passes. Mock implies default behavior. |
| Demo unchanged | HUD overlay | `npm test -- demo` passes. |
| TypeScript | No type errors | `npx tsc --noEmit` exits 0. |
| Build | Succeeds | `npm run build` exits 0. |
| Test count | Exactly equals Pre-Flight baseline | `npm test -- --passWithNoTests --verbose` output. |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**  
⚠️ **Do not proceed past a Human Gate without explicit human input.**  
⚠️ **If blocked, mark 🟨 In Progress and output the State Manifest before stopping.**  
⚠️ **Do not batch multiple steps into one git commit.**
