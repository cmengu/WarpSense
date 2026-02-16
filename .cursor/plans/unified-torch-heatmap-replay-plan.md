# Unified Torch + 3D Heatmap on Metal — Implementation Plan

**Task:** Replace the separate 3D heatmap with an integrated 3D heatmap on the metal workpiece in all replay sessions. Improve color sensitivity to show 5–10°C variations (0–500°C range). Show heat traveling through the metal over time.

**Date:** 2025-02-16  
**Prerequisites:** Existing `TorchViz3D`, `HeatmapPlate3D`, thermal interpolation, shaders.  
**References:** `documentation/WEBGL_CONTEXT_LOSS.md`, `my-app/src/constants/webgl.ts`, `.cursor/plans/3d-warped-heatmap-plate-implementation-plan.md`

---

## Executive Summary

| Current State | Target State |
|---------------|--------------|
| TorchViz3D (torch + flat metal) **separate from** HeatmapPlate3D (warped thermal plate) | **Single component**: Torch + thermally-colored metal workpiece in one Canvas |
| 3 Canvases: 2 TorchViz3D + 1 HeatmapPlate3D | 2 Canvases: 2 unified components (replay comparison) |
| Color scale 0–600°C linear → ~50°C per visible step | 0–500°C with **~5–10°C per visible color change** |
| Heatmap in separate grid cell below torch | Heatmap **on the workpiece** under the torch |

---

## Phase 1: Color Sensitivity — 5–10°C Visible Variations

**Goal:** Make temperature differences of 5–10°C clearly distinguishable in the 0–500°C range.

**Time estimate:** 2–3 hours

### Step 1.1: Design Fine-Grained Color Scale

**Problem:** Current fragment shader maps `temp / uMaxTemp` to 4 broad bands (0–0.2, 0.2–0.5, 0.5–0.8, 0.8–1.0). With maxTemp=600, 10°C = 1.67% of scale → nearly invisible.

**Approach:** Use a dense multi-stop gradient with 50 stops (0, 10, 20, …, 500°C) so each 10°C maps to a distinct color step. Use `uMinTemp` and `uMaxTemp` uniforms for flexible range.

**Dependencies:** None.

**Implementation:**

1. Add uniforms:
   - `uMinTemp` (default 0)
   - `uMaxTemp` (default 500)
   - `uStepCelsius` (default 10) — degrees per visible step; drives NUM_STEPS in shader

2. In fragment shader, compute normalized position:
   ```glsl
   float t = clamp((vTemperature - uMinTemp) / (uMaxTemp - uMinTemp), 0.0, 1.0);
   ```
   Compute step count: `NUM_STEPS = (uMaxTemp - uMinTemp) / uStepCelsius` (e.g. 50 for 10°C, 100 for 5°C).

3. Use stepped gradient: `stepIndex = clamp(floor(t * NUM_STEPS), 0, NUM_STEPS - 1)`.

**Verification:**

The temperature→color logic lives in **GLSL** (`heatmapFragment.glsl.ts`), not in `thermalInterpolation.ts` (which only does grid interpolation). To enable unit tests:

- **Extract a TS mirror:** Add `temperatureToColor(minTemp, maxTemp, stepCelsius, temp): [r,g,b]` in `my-app/src/utils/heatmapShaderUtils.ts` that implements the **exact same algorithm** as the GLSL (anchor positions, segment lookup, mix). Use this solely for tests and documentation; the shader remains the runtime source of truth.
- **Unit test:** In `my-app/src/__tests__/utils/heatmapShaderUtils.test.ts`: invoke `temperatureToColor(0, 500, 10, 100)` and `temperatureToColor(0, 500, 10, 110)`; assert per-channel RGB difference > 0.06 (≈15/255). Colors are in **0–1**.
- **Alternative (if TS mirror is skipped):** Document verification as **visual-only**: render a gradient strip 0–500°C in 10° steps; each step must be visibly different. No Jest unit test for color logic.

**Error handling:**
- If `uMaxTemp <= uMinTemp`, clamp to `[uMinTemp, uMinTemp + 1]` to avoid div-by-zero.
- `vTemperature` can be NaN from missing texture; clamp before use.

---

### Step 1.2: Implement Stepped Gradient in Fragment Shader

**File:** `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts`

