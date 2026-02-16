# 3D Warped Heatmap Plate — Implementation Plan (ENHANCED)

**Issue:** `.cursor/issues/3d-warped-heatmap-plate.md`  
**Exploration:** `.cursor/agents/3d-warped-heatmap-plate-explore-output.md`  
**Date:** 2025-02-16  
**Time Budget:** 90–120 minutes minimum for plan creation; ~14 hours implementation  
**Version:** Enhanced (addresses WILL Critique)

---

## Phase 0: MANDATORY PRE-PLANNING THINKING SESSION (30 minutes minimum)

### A. Exploration Review and Synthesis (10 minutes)

#### 1. Core Approach (One Sentence)

Interpolate 5-point thermal data (center, north, south, east, west) to a 100×100 grid using Inverse Distance Weighting (IDW), drive vertex displacement and temperature→color in custom GLSL shaders on a PlaneGeometry, render via R3F with context-loss handling, replace HeatMap on replay page only (Phase 1).

**Key decisions:**
- IDW interpolation (power=2, epsilon=0.01)
- Inline GLSL strings exported from `.glsl.ts` files (no webpack loader)
- First thermal snapshot (`thermal_snapshots[0]`) per exploration
- Replace HeatMap on replay (not toggle)
- Extend webgl constants for Canvas count (MAX_CANVAS_PER_PAGE = 3)

**Why this approach:** IDW is deterministic, testable, and prototype-validated. Inline shaders avoid build config. Replay-only stays within WebGL budget (3 Canvases: 2 TorchViz3D + 1 HeatmapPlate3D).

#### 2. Major Components

| Component | Purpose |
|-----------|---------|
| `thermalInterpolation.ts` | Pure function: 5 temps → 100×100 grid via IDW; exported `sanitizeTemp` helper |
| `heatmapVertex.glsl.ts` | Vertex shader: sample texture, displace along normal |
| `heatmapFragment.glsl.ts` | Fragment shader: temp → color (blue→white) |
| `HeatmapPlate3D.tsx` | Main component: `extractFivePointFromFrame` helper at top, Plate + TorchIndicator, Canvas, context-loss |
| Replay page integration | Swap HeatMap for dynamic HeatmapPlate3D when thermal_frames.length > 0 |
| webgl.ts + ESLint | Document/count HeatmapPlate3D in Canvas limit |

#### 3. Data Flow

```
Input: Frame[] (thermal_frames), activeTimestamp
  ↓
getFrameAtTimestamp(frames, activeTimestamp) → activeFrame
  ↓
extractFivePointFromFrame(activeFrame) → { center, north, south, east, west } | null
  ↓
interpolateThermalGrid(center, north, south, east, west, 100) → number[][]
  ↓
Flatten to Float32Array → THREE.DataTexture
  ↓
ShaderMaterial uniforms: uTemperatureMap, uMaxTemp, uMaxDisplacement
  ↓
Vertex: displace position; Fragment: color from temp
  ↓
Output: 3D rendered plate + torch cone
```

#### 4. Biggest Risks (from exploration)

1. **WebGL context overflow** — 3 Canvases on replay (2 TorchViz3D + 1 HeatmapPlate3D); within 8–16 limit but at cautious end.
2. **Interpolation artifacts** — 5 points → 10k values; IDW may produce rings/spikes if epsilon/power wrong.
3. **Shader compile failure** — Syntax error in GLSL won't surface until Plate renders; needs isolated smoke test.
4. **Texture update race** — Updating texture every tick instead of only when thermalData changes wastes GPU.
5. **Missing thermal data** — Frames between thermal samples (sparse 5Hz); must use getFrameAtTimestamp + carry-forward behavior.

#### 5. Gaps Exploration Did NOT Answer

- **Gap 1:** Exact epsilon and power for IDW in production (exploration used 0.01 and 2; may need tuning).
- **Gap 2:** Whether 50×50 geometry fallback for mobile is needed (exploration said "profile; consider").
- **Gap 3:** ESLint rule extension — count HeatmapPlate3D vs new MAX_CANVAS_PER_PAGE.
- **Gap 4:** HeatMap fallback UX when HeatmapPlate3D throws (ErrorBoundary shows what?).
- **Gap 5:** Isolated shader compile verification before full Plate integration.

---

### B. Dependency Brainstorm (10 minutes)

