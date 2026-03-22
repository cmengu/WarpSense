# Development Learning Log

**Purpose:** Document mistakes, solutions, and lessons learned to prevent repeating the same errors. Feed lessons to AI tools.  
**For AI Tools:** Reference this file with `@LEARNING_LOG.md` when implementing 3D/WebGL, SSE/streaming APIs, or analysis UI (`AnalysisTimeline`).  
**For `.cursorrules`:** Check LEARNING_LOG.md for anti-patterns, required patterns, and past incidents before generating code.

**Last Updated:** 2026-03-21  
**Total Entries:** 29 incidents + Lessons & Reflections

**Dashboard code review (2026-03-02):** `Promise.race` with `setTimeout` — clear timer in `finally` or it leaks when the main promise wins first. Tests: use `within(container).getByText()` + `toHaveAttribute` instead of `document.querySelector`; remove dead mocks (e.g. useRouter when page doesn't use it). See project-context.md "Promise.race Timeout Cleanup" and "Common Failure Points".

**Demo circle heatmap (2026-03-02):** TorchWithHeatmap3D on new pages (e.g. demo) MUST use `dynamic(..., { ssr: false })` — never static import. Plan said `import TorchWithHeatmap3D from '...'`; implementation followed that and caused blank canvas (WebGL/DOM not available during SSR). Cross-check replay/compare pages before implementing; they already use dynamic import. Also: when `enableOrbitControls={false}`, R3F Canvas needs custom no-op events to avoid addEventListener on null. See project-context.md "SSR Safety (WebGL/Canvas)" and "Common Failure Points".

**Session report data layer (2026-02-26):** `GET /api/sessions/{id}/report-summary` returns ReportSummary (heat input, travel angle excursions, arc termination, defect counts). `run_session_alerts()` in alert_service.py — single source for alerts + report-summary. Process_type mapping owned by `compute_report_summary`. Report_thresholds.json cached per process. See project-context.md "Session Report Data Layer".

**Scoring decomposition (2026-02-26):** Defect score penalty must use valid AlertPayload count, not `len(alerts)` — non-AlertPayload items are dropped but would be wrongly penalized. Config weights must sum to 1.0; validate on load. Use `_build_alerts_from_frames` from scorer.py; do not duplicate. See project-context.md AWS D1.2 Decomposed Scoring.

**Mock data Pydantic compatibility (2026-02-26):** Use `hasattr(obj, "model_copy")` instead of `try/except AttributeError` when copying Pydantic models. The broad except swallows unrelated attribute errors and makes debugging hard.

**Mock data division guard (2026-02-26):** Add `param = max(param, 1.0)` at function top for numeric params that may cause division by zero — defensive guards belong at the boundary, not at call sites.

**Mock data magic numbers (2026-02-26):** Extract inline values (e.g. 400.0, 12.0) to constants (AL_TRAVEL_SPEED_BASE_MEAN, AL_TRAVEL_SPEED_BASE_SIGMA). Inline numbers create multiple sources of truth for the next agent.

**Mock data docstring drift (2026-02-26):** A docstring that contradicts the implementation is worse than no docstring — it will cause the next agent to "fix" the code to match the wrong docstring. Update immediately.

**Defect alert hardcoded values (2026-02-26):** Alert messages said "19.5V" or "140A" instead of config values. When voltage_lo_V changes for a different material, the message would mislead. Fix: interpolate `self._cfg["voltage_lo_V"]` etc. into f-strings.

**Crater buffer false positive on sensor dropout (2026-02-26):** When amps=None (sensor dropout) then amps=0 at bead end, crater_crack could fire using stale arc history. Fix: call `_crater_buffer.reset()` when amps is None.

**Metal plane clipping (2025-02-16):** Y-coordinates were scattered across TorchWithHeatmap3D; metal could clip through torch. Fix: centralize all workpiece/ring/grid/shadows Y in `welding3d.ts` with explicit constraint `metal_surface_max_Y < weld_pool_center_Y`. See `my-app/src/constants/welding3d.ts`.

**Color sensitivity (2025-02-16):** Heatmap shader now uses stepped gradient (0–500°C, 10°C per visible step). `heatmapShaderUtils.ts` provides TS mirror for unit tests. See `unified-torch-heatmap-replay-plan.md`.

**ThermalPlate WebGL lifecycle (2025-02-16):** Never allocate DataTexture or ShaderMaterial in `useMemo` — use `useEffect` with cleanup. `useMemo` is for pure computations; side effects (GPU resources) violate React rules and cause leaks in Strict Mode. See Round 1 review (.cursor/review-round1-output.md).

**Unified torch+heatmap (2025-02-16):** TorchWithHeatmap3D replaces separate TorchViz3D + HeatmapPlate3D. One Canvas: torch + thermally-colored metal. Replay/demo use this; HeatmapPlate3D kept for dev/standalone only.

**WWAD macro-analytics (2025-02-17):** Supervisor dashboard built orthogonally to micro-feedback — aggregate session data only, no frame/3D coupling. Migration `score_total` nullable + backfill; export with truncation logging.

**Warp Prediction ML (2025-02-18):** Shared `warp_features.py` for train + inference; ONNX model degrades gracefully when missing. `get_session_frames_raw` in sessions.py; WarpRiskGauge on replay page. See `_merge/agent2_main.py`, `_merge/agent2_api.ts`.

**random.seed() vs random.Random(seed) (2026-02-23):** For deterministic mock data generators, use `rng = random.Random(seed)` + `rng.gauss()` instead of global `random.seed()` + `random.gauss()`. Global seed mutates process-wide state; any other caller of `random` breaks reproducibility. See `backend/data/mock_sessions.py` aluminum generators.

**Stale seed data when mock generators change (2026-02-23):** `seed_demo_data.py` skips re-seeding when existing count matches expected. If you change mock_sessions.py (e.g. duration_ms, arc types), run `python -m scripts.seed_demo_data --force` or `curl -X POST .../wipe-mock-sessions` then `.../seed-mock-sessions`. See STARTME.md.

**GZip middleware + SSE (2026-03-21):** FastAPI `GZipMiddleware(minimum_size=1000)` buffers small chunks until 1 KB before flushing. WarpSense SSE events (~80–100 B each) sat in the buffer until the large `complete` event — browser saw silence then a burst. Fix: set `Content-Encoding: identity` on `StreamingResponse` for SSE so gzip skips that response. See `backend/routes/warp_analysis.py` `run_analysis` headers.

**AnalysisTimeline + Analyse All (2026-03-21):** Calling `onComplete(report)` in the same synchronous block as `setReport` + `setPhase("done")` let React 18 batch with parent `startStream(next)`; `key={sessionId}` changed in the same commit, unmounting the timeline before the report painted. Fix: defer `onComplete` with `useEffect` + `setTimeout(..., 800)` after `phase === "done"` and `report` are set. See `my-app/src/components/analysis/AnalysisTimeline.tsx`.

---

## Quick Reference

| Date | Title | Category | Severity |
|------|-------|----------|----------|
| 2026-03-21 | GZipMiddleware Buffers SSE Until 1 KB — Use identity | API / Streaming | 🟡 High |
| 2026-03-21 | onComplete + key — Batch Unmount Before Report Renders | Frontend / React | 🟡 High |
| 2026-03-02 | Promise.race Timeout Leak — No clearTimeout on Settle | Performance | 🟢 Medium |
| 2026-03-02 | Testing: document.querySelector vs Testing Library | Testing | ⚪ Low |
| 2026-03-02 | Dead Mocks (useRouter) in Tests | Testing | ⚪ Low |
| 2026-03-02 | Demo Circle Heatmap — Static Import SSR Blank Canvas | Frontend / 3D | 🟡 High |
| 2026-02-26 | Defect Score Penalty Uses Wrong Alert Count | Backend / Scoring | 🟢 Medium |
| 2026-02-26 | Scoring Config Weight Validation | Backend / Config | 🟢 Medium |
| 2026-02-26 | Backfill Script Per-Item Error Handling | Backend / Scripts | ⚪ Low |
| 2026-02-26 | Pydantic hasattr vs try/except (Mock Data) | Backend / Pydantic | 🟢 Medium |
| 2026-02-26 | Division-by-Zero Defensive Guard (Mock Data) | Backend | ⚪ Low |
| 2026-02-26 | Magic Numbers to Constants (Mock Data) | Backend / Code Quality | ⚪ Low |
| 2026-02-26 | Docstring Contradicts Implementation (Mock Data) | Backend / Code Quality | ⚪ Low |
| 2026-02-26 | Spacing/Style Fix Immediately (Mock Data) | Code Quality | ⚪ Low |
| 2026-02-26 | Defect Alert Hardcoded Config in Messages | Backend / Alerts | 🟢 Medium |
| 2026-02-26 | Crater Buffer Not Reset on amps=None | Backend / Alerts | 🟢 Medium |
| 2026-02-26 | Python 3.8 deque Type Annotation | Backend | ⚪ Low |
| 2026-02-26 | caplog.messages for Log Assertions | Testing | ⚪ Low |
| 2026-02-26 | Thermal Data Dict KeyError — Use .get() | Backend / Data | 🟢 Medium |
| 2026-02-26 | Array Mutation in Render (.sort) | Frontend | ⚪ Low |
| 2026-02-26 | React List Keys — Duplicate Excursions | Frontend | ⚪ Low |
| 2026-02-26 | Config File Repeated Reads — Cache | Backend / Performance | ⚪ Low |
| 2026-02-23 | Stale Validation Error Message (process_type) | API / Backend | 🟡 High |
| 2026-02-23 | API Docs, Logs, Imports Drift | Backend | 🟢 Medium |
| 2026-02-23 | random.Random(seed) for Deterministic Mock Data | Backend / Data | 🟢 Medium |
| 2025-02-18 | Warp Prediction ML (Batch 1) | Backend / ML | 🟢 Medium |
| 2025-02-17 | WWAD Macro-Analytics (Supervisor Dashboard) | Backend / Architecture | 🟢 Medium |
| 2025-02-16 | Metal Plane Clipping Through Torch | Frontend / 3D | 🟢 Medium |
| 2025-02-16 | Unified Torch + Thermal Metal (Replay) | Frontend | 🟢 Medium |
| 2025-02-16 | WebGL Context Lost — Project-Wide Mitigations | Frontend / Performance | 🟡 High |
| 2025-02-12 | WebGL Context Lost — White Screen | Frontend / Performance | 🟡 High |

---

## ⚡ Performance & Optimization

### 📅 2026-03-02 — Promise.race Timeout Leak (No clearTimeout on Settle)

**Category:** Performance  
**Severity:** 🟢 Medium

**What Happened:**
`fetchScoreWithTimeout` used `Promise.race([fetchScore(...), timeout])` where `timeout` was created with `setTimeout`. When `fetchScore` resolved first, the timeout stayed scheduled until it fired — leaking the timer and wasting work.

**The Fix:**

```typescript
// ❌ BEFORE — timeout never cleared when fetch wins
const timeout = new Promise<null>((_, reject) =>
  setTimeout(() => reject(new Error("timeout")), FETCH_TIMEOUT_MS)
);
try {
  return await Promise.race([fetchScore(sessionId, signal), timeout]);
} catch { return null; }

// ✅ AFTER — clear timer in finally
let timeoutId: ReturnType<typeof setTimeout>;
const timeout = new Promise<never>((_, reject) => {
  timeoutId = setTimeout(() => reject(new Error("timeout")), FETCH_TIMEOUT_MS);
});
try {
  return await Promise.race([fetchScore(sessionId, signal), timeout]);
} catch { return null; }
finally { clearTimeout(timeoutId!); }
```

**Prevention:**
- ✅ DO: Store setTimeout id; clear it in `finally` so it runs whether race resolves or rejects
- ❌ DON'T: Create timeout Promise without cleanup when using Promise.race

**AI Guidance:** When implementing timeouts with Promise.race, always clear the timer in a finally block. See project-context.md "Promise.race Timeout Cleanup".

---

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
- **Knowledge gap:** Unfamiliar with browser WebGL context limits and R3F's one-context-per-Canvas behavior.

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
- ✅ DO: Add `webglcontextlost` / `webglcontextrestored` handlers and show "Refresh to restore" overlay
- ✅ DO: Add `loading` fallback to dynamic 3D imports
- ✅ DO: Use 1024×1024 shadow maps instead of 2048×2048 when possible
- ❌ DON'T: Render 6+ independent Canvases on one page
- ❌ DON'T: Ignore context loss — surface it to the user

**Process Level:**
- [x] Add to code review: "Does this page use multiple 3D Canvases? Count them."
- [x] Add test: Demo and Replay pages have tests verifying ≤2 TorchViz3D instances
- [x] Lint/comment guidance: src/constants/webgl.ts + WEBGL_CONTEXT_LOSS.md checklist

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

---

### 📅 2025-02-16 — WebGL Context Lost — Project-Wide Mitigations

**Category:** Frontend / Performance  
**Severity:** 🟡 High

**What Was Done:**
Hardened TorchViz3D overlay for visibility (z-[100], isolate), added demo instance-count test, ESLint rule enforcing ≤2 TorchViz3D per page, HMR documentation, manual overlay verification procedure, code review checklist.

**Key Changes:**
- Overlay: `isolate` on wrapper, `z-[100]` to beat parent stacking contexts
- Tests: Demo and replay pages both assert ≤2 TorchViz3D instances
- ESLint: Custom rule `max-torchviz/max-torchviz3d-per-page` fails build when page has >2 instances
- Docs: HMR section, manual verification procedure, code review checklist in WEBGL_CONTEXT_LOSS.md

**Process Level (updated):**
- ESLint rule for instance count
- Manual overlay verification doc
- Code review checklist for 3D/WebGL

**References:**
- `.cursor/plans/webgl-context-loss-project-wide-plan.md`
- `documentation/WEBGL_CONTEXT_LOSS.md`

---

## 🎨 Frontend / 3D Thermal Visualization

### 📅 2025-02-16 — Unified Torch + Thermal Metal (Replay)

**Category:** Frontend  
**Severity:** 🟢 Medium

**What Was Done:**
Integrated 3D heatmap on metal into replay/demo instead of a separate heatmap component. TorchWithHeatmap3D renders torch + thermally-colored workpiece in one Canvas. Heat "travels" through the metal as frames advance (0–500°C). Color sensitivity tuned so 5–10°C differences are visible.

**Impact:**
- Single 3D view per session (torch + metal), no separate HeatmapPlate3D
- 10°C per visible step (THERMAL_COLOR_SENSITIVITY=10); for finer steps use 5
- WebGL instance count stays ≤2 per page (TorchWithHeatmap3D replaces TorchViz3D + HeatmapPlate3D)

**Patterns:**

```tsx
// ❌ BEFORE — separate torch and heatmap (2 Canvas-equivalent components)
<TorchViz3D angle={45} temp={450} />
<HeatmapPlate3D frames={frames} />

// ✅ AFTER — unified component (1 Canvas, torch + thermal metal)
<TorchWithHeatmap3D
  frames={thermalFrames}
  maxTemp={THERMAL_MAX_TEMP}
  minTemp={THERMAL_MIN_TEMP}
  colorSensitivity={THERMAL_COLOR_SENSITIVITY}
/>
```

**Prevention:**
- ✅ DO: Use TorchWithHeatmap3D for replay/demo when thermal data exists
- ✅ DO: Pass colorSensitivity (5–10) so small temp changes are visible; 10 = 50 steps over 0–500°C
- ✅ DO: Keep heatmapShaderUtils.ts in sync with heatmapFragment.glsl.ts for tests
- ❌ DON'T: Add separate HeatmapPlate3D alongside TorchViz3D on same page (inflates WebGL count)

**AI Guidance:**
```
When adding thermal visualization to replay/demo:
"Use TorchWithHeatmap3D (not TorchViz3D + HeatmapPlate3D). Pass frames, maxTemp/minTemp, colorSensitivity from constants/thermal.ts. For 5°C visibility set THERMAL_COLOR_SENSITIVITY=5."
```

**References:**
- `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
- `my-app/src/constants/thermal.ts` — THERMAL_COLOR_SENSITIVITY, THERMAL_MAX_TEMP
- `.cursor/plans/unified-torch-heatmap-replay-plan.md`

---

### 📅 2026-03-02 — Demo Circle Heatmap — Static Import Caused Blank Canvas

**Category:** Frontend / 3D  
**Severity:** 🟡 High

**What Happened:**
Plan execution for demo page TorchWithHeatmap3D (two circles side-by-side) followed the plan exactly: `import TorchWithHeatmap3D from '...'` (static import). The heatmap circles did not display — blank or white canvas. Multiple camera position iterations and debugging followed before discovering the root cause.

**Impact:**
- Blank/white 3D view on demo page
- 10+ camera position tweaks (trial and error)
- R3F events error when enableOrbitControls={false} (addEventListener on null)
- Extended debug time

**Root Cause:**
- **Technical:** Static import runs TorchWithHeatmap3D (R3F Canvas + WebGL) during Next.js SSR. WebGL and DOM do not exist in Node — result: blank canvas or hydration mismatch.
- **Technical:** When OrbitControls disabled, R3F's default event system still tries to attach; needs custom no-op events on Canvas.
- **Process:** Plan specified static import; did not cross-reference replay/compare pages which use `dynamic(..., { ssr: false })`.
- **Knowledge:** Plan assumed "add import" without checking SSR safety for WebGL components.

**The Fix:**

```tsx
// ❌ BEFORE — plan said: static import → SSR runs WebGL → blank canvas
import TorchWithHeatmap3D from '@/components/welding/TorchWithHeatmap3D';

// ✅ AFTER — dynamic + ssr: false (matches replay, compare)
const TorchWithHeatmap3D = dynamic(
  () => import('@/components/welding/TorchWithHeatmap3D').then((m) => m.default),
  { ssr: false, loading: () => <div>Loading 3D…</div> }
);
```

**Prevention:**
- ✅ DO: Use `dynamic(..., { ssr: false })` for TorchWithHeatmap3D on any new page
- ✅ DO: Cross-check replay and compare pages before implementing — they are the reference
- ✅ DO: When enableOrbitControls={false}, pass custom no-op events to R3F Canvas (avoid null addEventListener)
- ❌ DON'T: Follow a plan's "add import" verbatim for WebGL components without verifying SSR safety
- ❌ DON'T: Guess camera position — enable OrbitControls, drag to find angle, then lock in values

**AI Guidance:**
```
When adding TorchWithHeatmap3D to a new page:
1. Use dynamic(..., { ssr: false }) — NEVER static import. Check replay/compare pages.
2. If enableOrbitControls={false}, pass events={() => ({ enabled: false, connect: () => {}, ... })} to Canvas.
3. For square/small viewports: cameraFov={72}, cameraPosition from user drag or replay default.
4. Reference @LEARNING_LOG.md and @.cursor/context/project-context.md before implementing.
```

**References:**
- `app/demo/[sessionIdA]/[sessionIdB]/page.tsx` — dynamic import
- `app/replay/[sessionId]/page.tsx` — reference pattern
- `.cursor/plans/demo-bead-diff-torch-split-execution.md` — plan that specified static import

---

### 📅 2025-02-16 — Metal Plane Clipping Through Torch

**Category:** Frontend / 3D  
**Severity:** 🟢 Medium

**What Happened:**
Metal workpiece, angle ring, grid, and ContactShadows used hardcoded or inconsistent Y-positions. Metal surface could intersect the weld pool; metal clipped through the torch during rotation.

**Impact:**
- Visual artifact: metal plane clipping through torch
- Inconsistent depth ordering when rotating view
- No enforcement of metal-below-torch constraint

**Root Cause:**
- **Technical:** Y-coordinates scattered across TorchWithHeatmap3D; workpiece, ring, grid, shadows each had different/ad-hoc values. No single source of truth.
- **Process:** No central constraint asserting `metal_surface_max_Y < weld_pool_center_Y`.

**The Fix:**

```tsx
// ❌ BEFORE — scattered Y values
<group position={[0, -0.85, 0]}>  // ad-hoc
<mesh position={[0, -0.84, 0]}>   // different ad-hoc
<ContactShadows position={[0, -0.84, 0]} />
```

```tsx
// ✅ AFTER — single source of truth
// welding3d.ts: WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y
// Constraint: metal_surface_max_Y (-0.35) < WELD_POOL_CENTER_Y (-0.2), gap ≥ 0.15
<group position={[0, WORKPIECE_GROUP_Y, 0]}>
<mesh position={[0, ANGLE_RING_Y, 0]}>
<ContactShadows position={[0, CONTACT_SHADOWS_Y, 0]} />
```

**Prevention:**
- ✅ DO: Use `welding3d.ts` for all workpiece/ring/grid/shadows Y positions
- ✅ DO: Assert `metal_surface_max_Y < WELD_POOL_CENTER_Y` and `gap >= 0.1` in tests
- ✅ DO: Keep weld pool Y (torch-internal) separate; only metal-side uses welding3d
- ❌ DON'T: Hardcode Y values in TorchWithHeatmap3D or related components
- ❌ DON'T: Change MAX_THERMAL_DISPLACEMENT without checking HeatmapPlate3D / ThermalPlate

**AI Guidance:**
```
When modifying 3D welding scene Y-positions:
"Use constants from welding3d.ts (WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y). Never hardcode Y in components. Constraint: metal_surface_max_Y < weld_pool_center_Y. See LEARNING_LOG.md metal plane clipping entry."
```

**References:**
- `my-app/src/constants/welding3d.ts`
- `.cursor/plans/metal-heatmap-y-position-clipping-fix-plan.md`
- `.cursor/issues/metal-heatmap-y-position-clipping-torch.md`

---

## 🌐 API / Validation

### 📅 2026-02-23 — Stale Validation Error Message (process_type)

**Category:** API / Backend  
**Severity:** 🟡 High

**What Happened:**
`POST /sessions` validates `process_type` against `VALID_PROCESS_TYPES` (which includes `aluminum`), but the HTTP 422 error message listed only `mig, tig, stick, flux_core`. A client sending `process_type=aluminum` received a confusing rejection message implying aluminum was invalid.

**Impact:**
- Clients adding aluminum support would get "must be one of: mig, tig, stick, flux_core" when passing `aluminum`
- Misleading error → wasted debugging, incorrect assumption that aluminum is unsupported

**Root Cause:**
- **Technical:** Error message string was not updated when aluminum was added to `VALID_PROCESS_TYPES`
- **Process:** No check that validation messages stay in sync with allowlists during feature expansion

**The Fix:**

```python
# ❌ BEFORE — omits aluminum from message
if process_type not in VALID_PROCESS_TYPES:
    raise HTTPException(
        status_code=422,
        detail=f"process_type must be one of: mig, tig, stick, flux_core (got: {body.process_type!r})",
    )

# ✅ AFTER — message matches allowlist
if process_type not in VALID_PROCESS_TYPES:
    raise HTTPException(
        status_code=422,
        detail=f"process_type must be one of: mig, tig, stick, flux_core, aluminum (got: {body.process_type!r})",
    )
```

**Prevention:**
- ✅ DO: When adding to allowlists/frozensets, update all related error messages and docstrings in the same commit
- ✅ DO: Derive error message from the allowlist when possible: `", ".join(sorted(VALID_PROCESS_TYPES))`
- ❌ DON'T: Add new valid values without grepping for hardcoded lists in error messages and docs
- [ ] Code review check: "Does this validation have an error message? Is it up to date with the allowlist?"

**AI Guidance:**
```
When adding new valid values to API enums/allowlists (e.g. process_type, weld_type):
"Update the HTTP 422 error message to include the new value. Update Pydantic Field descriptions. Search for hardcoded 'must be one of' strings. See LEARNING_LOG.md stale validation message entry."
```

**Warning Signs:**
- Allowlist (frozenset/set) has more values than the error message lists
- Docstring lists fewer options than the schema allows

**References:**
- `backend/routes/sessions.py` — `CreateSessionRequest`, `create_session`
- `VALID_PROCESS_TYPES`, `CreateSessionRequest.process_type`

---

### 📅 2026-03-21 — GZipMiddleware Buffers SSE Until minimum_size (1 KB)

**Category:** API / Streaming  
**Severity:** 🟡 High

**What Happened:**
The app used `GZipMiddleware` with `minimum_size=1000`. GZip accumulates response body bytes and only compresses/flushes once enough data exists. Each WarpSense SSE `data:` line is tiny (~80–100 bytes). The middleware held events 1–8 until the final `complete` event (large JSON report) pushed the buffer over 1 KB. The browser then received everything at once after ~15 s of apparent silence — looked like React batching or a broken stream, but the server had never flushed.

**Impact:**
- No live progressive UI for agent stages; report appeared only after full pipeline finished
- Misleading debugging (frontend yields, keepalives) while root cause was response compression

**Root Cause:**
- **Technical:** Starlette/FastAPI `GZipMiddleware` is inappropriate for streaming bodies that must flush per chunk unless explicitly bypassed.

**The Fix:**

```python
# On StreamingResponse for SSE — tell middleware not to compress this response
return StreamingResponse(
    analyse_session_stream(session_id, db),
    media_type="text/event-stream",
    headers={
        "X-Accel-Buffering": "no",
        "Cache-Control":     "no-cache",
        "Content-Encoding":  "identity",
    },
)
```

**Prevention:**
- ✅ DO: For `text/event-stream` / SSE, set `Content-Encoding: identity` (or exclude streaming routes from GZip) so bytes pass through immediately
- ✅ DO: When adding new streaming endpoints, grep for `GZipMiddleware` and verify they bypass compression
- ❌ DON'T: Assume small incremental writes from a generator reach the client immediately if global compression middleware is enabled

**AI Guidance:**
```
When implementing SSE or chunked streaming in FastAPI with GZipMiddleware:
"Set Content-Encoding: identity on the StreamingResponse (or disable gzip for that route). Otherwise events buffer until minimum_size. See LEARNING_LOG.md GZip SSE entry and backend/routes/warp_analysis.py run_analysis."
```

**References:**
- `backend/main.py` — `app.add_middleware(GZipMiddleware, minimum_size=1000)`
- `backend/routes/warp_analysis.py` — `POST .../analyse`, `StreamingResponse` headers

---

## ⚙️ Backend / Scoring (2026-02-26)

### 📅 2026-02-26 — Defect Score Penalty Uses Wrong Alert Count

**Category:** Backend / Scoring  
**Severity:** 🟢 Medium

**What Happened:**
`calculate_defect_alert_component` used `len(alerts)` for the score penalty (`1.0 - min(1.0, len(alerts) * 0.1)`), but drops non-`AlertPayload` items. Invalid items were still counted in the penalty, inflating the score reduction for alerts that never made it into excursions.

**Impact:**
- Over-penalization when alert list contains non-AlertPayload objects
- Inconsistent behavior between `passed` (based on valid alerts) and `score` (based on raw count)

**The Fix:**

```python
# ❌ BEFORE — counts dropped items in penalty
score_val = 0.0 if has_critical else (1.0 - min(1.0, len(alerts) * 0.1))

# ✅ AFTER — use valid alert count
valid_count = sum(by_rule.values())  # or len([a for a in alerts if isinstance(a, AlertPayload)])
score_val = 0.0 if has_critical else (1.0 - min(1.0, valid_count * 0.1))
```

**Prevention:**
- ✅ DO: When filtering input (e.g. dropping non-AlertPayload), use the filtered count for downstream calculations
- ❌ DON'T: Use raw `len(input_list)` for penalties when some items are excluded
- [ ] Code review: "Does this score/penalty use the same population as the pass/fail logic?"

**AI Guidance:**
```
When implementing component score calculations that filter input:
"Use the count of items that actually contributed to the result (e.g. sum(by_rule.values())) for score/penalty logic. Never use len(raw_input) when some items are dropped. See LEARNING_LOG.md defect score penalty."
```

---

### 📅 2026-02-26 — Scoring Config Weight Validation

**Category:** Backend / Config  
**Severity:** 🟢 Medium

**What Happened:**
`load_scoring_config` validated that required keys exist but did not validate that component weights sum to 1.0. A misconfigured JSON (e.g. typo changing 0.35 to 0.035) would produce incorrect `overall_score` without failing fast.

**Impact:**
- Silent wrong scores when weights don't sum to 1.0
- Debugging requires manual config audit

**The Fix:**

```python
# ✅ Add after key validation
total = sum(data[k] for k in (
    "arc_termination_weight", "heat_input_weight", "torch_angle_weight",
    "defect_alert_weight", "interpass_weight"))
if abs(total - 1.0) > 1e-6:
    raise ValueError(f"Component weights must sum to 1.0, got {total}")
```

**Prevention:**
- ✅ DO: Validate invariants (e.g. weights sum to 1.0) when loading configs that drive numeric aggregation
- ❌ DON'T: Assume config is correct; fail fast on load
- [ ] Code review: "Does this config have invariants? Are they validated?"

**AI Guidance:**
```
When loading configs that define weights used for weighted averages:
"Validate that weights sum to 1.0 (or expected total) with a small epsilon. Raise ValueError on load if invalid. See LEARNING_LOG.md scoring config weights."
```

---

### 📅 2026-02-26 — Backfill Script: Per-Item Error Handling

**Category:** Backend / Scripts  
**Severity:** ⚪ Low

**What Happened:**
`rescore_all_sessions.py` iterates over sessions and updates `score_total` in a single transaction. One failing session (e.g. corrupt frame data) would abort the whole run and leave partial updates; no per-session try/except.

**Prevention:**
- ✅ DO: Wrap per-item logic in try/except in backfill scripts; log failures and continue
- ✅ DO: Consider single commit at end vs per-item — trade-off between atomicity and partial progress
- ❌ DON'T: Let one bad record kill the entire backfill

**AI Guidance:**
```
When implementing backfill scripts that process many records:
"Wrap per-record logic in try/except; log and continue on failure. Decide: single commit (all-or-nothing) vs per-item commit (partial progress on error). See LEARNING_LOG.md backfill script."
```

---

## 🔧 Mock Data / Code Quality (2026-02-26)

### 📅 2026-02-26 — Pydantic v1/v2: hasattr vs try/except AttributeError

**Category:** Backend / Pydantic  
**Severity:** 🟢 Medium

**What Happened:**
`_with_termination(f, label)` used `try: f.model_copy(update={...}) except AttributeError: f.copy(...)` for Pydantic v1/v2 compatibility. The broad `except AttributeError` catches any attribute error on the frame object — including unrelated ones from future changes — and makes debugging hell. Silent failures become possible.

**Impact:**
- Unrelated AttributeError (e.g. typo, missing field) gets swallowed and wrong code path runs
- Debugging requires knowing the exact exception source

**The Fix:**

```python
# ❌ BEFORE — broad except swallows unrelated errors
try:
    return f.model_copy(update={"arc_termination_type": label})
except AttributeError:
    return f.copy(update={"arc_termination_type": label})

# ✅ AFTER — explicit check; no swallowed errors
if hasattr(f, "model_copy"):
    return f.model_copy(update={"arc_termination_type": label})
return f.copy(update={"arc_termination_type": label})
```

**Prevention:**
- ✅ DO: Use `hasattr(obj, "model_copy")` for Pydantic v1/v2 branching
- ❌ DON'T: Use `except AttributeError` for optional APIs — it hides bugs

**AI Guidance:** When implementing Pydantic model copy/update that must work on v1 and v2, use `hasattr` check. See `@.cursor/context/project-context.md` pattern "Pydantic v1/v2 Compatibility".

---

### 📅 2026-02-26 — Division-by-Zero: Defensive Guard at Function Boundary

**Category:** Backend  
**Severity:** ⚪ Low

**What Happened:**
`_step_thermal_state(..., travel_speed_mm_per_min)` could receive 0, causing division by zero in `speed_scale = AL_TRAVEL_SPEED_NOMINAL / travel_speed_mm_per_min`. Callers currently ensure positive values, but that may change.

**The Fix:**

```python
# ✅ Add at function top — one line, zero risk
def _step_thermal_state(..., travel_speed_mm_per_min: float = ...) -> ...:
    travel_speed_mm_per_min = max(travel_speed_mm_per_min, 1.0)
    ...
```

**Prevention:** Defensive guards belong at the function boundary, not at call sites. Callers may change; a one-line guard is zero risk.

---

### 📅 2026-02-26 — Magic Numbers: Extract to Constants Now

**Category:** Backend / Code Quality  
**Severity:** ⚪ Low

**What Happened:**
Expert travel speed used inline `400.0 + rng.gauss(0, 12.0)` and `380.0`, `420.0`. The next agent touching travel speed would use the inline number and create a third source of truth.

**The Fix:**

```python
# ❌ BEFORE — inline magic numbers
travel_speed_base = 400.0 + rng.gauss(0, 12.0)

# ✅ AFTER — constants block
AL_TRAVEL_SPEED_BASE_MEAN = 400.0
AL_TRAVEL_SPEED_BASE_SIGMA = 12.0
travel_speed_base = AL_TRAVEL_SPEED_BASE_MEAN + rng.gauss(0, AL_TRAVEL_SPEED_BASE_SIGMA)
```

**Prevention:** Extract to constants now, not later. Reason: next agent session touching the same logic will use inline numbers and create divergence.

---

### 📅 2026-02-26 — Docstring Contradicts Implementation

**Category:** Backend / Code Quality  
**Severity:** ⚪ Low

**What Happened:**
Expert mock docstring said "thermal snapshots emitted every 20 frames (200ms)" but implementation had `is_thermal_frame = True` (every frame). A docstring that contradicts the implementation is worse than no docstring — it will cause the next agent to "fix" the code to match the wrong docstring.

**Prevention:** Update docstrings immediately when behavior changes. Wrong doc causes "fix" that breaks code.

---

### 📅 2026-02-26 — Spacing/Style: Fix Immediately

**Category:** Code Quality  
**Severity:** ⚪ Low

**What Happened:**
Missing blank line before `def _percentile` in verify_aluminum_mock.py. Cosmetic issues left in signal to the next agent that style rules are optional, which compounds across sessions.

**Prevention:** Fix cosmetic issues (spacing, style) before closing the session, not as a follow-up ticket.

---

## 🔧 Backend / Data Parsing

### 📅 2026-02-26 — Thermal Data Dict KeyError — Use .get() for Optional Keys

**Category:** Backend / Data  
**Severity:** 🟢 Medium

**What Happened:**
`_ns_asymmetry_from_frame_data()` in alert_service.py used `r["temp_celsius"]` inside a generator for thermal readings. When a reading had `direction: "north"` but no `temp_celsius` key (malformed or partial frame data), the code raised `KeyError`.

**Impact:**
- Session alerts or report-summary could crash on bad thermal data
- Sensor dropout or schema drift could produce unexpected shapes

**The Fix:**

```python
# ❌ BEFORE — KeyError when temp_celsius missing
north = next(
    (r["temp_celsius"] for r in readings if r.get("direction") == "north"),
    None,
)

# ✅ AFTER — .get() returns None; existing None check handles it
north = next(
    (r.get("temp_celsius") for r in readings if r.get("direction") == "north"),
    None,
)
```

**Prevention:**
- ✅ DO: Use `.get("key")` when parsing dicts from JSON/ORM that may have optional or missing keys
- ❌ DON'T: Use `dict["key"]` for sensor/frame data without validation that the key exists
- [ ] Code review: "Does this parse external/ORM dict data? Use .get() for optional keys."

**AI Guidance:**
```
When parsing frame_data, thermal_snapshots, or other dict structures from DB/JSON:
"Use .get('key') for optional fields. Existing None checks (e.g. if north is None) handle missing keys. See LEARNING_LOG.md thermal dict KeyError."
```

---

## 📐 Frontend / React Rendering

### 📅 2026-02-26 — Array Mutation in Render — .sort() Mutates

**Category:** Frontend  
**Severity:** ⚪ Low

**What Happened:**
WelderReportPDF rendered `reportSummary.excursions.slice(0, 10).sort(...)`. `.sort()` mutates the array in place. `.slice()` returns a new array, so the mutation affected only the slice — but the pattern is fragile and non-obvious.

**The Fix:**

```tsx
// ❌ BEFORE — .sort() mutates the sliced array
{reportSummary.excursions.slice(0, 10).sort((a, b) => ...).map(...)}

// ✅ AFTER — explicit copy, sort, then slice
{[...reportSummary.excursions].sort((a, b) => ...).slice(0, 10).map(...)}
```

**Prevention:**
- ✅ DO: Use `[...arr].sort()` or `arr.slice().sort()` when you need sorted output without mutating the source
- ❌ DON'T: Call `.sort()` on arrays that may be shared or passed as props
- [ ] Code review: "Does this .sort()? Is the array copied first?"

**AI Guidance:**
```
When sorting arrays for display: "Use [...arr].sort() or arr.slice().sort() — never mutate props or shared arrays. See LEARNING_LOG.md array mutation."
```

---

### 📅 2026-02-26 — React List Keys — Duplicate Excursions

**Category:** Frontend  
**Severity:** ⚪ Low

**What Happened:**
ExcursionLogTable used `key={timestamp_ms}-${defect_type}-${i}`. Multiple excursions can share the same timestamp and defect_type (e.g. two alerts at same frame); index `i` keeps keys unique but is not stable if list order changes.

**The Fix:**
Include additional unique fields: `key={\`${timestamp_ms}-${defect_type}-${parameter_value ?? ""}-${notes ?? ""}-${i}\`}` so duplicates with different values are distinguishable.

**Prevention:**
- ✅ DO: When list items can have duplicate primary fields, include secondary fields or a stable id in the key
- ❌ DON'T: Rely on index alone when items can be reordered or filtered
- [ ] Code review: "Can two items have the same (timestamp, type)? Is the key sufficiently unique?"

---

### 📅 2026-03-21 — onComplete + session key — React 18 batch unmounts before report paints

**Category:** Frontend / React  
**Severity:** 🟡 High

**What Happened:**
`AnalysisTimeline` called `setReport`, `setPhase("done")`, and `onComplete(report)` synchronously when the SSE `complete` event arrived. The parent’s `onComplete` (Analyse All) called `startStream(nextSessionId)`, updating `sessionId`. `AnalysisTimeline` was rendered with `key={sessionId}`. React 18 batched the child state updates and the parent update into one render; the key changed, so React destroyed the timeline instance before the user ever saw the report for the finished session.

**Impact:**
- Last item in Analyse All (or any flow that advances immediately) showed no final report flash
- Appeared as “skipped” or broken queue behaviour

**Root Cause:**
- **Technical:** Same render commit: timeline transitions to “done” and parent replaces `sessionId` → new component instance
- **Process:** Parent callbacks that change identity (`key`) must not run in the same synchronous turn as “show result” state

**The Fix:**

```tsx
// ❌ BEFORE — in SSE loop on complete
setReport(event.report);
setPhase("done");
onCompleteRef.current?.(event.report); // parent changes key → unmount

// ✅ AFTER — report commits first; onComplete deferred
setReport(event.report);
setPhase("done");
// useEffect when phase === "done" && report:
//   setTimeout(() => onCompleteRef.current?.(report), 800)
// cleanup: clearTimeout
```

**Prevention:**
- ✅ DO: Defer parent notifications that remount or change `key` until after the user-visible state has committed (e.g. `useEffect` + short `setTimeout`, or `queueMicrotask`/`requestAnimationFrame` if sufficient)
- ✅ DO: Reset any “fired once” ref when `sessionId` / `streamTrigger` restarts the stream
- ❌ DON'T: Call parent queue-advance callbacks inline in the same handler that sets “show result” UI when the parent passes a changing `key`

**AI Guidance:**
```
When a child finishes async work and the parent advances queue / changes key:
"Do not call onComplete synchronously with setState that shows the result. Defer onComplete (useEffect + setTimeout) so the report renders first. See LEARNING_LOG.md AnalysisTimeline onComplete batching."
```

**References:**
- `my-app/src/components/analysis/AnalysisTimeline.tsx` — deferred `onComplete`, `onCompleteFiredRef`
- `my-app/src/app/(app)/analysis/page.tsx` — `key={viewState.sessionId}`, `handleStreamComplete`

---

## ⚡ Backend / Performance

### 📅 2026-02-26 — Config File Repeated Reads — Cache Per Process

**Category:** Backend / Performance  
**Severity:** ⚪ Low

**What Happened:**
`_load_report_thresholds()` in report_summary.py read `report_thresholds.json` on every `compute_report_summary()` call. Under load, repeated file I/O adds overhead.

**The Fix:**

```python
# ❌ BEFORE — read file every call
def _load_report_thresholds() -> dict:
    path = backend / "config" / "report_thresholds.json"
    return json.loads(path.read_text())

# ✅ AFTER — module-level cache
_REPORT_THRESHOLDS_CACHE: dict | None = None

def _load_report_thresholds() -> dict:
    global _REPORT_THRESHOLDS_CACHE
    if _REPORT_THRESHOLDS_CACHE is not None:
        return _REPORT_THRESHOLDS_CACHE
    path = backend / "config" / "report_thresholds.json"
    _REPORT_THRESHOLDS_CACHE = json.loads(path.read_text())
    return _REPORT_THRESHOLDS_CACHE
```

**Prevention:**
- ✅ DO: Cache loaded JSON config at module level when it's read on every request
- ❌ DON'T: Read static config files in hot paths without caching
- [ ] Code review: "Is this config read per-request? Add cache if so."

**AI Guidance:**
```
When loading static config (JSON, YAML) that is called frequently (e.g. per API request):
"Cache at module level. Config changes require process restart — acceptable for deploy-time config. See LEARNING_LOG.md config cache."
```

---

## ⚡ Backend / Alerts

### 📅 2026-02-26 — Defect Alert Hardcoded Config in Messages

**Category:** Backend / Alerts  
**Severity:** 🟢 Medium

**What Happened:**
Alert messages for arc instability ("voltage < 19.5V sustained") and lack of fusion ("Increase current to 140+ A", "Reduce speed below 520 mm/min") used hardcoded values. Config threshold keys (`voltage_lo_V`, `lack_of_fusion_amps_max`, etc.) were validated and used for rule logic, but messages displayed static numbers.

**Impact:**
- When someone changes `voltage_lo_V` in config for a different material or WPS, the alert fires at the new threshold but tells the welder or QA report the wrong number
- Diagnostic trust problem: auditor reads "voltage < 19.5V" while actual threshold is 18V

**Root Cause:**
- Copy-paste of nominal values into message strings
- No pattern enforcing "config drives both logic and display"

**The Fix:**

```python
# ❌ BEFORE — hardcoded; wrong when config changes
message="Arc instability: voltage < 19.5V sustained",
correction="Increase current to 140+ A",

# ✅ AFTER — interpolate from config
message=f"Arc instability: voltage < {self._cfg['voltage_lo_V']}V sustained",
correction=f"Increase current to {self._cfg['lack_of_fusion_amps_max']}+ A",
```

**Prevention:**
- ✅ DO: Interpolate config values into any user-facing or logged message that mentions thresholds
- ✅ DO: Grep for numeric literals in alert messages when adding new rules
- ❌ DON'T: Hardcode threshold values in messages, corrections, or logs when config defines them
- [ ] Code review check: "Does this alert message mention a threshold? Is it from config?"

**AI Guidance:**
```
When implementing alert rules with threshold-based messages:
"Use f-strings with self._cfg['threshold_key'] for any message or correction that displays a threshold value. Never hardcode 19.5, 140, 520, etc. when those come from config. See LEARNING_LOG.md defect alert hardcoded values."
```

---

### 📅 2026-02-26 — Crater Buffer Not Reset on amps=None

**Category:** Backend / Alerts  
**Severity:** 🟢 Medium

**What Happened:**
When `frame.amps` is `None` (sensor dropout), the crater crack rule skipped evaluation but did not reset `CurrentRampDownBuffer`. The buffer retained arc-on history from before the dropout. If amps later returned as 0 (e.g. at bead end), the rule could fire "crater crack" using stale history — a false positive.

**Impact:**
- False crater_crack alerts when sensor briefly drops then returns 0
- QA auditor sees incorrect defect in alert log

**Root Cause:**
- Design assumed "skip when None" was sufficient
- Buffer state was not invalidated on data gap

**The Fix:**

```python
# ❌ BEFORE — buffer keeps stale history; false positive on dropout → 0
if frame.amps is None:
    if not self._warned_amps_missing_crater:
        logger.warning(...)
    ...
else:
    abrupt = self._crater_buffer.push(...)

# ✅ AFTER — reset clears history; no false positive after gap
if frame.amps is None:
    self._crater_buffer.reset()
    if not self._warned_amps_missing_crater:
        logger.warning(...)
    ...
else:
    abrupt = self._crater_buffer.push(...)
```

**Prevention:**
- ✅ DO: Reset stateful buffers when required sensor data is None
- ✅ DO: Add unit test: arc-on → amps=None for N frames → amps=0 should NOT fire crater_crack
- ❌ DON'T: Assume "skip" is enough — stale state can still produce wrong result on next valid frame
- [ ] Code review check: "If this rule needs X and X is None, does the buffer reset?"

**AI Guidance:**
```
When implementing rules with time-based buffers (voltage sustain, current ramp-down):
"If the rule requires volts/amps and the frame has None, call buffer.reset() before skipping. Documented wrong behavior is still wrong when a QA auditor reads the alert log. See LEARNING_LOG.md crater buffer reset."
```

---

### 📅 2026-02-26 — Python 3.8 deque Type Annotation

**Category:** Backend  
**Severity:** ⚪ Low

**What Happened:**
`deque[tuple[float, float]]` as a runtime type annotation fails on Python 3.8. The `deque[...]` generic syntax requires Python 3.9+. The plan explicitly targets Python 3.8 compatibility.

**The Fix:**

```python
# ❌ BEFORE — breaks on 3.8
from collections import deque
self._samples: deque[tuple[float, float]] = deque()

# ✅ AFTER — typing module for 3.8
from typing import Deque, Tuple
self._samples: Deque[Tuple[float, float]] = deque()
```

**Prevention:**
- ✅ DO: Use `Deque`, `Tuple`, `List` from `typing` when targeting Python 3.8
- ❌ DON'T: Use `deque[...]`, `tuple[...]` as runtime annotations on 3.8
- [ ] Check `python_requires` or plan constraints before using 3.9+ generic syntax

---

## 📊 Backend / Architecture

### 📅 2026-02-23 — API Docs, Logs, and Imports Drift

**Category:** Backend  
**Severity:** 🟢 Medium

**What Happened:**
During aluminum threshold code review, three drift issues were found:
1. **Unused import:** `get_previous_frame` imported in `sessions.py` but never used
2. **Outdated docstring:** `CreateSessionRequest.process_type` said "mig|tig|stick|flux_core" but `aluminum` is valid
3. **Misleading log:** `threshold_service` logged "scoring will use MIG" when missing aluminum row, but the code raises `ValueError` — scoring never runs

**Impact:**
- Unused imports add noise, can mask missing usage or dead code
- Wrong docstrings mislead API consumers and AI tools
- Logs that describe non-existent behavior frustrate debugging

**Root Cause:**
- **Process:** Adding `aluminum` touched multiple files; docstrings and logs were not updated in lockstep
- **Technical:** Log message was copy-pasted from a prior design (fallback-to-MIG) before the fail-fast behavior was implemented

**The Fix:**

```python
# ❌ BEFORE — unused import
from services.thermal_service import calculate_heat_dissipation, get_previous_frame

# ✅ AFTER
from services.thermal_service import calculate_heat_dissipation
```

```python
# ❌ BEFORE — docstring omits aluminum
description="Process type: mig|tig|stick|flux_core. Default mig."

# ✅ AFTER
description="Process type: mig|tig|stick|flux_core|aluminum. Default mig."
```

```python
# ❌ BEFORE — log implies fallback; we actually raise
log.error(
    "weld_thresholds missing row for process_type=%r; scoring will use MIG. "
    "Add row or run migration seed.", key
)

# ✅ AFTER — matches behavior
log.error(
    "weld_thresholds missing row for process_type=%r. Add row or run migration.",
    key,
)
```

**Prevention:**
- ✅ DO: When changing behavior (fail-fast vs fallback), update logs to match
- ✅ DO: When extending enums/allowlists, grep for docstrings and error messages
- ✅ DO: Run "unused import" linters (ruff F401, pyflakes) in CI
- ❌ DON'T: Leave log messages that describe old or alternative code paths
- [ ] Code review check: "Do docstrings and logs reflect the actual behavior?"

**AI Guidance:**
```
When extending APIs or changing control flow:
"Update docstrings, error messages, and log messages in the same change. Remove unused imports. Logs must describe what the code actually does, not a prior design. See LEARNING_LOG.md API docs drift entry."
```

**References:**
- `backend/routes/sessions.py` — imports, CreateSessionRequest
- `backend/services/threshold_service.py` — get_thresholds log

---

### 📅 2026-02-23 — random.Random(seed) for Deterministic Mock Data

**Category:** Backend / Data  
**Severity:** 🟢 Medium

**What Happened:**
Aluminum stitch mock generators used `random.seed(session_index * 42)` and `random.gauss()` to produce deterministic frames. Sessions were supposed to be reproducible (same seed → same frames) for verification, seeding, and comparison.

**Impact:**
- Python's `random` module has one global RNG shared across the whole process
- `random.seed()` resets that global generator — it affects everyone, not just your function
- If Thread B (or any other code) calls `random.seed()` or `random.random()` between your seed and your draws, your sequence is disrupted
- Result: sessions drift, verification assertions become flaky, DB seed vs browser comparison may disagree

**Root Cause:**
- Assumed `random.seed()` was scoped to the generator function; it is not
- Single-threaded tests passed locally; parallel or interleaved usage would fail

**The Fix:**

```
# ❌ BEFORE — poisons global state; breaks when other code uses random
def _generate_stitch_expert_frames(session_index, num_frames=1500):
    random.seed(session_index * 42)
    ...
    angle += random.gauss(0, 1.2)

# ✅ AFTER — isolated instance; never touches global state
def _generate_stitch_expert_frames(session_index, num_frames=1500):
    rng = random.Random(session_index * 42)
    ...
    angle += rng.gauss(0, 1.2)
```

**Prevention:**
- ✅ DO: Use `rng = random.Random(seed)` for any deterministic mock/fixture generator
- ✅ DO: Call `rng.gauss()`, `rng.uniform()`, etc. — never the global `random.*` after seeding
- ❌ DON'T: Use `random.seed()` when you need reproducibility that survives parallel or interleaved calls
- ❌ DON'T: Assume single-threaded dev is sufficient — tests or production may run generators concurrently

**AI Guidance:**
```
When implementing deterministic mock data generators (welding sessions, frames, thermal state):
"Use random.Random(seed) and call rng.gauss(), rng.uniform(), etc. on that instance. Never use random.seed() — it mutates global state and breaks reproducibility. See LEARNING_LOG.md random.Random entry."
```

**References:**
- `backend/data/mock_sessions.py` — `_generate_stitch_expert_frames`, `_generate_continuous_novice_frames`

---

### 📅 2025-02-17 — WWAD Macro-Analytics (Supervisor Dashboard)

**Category:** Backend / Architecture  
**Severity:** 🟢 Medium

**What Was Done:**
Implemented supervisor-level macro analytics (WWAD) orthogonally to the MVP. New aggregate API (`/api/sessions/aggregate`), KPI tiles, trend chart, calendar heatmap, and CSV export. Session-level aggregation only — no frame data or 3D coupling.

**Impact:**
- Supervisors see team KPIs, trends, and activity at a glance
- Fully decoupled from TorchViz3D, HeatmapPlate3D, micro-feedback logic
- Adding/changing macro features does not touch replay or scoring

**Root Cause (Design Decision):**
- MVP dashboard was tightly coupled to frame-level + 3D visualization
- Macro analytics needed team/line/shift trends without reworking micro-feedback

**Patterns:**

```python
# ❌ BEFORE — macro features would touch frame-level or 3D
# Any change to scoring or visualization could break dashboard

# ✅ AFTER — orthogonal design
# Aggregate API: session → score + metrics → trend/KPI dashboard
# No per-frame data, no WebGL, no micro-feedback dependency
```

**Database pattern:**

```sql
-- ✅ DO: Add nullable + default, backfill separately
ALTER TABLE sessions ADD COLUMN score_total NUMERIC DEFAULT NULL;
-- Run backfill script; then optionally add NOT NULL + constraint
```

**Prevention:**
- ✅ DO: Keep macro analytics on session-level aggregation only
- ✅ DO: Use nullable + backfill for new columns on existing tables
- ✅ DO: Log truncation and export failures; handle empty/null edge cases
- ❌ DON'T: Couple supervisor dashboards to frame-level or 3D components
- ❌ DON'T: Add NOT NULL to new columns without backfill path

**AI Guidance:**
```
When adding macro/aggregate features:
"Use session-level data only. Do not depend on frame extraction, 3D components, or micro-feedback. New columns: add nullable first, backfill, then optionally constrain. See LEARNING_LOG.md WWAD entry."
```

**References:**
- `backend/services/aggregate_service.py`, `backend/routes/aggregate.py`
- `my-app/src/app/(app)/supervisor/page.tsx`
- `backend/scripts/backfill_score_total.py`, `backend/alembic/versions/003_add_score_total.py`

---

### 📅 2025-02-18 — Warp Prediction ML (Batch 1)

**Category:** Backend / ML  
**Severity:** 🟢 Medium

**What Was Done:**
Implemented warp risk prediction for welding sessions: training pipeline (generate_training_data, train_warp_model), ONNX inference in `prediction_service`, `GET /api/sessions/{session_id}/warp-risk` endpoint, WarpRiskGauge on replay page.

**Impact:**
- Predicts thermal asymmetry breach from rolling 50-frame window
- Degrades gracefully when `warp_model.onnx` missing — returns `model_available: false`
- Replay page shows semicircle gauge (ok / warning / critical)

**Patterns:**

```python
# ✅ DO: Single shared feature module for train + inference (no drift)
# backend/features/warp_features.py: extract_asymmetry, extract_features, features_to_array
# Used by: generate_training_data.py, train_warp_model.py, prediction_service.py

# ✅ DO: Degraded mode when model absent
sess = _get_session()
if sess is None:
    return {"probability": 0.0, "risk_level": RiskLevel.OK, "model_available": False}
```

**Prevention:**
- ✅ DO: Use `backend/features/warp_features.py` for both training and inference — FEATURE_COLS order must match ONNX input
- ✅ DO: Return `model_available: false` when ONNX file absent; never crash
- ✅ DO: Add `get_session_frames_raw` to sessions.py for prediction route reuse
- ❌ DON'T: Duplicate feature extraction logic in training vs service
- ❌ DON'T: Touch main.py or api.ts directly when using _merge/ files for multi-agent coordination

**AI Guidance:**
```
When implementing warp/ML prediction features:
"Use warp_features.py for feature extraction in both training and inference. Degrade gracefully when ONNX missing. See backend/services/prediction_service.py, backend/routes/predictions.py. Training: backend/scripts/generate_training_data, train_warp_model."
```

**Verification:**
```bash
# 1. Training pipeline (from project root)
python -m backend.scripts.generate_training_data --output data/training_data.csv
python -m backend.scripts.train_warp_model --input data/training_data.csv --output backend/models/warp_model.onnx

# 2. Backend (seed first if empty)
curl -s http://localhost:8000/api/sessions/sess_novice_001/warp-risk | jq .
# Degraded: rm backend/models/warp_model.onnx and restart → model_available: false

# 3. Frontend
cd my-app && npm run build
npm test -- --testPathPattern="WarpRiskGauge|replay" --watchAll=false
```

**References:**
- `backend/features/warp_features.py`, `backend/services/prediction_service.py`
- `backend/routes/predictions.py`, `backend/routes/sessions.py` (get_session_frames_raw)
- `my-app/src/components/welding/WarpRiskGauge.tsx`, `my-app/src/app/replay/[sessionId]/page.tsx`
- `_merge/agent2_main.py`, `_merge/agent2_api.ts`

---

## 🧪 Testing

### 📅 2026-03-02 — document.querySelector vs Testing Library

**Category:** Testing  
**Severity:** ⚪ Low

**What Happened:**
Dashboard test used `document.querySelector('[data-score-tier="good"]')` to assert badge styling. Bypasses Testing Library's scoping and user-centric queries; couples to implementation details.

**The Fix:**

```tsx
// ❌ BEFORE — document API, no scoping
const badge = document.querySelector('[data-score-tier="good"]');
expect(badge).toBeInTheDocument();

// ✅ AFTER — within + getByText + toHaveAttribute
const mikeCard = screen.getByRole("heading", { name: /Mike Chen/ })
  .closest("[class*='rounded-xl']") as HTMLElement | null;
expect(mikeCard).toBeInTheDocument();
const badge = within(mikeCard!).getByText("85/100");
expect(badge).toHaveAttribute("data-score-tier", "good");
```

**Prevention:**
- ✅ DO: Use `within(container).getByText()` and `toHaveAttribute` for data attributes
- ❌ DON'T: Use `document.querySelector` in React tests — prefer Testing Library queries

---

### 📅 2026-03-02 — Dead Mocks (useRouter When Page Doesn't Use It)

**Category:** Testing  
**Severity:** ⚪ Low

**What Happened:**
Dashboard test had `jest.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }))` and `mockPush` but the DashboardPage never calls `useRouter`. Dead code clutters tests and suggests behavior that doesn't exist.

**The Fix:**
Remove unused `jest.mock("next/navigation", ...)` and `mockPush`. Only mock what the component actually uses.

**Prevention:**
- ✅ DO: Mock only APIs the component under test uses
- ❌ DON'T: Copy mocks from other tests without verifying the component imports them

---

### 📅 2026-02-26 — caplog.messages for Log Assertions

**Category:** Testing  
**Severity:** ⚪ Low

**What Happened:**
Test used `r.message` on `caplog.records` to assert exactly one warning. `LogRecord.message` is not always populated (depends on formatting/handler). Can be fragile across pytest versions or log config.

**The Fix:**

```python
# ❌ BEFORE — LogRecord.message may be unset
warns = [r for r in caplog.records if "arc_instability" in r.message and "volts" in r.message]

# ✅ AFTER — caplog.messages gives formatted strings directly
warns = [m for m in caplog.messages if "arc_instability" in m and "volts" in m]
```

**Prevention:**
- ✅ DO: Use `caplog.messages` when asserting on log content — sidesteps LogRecord internals
- ❌ DON'T: Rely on `r.message` for log assertions unless pytest/caplog guarantees it

---

## 📋 Lessons & Reflections

> **Scope:** WebGL context loss hardening, Docker one-click deploy, premium landing page, demo page refactor, WWAD macro-analytics.  
> **Date:** 2025-02-17

### What Worked Well

1. **Orthogonal macro analytics (WWAD)** — Supervisor dashboard built on session aggregation only; zero coupling to frame-level data, 3D components, or micro-feedback. New features (KPIs, heatmap, export) added without touching replay or scoring. Migration used nullable `score_total` + separate backfill script.

2. **Layered WebGL mitigation** — Documentation (WEBGL_CONTEXT_LOSS.md) → code (overlay, handlers) → tests (instance count) → ESLint (max-torchviz rule). Each layer catches different failure modes. AI tools can reference one source.

3. **Route groups for layout separation** — `(marketing)` vs `(app)` eliminated conditional `isLanding` logic in AppNav. Layout structure controls nav visibility; no branching in components.

4. **One-click deploy script with fail-fast checks** — Port pre-check, Docker V1/V2 resolution, per-service health wait, secure `.env` (umask 077, openssl rand). Script exits early with clear messages instead of cryptic Docker errors.

5. **Idempotent seed script** — `seed_demo_data.py` can run multiple times; "already present" handling avoids deploy failures on re-run. Kept seed in deploy.sh exec (not backend entrypoint) so backend CMD stays simple.

6. **Proxy-based Framer Motion mock** — Jest tests need to filter `style` prop (MotionValues are invalid in DOM). Proxy mock that strips/filters `style` enables testing animated components without DOM errors.

7. **Backwards compatibility via re-exports** — Keeping `/landing` as re-export of `(marketing)/page` avoided breaking existing links while canonical route moved to `/`.

### What Didn't Work or Was Challenging

1. **Six TorchViz3D instances** — Initial demo layout exhausted WebGL context limit. No prior check for browser limits when designing multi-instance 3D layouts. Recovery required layout redesign + overlay + tests.

2. **Remote deployment requires rebuild** — `NEXT_PUBLIC_API_URL` is build-time in Next.js. Changing server IP means rebuild + redeploy. API proxy (Phase 1) was deferred; current approach works for localhost and single-server trials only.

3. **Seeding failure is non-fatal** — If seed fails (schema/import issue), deploy continues. Demo pages may show empty data. No automated verification that `sess_expert_001` exists; manual curl check required.

4. **Safari transform glitches** — Grid/parallax effects caused visual glitches. Required `perspective` on parent, `rotateX` on child workaround. Cross-browser 3D/CSS testing is essential.

5. **Framer Motion + Jest** — MotionValues in `style` prop fail when passed to DOM in tests. Required custom mock; not obvious until tests failed.

### Patterns to Reuse

1. **Orthogonal macro analytics** — Build supervisor/management dashboards on session-level aggregation only. No frame data, no 3D, no micro-feedback. New columns: nullable + backfill, then optionally constrain.

2. **3D/WebGL page pattern** — Limit 1–2 Canvas per page; add `webglcontextlost` handlers + overlay; use `dynamic(..., { ssr: false, loading })`; enforce with ESLint.

3. **Deploy script pattern** — Prerequisite checks (ports, Docker) → generate secrets → build → up → health wait → optional seed. Use `$COMPOSE` for V1/V2 compatibility.

4. **Env fallback with trim** — `process.env.X?.trim() || '/fallback'` handles empty string (common when env var is set but empty). Prefer explicit fallbacks over undefined.

5. **Route group layout pattern** — One layout per route group; no conditional "if marketing, hide nav" inside components. Layout composition at route level.

### Gotchas & Edge Cases

- **HMR + context lost** — Expected during dev; R3F calls `forceContextLoss()` on unmount. Don't file as bug; add to onboarding.
- **Empty env string** — `NEXT_PUBLIC_X=""` yields `""` not `undefined`. Use `.trim()` before fallback.
- **Docker healthcheck deps** — Alpine has no curl/wget. Use `python -c "urllib.request.urlopen(...)"` or `node -e "require('http').get(...)"` for health checks.
- **Safari stacking/transform** — Overlay needed `isolate` and `z-[100]` to beat parent stacking contexts. Test overlay visibility in Safari.

### Process Improvements for Next Time

- [ ] **Pre-3D work:** Check LEARNING_LOG.md and WEBGL_CONTEXT_LOSS.md before adding Canvas components.
- [ ] **Deploy validation:** Run `./deploy.sh` on clean Linux host (e.g. DigitalOcean droplet) before considering deploy "done".
- [ ] **Seed verification:** Add deploy.sh poll for `sess_expert_001`; fail deploy if missing after ~50s.
- [ ] **Cross-browser checklist:** Chrome, Firefox, Safari for any 3D/CSS transform work.

### Technical Insights

- Browsers limit ~8–16 WebGL contexts per tab; each R3F `<Canvas>` = 1 context.
- `NEXT_PUBLIC_*` in Next.js are inlined at build time; no runtime override without rebuild.
- Docker Compose V2 uses `docker compose` (plugin); V1 uses `docker-compose` (standalone). Resolve and use `$COMPOSE` throughout scripts.
- ESLint custom rules can enforce domain constraints (e.g. max instances per page) and fail CI.

### Mistakes & How to Avoid

| Mistake | Avoidance |
|---------|-----------|
| Assumed 6 Canvases would work | Count Canvas/3D instances before designing layout; check browser limits. |
| No context-loss handling | Always add `webglcontextlost` listener and user-facing overlay. |
| Env fallback without trim | Use `.trim()` so empty string triggers fallback. |
| Healthcheck with missing deps | Use runtime-available tools (python urllib, node http) not curl/wget. |
| Seed in entrypoint vs script | Prefer deploy.sh exec for clarity; add verification step if demo data is critical. |
| Stale validation error message | When adding to allowlists, grep for "must be one of" and update message. |
| Defect score penalty on raw list | Use filtered/valid count for penalties when input is filtered. |
| Config weights not validated | Validate weight sum on load when used for weighted averages. |
| Logs/docstrings describe old behavior | Update logs and docstrings in same commit as behavior change. |
| Hardcoding thresholds in alert messages | Use `self._cfg['key']` in f-strings; config drives both logic and display. |
| Not resetting buffer on sensor dropout | Call `buffer.reset()` when required field is None to avoid false positives. |
| Thermal dict KeyError on temp_celsius | Use `.get("temp_celsius")` when parsing readings from frame_data. |
| Array .sort() in render | Use `[...arr].sort()` to avoid mutating source. |
| Config read every request | Cache at module level for static config. |

### Additional Insights (WebGL / Demo / Tooling)

- **Incident → Doc → Automation** — When something breaks: root-cause in a doc, add fix examples, add tests + lint enforcement. Don't stop at "fixed in code."
- **Single source of truth** — `src/constants/webgl.ts` exports `MAX_TORCHVIZ3D_PER_PAGE`; ESLint and tests reference it. `src/constants/welding3d.ts` exports Y-coordinates for workpiece/ring/grid/shadows; all 3D metal geometry uses it. Change in one place.
- **Demo vs replay contracts** — Demo uses in-memory `Session`; replay fetches from API. Both must produce frames compatible with `extractHeatmapData`, `extractAngleData`, `getFrameAtTimestamp`.
- **ESLint rule scope** — Rule must exclude `__tests__` and `/app/dev/`. Windows paths need `replace(/\\/g, '/')`. Aliased imports (`<T />`) not detected.
- **1024×1024 shadow maps** — Reduces GPU memory pressure vs 2048×2048. Use `@react-three/scissor` for >2 views (one Canvas, scissor regions).
- **Dev-only overlay test** — Add `/dev/context-loss-test` that toggles `setContextLost(true)` for 2s; no need to exhaust contexts for QA.

---

## Maintenance

**Daily:** Add entries when fixing bugs (5 min)  
**Weekly:** Review with team, update .cursorrules  
**Monthly:** Analyze trends, update checklist

---

## Related Docs

| File | Purpose |
|------|---------|
| `.cursor/context/project-context.md` | What exists, patterns |
| `.cursorrules` | AI configuration |
| `README.md` | Project setup |

---

**Remember:** Every mistake documented is future productivity gained. Start small, be consistent. 🚀