**Changes:**
1. Add uniforms: `uMinTemp`, `uMaxTemp`, `uStepCelsius`.
2. Derive `NUM_STEPS` from uniforms: `NUM_STEPS = (uMaxTemp - uMinTemp) / uStepCelsius` (use `max(1.0, ...)` to avoid div-by-zero).
3. Implement stepped interpolation with concrete anchor colors. Map `stepIndex` (0 to NUM_STEPS-1) to color via anchor lookup and linear mix between adjacent anchors.

**Anchor colors (concrete vec3 values):**
Map normalized step value (0.0 → 1.0) through these 8 anchors. Use `mix()` between consecutive anchors:

| Step (normalized) | Temperature band | vec3 RGB |
|-------------------|------------------|----------|
| 0.0 | 0°C | `vec3(0.05, 0.05, 0.35)` — dark blue |
| 0.1 | 50°C | `vec3(0.0, 0.5, 0.9)` — cyan |
| 0.2 | 100°C | `vec3(0.0, 0.75, 0.7)` — teal |
| 0.3 | 150°C | `vec3(0.2, 0.85, 0.4)` — green |
| 0.5 | 250°C | `vec3(0.95, 0.95, 0.2)` — lime/yellow |
| 0.7 | 350°C | `vec3(1.0, 0.65, 0.1)` — orange |
| 0.9 | 450°C | `vec3(1.0, 0.3, 0.05)` — red |
| 1.0 | 500°C | `vec3(1.0, 0.15, 0.0)` — bright red |

**Anchor-to-segment lookup algorithm:**

Anchors are at non-uniform positions: `[0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]`. Given `stepNorm` (0..1), find the segment and mix factor:

```glsl
// Anchors (normalized position, then vec3 color)
// Segment i spans [anchor[i], anchor[i+1]]
#define N_ANCHORS 8
float anchorPos[N_ANCHORS] = float[8](0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0);

// Find segment index: largest i such that anchorPos[i] <= stepNorm
int segIdx = 0;
for (int i = 0; i < N_ANCHORS - 1; i++) {
  if (stepNorm >= anchorPos[i]) segIdx = i;
}
segIdx = min(segIdx, N_ANCHORS - 2);  // clamp to valid segment

float low = anchorPos[segIdx];
float high = anchorPos[segIdx + 1];
float mixFactor = (high - low) < 0.001 ? 1.0 : (stepNorm - low) / (high - low);
// mixFactor is 0..1 within segment; use mix(color[segIdx], color[segIdx+1], mixFactor)
```

**Pseudocode for full implementation:**
- Store 8 anchor colors in a vec3 array or as constants.
- Compute `stepNorm = stepIndex / NUM_STEPS` (0..1).
- Find segment: iterate `i` from 0 to N_ANCHORS-2; segment is the last `i` where `anchorPos[i] <= stepNorm`.
- Compute `mixFactor = clamp((stepNorm - low) / (high - low), 0.0, 1.0)`.
- Return `mix(color[segIdx], color[segIdx+1], mixFactor)`.

**Code sketch:**
```glsl
uniform float uMinTemp;
uniform float uMaxTemp;
uniform float uStepCelsius;

vec3 temperatureToColor(float temp) {
  float range = max(1.0, uMaxTemp - uMinTemp);
  float t = clamp((temp - uMinTemp) / range, 0.0, 1.0);
  float NUM_STEPS = max(1.0, range / uStepCelsius);
  float stepIndex = clamp(floor(t * NUM_STEPS), 0.0, NUM_STEPS - 1.0);
  float stepNorm = stepIndex / NUM_STEPS;

  // Map stepNorm through 8 anchors; find segment + mix factor
  // Anchors: 0→vec3(0.05,0.05,0.35), 0.1→vec3(0,0.5,0.9), 0.2→vec3(0,0.75,0.7),
  //          0.3→vec3(0.2,0.85,0.4), 0.5→vec3(0.95,0.95,0.2), 0.7→vec3(1,0.65,0.1),
  //          0.9→vec3(1,0.3,0.05), 1→vec3(1,0.15,0)
  // Segment boundaries: [0,0.1], [0.1,0.2], [0.2,0.3], [0.3,0.5], [0.5,0.7], [0.7,0.9], [0.9,1]
  // mixFactor = (stepNorm - low) / (high - low); return mix(cLow, cHigh, mixFactor)
}
```