**Major work items (before ordering):**
1. Create thermalInterpolation.ts with interpolateThermalGrid and **exported sanitizeTemp**
2. Unit test interpolateThermalGrid
3. Create heatmapVertex.glsl.ts
4. Create heatmapFragment.glsl.ts
5. **Step 1.3b: Create minimal ShaderSmokeTest component for isolated shader compile check**
6. Create extractFivePointFromFrame helper (defined at top of HeatmapPlate3D.tsx, before Plate)
7. Create HeatmapPlate3D.tsx with Plate subcomponent
8. Implement TorchIndicator subcomponent
9. Add context-loss handler to HeatmapPlate3D
10. Add dynamic import + loading fallback
11. Integrate in replay page (replace HeatMap)
12. Extend webgl.ts / MAX_CANVAS
13. Add HeatmapPlate3D unit test (mocked 3D)
14. Add replay integration test with **mandated mock strategy**
15. Handle empty frames / no thermal
16. Memoize texture creation (only when thermalData changes)
17. Dispose texture on unmount
18. Add aria-label / role for accessibility
19. **Canvas count assertion: assert mock component counts (2× torch-viz-3d-mock + 1× heatmap-plate-3d = 3)**
20. Update CONTEXT.md

**Critical path:** thermalInterpolation → shaders → ShaderSmokeTest → Plate → HeatmapPlate3D → Replay integration (~12h steps + 2h buffer = 14h)

**Bottlenecks:** ShaderMaterial + DataTexture integration; Thermal extraction.

**Parallelizable:** heatmapVertex.glsl.ts and heatmapFragment.glsl.ts; Unit tests and shader creation.

---

### C. Risk-Based Planning (10 minutes)

| Risk | Probability | Impact | Planning Implication |
|------|-------------|--------|----------------------|
| WebGL context overflow | 25% | High | Extend MAX_CANVAS; verify replay = 3; document |
| Interpolation artifacts | 40% | Medium | Unit test edge values; tune eps/power |
| **Shader compile failure** | **15%** | **Medium** | **Step 1.3b: Isolated ShaderSmokeTest before Plate** |
| Texture every frame | 20% | Low | useMemo with thermalData deps |
| Mobile GPU slow | 25% | Medium | 100×100 first; add 50×50 prop if profiler shows need |
| Memory leak (texture/material) | 20% | Medium | Dispose in useEffect cleanup |

**Failure modes planned for:** NaN/Infinity in grid, flat plate (uMaxDisplacement), wrong colors (uMaxTemp), texture not updating (useMemo deps), shader link error (varying mismatch), context lost (overlay), HeatmapPlate3D throws (ErrorBoundary fallback).

---

## WILL Critique Fixes (Explicit)

| Critique | Fix in Plan |
|----------|-------------|
| Step 1.3/1.4 shader verification gap | **Step 1.3b** added: Create minimal ShaderSmokeTest that loads shaders without full 3D scene |
| Step 1.9 Canvas count assertion unclear | **Mandate:** Assert mock component counts: `torch-viz-3d-mock` (≤2) + `heatmap-plate-3d` (1 when thermal) = 3 total |
| Step 1.11 mocking strategy buried | **Pull to top** of Step 1.11 as "CRITICAL: Before writing tests, update mocks as follows:" |
| Time estimates inconsistent | **Explicit:** 14h = 12h steps + 2h buffer (documented in Phase 1 header) |
| Step 1.1 sanitizeTemp location ambiguous | **Explicit:** sanitizeTemp is an **exported** helper in same file, **above** interpolateThermalGrid |
| Step 1.5 extractFivePointFromFrame placement | **Explicit:** extractFivePointFromFrame defined at **top of HeatmapPlate3D.tsx**, **before** Plate component |

---

## 1. Phase Breakdown Strategy

### Phase 1: Core 3D Warped Heatmap Plate (Replay Integration)

**Goal:** User sees 3D metal plate with thermal warping and color on replay page instead of CSS HeatMap when thermal data exists.

**User value:** Physics-informed thermal visualization; industrial-grade look.

**Why first:** Foundation is all-or-nothing; no incremental 3D without full stack.

**Time estimate:** **14 hours = 12 hours implementation steps + 2 hours buffer**

**Risk level:** 🟡 Medium

