# WebGL Context Loss — Error Reference

**Error:** `THREE.WebGLRenderer: Context Lost`

**Category:** Frontend / Performance  
**Severity:** 🟡 High  
**Date documented:** 2025-02-12

---

## Exact Error Message

```
THREE.WebGLRenderer: Context Lost.
```

Often appears in browser console alongside:
```
[HMR] connected
```

---

## What It Means

The browser has **invalidated the WebGL context**. The GPU can no longer use that context for rendering. The canvas will stop drawing and typically shows:
- **White screen**
- **Black screen**
- **Frozen / blank 3D view**

**Recovery:** WebGL contexts cannot be recovered in-place. The user must **refresh the page** to get a new context.

---

## Root Causes

| Cause | Description |
|-------|-------------|
| **Too many WebGL contexts** | Browsers limit ~8–16 contexts per tab. Each R3F `<Canvas>` creates one. Six+ instances can exhaust the limit. |
| **HMR (Hot Module Replacement)** | On save, Next.js remounts components. R3F calls `forceContextLoss()` on unmount. The message is expected during dev but harmless if re-mount succeeds. |
| **Tab switch / background** | Browsers throttle or revoke WebGL when the tab is backgrounded to save GPU memory. |
| **GPU memory pressure** | Heavy scenes (HDRI Environment, large shadow maps, many draw calls) can trigger context loss when the GPU runs out of memory. |

---

## Prevention Checklist

### Code Level

- ✅ **DO:** Use **1–2 Canvas instances per page max**. Use `@react-three/scissor` or split views instead of multiple full Canvases.
- ✅ **DO:** Add `webglcontextlost` / `webglcontextrestored` listeners and show a user-facing overlay when context is lost.
- ✅ **DO:** Use modest shadow map sizes (1024×1024 instead of 2048×2048) to reduce GPU memory.
- ✅ **DO:** Add a `loading` fallback to `dynamic()` for 3D components so users see feedback while the bundle loads.

- ❌ **DON'T:** Render 6+ independent `<Canvas>` components on a single page.
- ❌ **DON'T:** Assume the Canvas will always work; handle context loss explicitly.
- ❌ **DON'T:** Use maximum-quality settings (e.g. 4096 shadow maps) without testing on modest GPUs.

### Detection

- If you see **white screen** on a page with R3F/Three.js 3D content → suspect context loss.
- Console message `THREE.WebGLRenderer: Context Lost` confirms it.

---

## Fix Reference

### 1. Reduce Canvas Count

```tsx
// ❌ BEFORE — 6 Canvases = 6 WebGL contexts (often exceeds limit)
<div className="grid grid-cols-2 gap-4">
  <TorchViz3D angle={45} temp={250} />
  <TorchViz3D angle={45} temp={400} />
  <TorchViz3D angle={45} temp={520} />
  <TorchViz3D angle={30} temp={450} />
  <TorchViz3D angle={45} temp={450} />
  <TorchViz3D angle={60} temp={450} />
</div>

// ✅ AFTER — 1 Canvas, within browser limit
<div>
  <TorchViz3D angle={45} temp={450} label="LIVE PREVIEW" />
</div>
```

### 2. Handle Context Loss in Canvas

```tsx
// ✅ Add onCreated handlers
<Canvas
  onCreated={({ gl }) => {
    const canvas = gl.domElement;
    const onLost = (e: Event) => {
      e.preventDefault();
      setContextLost(true);
    };
    const onRestored = () => setContextLost(false);
    canvas.addEventListener('webglcontextlost', onLost, false);
    canvas.addEventListener('webglcontextrestored', onRestored, false);
  }}
>
  {/* ... */}
</Canvas>

// Show overlay when lost
{contextLost && (
  <div className="absolute inset-0 flex items-center justify-center bg-neutral-900/95">
    <p>WebGL context lost. Refresh the page to restore 3D view.</p>
  </div>
)}
```

### 3. Add Dynamic Loading Fallback

```tsx
const TorchViz3D = dynamic(
  () => import('@/components/welding/TorchViz3D').then((m) => m.default),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-64 items-center justify-center rounded-xl border border-cyan-400/40 bg-neutral-900">
        <span className="text-cyan-400/80 animate-pulse">Loading 3D…</span>
      </div>
    ),
  }
);
```

### 4. Reduce Shadow Map Size

```tsx
// ❌ BEFORE — 2048×2048 (heavy)
<directionalLight shadow-mapSize-width={2048} shadow-mapSize-height={2048} />

// ✅ AFTER — 1024×1024 (lighter, less GPU memory)
<directionalLight shadow-mapSize-width={1024} shadow-mapSize-height={1024} />
```

---

## Related Files

- `my-app/src/components/welding/TorchViz3D.tsx` — Context loss handlers, overlay
- `my-app/src/app/dev/torch-viz/page.tsx` — Reduced to 1 instance, loading fallback

---

## AI Prompting Guidance

When implementing 3D / React Three Fiber features, tell AI:

> "Use at most 1–2 Canvas instances per page. Browsers limit WebGL contexts (~8–16 per tab). Add webglcontextlost listeners and show a 'Refresh to restore' overlay. Use a loading fallback for dynamic 3D imports. See documentation/WEBGL_CONTEXT_LOSS.md."

---

## External References

- [WebGL Context Limits — Stack Overflow](https://stackoverflow.com/questions/41919341/is-there-a-limit-to-the-number-of-three-webglrenderer-instances-in-a-page)
- [R3F Context Lost Discussion #2109](https://github.com/pmndrs/react-three-fiber/discussions/2109)
- [R3F Canvas onCreated for context events](https://github.com/pmndrs/react-three-fiber/issues/3206)
