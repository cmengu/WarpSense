# Exploration: White Screen After Reload — WebGL Context Loss Root Causes

**Date:** 2025-02-16  
**Context:** User reports white screen after reload; provided ranked causes from research.

---

## Executive Summary

All three causes you identified are **present in this codebase**. The most impactful and easiest fix is **removing `e.preventDefault()`** from `webglcontextlost` handlers — it's in 3 components plus the docs example, and the project does **not** manually recreate the renderer.

---

## Finding 1: `preventDefault()` on `webglcontextlost` (Most Likely Cause)

### What You Said
> Tells the browser: "I will restore this context myself"  
> But Three.js cannot actually do that  
> Result: permanent white canvas until hard tab reset

### Evidence in Codebase

| File | Line | Current Code |
|------|------|--------------|
| `TorchViz3D.tsx` | 262 | `e.preventDefault();` |
| `TorchWithHeatmap3D.tsx` | 333 | `e.preventDefault();` |
| `HeatmapPlate3D.tsx` | 109 | `e.preventDefault();` |
| `documentation/WEBGL_CONTEXT_LOSS.md` | 101 | Example shows `e.preventDefault();` |

**Pattern in all three components:**
```tsx
const onLost = (e: Event) => {
  e.preventDefault();  // ⚠️ Dangerous — project does NOT recreate renderer
  if (mountedRef.current) setContextLost(true);
};
```

**What happens today:** Overlay appears, user clicks "Refresh page" → `window.location.reload()`.  
**Problem:** After `preventDefault()`, the browser never fully resets the WebGL state. Reload may not be enough; user might need a **hard tab close** or new tab.

---

## Finding 2: Canvas Never Unmounted (Dead Context Stays Attached)

### What You Said
> If the Canvas stays mounted, the dead WebGL context stays attached.

### Evidence in Codebase

**Current flow in all 3D components:**
```
contextLost = false:
  <Canvas> (mounted) + nothing else

contextLost = true:
  <Canvas> (STILL mounted with dead context) + overlay div on top
```

**No key, no conditional unmount:**
- No `key={canvasKey}` on Canvas
- No `{!contextLost && <Canvas>}` — Canvas is always rendered
- Overlay is an **additional** div, not a replacement

**Relevant snippet from TorchWithHeatmap3D:**
```tsx
<Canvas ...>  {/* No key; always mounted */}
  <SceneContent ... />
</Canvas>
{contextLost && (
  <div className="absolute inset-0 ...">  {/* Overlay on top */}
    <button onClick={() => window.location.reload()}>Refresh page</button>
  </div>
)}
```

The dead WebGL context stays in the DOM until full page reload. If `preventDefault()` blocked proper cleanup, the GPU may never fully release it.

---

## Finding 3: Multiple Canvases After Navigation

### What You Said
> Old Canvases may still exist in memory when you "leave the page"

### Evidence in Codebase

| Page | Canvases | Notes |
|------|----------|-------|
| `/demo` | 2 (TorchWithHeatmap3D × 2) | Expert + novice side-by-side |
| `/replay/[sessionId]` | 2 (TorchWithHeatmap3D × 2) | Primary + comparison |
| `/compare` | 2 | Side-by-side comparison |

**Already documented:** `.cursor/issues/webgl-context-lost-root-cause-prevention.md` lists "Navigation / mounting race" as a cause: "Demo → Replay → Demo: old Canvases may not dispose before new ones mount."

**Layout structure:**
- Root layout: minimal; no shared 3D
- Demo: `DemoLayoutClient` (ErrorBoundary wrapper)
- Replay: no extra layout; Suspense for params

Next.js App Router does not guarantee immediate unmount of previous route when navigating. Old Canvases can persist briefly during transition.

---

## Data Flow (Current)

```
User on /demo or /replay
  → 2 × TorchWithHeatmap3D mount (dynamic, ssr: false)
  → Each creates 1 WebGL context via R3F <Canvas>
  → onCreated: addEventListener('webglcontextlost', onLost)
  → onLost: e.preventDefault() + setContextLost(true)
  → Overlay renders on top of Canvas
  → User clicks "Refresh page" → window.location.reload()
  → If preventDefault blocked browser cleanup: white screen persists
```