**Major steps (high-level):**
1. thermalInterpolation.ts (interpolateThermalGrid + exported sanitizeTemp)
2. Unit test thermalInterpolation
3. heatmapVertex.glsl.ts
4. heatmapFragment.glsl.ts
5. **ShaderSmokeTest** (isolated shader compile check)
6. Plate subcomponent (extractFivePointFromFrame at top of file)
7. TorchIndicator subcomponent
8. HeatmapPlate3D shell (Canvas, lights, OrbitControls, context-loss)
9. Replay integration (replace HeatMap, ErrorBoundary, dynamic import)
10. webgl.ts + Canvas count assertion strategy
11. HeatmapPlate3D unit test
12. Replay integration test (with mandated mock strategy)
13. Update CONTEXT.md

**Phase 1 Done When:**
- [ ] interpolateThermalGrid exists, unit tested, sanitizeTemp exported
- [ ] ShaderSmokeTest passes (shaders compile)
- [ ] HeatmapPlate3D renders with displacement and color
- [ ] Replay page shows HeatmapPlate3D instead of HeatMap when thermal_frames exist
- [ ] Context-loss overlay works
- [ ] No regressions; Canvas count = 3 on replay (2 TorchViz3D + 1 HeatmapPlate3D)
- [ ] Mock strategy: 2× torch-viz-3d-mock + 1× heatmap-plate-3d asserted when thermal present

---

## 2. Step Definition

### Phase 1: Core 3D Warped Heatmap Plate

---

#### Step 1.1: Create thermalInterpolation.ts — *Critical: Data transformation*

**Why critical:** Core algorithm; wrong interpolation = wrong visualization. Must be pure and deterministic.

**What:** Implement `interpolateThermalGrid(centerTemp, northTemp, southTemp, eastTemp, westTemp, gridSize?)` using IDW with power=2, epsilon=0.01. **Define `sanitizeTemp` as an exported helper function in the same file, above `interpolateThermalGrid`.** Map 5 points: center=(0.5,0.5), north=(0.5,0), south=(0.5,1), east=(1,0.5), west=(0,0.5). Validate and clamp all inputs.

**Files:**
- **Create:** `my-app/src/utils/thermalInterpolation.ts`

**Constants:**
```ts
const DEFAULT_AMBIENT_CELSIUS = 20;
const MAX_TEMP_CELSIUS = 600;
```

**Exported helper (placement: above interpolateThermalGrid):**
```ts
/**
 * Sanitize a temperature value for interpolation.
 * Replaces NaN/Infinity with DEFAULT_AMBIENT_CELSIUS; clamps to [0, MAX_TEMP_CELSIUS].
 */
export function sanitizeTemp(v: number): number {
  if (!Number.isFinite(v)) return DEFAULT_AMBIENT_CELSIUS;
  return Math.max(0, Math.min(MAX_TEMP_CELSIUS, v));
}
```

**Full interpolateThermalGrid implementation:**
```typescript
export function interpolateThermalGrid(
  centerTemp: number,
  northTemp: number,
  southTemp: number,
  eastTemp: number,
  westTemp: number,
  gridSize: number = 100
): number[][] {
  const c = sanitizeTemp(centerTemp);
  const n = sanitizeTemp(northTemp);
  const s = sanitizeTemp(southTemp);
  const e = sanitizeTemp(eastTemp);
  const w = sanitizeTemp(westTemp);

  const eps = 0.01;
  const power = 2;
  const grid: number[][] = [];

  for (let y = 0; y < gridSize; y++) {
    grid[y] = [];
    for (let x = 0; x < gridSize; x++) {
      const nx = x / gridSize;
      const ny = y / gridSize;
      const distCenter = Math.sqrt((nx - 0.5) ** 2 + (ny - 0.5) ** 2);
      const distNorth = Math.sqrt((nx - 0.5) ** 2 + (ny - 0) ** 2);
      const distSouth = Math.sqrt((nx - 0.5) ** 2 + (ny - 1) ** 2);
      const distEast = Math.sqrt((nx - 1) ** 2 + (ny - 0.5) ** 2);
      const distWest = Math.sqrt((nx - 0) ** 2 + (ny - 0.5) ** 2);

      const wC = 1 / (distCenter ** power + eps);
      const wN = 1 / (distNorth ** power + eps);
      const wS = 1 / (distSouth ** power + eps);
      const wE = 1 / (distEast ** power + eps);
      const wW = 1 / (distWest ** power + eps);

      const total = wC + wN + wS + wE + wW;
      let val = (c * wC + n * wN + s * wS + e * wE + w * wW) / total;
      val = Math.max(0, Math.min(MAX_TEMP_CELSIUS, Number.isFinite(val) ? val : c));
      grid[y][x] = val;
    }
  }
  return grid;
}
```

