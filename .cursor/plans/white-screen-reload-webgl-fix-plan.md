# White Screen After Reload — WebGL Context Loss Fix Plan

**Overall Progress:** `100%` (Phase 1 complete)

## TLDR

Remove `e.preventDefault()` from `webglcontextlost` handlers in all 3D components. The project does not manually recreate the WebGL renderer, so calling `preventDefault()` tells the browser "I will restore the context" — but we never do. That blocks proper GPU reset and causes white screen to persist after reload until hard tab close.

---

## Critical Decisions

- **Decision 1:** Remove `preventDefault()` only — do not add keyed remount yet. The exploration ranks this as the most likely cause and lowest-risk fix. If reload still fails, we add Phase 2.
- **Decision 2:** Update all three components plus `documentation/WEBGL_CONTEXT_LOSS.md`. Consistency prevents future regressions and educates future implementers.
- **Decision 3:** Add an explicit Rule section to the docs. Prevents copy-pasting the old (broken) example into new 3D components.

---

## Tasks

### Phase 1 — Remove `preventDefault` from Context-Loss Handlers

**Goal:** User can hit "Refresh page" after WebGL context loss and get a fully functional 3D view again (no white screen persistence).

---

- [x] 🟩 **Step 1: TorchViz3D — Remove `e.preventDefault()`**

  **Subtasks:**
  - [x] 🟩 Remove `e.preventDefault();` from `onLost` in `onCreated` (line ~262)

  **Context:** TorchViz3D is a standalone 3D torch visualizer. Its context-loss handler currently prevents default and shows an overlay, but the project does not recreate the renderer. Removing `preventDefault` lets the browser reset WebGL state so reload works.

  **Code change:**
  ```tsx
  // BEFORE
  const onLost = (e: Event) => {
    e.preventDefault();
    if (mountedRef.current) setContextLost(true);
  };

  // AFTER
  const onLost = () => {
    if (mountedRef.current) setContextLost(true);
  };
  ```

  **What it does:** Stops claiming we will restore the context; lets the browser perform its default cleanup on reload.

  **Assumptions:** Event parameter is no longer needed after removing `preventDefault`; listener still fires.

  **Risks:** None expected; this is a removal of incorrect behavior.

  **✓ Verification Test:**

  **Action:**
  - Run dev server, open `/demo` or any page using TorchViz3D
  - Trigger context loss (e.g., open 8+ tabs with 3D, or use dev tools to force loss)
  - Confirm overlay appears with "Refresh page" button
  - Click "Refresh page"

  **Expected Result:**
  - Page reloads
  - 3D view renders correctly (no persistent white screen)

  **How to Observe:**
  - **Visual:** 3D canvas shows torch/heatmap content after reload
  - **Console:** No `THREE.WebGLRenderer: Context Lost` loop after reload

  **Pass Criteria:** Reload restores 3D view; no white screen persistence.

  **Common Failures & Fixes:**
  - **If white screen still persists after reload:** Proceed to Phase 2 (keyed remount)

---

- [x] 🟩 **Step 2: TorchWithHeatmap3D — Remove `e.preventDefault()`**

  **Subtasks:**
  - [x] 🟩 Remove `e.preventDefault();` from `onLost` in `onCreated` (line ~333)

  **Code change:** Same pattern as Step 1 — remove `e.preventDefault()`; optionally drop `e` parameter from `onLost` for consistency.

  **✓ Verification Test:**

  **Action:**
  - Run dev server, open `/demo` (uses 2 × TorchWithHeatmap3D)
  - Trigger context loss, confirm overlay, click "Refresh page"

  **Expected Result:**
  - Both expert and novice 3D views render after reload

  **How to Observe:**
  - **Visual:** Both side-by-side 3D canvases show content
  - **Console:** No context-loss error loop

  **Pass Criteria:** Reload restores both 3D views.

  **Common Failures & Fixes:**
  - **If only one view restores:** Possible component unmount ordering; check dynamic import and layout.

---

- [x] 🟩 **Step 3: HeatmapPlate3D — Remove `e.preventDefault()`**

  **Subtasks:**
  - [x] 🟩 Remove `e.preventDefault();` from `onLost` in `onCreated` (line ~109)

  **Code change:** Same pattern as Steps 1–2.

  **✓ Verification Test:**

  **Action:**
  - Open any page that renders HeatmapPlate3D
  - Trigger context loss, overlay appears, click "Refresh page"

  **Expected Result:**
  - 3D heatmap plate renders after reload

  **Pass Criteria:** Reload restores HeatmapPlate3D view.

---

