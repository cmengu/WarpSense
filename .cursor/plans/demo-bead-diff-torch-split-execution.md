# Demo Bead Diff — Torch Split + CSS Execution Plan

**Overall Progress:** `100%`

## TLDR

Replace the static BeadDiffPlaceholder canvas with two side-by-side TorchWithHeatmap3D instances (Session A vs B) inside the demo circle. Add five props to TorchWithHeatmap3D (background, containerClassName, enableOrbitControls, showLegend) so the component fits the circle layout without blue borders, fixed 256px height, accidental camera drift, or off-brand legend. Pass `label=""` so no blue HUD card renders; add session overlay labels in DemoPageInner. Fix height chain by adding h-full to root div when containerClassName is passed. Use conditional rendering when `currentTimestamp == null`, bump circle max-width to 460px, and apply CSS fixes for grid/alert/values.

---

## Critical Decisions

- **TorchWithHeatmap3D changes (5 props):** Add `background?: string`, `containerClassName?: string`, `enableOrbitControls?: boolean`, `showLegend?: boolean`. Defaults preserve replay-page behavior.
- **Height chain:** When containerClassName is passed, the root div must also get `h-full` — otherwise h-full on children resolves to auto (parent has no height) and Canvas renders at 150px default. Root → container → inner all need h-full for the chain to work.
- **containerClassName:** When provided, replaces default `h-64 min-h-64 rounded-xl border-2 border-blue-400/80` so caller can pass `h-full border-0 rounded-[0px]` for demo context. Use `rounded-[0px]` (arbitrary value) not `rounded-none` — arbitrary values are always emitted by Tailwind JIT.
- **showLegend:** Default `true`; when `false`, the temperature legend (0–500°C blue-bordered pill) is hidden.
- **HUD label (Option A):** Pass `label=""` to TorchWithHeatmap3D — falsy label means hudContent is null, no blue HUD card renders. Add session identifiers as two small overlay divs in DemoPageInner (one per half), using design tokens C.novice/C.expert, FONT_DATA, fontSize: 9.
- **enableOrbitControls:** Default `true`; when `false`, OrbitControls not rendered — prevents camera drift when scrubbing.
- **Conditional guard:** Use `currentTimestamp == null` (not frame nulls) to avoid mounting R3F before timestamp is set.
- **Split layout:** Two TorchWithHeatmap3D instances in a flex row, each 50% width; circle's `overflow: hidden` + `borderRadius: 50%` clips both.
- **Data reuse:** All six values already computed in DemoPageInner — no new data work.
- **CSS:** Grid columns `200px 1fr 300px`; alert/counter/values typography increased.

---

## Decisions Log

| Issue | Resolution | Source | Affects |
|-------|------------|--------|---------|
| Background: CSS vs WebGL clear color | `gl={{ alpha: true }}` → CSS `style={{ background }}` on canvas controls visible background. Prop `background ?? '#0a0a0a'` is correct. | TorchWithHeatmap3D.tsx | Step 1 #4 |
| `rounded-none` not in source; Tailwind JIT may not emit in prod | Use `rounded-[0px]` everywhere. Arbitrary values always emitted. | grep — rounded-none absent | Step 1 docstring, Step 2 prop |
| Blue legend (bottom-4 right-4) not eliminated by containerClassName | Add `showLegend?: boolean`, wrap legend in `{showLegend !== false && (...)}`, pass `showLegend={false}` from demo. | Option A | Step 1 #8, Step 2 |
| Blue HUD card obscures ~50% of 230px half | Pass `label=""` — falsy → hudContent null. Add overlay divs in DemoPageInner (position absolute, FONT_DATA, fontSize: 9, C.novice/C.expert). | Option A | Step 2 |
| h-full chain breaks at root — child resolves to auto, Canvas 150px | Add `${containerClassName ? 'h-full' : ''}` to root div. Root, container, inner all need h-full when containerClassName passed. | TorchWithHeatmap3D.tsx | Step 1 #3 |
| OrbitControls in sub-components? | TorchSceneContent has none. OrbitControls only in TorchWithHeatmap3D, TorchViz3D, HeatmapPlate3D. Conditional in TorchWithHeatmap3D sufficient. | grep | Step 1 #7 |
| extractCenterTemperatureWithCarryForward return type | Always returns number. Fallback `?? 300` redundant but harmless. | frameUtils.ts | Step 2 — no change |
| Step title "7 CSS fixes" vs 10 rows | Step titled "Apply CSS fixes"; 10 replacements in table; commit omits count. | Previous logic check | Step 4 |
| Legend wrap placeholder | Instruction: opening before legend div, closing after its closing </div>. Exact placement specified. | Plan prohibits placeholders | Step 1 #8 |

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| None | — | — | — | ✅ |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Before stopping:
   - Output the full current contents of every file modified in this step.
   - Report: (a) command run, (b) full error verbatim, (c) fix attempted, (d) exact state of each modified file, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Read my-app/src/components/welding/TorchWithHeatmap3D.tsx in full. Capture and output:
(1) TorchWithHeatmap3DProps interface fields, in order
(2) Line numbers of: root div (w-full), Canvas style, outer container div (h-64), OrbitControls, temperature legend div (absolute bottom-4 right-4)
(3) Line where BeadDiffPlaceholder is rendered in page.tsx
(4) Run: cd my-app && npm run test -- --testPathPattern="demo" --passWithNoTests 2>&1 | tail -25
(5) Run: wc -l my-app/src/components/welding/TorchWithHeatmap3D.tsx my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____
Line count TorchWithHeatmap3D.tsx: ____
Line count demo page.tsx: ____
```

**Automated checks (all must pass before Step 1):**

- [ ] `TorchWithHeatmap3DProps` does not yet have `background`, `containerClassName`, `enableOrbitControls`, or `showLegend`
- [ ] Root div has `className="w-full"` with no height
- [ ] Canvas has `style={{ background: '#0a0a0a' }}`
- [ ] Outer container div has `h-64 min-h-64 rounded-xl overflow-hidden border-2 border-blue-400/80`
- [ ] OrbitControls rendered unconditionally
- [ ] Temperature legend div (absolute bottom-4 right-4) rendered unconditionally
- [ ] `BeadDiffPlaceholder` rendered inside circle container
- [ ] No existing TorchWithHeatmap3D import in demo page

---

## Environment Matrix

| Step | Dev | Staging | Prod |
|------|-----|---------|------|
| All | ✅ | ✅ | ✅ |

---

## Tasks

### Phase 1 — TorchWithHeatmap3D component changes (5 props)

**Goal:** Component supports demo embedding: configurable background, height chain when embedded, container styling override, no OrbitControls when embedded, no temperature legend when embedded.

---

- [x] 🟩 **Step 1: Add background, containerClassName, enableOrbitControls, showLegend props to TorchWithHeatmap3D** — *Critical*

  **Idempotent:** Yes — additive optional props; existing call sites unchanged.

  **Context:** Demo circle requires: (1) `#07090d` background, (2) height chain (root div must have h-full when containerClassName passed — otherwise children resolve to auto and Canvas renders 150px), (3) `h-full border-0 rounded-[0px]` on container, (4) OrbitControls disabled, (5) Temperature legend hidden.

  **Pre-Read Gate:**
  - `grep -n "export interface TorchWithHeatmap3DProps" my-app/src/components/welding/TorchWithHeatmap3D.tsx` — 1 match
  - `grep -n '<div className="w-full">' my-app/src/components/welding/TorchWithHeatmap3D.tsx` — 1 match
  - `grep -n "style={{ background:" my-app/src/components/welding/TorchWithHeatmap3D.tsx` — 1 match
  - `grep -n "relative w-full h-64 min-h-64" my-app/src/components/welding/TorchWithHeatmap3D.tsx` — 1 match
  - `grep -n "<OrbitControls" my-app/src/components/welding/TorchWithHeatmap3D.tsx` — 1 match
  - `grep -n "absolute bottom-4 right-4" my-app/src/components/welding/TorchWithHeatmap3D.tsx` — 1 match

  **Self-Contained Rule:** All code below is complete and runnable.

  **No-Placeholder Rule:** No placeholders.

  **Changes in `my-app/src/components/welding/TorchWithHeatmap3D.tsx` — apply in order (matches file structure top-to-bottom):**

  1. In `TorchWithHeatmap3DProps` interface, add:
  ```tsx
  /** Canvas background color. Default '#0a0a0a'. */
  background?: string;
  /** Override container div classes. When provided, replaces default h-64/border/rounded. Use e.g. "h-full border-0 rounded-[0px]" for embedded contexts. rounded-[0px] (not rounded-none) ensures Tailwind JIT emits the class in production. */
  containerClassName?: string;
  /** Whether OrbitControls are enabled. Default true. Set false when embedded (e.g. demo circle) to prevent accidental camera drift. */
  enableOrbitControls?: boolean;
  /** Whether the temperature scale legend (0–500°C pill) is shown. Default true. Set false when embedded to avoid off-brand blue styling. */
  showLegend?: boolean;
  ```

  2. In function destructuring, add: `background`, `containerClassName`, `enableOrbitControls = true`, `showLegend = true`

  3. Replace the root div. Current:
  ```tsx
  <div className="w-full">
  ```
  New (h-full closes the height chain when containerClassName is passed; without it, child h-full resolves to auto):
  ```tsx
  <div className={`w-full ${containerClassName ? 'h-full' : ''}`}>
  ```

  4. Replace Canvas `style={{ background: '#0a0a0a' }}` with:
  ```tsx
  style={{ background: background ?? '#0a0a0a' }}
  ```

  5. Replace the outer container div className. Current:
  ```tsx
  className="relative w-full h-64 min-h-64 rounded-xl overflow-hidden border-2 border-blue-400/80 bg-neutral-950 shadow-[0_0_30px_rgba(59,130,246,0.15)]"
  ```
  New (overflow-hidden in the always-on prefix is correct; replay page retains it; do not move overflow-hidden into the ?? fallback):
  ```tsx
  className={`relative w-full overflow-hidden bg-neutral-950 ${containerClassName ?? 'h-64 min-h-64 rounded-xl border-2 border-blue-400/80 shadow-[0_0_30px_rgba(59,130,246,0.15)]'}`}
  ```

  6. Replace the inner div that has `relative h-64 w-full isolate`. Current:
  ```tsx
  <div className="relative h-64 w-full isolate">
  ```
  New:
  ```tsx
  <div className={`relative w-full isolate ${containerClassName ? 'h-full' : 'h-64'}`}>
  ```

  7. Wrap OrbitControls in conditional:
  ```tsx
  {enableOrbitControls !== false && (
    <OrbitControls
      enablePan={false}
      enableZoom
      minDistance={1}
      maxDistance={4}
      minPolarAngle={Math.PI / 6}
      maxPolarAngle={Math.PI / 2}
      dampingFactor={0.05}
    />
  )}
  ```

  8. Wrap the temperature legend: The opening `{showLegend !== false && (` goes on the line immediately before `<div className="absolute bottom-4 right-4 z-10">`, and the closing `)}` goes on the line immediately after that div's closing `</div>`. Do not modify any content inside the legend div.

  **What it does:** Four optional props; root + container + inner get h-full when containerClassName passed; background drives canvas; enableOrbitControls=false hides OrbitControls; showLegend=false hides legend pill.

  **Why this approach:** Root div h-full is required — h-full on a child of an auto-height parent resolves to auto; Canvas then defaults to 150px.

  **Assumptions:**
  - Replay page does not pass containerClassName, enableOrbitControls, or showLegend
  - Tailwind classes `h-full`, `border-0`, `rounded-[0px]` available

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchWithHeatmap3D.tsx
  git commit -m "step 1: add background, containerClassName, enableOrbitControls, showLegend props to TorchWithHeatmap3D"
  ```

  **✓ Verification Test:**

  **Type:** Unit  
  **Action 1:** `grep -n "containerClassName ? 'h-full' : ''" my-app/src/components/welding/TorchWithHeatmap3D.tsx`  
  **Expected:** 1 match — root div only (inner div uses `: 'h-64'` not `: ''`)  
  **Action 2:** `grep -E "background|containerClassName|enableOrbitControls|showLegend" my-app/src/components/welding/TorchWithHeatmap3D.tsx`  
  **Expected:** All four in interface, destructured, used; OrbitControls and legend wrapped in conditionals; no `rounded-none`  
  **Pass:** Root div height fix present; props present; conditional renders  
  **Fail:** No root div h-full, or missing prop, or rounded-none used → re-check

---

### Phase 2 — Replace placeholder with split TorchWithHeatmap3D

**Goal:** Circle shows Session A (left) and Session B (right) with conditional fallback; TorchWithHeatmap3D receives demo-specific props; session labels rendered via overlay divs (no blue HUD).

---

- [x] 🟩 **Step 2: Replace BeadDiffPlaceholder with split div + two TorchWithHeatmap3D** — *Critical*

  **Idempotent:** Yes — replaces one block with another.

  **Context:** Static placeholder replaced by live dual-torch view. Pass `label=""` so no blue HUD card renders; add overlay divs for session identifiers. Guard on `currentTimestamp == null` avoids mounting R3F before timestamp is set.

  **Pre-Read Gate:**
  - `grep -n "BeadDiffPlaceholder" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` — exactly 1 usage
  - `grep -n "TorchWithHeatmap3D" my-app/src/app/demo` — 0 matches

  **Anchor Uniqueness Check:**
  - Target: `<BeadDiffPlaceholder />` inside circle div
  - Must appear exactly 1 time in correct scope

  **Self-Contained Rule:** All code below is complete.

  **No-Placeholder Rule:** No placeholders.

  1. Add import at top of `my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx`:
  ```tsx
  import TorchWithHeatmap3D from '@/components/welding/TorchWithHeatmap3D';
  ```

  2. Replace circle content (the div that currently contains `<BeadDiffPlaceholder />`) with:
  ```tsx
  {currentTimestamp == null ? (
    <BeadDiffPlaceholder />
  ) : (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'row' }}>
      <div style={{ flex: 1, position: 'relative', borderRight: '1px solid rgba(255,255,255,0.06)' }}>
        <div
          style={{
            position: 'absolute',
            top: 6,
            left: 8,
            zIndex: 10,
            fontFamily: FONT_DATA,
            fontSize: 9,
            color: C.novice,
          }}
        >
          A
        </div>
        <TorchWithHeatmap3D
          angle={currentFrameA?.angle_degrees ?? 67}
          temp={currentTempA ?? 300}
          frames={sessionA?.frames ?? []}
          activeTimestamp={currentTimestamp}
          label=""
          labelPosition="inside"
          background="#07090d"
          containerClassName="h-full border-0 rounded-[0px]"
          enableOrbitControls={false}
          showLegend={false}
        />
      </div>
      <div style={{ flex: 1, position: 'relative' }}>
        <div
          style={{
            position: 'absolute',
            top: 6,
            left: 8,
            zIndex: 10,
            fontFamily: FONT_DATA,
            fontSize: 9,
            color: C.expert,
          }}
        >
          B
        </div>
        <TorchWithHeatmap3D
          angle={currentFrameB?.angle_degrees ?? 67}
          temp={currentTempB ?? 300}
          frames={sessionB?.frames ?? []}
          activeTimestamp={currentTimestamp}
          label=""
          labelPosition="inside"
          background="#07090d"
          containerClassName="h-full border-0 rounded-[0px]"
          enableOrbitControls={false}
          showLegend={false}
        />
      </div>
    </div>
  )}
  ```

  **What it does:** Conditional on `currentTimestamp == null`; when set, renders split with overlay labels A/B (design tokens) and TorchWithHeatmap3D with `label=""` (no blue HUD), plus demo props.

  **Why `label=""`:** Label truthy renders blue HUD card. Empty string is falsy → hudContent = null → no blue card. Overlay divs provide session IDs using demo design system.

  **Overlay placement:** Overlay div is a sibling of TorchWithHeatmap3D inside the half-wrapper, not a child. Do not move it inside the component.

  **Assumptions:**
  - `currentFrameA`, `currentFrameB`, `currentTempA`, `currentTempB`, `sessionA?.frames`, `sessionB?.frames`, `currentTimestamp` in scope
  - `C`, `FONT_DATA` in scope (page has both)
  - Circle div has `overflow: hidden` and `borderRadius: 50%`

  **Risks:**
  - WebGL context: 2 canvases — within 8–16 limit. See LEARNING_LOG.md / WEBGL_CONTEXT_LOSS.md.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
  git commit -m "step 2: replace BeadDiffPlaceholder with split TorchWithHeatmap3D"
  ```

  **✓ Verification Test:**

  **Type:** Integration  
  **Action:** Load `/demo/sess_a/sess_b` in dev  
  **Expected:** Placeholder until data+timestamp ready; then two torch views fill circle halves; session labels "A" and "B" from overlay divs; no blue HUD card; no blue legend pill; no camera drift on scrub; canvas fills each half (not 150px)  
  **Pass:** Visual check; no console errors; full-height torch views  
  **Fail:** Blue HUD/legend, truncated views, or camera drifts → check label="" and props