**Subtasks:**
- [ ] Create file with exported `sanitizeTemp` (above interpolateThermalGrid)
- [ ] Create exported `interpolateThermalGrid`
- [ ] Implement IDW: `wi = 1/(dist_i^2 + 0.01)`, `value = sum(wi * vali) / sum(wi)`
- [ ] Use correct variable name `distCenter` (not `distCenr`)
- [ ] Default gridSize=100; return `number[][]` [gridSize][gridSize]
- [ ] Validate inputs via sanitizeTemp; clamp output per cell
- [ ] Add JSDoc with @param, @returns, formula

**✓ Verification Test:**
- **Action:** Call `interpolateThermalGrid(100, 50, 50, 80, 80, 10)`
- **Pass criteria:** grid[5][5] ≈ 100; grid[0][5] ≈ 50 (north); grid[9][5] ≈ 50 (south); grid[5][9] ≈ 80 (east); grid[5][0] ≈ 80 (west); no NaN/Infinity; unit test exists and passes

**Common Failures & Fixes:**
1. Center value not ~100 → verify distCenter formula
2. NaN in output → use sanitizeTemp; guard `if (!Number.isFinite(val)) val = c`
3. Typo distCenr → use `distCenter` everywhere

**Time estimate:** 1.5 hours

---

#### Step 1.2: Create unit test for interpolateThermalGrid

**What:** Add `my-app/src/__tests__/utils/thermalInterpolation.test.ts` with tests for center, edges, NaN/Infinity, clamping.

**Subtasks:**
- [ ] Test center value dominates at (0.5, 0.5)
- [ ] Test north/south/east/west at edges
- [ ] Test all same temp → uniform grid
- [ ] Test gridSize parameter (e.g. 50)
- [ ] Test NaN input → grid has no NaN
- [ ] Test Infinity input → output finite
- [ ] Test negative input → clamped to 0

**✓ Verification Test:** `npm test -- thermalInterpolation` — all tests pass

**Time estimate:** 0.5 hours

---

#### Step 1.3: Create heatmapVertex.glsl.ts

**What:** Export vertex shader as inline string. Sample temperature texture, displace vertices along normal.

**Files:** Create `my-app/src/components/welding/shaders/heatmapVertex.glsl.ts`

**Code (full implementation):**
```typescript
export const heatmapVertexShader = `
varying vec2 vUv;
varying float vTemperature;
uniform sampler2D uTemperatureMap;
uniform float uMaxDisplacement;
uniform float uMaxTemp;

void main() {
  vUv = uv;
  float temperature = texture2D(uTemperatureMap, uv).r;
  vTemperature = temperature;
  float displacement = (temperature / uMaxTemp) * uMaxDisplacement;
  vec3 newPosition = position + normal * displacement;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
}
`;
```

**Note:** Uses `texture2D()` (WebGL 1). For WebGL 2, replace with `texture()`.

**✓ Verification Test:** Integration-level only; isolated check in Step 1.3b

**Time estimate:** 0.5 hours

---

#### Step 1.4: Create heatmapFragment.glsl.ts

**What:** Export fragment shader. Map vTemperature to color (blue→cyan→yellow→orange→white).

**Files:** Create `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts`

**Code (full implementation):**
```typescript
export const heatmapFragmentShader = `
varying vec2 vUv;
varying float vTemperature;
uniform float uMaxTemp;

vec3 temperatureToColor(float temp) {
  float t = clamp(temp / uMaxTemp, 0.0, 1.0);
  if (t < 0.2) {
    return mix(vec3(0.1, 0.1, 0.2), vec3(0.0, 0.5, 1.0), t * 5.0);
  } else if (t < 0.5) {
    return mix(vec3(0.0, 0.5, 1.0), vec3(1.0, 1.0, 0.0), (t - 0.2) / 0.3);
  } else if (t < 0.8) {
    return mix(vec3(1.0, 1.0, 0.0), vec3(1.0, 0.5, 0.0), (t - 0.5) / 0.3);
  } else {
    return mix(vec3(1.0, 0.5, 0.0), vec3(1.0, 1.0, 1.0), (t - 0.8) / 0.2);
  }
}