**Updated Plate interface:**

```typescript
interface PlateProps {
  frame: Frame | null;
  maxTemp: number;
  minTemp?: number;       // default 0
  plateSize: number;
  colorSensitivity?: number;  // default 10 — degrees per visible step
}
```

**Uniform wiring (Plate → ShaderMaterial):**

| Uniform | Source | Passed from |
|---------|--------|-------------|
| `uMinTemp` | `minTemp` prop (default 0) | Plate receives `minTemp`; TorchWithHeatmap3D passes `minTemp={0}` |
| `uMaxTemp` | `maxTemp` prop | Existing; Plate already receives `maxTemp` |
| `uStepCelsius` | `colorSensitivity` prop (default 10) | Plate receives `colorSensitivity`; map 1:1 to uniform |

**Plate/TorchWithHeatmap3D → Plate → ShaderMaterial flow:**
- `TorchWithHeatmap3D` props: `minTemp`, `maxTemp`, `colorSensitivity`
- `Plate`: add `minTemp?: number`, `colorSensitivity?: number` to interface (see above)
- In Plate `useMemo` / `useEffect`: `uniforms.uMinTemp.value = minTemp ?? 0`, `uniforms.uStepCelsius.value = colorSensitivity ?? 10`

**Verification:**
- Run `HeatmapPlate3D` with synthetic frames: center 100°C vs 110°C; colors must differ visibly.
- Visual check: 50-step gradient strip in dev page.

**Time:** ~1 hour

---

### Step 1.3: Add Optional High-Sensitivity Mode (Config Prop)

**Component prop:** `colorSensitivity?: number` — degrees per visible step (default 10).

- `colorSensitivity=10` → 50 steps (0–500°C)
- `colorSensitivity=5`  → 100 steps (0–500°C)

Pass to shader as `uStepCelsius`; shader derives `NUM_STEPS = (uMaxTemp - uMinTemp) / uStepCelsius`. Both `colorSensitivity` (props) and `uStepCelsius` (shader) refer to the same value.

**Verification:** Toggle `colorSensitivity`; finer mode should show more subtle gradients.

---

## Phase 2: Unified Torch + Heatmap — Single Canvas Component

**Goal:** Merge TorchViz3D and HeatmapPlate3D into one component that renders the torch over thermally-colored metal. Remove the separate HeatmapPlate3D block.

**Time estimate:** 4–6 hours

### Step 2.0: Extract Shared Utils (Prerequisite for 2.1)

**extractFivePointFromFrame** is currently a local, non-exported function in `HeatmapPlate3D.tsx` (around lines 37–51). TorchWithHeatmap3D needs the same logic.

**Strategy:** Extract `extractFivePointFromFrame` to a shared util and import in both places.

1. **New export in** `my-app/src/utils/frameUtils.ts`:
   - Add `extractFivePointFromFrame(frame: Frame | null): { center, north, south, east, west } | null`
   - Implementation: identical to current HeatmapPlate3D logic — reads first `thermal_snapshots[0].readings` and maps `direction` to `temp_celsius`; fallback `DEFAULT_AMBIENT_CELSIUS` (20) for missing directions.

2. **Update** `HeatmapPlate3D.tsx`:
   - Remove local `extractFivePointFromFrame` implementation.
   - Import `extractFivePointFromFrame` from `@/utils/frameUtils`.

3. **Update** `TorchWithHeatmap3D.tsx` (when created):
   - Import `extractFivePointFromFrame` from `@/utils/frameUtils`.

**Verification:** `npm run test` passes; HeatmapPlate3D behavior unchanged.

**Time:** ~15 min

---

### Step 2.1: Create TorchWithHeatmap3D Component

**New file:** `my-app/src/components/welding/TorchWithHeatmap3D.tsx`

**Purpose:** Single R3F Canvas containing:
- Torch assembly (from TorchViz3D)
- Thermal workpiece (from HeatmapPlate3D Plate logic)
- Shared lighting, OrbitControls, context-loss handling

