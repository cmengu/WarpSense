# Development Learning Log

**Purpose:** Document mistakes, solutions, and lessons learned to prevent repeating the same errors.  
**For AI Tools:** Reference this file with `@LEARNING_LOG.md` when implementing 3D/WebGL features.

**Last Updated:** 2025-02-12  
**Total Entries:** 1

---

## Quick Reference

| Date | Title | Category | Severity |
|------|-------|----------|----------|
| 2025-02-12 | WebGL Context Lost — White Screen | Frontend / Performance | 🟡 High |

---

## ⚡ Performance & Optimization

### 📅 2025-02-12 — WebGL Context Lost / White Screen on /dev/torch-viz

**Category:** Frontend / Performance  
**Severity:** 🟡 High

**What Happened:**
The `/dev/torch-viz` page showed a white screen instead of the 3D torch visualization. Console reported `THREE.WebGLRenderer: Context Lost.`

**Impact:**
- Dev demo page unusable — users saw white screen
- Replay page (1–2 instances) worked; dev page (6 instances) failed
- No user-facing message — only console error

**Root Cause:**
- **Technical:** Browsers limit WebGL contexts to ~8–16 per tab. Each `<Canvas>` in react-three-fiber creates one. Six TorchViz3D instances = 6 contexts; combined with HMR or other tabs, the limit was exceeded.
- **Process:** No check for WebGL context limits when designing multi-instance 3D layouts.
- **Knowledge gap:** Unfamiliar with browser WebGL context limits and R3F’s one-context-per-Canvas behavior.

**The Fix:**

```tsx
// ❌ BEFORE — 6 Canvases exhausted WebGL context limit
<div className="grid grid-cols-2 gap-4">
  <TorchViz3D angle={45} temp={250} />
  <TorchViz3D angle={45} temp={400} />
  <TorchViz3D angle={45} temp={520} />
  <TorchViz3D angle={30} temp={450} />
  <TorchViz3D angle={45} temp={450} />
  <TorchViz3D angle={60} temp={450} />
</div>

// ✅ AFTER — 1 instance + loading fallback + context-loss handler
const TorchViz3D = dynamic(
  () => import('@/components/welding/TorchViz3D').then((m) => m.default),
  { ssr: false, loading: () => <div>Loading 3D…</div> }
);
// In TorchViz3D: onCreated adds webglcontextlost listener; overlay when lost
<div><TorchViz3D angle={45} temp={450} label="LIVE PREVIEW" /></div>
```

**Prevention Strategy:**

**Code Level:**
- ✅ DO: Limit to 1–2 Canvas instances per page; use scissor/multi-view if more views needed
- ✅ DO: Add `webglcontextlost` / `webglcontextrestored` handlers and show “Refresh to restore” overlay
- ✅ DO: Add `loading` fallback to dynamic 3D imports
- ✅ DO: Use 1024×1024 shadow maps instead of 2048×2048 when possible
- ❌ DON'T: Render 6+ independent Canvases on one page
- ❌ DON'T: Ignore context loss — surface it to the user

**Process Level:**
- [x] Add to code review: “Does this page use multiple 3D Canvases? Count them.”
- [ ] Add test: Verify single-instance limit on dev torch-viz page
- [ ] Consider linter/comment: Warn when >2 Canvas imports on same page

**AI Prompting Guidance:**
When implementing 3D / React Three Fiber features:
> "Use at most 1–2 Canvas instances per page. Browsers limit WebGL contexts (~8–16 per tab). Add webglcontextlost listeners and show a 'Refresh to restore' overlay. See documentation/WEBGL_CONTEXT_LOSS.md and @LEARNING_LOG.md."

**Good Prompt Example:**
> "Add a TorchViz3D 3D component to the compare page. Follow LEARNING_LOG.md WebGL patterns: single Canvas per view, context-loss overlay, loading fallback. Check documentation/WEBGL_CONTEXT_LOSS.md."

**Warning Signs:**
- White or blank 3D canvas → likely context loss
- `THREE.WebGLRenderer: Context Lost` in console → confirmed
- [HMR] connected followed by context lost → common during dev; new mount should work
- Multiple Canvas components in same route → high risk of hitting limit

**Related:**
- `documentation/WEBGL_CONTEXT_LOSS.md` — Full error reference and fix examples