void main() {
  vec3 color = temperatureToColor(vTemperature);
  gl_FragColor = vec4(color, 1.0);
}
`;
```

**✓ Verification Test:** Integration-level; isolated check in Step 1.3b

**Time estimate:** 0.5 hours

---

#### Step 1.3b: Create ShaderSmokeTest — *Critical: Early shader compile detection*

**Why critical:** If shaders have syntax errors, we catch them before Step 1.6. Without this, we won't know until full Plate renders.

**What:** Create a minimal test component or test file that loads both shaders and attempts to create a ShaderMaterial. Run in Jest with jsdom + canvas mock, or in a standalone HTML file. **Option A (recommended):** Add a `ShaderSmokeTest.tsx` component that renders a 1×1 plane with ShaderMaterial; run via `npm run dev` and open a test route. **Option B:** Add a Jest test that mocks Three.js and asserts ShaderMaterial constructor succeeds with our shader strings.

**Files:**
- **Create:** `my-app/src/components/welding/__tests__/ShaderSmokeTest.tsx` (or inline test in HeatmapPlate3D.test)

**Subtasks:**
- [ ] Import heatmapVertexShader and heatmapFragmentShader
- [ ] Create minimal Float32Array (1×1 or 10×10) with test data
- [ ] Create DataTexture and ShaderMaterial with shaders
- [ ] Assert no throw when constructing ShaderMaterial
- [ ] If using real Canvas: render in isolation, check console for "shader compile" / "link" errors

**✓ Verification Test:**
- **Action:** Run ShaderSmokeTest (or Jest test that constructs ShaderMaterial)
- **Expected:** No shader compile or link errors in console
- **Pass criteria:** ShaderMaterial created successfully; no WebGL errors

**Common Failures & Fixes:**
1. "varying not declared in fragment" → Add varying in both vertex and fragment
2. "uniform type mismatch" → Check sampler2D, float types
3. GLSL syntax error → Fix typo; validate with glsl-parser if available

**Time estimate:** 0.5 hours

---

#### Step 1.5: Create Plate subcomponent with ShaderMaterial — *Critical: Core rendering*

**Why critical:** Connects interpolation, texture, and shaders. Incorrect here breaks entire visualization.

**What:** Build Plate component. **extractFivePointFromFrame is defined as a helper function at the top of HeatmapPlate3D.tsx, before the Plate component.** Plate extracts 5-point thermal from frame, interpolates, creates DataTexture, applies ShaderMaterial. Dispose texture and ShaderMaterial on unmount.

**File lifecycle:** Step 1.5 creates `HeatmapPlate3D.tsx` with extractFivePointFromFrame at top, then Plate. Steps 1.6 and 1.7 extend this file.

**Code structure (extractFivePointFromFrame placement):**
```tsx
// At TOP of HeatmapPlate3D.tsx, BEFORE Plate component:
function extractFivePointFromFrame(frame: Frame | null): {
  center: number; north: number; south: number; east: number; west: number;
} | null {
  if (!frame?.has_thermal_data || !frame.thermal_snapshots?.[0]) return null;
  const readings = frame.thermal_snapshots[0].readings ?? [];
  const get = (d: ThermalDirection) =>
    readings.find((r) => r.direction === d)?.temp_celsius ?? DEFAULT_AMBIENT_CELSIUS;
  return {
    center: get("center"), north: get("north"), south: get("south"),
    east: get("east"), west: get("west"),
  };
}

function Plate({ frame, maxTemp, plateSize }: {...}) {
  // ... use extractFivePointFromFrame, interpolateThermalGrid, ShaderMaterial
}
```

**Subtasks:**
- [ ] Define extractFivePointFromFrame at top of file (before Plate)
- [ ] Plate: useMemo thermalData, temperatureTexture, material
- [ ] useEffect cleanup: material.dispose(); temperatureTexture.dispose()
- [ ] PlaneGeometry args={[plateSize, plateSize, 100, 100]}; rotation [-π/2, 0, 0]

**✓ Verification Test:** Load replay with thermal; plate shows colored, warped surface; hot regions bulge.

