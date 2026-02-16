# [Bug] WebGL Context Lost — "Refresh to restore 3D view" — Root Cause & Prevention

## TL;DR

Users and developers repeatedly hit "WebGL context lost" with a "Refresh the page to restore 3D view" overlay. The overlay is *working as designed* (it surfaces the failure), but the underlying problem is that context loss keeps happening. This issue documents **why it happens** and **how to reduce or prevent it**.

---

## Current State vs Expected

| Current | Expected |
|---------|----------|
| Overlay appears on demo, replay, dev pages; user must refresh | Overlay should rarely appear; 3D view should stay stable |
| Console: `THREE.WebGLRenderer: Context Lost` (often with `[HMR] connected`) | No context loss in normal usage; HMR context loss documented as expected |
| White/black screen → overlay → refresh cycle | Deterministic 3D rendering; no forced refresh |
| Multiple 3D Canvases per page (2 on replay/demo) | As few Canvas instances as possible; within browser limit |

---

## Why This Happens (Root Causes)

### 1. **Too many WebGL contexts**

Browsers limit **~8–16 WebGL contexts per tab**. Each `<Canvas>` (R3F) = 1 context.

| Page | Canvas count | Risk |
|------|--------------|------|
| `/demo` | 2 (TorchWithHeatmap3D × 2) | OK alone; risk if user opens multiple tabs or navigates rapidly |
| `/replay` | 2 (TorchWithHeatmap3D × 2) | Same |
| `/dev/torch-viz` | 1 (TorchViz3D) | Lowest risk |

**Trigger:** 6+ tabs with 3D content, or 2–3 tabs with 2 Canvases each → limit exceeded → context lost.

### 2. **HMR (Hot Module Replacement) in development**

On save, Next.js remounts components. R3F calls `forceContextLoss()` on unmount. The browser invalidates the context. **This is expected and not a bug.** A new context is created on remount. No user action required — but the console message is noisy and alarming.

### 3. **Tab backgrounding**

Browsers throttle or revoke WebGL when the tab goes to background to save GPU memory. Returning to the tab can show context lost.

### 4. **GPU memory pressure**

Heavy scenes (large shadow maps, HDRI, many draw calls) can exhaust GPU memory → context loss.

### 5. **Navigation / mounting race**

Demo → Replay → Demo: old Canvases may not dispose before new ones mount → temporary context accumulation risk.

---

## How to Stop It (Prevention)

### Code-level (enforced)

| Action | Status | Where |
|--------|--------|-------|
| Limit to 1–2 Canvas per page | ✅ ESLint rule | `eslint-rules/max-torchviz3d-per-page.cjs` |
| Add `webglcontextlost` / `webglcontextrestored` listeners | ✅ Done | TorchViz3D, TorchWithHeatmap3D, HeatmapPlate3D |
| Show overlay when context lost | ✅ Done | All 3D components |
| Dynamic import with `ssr: false` + loading fallback | ✅ Done | Demo, replay, dev |
| Use modest shadow map (1024×1024, not 2048) | ⚠️ Verify | Check `directionalLight` in 3D components |

### Architectural (reduce context count)

| Option | Effort | Impact |
|--------|--------|--------|
| **Shared Canvas + scissor** | High | 2 views in 1 Canvas → 1 context instead of 2 |
| **Lazy load comparison view** | Medium | Don’t mount 2nd Canvas until user enables comparison |
| **Single 3D view with toggle** | Medium | Expert OR novice, not both at once |

### Operational / docs

- Document HMR context loss as expected in dev (see `WEBGL_CONTEXT_LOSS.md`).
- Onboarding note: "Context Lost during HMR is expected; do not file a bug."
- Manual verification: open 8+ tabs → confirm overlay appears.

---

## Relevant Files

| File | Role |
|------|------|
| `documentation/WEBGL_CONTEXT_LOSS.md` | Error reference, causes, fixes |
| `LEARNING_LOG.md` | Past incidents, DO/DON'T |
| `my-app/src/constants/webgl.ts` | `MAX_TORCHVIZ3D_PER_PAGE`, `MAX_CANVAS_PER_PAGE` |
| `my-app/src/components/welding/TorchWithHeatmap3D.tsx` | Context-loss handlers, overlay |
| `my-app/src/components/welding/TorchViz3D.tsx` | Context-loss handlers |
| `my-app/src/components/welding/HeatmapPlate3D.tsx` | Context-loss handlers |
| `.cursor/issues/webgl-context-lost-consistent-project-wide.md` | Acceptance criteria, scope |

---

## Proposed Next Steps

1. **Short term:** Confirm shadow map sizes are 1024×1024 (or smaller) in all 3D components.
2. **Medium term:** Add lazy mount for replay comparison — 2nd Canvas only when user toggles "Show Comparison".
3. **Long term:** Evaluate shared Canvas + scissor for demo/replay side-by-side views if context loss persists.

---

## Classification

**Type:** bug  
**Priority:** high  
**Effort:** medium  
**Category:** frontend / performance