- [x] 🟩 **Step 4: Update `documentation/WEBGL_CONTEXT_LOSS.md`**

  **Subtasks:**
  - [x] 🟩 Update example in "Handle Context Loss in Canvas" section — remove `e.preventDefault()` from the code block
  - [x] 🟩 Add Rule section explaining when to use (or omit) `preventDefault`

  **What it does:** Prevents future copy-paste of the broken pattern; documents the correct approach.

  **Code change:**
  ```tsx
  // In the example code block: remove e.preventDefault()
  const onLost = (e: Event) => {
    // Do NOT call e.preventDefault() unless you manually recreate the renderer
    setContextLost(true);
  };
  ```

  Add new Rule section:
  > **Rule:** Only call `preventDefault()` on `webglcontextlost` if you are **manually recreating the renderer** (almost nobody does). Otherwise omit it — let the browser reset. Calling it without manual restoration causes permanent white canvas until hard tab reset.

  **✓ Verification Test:**

  **Action:**
  - Read `documentation/WEBGL_CONTEXT_LOSS.md`
  - Confirm example has no `preventDefault()`
  - Confirm Rule section exists and matches intent

  **Pass Criteria:** Docs clearly state to omit `preventDefault` when not recreating renderer.

---

### Phase 2 — Keyed Canvas Remount (Optional, Only If Phase 1 Insufficient)

**Goal:** If reload still fails after Phase 1, provide a "Reload 3D" path that unmounts and remounts the Canvas instead of full page reload.

**Trigger:** Only implement if user confirms white screen persists after Phase 1.

---

- [x] 🟩 **Step 5: Add keyed remount to TorchWithHeatmap3D (Phase 2, optional)**

  **Context:** When context is lost, Canvas stays mounted with dead WebGL context. Unmounting it and remounting with a new key forces a fresh context.

  **Subtasks:**
  - [x] 🟩 Add `canvasKey` state, increment on "Reload 3D"
  - [x] 🟩 Conditionally render `{!contextLost && <Canvas key={canvasKey}>}`
  - [x] 🟩 When `contextLost`, show overlay with "Reload 3D" button that increments key and resets `contextLost`
  - [x] 🟩 Keep "Refresh page" as fallback for exhausted context pool

  **Assumptions:** GPU context pool may recover after unmount; new Canvas might succeed.

  **Risks:** If pool is exhausted, "Reload 3D" may fail; "Refresh page" remains fallback.

  **✓ Verification Test:**

  **Action:**
  - Trigger context loss
  - Click "Reload 3D" (new button)

  **Expected Result:**
  - Canvas unmounts, remounts with new key
  - 3D view restores without full page reload (when possible)

  **Pass Criteria:** "Reload 3D" restores view when context pool has capacity.

---

## Pre-Flight Checklist (Print & Check Each Phase)

| Phase   | Dependency Check         | How to Verify                                           | Status |
|---------|---------------------------|---------------------------------------------------------|--------|
| Phase 1 | Dev server runs           | `npm run dev` in my-app, no build errors                | ⬜     |
|         | Demo/Replay pages load    | Navigate to /demo, /replay/[any-id]; 3D views render    | ⬜     |
|         | Context-loss overlay exists | Overlay appears when context lost (test with many tabs) | ⬜     |
| Phase 2 | Phase 1 complete          | `preventDefault` removed; reload still fails if testing | ⬜     |

---

## Risk Heatmap (Where You'll Get Stuck)

| Phase   | Risk Level | What Could Go Wrong                           | How to Detect Early                             |
|---------|------------|-----------------------------------------------|-------------------------------------------------|
| Phase 1 | 🟢 **10%** | Typos; wrong file                             | Lint and type-check before manual test          |
| Phase 2 | 🟡 **35%** | "Reload 3D" fails when context pool exhausted  | Keep "Refresh page" as fallback; test with 8+ tabs |

---

## Success Criteria (End-to-End Validation)

| Feature              | Target Behavior                                              | Verification Method                                                                 |
|----------------------|--------------------------------------------------------------|--------------------------------------------------------------------------------------|
| Reload after context loss | User clicks "Refresh page" → full 3D restore, no white screen | **Test:** Trigger loss → overlay → Refresh page → **Expect:** 3D renders → **Location:** Visual |
| Docs correctness     | New 3D code does not copy broken `preventDefault` pattern    | **Test:** Read WEBGL_CONTEXT_LOSS.md → **Expect:** Example has no preventDefault, Rule explains | |
| Tests pass           | Existing unit tests still pass                               | **Test:** Run `npm test` in my-app → **Expect:** All pass                             |

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.**