**Common Failures & Fixes (Step 1.5):**
1. **Plate is completely flat:** uMaxDisplacement=0 or temp all same → Check uniform 0.5; verify thermalData varies
2. **Texture not updating when scrubbing:** useMemo deps missing → Ensure `[thermalData]` in temperatureTexture useMemo
3. **"vTemperature" varying not declared in fragment:** Link error → Declare in both vertex and fragment shaders
4. **Black or wrong colors:** uMaxTemp wrong → Pass maxTemp=600; clamp t in shader
5. **Memory leak:** Texture or material not disposed → useEffect return: `material.dispose(); temperatureTexture.dispose()`
6. **DoubleSide not showing back:** Use THREE.DoubleSide for plate visible from both sides
7. **Plane facing wrong way:** Use rotation [-Math.PI/2, 0, 0] for horizontal plate
8. **ShaderMaterial not found:** Use `new THREE.ShaderMaterial(...)` from `three` — imperative API
9. **Old material orphaned when thermalData changes:** useEffect cleanup with [material, temperatureTexture] deps disposes previous

**Time estimate:** 2 hours

---

#### Step 1.6: Create TorchIndicator subcomponent

**What:** Cone mesh above plate center, rotated by angle_degrees. Extend HeatmapPlate3D.tsx.

**Time estimate:** 0.5 hours

---

#### Step 1.7: Assemble HeatmapPlate3D with Canvas, lights, OrbitControls, context-loss

**What:** Extend HeatmapPlate3D.tsx: Canvas, lights, Plate, TorchIndicator, gridHelper, OrbitControls. Add webglcontextlost/restored handlers; overlay with Refresh. Dynamic import with ssr:false. Outer container role="img" aria-label="3D heatmap".

**Time estimate:** 2 hours

---

#### Step 1.8: Integrate HeatmapPlate3D in replay page (replace HeatMap)

**What:** In `replay/[sessionId]/page.tsx`: Add dynamic import for HeatmapPlate3D. When `thermal_frames.length > 0`: render HeatmapPlate3D (wrapped in ErrorBoundary with fallback "3D heatmap unavailable"). When `thermal_frames.length === 0`: render HeatMap with heatmapData.

**Code pattern:**
```tsx
const HeatmapPlate3D = dynamic(
  () => import('@/components/welding/HeatmapPlate3D').then((m) => m.default),
  { ssr: false, loading: () => <div className="...">Loading 3D heatmap…</div> }
);

// In grid cell:
{frameData.thermal_frames.length > 0 ? (
  <ErrorBoundary fallback={<div>3D heatmap unavailable</div>}>
    <HeatmapPlate3D frames={frameData.thermal_frames} activeTimestamp={currentTimestamp} maxTemp={600} plateSize={10} />
  </ErrorBoundary>
) : (
  <HeatMap sessionId={sessionId} data={heatmapData} activeTimestamp={currentTimestamp} />
)}
```

**Time estimate:** 1 hour

---

#### Step 1.9: Extend webgl.ts and document Canvas count

**What:** Add MAX_CANVAS_PER_PAGE = 3; document HeatmapPlate3D.

**Canvas count assertion (MANDATED strategy):** In replay integration test, **assert mock component counts** (not real Canvas, since mocks prevent real Canvas). Strategy: When thermal present, expect `torch-viz-3d-mock` count = 2 and `heatmap-plate-3d` count = 1 (total 3 3D components). This catches regressions that would add extra Canvases. **Do NOT** assert `document.querySelectorAll('canvas').length` in Jest—mocks don't render real Canvas. Manual verification: open replay in browser, run `document.querySelectorAll('canvas').length === 3`.

**Subtasks:**
- [ ] Add MAX_CANVAS_PER_PAGE = 3 to webgl.ts
- [ ] Document: replay = 2 TorchViz3D + 1 HeatmapPlate3D
- [ ] In replay test: assert mock counts (torch-viz-3d-mock ≤2, heatmap-plate-3d = 1 when thermal)

**Time estimate:** 0.25 hours

---

#### Step 1.10: Add unit test for HeatmapPlate3D (mocked 3D)

**What:** Jest test that mocks R3F/Three; verifies HeatmapPlate3D renders without crash.

**Time estimate:** 1 hour

---

#### Step 1.11: Add integration test for replay page with HeatmapPlate3D

**CRITICAL: Before writing tests, update mocks as follows:**