---

- [x] 🟩 **Step 3: Circle container max-width 420px → 460px** — *Non-critical*

  **Idempotent:** Yes — single value change.

  **Context:** 460px gives ~230px per half for better usability.

  **Pre-Read Gate:**
  - `grep -n "420px" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` — exactly 1 match

  **Uniqueness-Before-Replace:** Line with `min(calc(100vh - 260px), 420px)`.

  ```tsx
  // Change:
  width: 'min(calc(100vh - 260px), 420px)',
  // To:
  width: 'min(calc(100vh - 260px), 460px)',
  ```

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
  git commit -m "step 3: bump circle max-width to 460px"
  ```

  **✓ Verification Test:**

  **Type:** Visual  
  **Action:** Inspect circle container  
  **Expected:** Max 460px  
  **Pass:** Styles include 460px

---

- [x] 🟩 **Step 4: Apply CSS fixes** — *Non-critical*

  **Idempotent:** Yes — value-only replacements. For alert count spans: replace existing fontSize and add fontWeight (do not remove other properties).

  **Context:** Typography and layout polish.

  **Pre-Read Gate:**
  - For each change, `grep -n` with surrounding context to confirm uniqueness. `fontSize: 9` appears in many places — use context to target the correct occurrence.

  **Replacements (exact):**

  | # | Target | Action | New |
  |---|--------|--------|-----|
  | 1 | Grid columns (2 occurrences) | Replace | `'200px 1fr 300px'` |
  | 2 | Alert count A span (firedCountA) | In same style object: fontSize 9→16, insert fontWeight: 700 after fontSize | `fontSize: 16, fontWeight: 700` |
  | 3 | Alert count B span (firedCountB) | In same style object: fontSize 9→16, insert fontWeight: 700 after fontSize | `fontSize: 16, fontWeight: 700` |
  | 4 | Alert rule label (getRuleLabel span) | Modify only fontSize; leave fontWeight, letterSpacing, textTransform, color | `fontSize: 11` |
  | 5 | Alert message div | Replace | `fontSize: 9` |
  | 6 | Alert state footer (corrected span) | Replace | `fontSize: 9` |
  | 7 | Alert state footer (uncorrected span) | Replace | `fontSize: 9` |
  | 8 | Alert card padding (button) | Replace | `padding: '10px 0'` |
  | 9 | Current values readout (av span) | Outer span only; do not modify nested unit span | `fontSize: 13` |
  | 10 | Current values readout (bv span) | Outer span only; do not modify nested unit span | `fontSize: 13` |

  **Locations (grep with context to confirm before edit):**
  - Grid: `grep -n "gridTemplateColumns: '220px 1fr 240px'" my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx` — Demo skeleton and main layout
  - Alert count A: span containing `A: {alertsErrorA ? '—' : firedCountA}` — in the same style object, change fontSize: 9 to fontSize: 16 and insert fontWeight: 700 as the next property immediately after fontSize
  - Alert count B: span containing `B: {alertsErrorB ? '—' : firedCountB}` — same instruction as Alert count A
  - Alert rule label: span enclosing `getRuleLabel(alert.rule_triggered)` — modify only fontSize in this span's style object (change 9 to 11); all other properties (fontWeight, letterSpacing, textTransform, color) remain unchanged
  - Alert message: div containing `{alert.message}` — replace fontSize: 7.5 with 9
  - Alert state corrected: span with "✓ corrected in" — replace fontSize: 7.5 with 9
  - Alert state uncorrected: span with "✗ not corrected" — replace fontSize: 7.5 with 9
  - Alert card padding: button with padding: '8px 0' — replace with '10px 0'
  - Current values av: the outer span containing `{av}` and its nested unit span — change fontSize: 11 to fontSize: 13 on the outer span only; do not modify the nested unit span's fontSize: 8
  - Current values bv: the outer span containing `{bv}` and its nested unit span — change fontSize: 11 to fontSize: 13 on the outer span only; do not modify the nested unit span's fontSize: 8

  **Git Checkpoint:**
  ```bash
  git add my-app/src/app/demo/[sessionIdA]/[sessionIdB]/page.tsx
  git commit -m "step 4: apply CSS fixes for grid, alerts, current values"
  ```

  **✓ Verification Test:**

  **Type:** Visual  
  **Action:** Load demo page; inspect grid, alert counts, values  
  **Expected:** Columns 200/300; alert counts larger and bold; values 13px  
  **Pass:** Styles match table

---

## Regression Guard

**Systems at risk:**
- TorchWithHeatmap3D — optional props; defaults preserve replay behavior
- Replay page — does not pass new props; must remain unchanged
- Demo page — conditional split; placeholder when currentTimestamp null

**Regression verification:**

| System | Pre-change | Post-change |
|--------|------------|-------------|
| TorchWithHeatmap3D (no new props) | Canvas background `#0a0a0a`, 256px, OrbitControls on, legend on | Same |
| Replay / torch-viz pages | Unchanged | Same — no new props passed |
| Demo page loading | Skeleton | Skeleton unchanged |
| Demo when currentTimestamp null | Placeholder | BeadDiffPlaceholder |