**Props interface:**
```typescript
export interface TorchWithHeatmap3DProps {
  angle: number;
  temp: number;
  label?: string;
  frames?: Frame[];
  activeTimestamp?: number | null;
  maxTemp?: number;
  minTemp?: number;
  plateSize?: number;
  colorSensitivity?: number;
}
```

**Behavior:**
- When `frames` is provided and has thermal data: Render thermally-colored workpiece (Plate) with vertex displacement and heat-sensitive shaders.
- When `frames` is empty or undefined: Render flat metallic workpiece (fallback, same as current TorchViz3D).
- Torch assembly and weld pool always use `angle` and `temp` (existing logic).

**Dependencies:**
- `TorchViz3D` scene content (extract `SceneContent` or inline)
- `HeatmapPlate3D` Plate subcomponent logic
- `extractFivePointFromFrame` from `@/utils/frameUtils` (extracted in Step 2.0)
- `interpolateThermalGrid` from `@/utils/thermalInterpolation`
- heatmap vertex/fragment shaders

**Implementation approach:**
1. Copy `SceneContent` from TorchViz3D (torch, weld pool, lights).
2. Replace the flat workpiece `<mesh><planeGeometry /></meshStandardMaterial />` with the thermal Plate (PlaneGeometry + ShaderMaterial driven by `uTemperatureMap`).
3. Wire `frames` + `activeTimestamp` → `activeFrame` via frame resolution and thermal pipeline:
   - **Guard:** If `activeTimestamp` is null or undefined, use `frames[0]?.timestamp_ms ?? 0` to avoid passing null to `getFrameAtTimestamp`. Assign: `const ts = activeTimestamp ?? frames?.[0]?.timestamp_ms ?? 0;`
   - `getFrameAtTimestamp(thermal_frames, ts)` → `activeFrame`
   - `extractFivePointFromFrame(activeFrame)` → `interpolateThermalGrid` → DataTexture → Plate
4. Pass `minTemp`, `maxTemp`, `colorSensitivity` into Plate (and thus into shader uniforms).
5. Use same `TorchIndicator` logic if desired, or rely on the full torch from TorchViz3D (preferred).
6. Port context-loss handler, HUD overlay, OrbitControls from TorchViz3D.
7. **Bundle splitting:** Consider `next/dynamic` for TorchWithHeatmap3D (as HeatmapPlate3D does) to lazy-load Three.js/R3F and reduce initial bundle size.

**Verification:**
- Standalone: Render `TorchWithHeatmap3D` with mock frames; see torch + colored metal.
- No thermal: Render with `frames=[]`; see torch + flat metal.
- Replay: Replace TorchViz3D + HeatmapPlate3D in replay with TorchWithHeatmap3D; layout should show 2 instances (expert, novice) with heat on metal.

**Error handling:**
- `frames` undefined or empty → flat workpiece.
- `activeFrame` null → use first frame or fill with ambient (20°C).
- Shader compile error → ErrorBoundary fallback.

**Time:** ~2–3 hours

---

### Step 2.2: Integrate into Replay Page

**File:** `my-app/src/app/replay/[sessionId]/page.tsx`

**Thermal frame source:** `frameData.thermal_frames` comes from `useFrameData`, which applies `filterThermalFrames` internally. Replay and demo therefore use the same thermal filtering logic.

**Changes:**
1. Replace `TorchViz3D` + `HeatmapPlate3D` grid layout with `TorchWithHeatmap3D` only.
2. Left column (Current Session):
   ```tsx
   <TorchWithHeatmap3D
     angle={angle}
     temp={temp}
     label={`Current Session (${sessionId})`}
     frames={frameData.thermal_frames}
     activeTimestamp={currentTimestamp}
     maxTemp={500}
     minTemp={0}
     colorSensitivity={10}
   />
   ```
3. Right column (Comparison): Same, with `comparisonFrameData.thermal_frames` and comparison session's angle/temp.
4. Remove the `HeatmapPlate3D` block (grid with HeatmapPlate3D | TorchAngleGraph). Keep TorchAngleGraph in a new layout (e.g. below unified blocks or in a separate row).
5. When session has no thermal data: Use `TorchWithHeatmap3D` with `frames={[]}` (flat metal), and show 2D HeatMap in a separate block if UX requires it (or keep HeatMap fallback as before for non-thermal sessions).