---

## Implementation Approach (How I Would Fix)

### Files to Modify (Priority Order)

1. **TorchViz3D.tsx** — Remove `e.preventDefault()` (line 262)
2. **TorchWithHeatmap3D.tsx** — Remove `e.preventDefault()` (line 333)
3. **HeatmapPlate3D.tsx** — Remove `e.preventDefault()` (line 109)
4. **documentation/WEBGL_CONTEXT_LOSS.md** — Update example to show no `preventDefault`, add warning

### Optional (Cause 2): Force Canvas Remount on Recovery

If removing `preventDefault` alone doesn't fix reload, add keyed unmount:

```tsx
// High-level only — pseudocode
const [canvasKey, setCanvasKey] = useState(0);
const [contextLost, setContextLost] = useState(false);

// When context lost: unmount Canvas
{!contextLost && (
  <Canvas key={canvasKey} ...>
    ...
  </Canvas>
)}
{contextLost && (
  <div>
    <p>WebGL context lost</p>
    <button onClick={() => {
      setCanvasKey(k => k + 1);
      setContextLost(false);
    }}>
      Reload 3D
    </button>
  </div>
)}
```

**Trade-off:** "Reload 3D" gives user a recovery path without full page reload. But if the GPU context pool is exhausted, a new Canvas might fail too. Full `window.location.reload()` remains the most reliable.

### Documentation Update

Add a "Rule" section to `WEBGL_CONTEXT_LOSS.md`:

> **Rule:** Only call `preventDefault()` on `webglcontextlost` if you are **manually recreating the renderer** (almost nobody does). Otherwise omit it — let the browser reset. Calling it without manual restoration causes permanent white canvas until hard tab reset.

---

## Component Structure (Current)

```
DemoPage / ReplayPage
  └─ 2 × TorchWithHeatmap3D (dynamic, ssr: false)
       └─ <Canvas onCreated={...}>
            └─ SceneContent
       └─ {contextLost && <Overlay>}
```

No shared Canvas; each instance is independent. No key-based remount strategy.

---

## Edge Cases

| Case | Current Behavior | After Fix (no preventDefault) |
|------|------------------|-------------------------------|
| HMR during dev | Context lost (expected); remount creates new | Same |
| 8+ tabs with 3D | Context limit; overlay appears | Same; overlay still correct |
| User clicks "Refresh page" | `window.location.reload()` | Should now fully reset GPU state |
| Tab background/foreground | Browser may revoke context | Same; overlay when detected |
| Navigation Demo → Replay | 2 old + 2 new Canvases briefly | Same; no change from this fix |

---

## Questions Resolved

- **Q: Are we calling preventDefault?** Yes, in all three 3D components.
- **Q: Do we manually recreate the renderer?** No. We only show overlay + reload button.
- **Q: Is Canvas unmounted on context loss?** No. Overlay is additive.
- **Q: Are there multiple Canvases?** Yes; 2 per page on demo/replay (documented limit).

---

## Recommended Next Step

**Start with Fix 1:** Remove `e.preventDefault()` from all three components and the docs example. This is the highest-impact, lowest-risk change. If white screen after reload persists, then consider Cause 2 (keyed remount) and Cause 3 (lazy Canvas mount, shared Canvas) as follow-up.

---

## Related Files

| File | Role |
|------|------|
| `my-app/src/components/welding/TorchViz3D.tsx` | Context-loss handler |
| `my-app/src/components/welding/TorchWithHeatmap3D.tsx` | Context-loss handler |
| `my-app/src/components/welding/HeatmapPlate3D.tsx` | Context-loss handler |
| `documentation/WEBGL_CONTEXT_LOSS.md` | Docs + example |
| `.cursor/issues/webgl-context-lost-root-cause-prevention.md` | Root cause analysis |