**Test count regression:**
- Before: `cd my-app && npm run test -- --testPathPattern="demo"` — record count
- After: Same or higher

---

## Rollback Procedure

```bash
# Reverse order
git revert <step 4 commit>
git revert <step 3 commit>
git revert <step 2 commit>
git revert <step 1 commit>
```

---

## Pre-Flight Checklist

| Phase | Check | How to Confirm | Status |
|-------|-------|----------------|--------|
| Pre-flight | Baseline snapshot | Test count + line counts | ⬜ |
| Step 1 | No new props in TorchWithHeatmap3DProps; root div w-full only | grep interface; grep root div | ⬜ |
| Step 2 | BeadDiffPlaceholder rendered once | grep usage | ⬜ |
| Step 3 | 420px in circle width | grep 420px | ⬜ |
| Step 4 | Current CSS values exist; confirm by context | grep with -A/-B | ⬜ |

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|---------------|
| background prop | Optional, default `#0a0a0a` | Pass `background="#07090d"` → Canvas uses it |
| Root div h-full | When containerClassName passed | grep finds `containerClassName ? 'h-full'` |
| containerClassName | Override height/border/rounded | Pass `h-full border-0 rounded-[0px]` → fills circle, no blue box |
| enableOrbitControls | Disable for demo | Pass `false` → no camera drag |
| showLegend | Hide for demo | Pass `false` → no 0–500°C legend pill |
| label="" | No blue HUD | hudContent null; overlay divs show A/B |
| Conditional guard | currentTimestamp null → placeholder | currentTimestamp null → BeadDiffPlaceholder |
| Split view | A left, B right, 50% each | Visual; labels from overlays |
| Circle size | Max 460px | Inspect width |
| CSS | All 10 replacements applied | Visual inspection |
| Replay page | Unchanged | No new props; same layout |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**  
⚠️ **No new data fetching, hooks, or dependencies.**  
⚠️ **Use `rounded-[0px]` not `rounded-none` — production Tailwind build.**