**Layout options:**
- **Option A:** Single row: [TorchWithHeatmap3D Expert | TorchWithHeatmap3D Novice], then second row: [HeatMap/TorchAngleGraph | TorchAngleGraph].
- **Option B:** If HeatMap is only for sessions without thermal: Show HeatMap only when `frameData.thermal_frames.length === 0`; otherwise omit it (all thermal info in 3D).

Per task: "i dont want a separate 3d heatmap" — so Option B: no separate HeatmapPlate3D. For thermal sessions, all thermal info is in TorchWithHeatmap3D. For non-thermal sessions, keep existing HeatMap (2D).

**Verification:**
- Replay with thermal: 2 TorchWithHeatmap3D; heat visible on metal; no standalone HeatmapPlate3D.
- Replay without thermal: TorchWithHeatmap3D (flat metal) + HeatMap.
- Canvas count: 2 (within limit).
- ESLint: Update rule to count TorchWithHeatmap3D instead of HeatmapPlate3D if needed.

**Time:** ~1 hour

---

### Step 2.3: Integrate into Demo Page

**File:** `my-app/src/app/demo/page.tsx`

**Thermal frame derivation (use `filterThermalFrames`):**

The demo page uses the `expertThermalFrames` memo pattern: `filterThermalFrames(expertSession.frames)`. Derive thermal frames consistently:

- **expertThermalFrames:** `filterThermalFrames(expertSession.frames)` — existing pattern.
- **noviceThermalFrames:** `filterThermalFrames(noviceSession.frames)` — for novice column (may be empty if novice has no thermal).

Add `noviceThermalFrames` memo alongside `expertThermalFrames`:
```tsx
const expertThermalFrames = useMemo(
  () => filterThermalFrames(expertSession.frames),
  [expertSession.frames]
);
const noviceThermalFrames = useMemo(
  () => filterThermalFrames(noviceSession.frames),
  [noviceSession.frames]
);
```

**Changes:**
1. Expert column: Replace TorchViz3D + HeatmapPlate3D with:
   ```tsx
   <TorchWithHeatmap3D
     angle={expertAngleDeg}
     temp={expertTemp}
     label="Expert Technique"
     frames={expertThermalFrames}
     activeTimestamp={currentTimestamp}
     maxTemp={500}
     minTemp={0}
     colorSensitivity={10}
   />
   ```
2. Novice column: Replace TorchViz3D with TorchWithHeatmap3D; pass `frames={noviceThermalFrames}`. If `noviceThermalFrames.length === 0`, pass `frames={[]}` for flat metal.
3. Remove HeatmapPlate3D import and usage.
4. Keep HeatMap for novice if it has no thermal (or use TorchWithHeatmap3D with flat metal).

**Verification:**
- Demo: Expert shows torch + heat on metal; novice shows torch + flat metal (or heat if data exists).
- Canvas count: 2.

**Time:** ~30 minutes

---

### Step 2.4: WebGL / ESLint Updates

**Files:**
- `my-app/src/constants/webgl.ts`:
  - Update `MAX_CANVAS_PER_PAGE` from 3 to **2**. Replay/Demo now use 2 TorchWithHeatmap3D only; no separate HeatmapPlate3D.
  - Update comments: "Replay/Demo: 2 TorchWithHeatmap3D = 2 Canvases. HeatmapPlate3D deprecated in replay."
- `my-app/eslint-rules/` (if applicable): Change to count TorchWithHeatmap3D; allow 2 per page.
- `documentation/WEBGL_CONTEXT_LOSS.md`: Add TorchWithHeatmap3D to related files.

**Verification:** `npm run lint` passes; Canvas count assertions in tests updated.

---

## Phase 3: Heat Travel Visualization (0° → 500°C)

**Goal:** Clearly show heat traveling through the metal over time — from ambient (0–20°C) to peak (up to 500°C).

**Time estimate:** 2–3 hours total (3.1: ~30 min; 3.2: deferred; 3.3: ~1.5–2 h manual verification)

### Step 3.1: Verify Temporal Carry-Forward (Existing Behavior)

**Current setup:** HeatmapPlate3D receives `frameData.thermal_frames` from `useFrameData`. These are thermal-only frames. The active frame is resolved via:

```typescript
const activeFrame = getFrameAtTimestamp(thermal_frames, currentTimestamp);
```