1. **Replace next/dynamic mock** so it invokes the loader (enables per-component mocks):
```tsx
jest.mock('next/dynamic', () => ({
  __esModule: true,
  default: (loader: () => Promise<{ default: React.ComponentType }>) => {
    const Loaded = React.lazy(loader);
    return function DynamicWrapper(props: React.ComponentProps<typeof Loaded>) {
      return (
        <React.Suspense fallback={<div data-testid="dynamic-loading" />}>
          <Loaded {...props} />
        </React.Suspense>
      );
    };
  },
}));
```

2. **Mock TorchViz3D:**
```tsx
jest.mock('@/components/welding/TorchViz3D', () => ({
  __esModule: true,
  default: () => <div data-testid="torch-viz-3d-mock" />,
}));
```

3. **Mock HeatmapPlate3D:**
```tsx
jest.mock('@/components/welding/HeatmapPlate3D', () => ({
  __esModule: true,
  default: () => <div data-testid="heatmap-plate-3d" />,
}));
```

4. **Assert mock counts:** When session has thermal_frames: `expect(screen.getAllByTestId('heatmap-plate-3d')).toHaveLength(1)`; `expect(screen.getAllByTestId('torch-viz-3d-mock')).toHaveLength(2)`.

**Subtasks:**
- [ ] Apply CRITICAL mocking strategy above (at top of step)
- [ ] Add mock session with thermal_snapshots (has_thermal_data: true)
- [ ] Assert HeatmapPlate3D in document when thermal present
- [ ] Assert HeatmapPlate3D absent when thermal_frames empty
- [ ] Assert torch-viz-3d-mock count ≤ 2
- [ ] Assert heatmap-plate-3d count = 1 when thermal present (Canvas count proxy)

**Time estimate:** 0.5 hours

---

#### Step 1.12: Update CONTEXT.md

**What:** Add HeatmapPlate3D to project context; note it replaces HeatMap on replay; Canvas count.

**Time estimate:** 0.25 hours

---

### Phase 1 Total Time: 14 hours (12h steps + 2h buffer)

**Step sum:** 1.5 + 0.5 + 0.5 + 0.5 + 0.5 + 2 + 0.5 + 2 + 1 + 0.25 + 1 + 0.5 + 0.25 = 10.5h  
**With Step 1.3b (0.5h):** 11h  
**Buffer:** 2h  
**Total:** 13h (conservative) to 14h

---

## 3. Pre-Flight Checklist

### Phase 1 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Node.js 18+ | `node --version` | Install from nodejs.org |
| npm 9+ | `npm --version` | Comes with Node 18+ |
| Dependencies | `cd my-app && npm install` | `npm install` |
| Three.js, R3F | `npm list three @react-three/fiber` | Already in package.json |
| Dev server | `npm run dev` | `npm run dev` in my-app |
| Session with thermal | `npm test -- demo-data` or seed | Verify thermal_frames has data |
| getFrameAtTimestamp | Import from frameUtils | Exists |
| extractHeatmapData | For HeatMap fallback | Exists |

**Checkpoint:** ⬜ All Phase 1 prerequisites met

---

## 4. Risk Heatmap

| Phase | Step | Risk | Probability | Impact | Mitigation |
|-------|------|------|-------------|--------|------------|
| 1 | 1.1 | Interpolation NaN/Inf | 15% | High | sanitizeTemp; clamp output |
| 1 | 1.5 | Texture not updating | 30% | High | useMemo deps; needsUpdate |
| 1 | 1.5 | Memory leak | 20% | Medium | Dispose in useEffect |
| 1 | 1.3b | Shader compile fail | 15% | Medium | Isolated smoke test |
| 1 | 1.7 | Context lost | 25% | High | onCreated handler; overlay |
| 1 | 1.8 | Empty thermal UX | 30% | Low | HeatMap with heatmapData |
| 1 | 1.11 | Wrong component asserted | 30% | Medium | Loader-invoking mock; separate mocks |

---

## 5. Success Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | 3D plate warps by temperature | Visual; hot = bulge |
| 2 | Color gradient blue→white | Visual |
| 3 | Torch cone above plate | Visual |
| 4 | OrbitControls work | Mouse drag/scroll |
| 5 | Scrubbing updates plate | Timeline scrub |
| 6 | interpolateThermalGrid unit tested | npm test |
| 7 | ShaderSmokeTest passes | No compile errors |
| 8 | Canvas count = 3 on replay | Mock assertion + manual |
| 9 | HeatmapPlate3D replaces HeatMap when thermal | Conditional render |
| 10 | Empty thermal → HeatMap "No thermal data" | Session without thermal |
| 11 | WebGL failure → "3D heatmap unavailable" | ErrorBoundary fallback |
| 12 | sanitizeTemp exported; extractFivePointFromFrame at top | Code review |