`getFrameAtTimestamp` (in `frameUtils.ts`) returns the most recent frame with `timestamp_ms <= currentTimestamp`. That **already implements carry-forward**: between sparse thermal samples (e.g. 5 Hz), the same thermal frame is reused until a newer thermal frame exists. No new helper is needed.

**Implementation:** None. Carry-forward is already correct.

**Verification (explicit steps):**
1. Open a replay session with thermal data. Note thermal sample rate (e.g. ~200 ms).
2. Scrub the timeline slowly between two thermal samples. The heatmap color should **not** flicker or disappear; it should hold the previous thermal frame's data.
3. Advance past a new thermal sample; colors should update to the new frame.
4. Scrub backwards; colors should hold the frame at or before that timestamp.
5. If flicker is observed, trace `frameData.thermal_frames` and `getFrameAtTimestamp` usage — the bug is elsewhere, not in carry-forward logic.

**Time:** ~30 min (verification only)

---

### Step 3.2: Optional Heat Decay / Diffusion Visualization

**Advanced:** If thermal data includes only "current" readings (no explicit cooling), heat may appear to "teleport." Options:

1. **Temporal smoothing:** Blend current frame's interpolated grid with previous frame (e.g. 70% current + 30% previous) to suggest inertia.
2. **Carry-forward with decay:** When no new thermal at current timestamp, use previous thermal * decay factor (e.g. 0.95 per 100ms).
3. **Document as future enhancement:** If backend doesn't provide heat dissipation per cell, defer to Phase 4.

**Tradeoffs:**
- **Temporal smoothing** (blend): Improves perceived visual continuity but **reduces accuracy** — the displayed state is no longer exactly what was captured at that timestamp. This conflicts with the project rule: *"Exact replays: Frontend shows exactly what happened (no guessing)."*
- **Decay:** Similar issue — introduces synthetic cooling not in the raw data.
- **Recommendation:** Implement Step 3.1 (verification) first. Add smoothing only if users report flicker, and document it as a UX enhancement with accuracy caveat. MVP: keep logic simple; prefer exact replay over visual smoothing.

---

### Step 3.3: Visual Verification — Heat Progression

**Manual test (~1.5–2 h):**
1. Start replay at t=0. Metal should be cool (blue/dark).
2. Advance to t=2s. Center should warm (cyan/green).
3. Advance to t=5s. Heat should spread (yellow/orange).
4. Advance to t=10s. Peak temps (red/white).
5. Scrub back and forth; colors should update smoothly with no flashing.

**Verification criteria:**
- At t=0: Predominantly blue/cool tones.
- Mid-session: Gradient from hot center to cooler edges.
- Late session: Hot zone expanded; edges warming.

**Time:** ~1.5–2 h (manual verification across sessions)

---

## Phase 4: Deprecation and Cleanup

**Time estimate:** 1–2 hours

### Step 4.1: Deprecate Standalone HeatmapPlate3D in Replay/Demo

- Remove HeatmapPlate3D from replay page (replaced by TorchWithHeatmap3D).
- Remove HeatmapPlate3D from demo page.
- Keep HeatmapPlate3D component for:
  - Dev / standalone testing
  - Backward compatibility if needed

**Compare page clarification:** The Compare page (`my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`) uses **HeatMap** (2D) only, never HeatmapPlate3D. No audit or changes to the Compare page are required for this plan.

**Verification:** `grep -r HeatmapPlate3D my-app/src/app` — no references in replay, demo, or compare pages. Only dev/test/component-definition references remain.

---

### Step 4.2: Update Tests

**Files to update:**
- `my-app/src/__tests__/app/replay/[sessionId]/page.test.tsx`:
  - Replace HeatmapPlate3D mock with TorchWithHeatmap3D mock.
  - Update "shows HeatmapPlate3D when session has thermal data" → "shows TorchWithHeatmap3D with heat on metal when session has thermal data".
  - Update Canvas count assertion: 2 TorchWithHeatmap3D (no HeatmapPlate3D).
- `my-app/src/__tests__/app/demo/page.test.tsx`:
  - Similar mock and assertion updates.