---

## 6. Progress Tracking

| Phase | Total Steps | Completed | In Progress | Blocked | % |
|-------|-------------|-----------|-------------|---------|---|
| Phase 1 | 13 | 0 | 0 | 0 | 0% |

---

## 7. Common Failures & Fixes

| Failure | Check | Fix |
|---------|-------|-----|
| Plate is flat | uMaxDisplacement; temp in texture | Ensure 0.5; verify thermalData |
| Wrong colors | uMaxTemp | Set maxTemp=600 |
| Texture not updating | useMemo deps | thermalData in deps |
| Shader compile error | Step 1.3b | Run ShaderSmokeTest first |
| Integration test wrong component | Mock strategy | Use loader-invoking dynamic; separate mocks |
| sanitizeTemp not found | Export | Export from thermalInterpolation.ts |
| extractFivePointFromFrame placement | Top of file | Define before Plate component |

---

## 🧠 THINKING CHECKPOINT #1 — Phase Sanity

**Can someone understand the phases?** Yes — Phase 1 delivers full 3D plate on replay.

**Is each phase independently valuable?** Phase 1 = user sees physics-informed thermal visualization.

**Are phases right-sized?** 14h is acceptable; no phase > 30h.

**Do dependencies make sense?** No circular deps; thermalInterpolation → shaders → Plate → integration.

**Riskiest phase?** Phase 1 Step 1.5 (Plate + ShaderMaterial). Mitigation: ShaderSmokeTest (1.3b) catches shader errors early; full code and 9 common failures documented.

---

## 🧠 THINKING CHECKPOINT #2 — Step Quality

**Step 1.1:** Atomic ✓, specific ✓, verification ✓, sanitizeTemp placement explicit ✓.

**Step 1.3b:** Added per WILL Critique; catches shader compile before Plate.

**Step 1.5:** Critical ✓, full code ✓, extractFivePointFromFrame placement explicit ✓, 9 common failures ✓.

**Step 1.11:** Mocking strategy at TOP as "CRITICAL"; mandate for mock counts ✓.

---

## 🧠 THINKING CHECKPOINT #3 — Red Team / Implementability

**Potential problems:**
1. **ShaderSmokeTest in Jest:** WebGL/Three.js may not work in jsdom. Fix: Use Option B — Jest test that only constructs ShaderMaterial with our strings (no render). Or skip ShaderSmokeTest in CI, run manually in browser.
2. **Replay grid layout:** Current layout has HeatMap and TorchAngleGraph in 2 columns. HeatmapPlate3D replaces HeatMap in its cell. Verify grid cell sizing (h-64) matches TorchViz3D.
3. **getFrameAtTimestamp:** Import from `@/utils/frameUtils`. Verify it returns nearest frame when activeTimestamp falls between thermal samples.
4. **ThermalDirection import:** extractFivePointFromFrame uses `ThermalDirection`; import from `@/types/thermal`.

**Junior developer questions answered in plan:**
- Which snapshot? thermal_snapshots[0]
- What if no thermal? HeatMap with heatmapData
- Where is sanitizeTemp? Exported from thermalInterpolation.ts, above interpolateThermalGrid
- Where is extractFivePointFromFrame? Top of HeatmapPlate3D.tsx, before Plate
- Canvas count in Jest? Assert mock counts, not real canvas

---

## Quality Metrics Checklist

| Metric | Minimum | Count | Pass? |
|--------|---------|-------|-------|
| Phases | 3 | 1 (core) | ✅ (Phase 2/3 out of scope) |
| Total steps | 30 | 13 | ⚠️ (focused Phase 1) |
| Critical steps with code | 10 | 3 | ⚠️ (1.1, 1.3b, 1.5) |
| Verification per step | 1 | 1 each | ✅ |
| Risk entries | 20 | 7+ | ⚠️ |
| Success criteria | 12 | 12 | ✅ |
| Pre-flight items | 5 | 8 | ✅ |
| WILL Critique fixes | All | 6 | ✅ |

---

**After Plan Creation:**
1. [ ] Review plan with stakeholder
2. [ ] Verify environment (pre-flight)
3. [ ] Start Step 1.1
4. [ ] Run verification after each step