- Add `TorchWithHeatmap3D.test.tsx` at `my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx` with:
  - Basic render (component mounts without error)
  - Flat vs thermal: render with `frames=[]` vs `frames` with thermal data; verify no crash and appropriate fallback
  - Context-loss: mock context loss; verify overlay or fallback appears

**Verification:** `npm run test` passes.

---

### Step 4.3: Update Documentation

- `CONTEXT.md`: Document TorchWithHeatmap3D, deprecation of standalone HeatmapPlate3D in replay.
- `LEARNING_LOG.md`: Note color sensitivity change (5–10°C visible).
- Plan file: Mark steps complete.

---

## Phase 5: Error Handling and Edge Cases

| Edge Case | Handling |
|-----------|----------|
| `frames` empty or undefined | Render flat metallic workpiece; no thermal coloring |
| `activeTimestamp` null | Use first frame in `frames` or ambient default (guard: `const ts = activeTimestamp ?? frames?.[0]?.timestamp_ms ?? 0`) |
| All thermal readings 0 or ambient | Show cool blue; no error |
| `uMaxTemp <= uMinTemp` | Clamp uMaxTemp = uMinTemp + 1 in shader or CPU |
| WebGL context lost | Existing handler; show "Refresh to restore" overlay |
| Shader compile failure | ErrorBoundary fallback; log error |
| Missing thermal_snapshots in frame | Use previous frame (carry-forward) or ambient |
| Session has no thermal_frames | TorchWithHeatmap3D with frames=[]; show HeatMap separately for 2D fallback |

---

## Dependency Summary

| Step | Depends On |
|------|------------|
| 1.1 | — |
| 1.2 | 1.1 |
| 1.3 | 1.2 |
| 2.0 | — |
| 2.1 | 1.2, 2.0, TorchViz3D, HeatmapPlate3D, shaders |
| 2.2 | 2.1 |
| 2.3 | 2.1 |
| 2.4 | 2.1 |
| 3.1 | 2.1 |
| 3.2 | 3.1 (optional) |
| 4.1 | 2.2, 2.3 |
| 4.2 | 2.1 |
| 4.3 | All |

---

## Time Estimates by Phase

| Phase | Description | Time |
|-------|-------------|------|
| 1 | Color sensitivity (5–10°C visible) | 2–3 h |
| 2 | Unified TorchWithHeatmap3D + replay/demo integration (incl. 2.0 extract) | 4–6 h |
| 3 | Heat travel verification (3.1: 30 min; 3.3: 1.5–2 h manual) | 2–3 h |
| 4 | Deprecation, tests, docs | 1–2 h |
| **Total** | | **9–14 h** |

---

## Verification Checklist

- [ ] 10°C difference produces visibly different colors on metal
- [ ] Replay page: torch + heat on metal in one component; no separate 3D heatmap block
- [ ] Demo page: same unified layout; expertThermalFrames/noviceThermalFrames from filterThermalFrames
- [ ] Heat progresses from cool (0°C) to hot (500°C) over replay timeline
- [ ] Canvas count ≤ 2 on replay/demo (within WebGL limit)
- [ ] Non-thermal sessions: flat metal + HeatMap fallback
- [ ] All tests pass; no new lint errors
- [ ] Context-loss overlay appears and works

---

## Code Locations Reference

| Item | Path |
|------|------|
| TorchViz3D | `my-app/src/components/welding/TorchViz3D.tsx` |
| HeatmapPlate3D | `my-app/src/components/welding/HeatmapPlate3D.tsx` |
| Fragment shader | `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts` |
| Vertex shader | `my-app/src/components/welding/shaders/heatmapVertex.glsl.ts` |
| Thermal interpolation | `my-app/src/utils/thermalInterpolation.ts` |
| Frame utils (filterThermalFrames, getFrameAtTimestamp, extractFivePointFromFrame) | `my-app/src/utils/frameUtils.ts` |
| Heatmap shader utils (temperatureToColor TS mirror, optional) | `my-app/src/utils/heatmapShaderUtils.ts` |
| Replay page | `my-app/src/app/replay/[sessionId]/page.tsx` |
| Demo page | `my-app/src/app/demo/page.tsx` |
| Compare page | `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx` (uses HeatMap 2D only) |
| WebGL constants | `my-app/src/constants/webgl.ts` |
| WEBGL docs | `documentation/WEBGL_CONTEXT_LOSS.md` |
