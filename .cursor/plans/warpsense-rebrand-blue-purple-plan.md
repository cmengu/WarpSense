# WarpSense Rebrand — Blue/Purple Palette — Implementation Plan

**Issue:** `.cursor/issues/warpsense-rebrand-blue-purple-palette.md`  
**Exploration:** `.cursor/explore-outputs/warpsense-rebrand-blue-purple-exploration.md`  
**Date:** 2026-02-16  
**Estimated Total Effort:** 16–20 hours  
**Phases:** 4  
**Total Steps:** 35+

---

## MANDATORY PRE-PLANNING THINKING SESSION

### A. Exploration Review and Synthesis

**1. Core approach in one sentence:**  
Create a centralized `constants/theme.ts` with blue→purple thermal anchors, chart palette, and semantic hex colors; update heatmapData, heatmapShaderUtils, and GLSL shader atomically to blue→purple; use Tailwind `blue-*`, `purple-*`, `violet-*` classes across all UI components; replace "Shipyard Welding" with "WarpSense" in demo, layouts, deploy scripts, and docs.

**2. Key decisions:**
- **theme.ts:** Single source of truth for hex (Recharts, Three.js, heatmap)
- **8 anchors:** Standardize thermal gradient on 8 steps (blue→purple) across heatmapData, heatmapShaderUtils, GLSL
- **Delta heatmap:** blue (B hotter) → white → purple (A hotter)
- **Expert = blue-400, Novice = purple-400**
- **Error = violet-600** (no red)
- **Docker container names unchanged** (out of scope)

**3. Major components:**
- **Component 1: theme.ts** — Centralized palette constants (THERMAL_ANCHORS, CHART_PALETTE, semantic hex)
- **Component 2: Thermal pipeline** — heatmapData.ts, heatmapShaderUtils.ts, heatmapFragment.glsl.ts (must stay in sync)
- **Component 3: Delta heatmap** — deltaHeatmapData.ts (blue→white→purple)
- **Component 4: Charts** — PieChart, BarChart, mockData (blue/purple palette)
- **Component 5: 3D components** — TorchWithHeatmap3D, HeatmapPlate3D (getWeldPoolColor, lights, Tailwind)
- **Component 6: Pages** — demo, landing, replay, compare, dashboard, **seagull** (branding, accents, error)
- **Component 7: Docs/scripts** — deploy.sh, Dockerfiles, CONTEXT.md, DEPLOY.md, .env.example

**4. Data flow:**
```
Input: Temperature (°C), delta (°C), session data
  ↓
theme.ts (anchors, palette)
  ↓
heatmapData / heatmapShaderUtils / GLSL (thermal color)
  ↓
deltaHeatmapData (delta color)
  ↓
Output: Hex colors for HeatMap, 3D thermal plate, charts
```

**5. Biggest risks:**
1. **Thermal source drift** — heatmapData vs shader vs heatmapShaderUtils produce different colors for same temp
2. **Missed colors** — Green/red/cyan in obscure component breaks "no rainbow"
3. **Test brittleness** — Tests assert exact hex; changing palette breaks them
4. **Purple danger** — Users may not recognize purple as error
5. **Chart distinguishability** — 6 blue/purple shades may be hard to tell apart
6. **Range [0,500] vs sensor data** — Real welding temps >500°C will clamp to max purple; verify against typical sensor range (most thermal sensors report within 0–600°C).

**6. Gaps exploration did NOT answer:**
- Exact 8 anchor hex values for smooth blue→purple (prototype showed 5; we need 8)
- Whether heatmapData clamp range stays [20, 600] or shifts to [0, 500] to match shader
- LineChart default color if used elsewhere

**Synthesis (400+ words):**  
The WarpSense rebrand spans two dimensions: name change and color palette. The name change is straightforward—find-and-replace "Shipyard Welding" with "WarpSense" in ~10 files. The color palette change is the hard part. Three thermal systems must stay in sync: heatmapData.ts (2D CSS heatmap via tempToColor), heatmapShaderUtils.ts (TypeScript mirror for tests), and heatmapFragment.glsl.ts (3D thermal plate GPU). Currently all use a rainbow blue→cyan→teal→green→yellow→orange→red gradient. We replace this with blue→indigo→violet→purple (8 anchors). The exploration recommended 8 anchors to match the shader's existing structure. heatmapData currently has 13 anchors with [20, 600]°C; we will reduce to 8 anchors and optionally adjust range to [0, 500] for consistency. **Range impact:** Temps >500°C will clamp to max purple; if real sensor data exceeds 500°C, verify against typical sensor range—most welding thermal sensors report within 0–600°C, so [0,500] is acceptable; document this in Known Issues. The delta heatmap (compare page) uses blue→white→red; we change the +50°C end from red to purple. Charts (PieChart, BarChart) use DEFAULT_COLORS with green, amber, red, pink; we replace with 6 blue/purple hex values. 3D components (TorchWithHeatmap3D, HeatmapPlate3D) have cyan borders, green status, amber warnings, and getWeldPoolColor uses cold→cyan→yellow→white; we change to cold blue→purple→white and cyan→blue, green→blue, amber→purple. Error panels across demo, replay, compare, dashboard, **seagull** use red/amber; we change to violet-600. Expert vs Novice: green vs red becomes blue vs purple. HeatMap active column outline is rgb(34 197 94) (green); we change to blue-500. TorchAngleGraph target line is #22c55e (green); we change to purple-500. Tests assert specific hex values and must be updated in the same PR. A grep for color keywords (green, red, cyan, amber, etc.) will catch misses. We do all changes in one PR to avoid partial states.

---

### B. Dependency Brainstorm

**Major work items (before ordering):**
1. Create theme.ts
2. Update heatmapData TEMP_COLOR_ANCHORS
3. Update heatmapShaderUtils ANCHOR_COLORS
4. Update heatmapFragment.glsl.ts anchor colors
5. Add theme sync test (heatmapData vs heatmapShaderUtils)
6. Update deltaHeatmapData deltaTempToColor
7. Update PieChart DEFAULT_COLORS
8. Update BarChart default color
9. Update mockData chart colors
10. Update HeatMap active outline
11. Update TorchAngleGraph target stroke
12. Update TorchWithHeatmap3D (getWeldPoolColor, lights, Tailwind)
13. Update HeatmapPlate3D Tailwind
14. Update demo page (branding, expert/novice, accents, error)
15. Update demo layout metadata
16. Update landing page gradients, stats, cards
17. Update DemoLayoutClient error
18. Update replay page error, loading
19. Update compare page error, warning, delta legend
20. Update dashboard page error, CTA
21. **Update seagull welder error (red→violet), seagull dashboard (amber→violet)**
22. Update AppNav Demo link
23. Update deploy.sh
24. Update .env.example
25. Update Dockerfiles
26. Update CONTEXT.md, DEPLOY.md
27. Update heatmapData.test.ts
28. Update HeatMap.test.tsx
29. Update heatmapShaderUtils.test.ts
30. Update deltaHeatmapData.test.ts
31. Update demo page.test.tsx
32. Visual QA pass

**Dependency graph:**
```
theme.ts (1)
  ↓
heatmapData (2), heatmapShaderUtils (3), heatmapFragment (4)
  ↓
theme sync test (5)
deltaHeatmapData (6)
  ↓
PieChart (7), BarChart (8), mockData (9), HeatMap (10), TorchAngleGraph (11)
  ↓
TorchWithHeatmap3D (12), HeatmapPlate3D (13)
  ↓
demo (14,15), landing (16), DemoLayoutClient (17), replay (18), compare (19), dashboard (20), seagull (21), AppNav (22)
  ↓
deploy (23), .env (24), Dockerfiles (25), CONTEXT (26), DEPLOY (27)
  ↓
Tests (28,29,30,31), QA (32)
```

**Critical path:** theme.ts → thermal triad (2,3,4) → delta (6) → charts/components → pages → docs → tests

**Parallelizable:** (7,8,9) can run together; (10,11) together; (12,13) together; pages (14–21) can be batched; docs (23–27) together.

---

### C. Risk-Based Planning

**Top 5 risks:**

1. **Thermal source drift** (P: 30%, Impact: High)  
   - Mitigate: Single PR; add sync test comparing heatmapData.tempToColor vs heatmapShaderUtils.temperatureToColor for sample temps  
   - Detect: Test fails if outputs diverge  
   - Contingency: Revert thermal changes, fix anchors, re-apply

2. **Missed colors** (P: 50%, Impact: Medium)  
   - Mitigate: Grep `green|red|cyan|amber|yellow|orange|pink|emerald|teal|lime` before and after  
   - Detect: Visual QA; grep returns hits  
   - Contingency: Second pass to fix stragglers

3. **Test brittleness** (P: 90%, Impact: Low)  
   - Mitigate: Update all color assertions in same PR as color changes  
   - Detect: CI fails  
   - Contingency: Fix assertions to match new palette

4. **Purple danger less recognizable** (P: 25%, Impact: Low)  
   - Mitigate: Strong violet-600; clear "Error" label; iconography  
   - Detect: User feedback  
   - Contingency: Add red as exception for critical errors (document)

5. **Chart segment indistinguishability** (P: 40%, Impact: Low)  
   - Mitigate: 6 distinct shades; test with real dashboard data  
   - Detect: Visual QA  
   - Contingency: Add luminance variation or patterns

**Failure modes:**
- If theme.ts wrong: All thermal/chart colors wrong → fix theme, cascade
- If shader out of sync: 3D plate shows different colors than 2D heatmap → sync test catches
- If tests not updated: CI blocks merge → update tests
- If demo page still says Shipyard: User sees old brand → grep for Shipyard before merge
- If landing has green: Rainbow persists → grep for green-* before merge
- If seagull routes missed: Red/amber persists in /seagull and /seagull/welder/[id] → Phase 3 includes seagull

---

## Phase Breakdown

### Phase 1: Foundation — theme.ts and Thermal Pipeline (6–8 hours)

**Goal:** Centralized palette exists; thermal gradient is blue→purple everywhere; 2D heatmap and 3D thermal plate show identical colors for same temperature.

**Delivered value:** Developer has single source of truth; thermal viz uses blue/purple only.

**Why first:** Everything else depends on palette definition and thermal consistency.

**Risk level:** 🟡 Medium (thermal sync risk)

**Major steps:**
1. Create theme.ts
2. Update heatmapData to use theme.ts anchors
3. Update heatmapShaderUtils to match
4. Update heatmapFragment.glsl.ts anchor colors
5. Add thermal sync test
6. Update deltaHeatmapData
7. Run heatmapData, heatmapShaderUtils, deltaHeatmapData tests

---

### Phase 2: Components — Charts and Welding UI (4–5 hours)

**Goal:** PieChart, BarChart, mockData, HeatMap, TorchAngleGraph, TorchWithHeatmap3D, HeatmapPlate3D use blue/purple only.

**Delivered value:** All reusable components respect palette.

**Why second:** Components are used by pages; pages depend on components.

**Risk level:** 🟢 Low

**Major steps:**
1. Update PieChart DEFAULT_COLORS
2. Update BarChart default color
3. Update mockData chart colors
4. Update HeatMap active outline
5. Update TorchAngleGraph target/stroke
6. Update TorchWithHeatmap3D (getWeldPoolColor, lights, Tailwind)
7. Update HeatmapPlate3D Tailwind
8. Update HeatMap.test.tsx

---

### Phase 3: Pages — Demo, Landing, Replay, Compare, Dashboard, Seagull (4–5 hours)

**Goal:** All pages show WarpSense branding; expert/novice use blue/purple; error states use violet; no rainbow colors; seagull routes included.

**Delivered value:** User-facing surfaces rebranded.

**Why third:** Pages compose components; branding and error UI live here.

**Risk level:** 🟢 Low

**Major steps:**
1. Demo page: branding, expert/novice, accents, error
2. Demo layout metadata
3. Landing page gradients, stats, cards
4. DemoLayoutClient, replay, compare, dashboard error/loading
5. **Seagull welder error (red→violet), seagull dashboard (amber→violet)**
6. AppNav Demo link
7. Update demo page.test.tsx
8. Compare page delta legend
9. Replay page 3D loading and error
10. Compare page amber warning

---

### Phase 4: Docs, Scripts, Final QA (2–3 hours)

**Goal:** deploy.sh, .env, Dockerfiles, CONTEXT, DEPLOY reference WarpSense; all tests pass; no color leaks.

**Delivered value:** Deploy and docs consistent; CI green; visual QA complete.

**Why last:** Low risk; can be done in parallel with any Phase 3 polish.

**Risk level:** 🟢 Low

**Major steps:**
1. deploy.sh, .env.example
2. Dockerfiles
3. CONTEXT.md, DEPLOY.md
4. Final grep for color keywords (exclude .cursor, node_modules, *.test.ts until tests updated—tests are updated in Phases 1–3 before Phase 4 grep)
5. Visual QA checklist (including seagull)
6. Run full test suite

---

## Phase 1 — Foundation (Detail)

**Time:** 6–8 hours | **Risk:** 🟡 Medium

---

### 🟥 Step 1.1: Create constants/theme.ts — *Critical: Single source of truth*

**Why critical:** All thermal, chart, and semantic colors derive from here. Wrong values cascade everywhere.

**What:** Create `my-app/src/constants/theme.ts` with THERMAL_COLOR_ANCHORS (8 steps, [temp, r, g, b]), CHART_PALETTE (6 hex), EXPERT_HEX, NOVICE_HEX, ERROR_HEX, and ANCHOR_COLORS_0_1 for shader/utils (0–1 normalized RGB).

**Files:** Create `my-app/src/constants/theme.ts`

**Code:**

```typescript
/**
 * WarpSense theme — blue/purple-only dark palette.
 * Single source of truth for thermal gradient, chart colors, semantic colors.
 * Thermal: 8 anchors, 0–500°C, blue (cold) → purple (hot).
 *
 * THERMAL_ANCHOR_COLORS_0_1: Array index i maps to shader anchorPos[i].
 * Shader positions are [0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0] (not 0.125, 0.25, etc.).
 * Keep heatmapData, heatmapShaderUtils, and GLSL aligned using these positions.
 */

/** 8 anchors [temp_celsius, r, g, b] for thermal gradient. Range [0, 500]°C. */
export const THERMAL_COLOR_ANCHORS: [number, number, number, number][] = [
  [0, 30, 58, 138],    // blue-900 #1e3a8a
  [62, 37, 99, 235],   // blue-600 #2563eb
  [125, 79, 70, 229],  // indigo-600 #4f46e5
  [187, 99, 102, 241], // indigo-500 #6366f1
  [250, 124, 58, 237], // violet-600 #7c3aed
  [312, 139, 92, 246], // purple-500 #8b5cf6
  [375, 168, 85, 247], // purple-500 #a855f7
  [500, 168, 85, 247], // purple-500 (max)
];

/**
 * 0–1 RGB at 8 positions for heatmapShaderUtils and GLSL shader.
 * Array index i maps to shader anchorPos[i]; positions are [0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0].
 */
export const THERMAL_ANCHOR_COLORS_0_1: readonly [number, number, number][] = [
  [0.12, 0.23, 0.54],  // position 0
  [0.15, 0.39, 0.92],  // position 0.1
  [0.31, 0.27, 0.90],  // position 0.2
  [0.39, 0.40, 0.95],  // position 0.3
  [0.49, 0.23, 0.93],  // position 0.5
  [0.55, 0.36, 0.96],  // position 0.7
  [0.66, 0.33, 0.97],  // position 0.9
  [0.66, 0.33, 0.97],  // position 1.0
];

/** Chart palette: 6 blue/purple hex values. */
export const CHART_PALETTE = [
  '#2563eb', '#4f46e5', '#7c3aed', '#8b5cf6', '#6366f1', '#9333ea',
];

/** Expert welder accent (blue). */
export const EXPERT_HEX = '#2563eb';

/** Novice welder accent (purple). */
export const NOVICE_HEX = '#a855f7';

/** Error/danger (violet). */
export const ERROR_HEX = '#7c3aed';

/** HeatMap active column outline. */
export const ACTIVE_COLUMN_HEX = '#3b82f6';

/** TorchAngleGraph target line. */
export const TARGET_LINE_HEX = '#a855f7';
```

**Subtasks:**
- [ ] Create file
- [ ] Export all constants
- [ ] Add JSDoc comments

**Note:** If `constants/index.ts` barrel exists, add theme export there.

**Verification:** Import theme in a test file; assert THERMAL_COLOR_ANCHORS.length === 8; assert CHART_PALETTE has no green/red/amber.

**Time:** 0.5 h

---

### 🟥 Step 1.2: Update heatmapData.ts to use theme anchors — *Critical: Thermal consistency*

**What:** Replace TEMP_COLOR_ANCHORS with import from theme; adjust tempToColor clamp range to [0, 500] to match theme.

**Files:** Modify `my-app/src/utils/heatmapData.ts`

**Code change:**

```typescript
import { THERMAL_COLOR_ANCHORS } from '@/constants/theme';

const TEMP_COLOR_ANCHORS = THERMAL_COLOR_ANCHORS;

export function tempToColor(temp_celsius: number): string {
  const t = Math.max(0, Math.min(500, temp_celsius));
  for (let i = 0; i < TEMP_COLOR_ANCHORS.length - 1; i++) {
    const [t0, r0, g0, b0] = TEMP_COLOR_ANCHORS[i];
    const [t1, r1, g1, b1] = TEMP_COLOR_ANCHORS[i + 1];
    if (t >= t0 && t <= t1) {
      const p = (t - t0) / (t1 - t0);
      const r = Math.round(r0 + (r1 - r0) * p);
      const g = Math.round(g0 + (g1 - g0) * p);
      const b = Math.round(b0 + (b1 - b0) * p);
      return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
    }
  }
  const last = TEMP_COLOR_ANCHORS[TEMP_COLOR_ANCHORS.length - 1];
  const [, r, g, b] = last;
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}
```

**tempToColorRange:** In `heatmapData.ts` near line 118, change remap from `const t = 20 + p * (600 - 20)` to `const t = p * 500` so normalized [0,1] maps to [0, 500]°C:

```typescript
return (temp_celsius: number) => {
  const p = Math.max(0, Math.min(1, (temp_celsius - minTemp) / span));
  const t = p * 500;
  return tempToColor(t);
};
```

**Verification Test:**
- Setup: Import tempToColor from heatmapData
- Action: Call tempToColor(0), tempToColor(250), tempToColor(500)
- Expect: tempToColor(0) = #1e3a8a (dark blue); tempToColor(250) = #7c3aed (indigo/violet); tempToColor(500) = #a855f7 (purple)
- Pass: No #ef4444, #eab308, #10b981 in outputs; cold=blue, hot=purple

**Common failures:**
- If tempToColor returns old colors: THERMAL_COLOR_ANCHORS not imported; check import path
- If clamp wrong: Verify Math.max(0, Math.min(500, temp)) in tempToColor

**Time:** 0.75 h

---

### 🟥 Step 1.3: Update heatmapShaderUtils.ts ANCHOR_COLORS — *Critical: Must match GLSL*

**What:** Replace local ANCHOR_COLORS definition with import from theme.THERMAL_ANCHOR_COLORS_0_1.

**Files:** Modify `my-app/src/utils/heatmapShaderUtils.ts`

**Code:**
```typescript
import { THERMAL_ANCHOR_COLORS_0_1 } from '@/constants/theme';

const ANCHOR_COLORS = THERMAL_ANCHOR_COLORS_0_1;
// Remove the local ANCHOR_COLORS array definition (lines ~18–28)
```

**Verification:** temperatureToColor(0, 500, 10, 0) returns cool blue [r~0.12, g~0.23, b>0.5]; temperatureToColor(0, 500, 10, 500) returns purple [r~0.66, b~0.97].

**Time:** 0.5 h

---

### 🟥 Step 1.4: Update heatmapFragment.glsl.ts anchor colors — *Critical: GPU thermal viz*

**What:** Replace anchorCol[0..7] vec3 values with 0–1 RGB from theme. Since GLSL can't import TS, copy values into shader string.

**Files:** Modify `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts`

**Code:** Replace the entire anchorCol block (lines 29–37) with this complete block. Positions stay [0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]; colors come from THERMAL_ANCHOR_COLORS_0_1:

```glsl
  vec3 anchorCol[8];
  anchorCol[0] = vec3(0.12, 0.23, 0.54);
  anchorCol[1] = vec3(0.15, 0.39, 0.92);
  anchorCol[2] = vec3(0.31, 0.27, 0.90);
  anchorCol[3] = vec3(0.39, 0.40, 0.95);
  anchorCol[4] = vec3(0.49, 0.23, 0.93);
  anchorCol[5] = vec3(0.55, 0.36, 0.96);
  anchorCol[6] = vec3(0.66, 0.33, 0.97);
  anchorCol[7] = vec3(0.66, 0.33, 0.97);
```

**Verification:** 3D thermal plate at /replay or /demo shows blue→purple gradient; no yellow/red.

**Time:** 0.75 h

---

### 🟥 Step 1.5: Add thermal sync test — *Critical: Prevents drift*

**What:** Create test that samples temps (0, 100, 250, 400, 500), calls tempToColor and temperatureToColor (mapping temp to same normalized space), and asserts hex from tempToColor matches rgb-to-hex of temperatureToColor within tolerance.

**Files:** Add to `my-app/src/__tests__/utils/heatmapData.test.ts` (preferred, keeps thermal tests colocated) or create new `my-app/src/__tests__/utils/heatmapSync.test.ts` if heatmapData.test.ts grows too large

**Verification Test:**
- Setup: Import tempToColor, temperatureToColor, theme THERMAL_COLOR_ANCHORS
- Action: For temps [0, 62, 125, 250, 375, 500], get hex from tempToColor and rgb from temperatureToColor(0, 500, 10, t); convert rgb to hex
- Expect: Hex values match within rounding (e.g. ±1 per channel)
- Pass: All 6 sample temps produce matching colors

**RGB-to-hex conversion (heatmapShaderUtils returns [r,g,b] in 0-1):**
```typescript
const toHex = (c: number) => Math.round(c * 255).toString(16).padStart(2, '0');
const rgbToHex = (r: number, g: number, b: number) =>
  '#' + toHex(r) + toHex(g) + toHex(b);
// Example: temperatureToColor(0, 500, 10, t) returns [r,g,b]; use rgbToHex(r,g,b)
```

**Common failures:**
- Mismatch at boundaries: Anchor positions in shader might differ; align ANCHOR_POSITIONS with theme [0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]
- NaN/Infinity: Both utilities should handle; optionally add `expect(tempToColor(NaN)).toBeDefined()` or document that NaN behavior is implementation-dependent and skip if not critical

**Optional edge-case test (if NaN handling is desired):**
```typescript
expect(tempToColor(NaN)).toBeDefined(); // no throw; behavior implementation-dependent
```

**Time:** 0.5 h

---

### 🟥 Step 1.6: Update deltaHeatmapData.ts — blue→white→purple

**What:** Change +50 branch from red to purple. Current: white→red (r=255, g/b decrease). New: white→purple (r=168, g=85, b=247 at +50).

**Files:** Modify `my-app/src/utils/deltaHeatmapData.ts`

**Code:**
```typescript
} else {
  // white (0) → purple (+50)  #a855f7
  const p = d / 50;
  r = Math.round(255 - (255 - 168) * p);
  g = Math.round(255 - (255 - 85) * p);
  b = Math.round(255 - (255 - 247) * p);
}
```

**Verification Test:**
- Setup: Import deltaTempToColor
- Action: Call deltaTempToColor(-50), deltaTempToColor(0), deltaTempToColor(50)
- Expect: -50 → blue (b > r); 0 → #ffffff; +50 → purple (r~168, g~85, b~247)
- Pass: No red at +50; white at 0

**Note on NaN:** Current impl uses `Math.max(-50, Math.min(50, d))`; NaN propagates and can produce invalid output. Low risk for compare page. Optionally add `expect(deltaTempToColor(NaN)).toBeDefined()` or guard in implementation: `if (Number.isNaN(d)) return '#ffffff';`

**Common failures:**
- +50 still red: Branch (d > 0) not updated; check else block
- Purple too dark: Use #a855f7 RGB (168, 85, 247)

**Time:** 0.25 h

---

### 🟥 Step 1.7: Update heatmapData, heatmapShaderUtils, deltaHeatmapData tests

**What:** Fix assertions that expect old rainbow colors.

**heatmapData.test.ts:**
- tempToColor(20) → tempToColor(0): expect dark blue hex #1e3a8a
- tempToColor(320) yellow → tempToColor(250): expect indigo/violet hex #7c3aed (no #eab308)
- tempToColor(600) red → tempToColor(500): expect purple hex #a855f7
- tempToColorRange(400, 550): atMin maps to p=0→t=0→#1e3a8a; atMax maps to p=1→t=500→#a855f7
- **Rename test:** "clamps temps below 20 to 20" → "clamps temps below 0 to 0" — new range [0,500]; tempToColor(-50) should equal tempToColor(0) = #1e3a8a
- Clamp tests: tempToColor(0), tempToColor(-50) clamps to 0→#1e3a8a; tempToColor(800) clamps to 500→#a855f7
- **Expert/novice semantics:** Old tests assert yellow-ish (g>50, r>b) at ~490°C and red-ish (r>150, b<100) at ~520°C. After rebrand both map to purple (b>r). Update to purple-ish assertions:
  - "expert ~490°C at center distance yields yellow-ish" → "expert ~490°C yields purple-ish": expect rgb.b > rgb.r (purple has higher B); expect rgb.r > 100
  - "novice spike ~520°C yields red-ish" → "novice spike ~520°C yields purple-ish": expect rgb.b > rgb.r; expect rgb.r > 100

**Exact assertions:**
```typescript
// tempToColor
expect(tempToColor(0).toLowerCase()).toBe("#1e3a8a");
expect(tempToColor(250).toLowerCase()).toBe("#7c3aed");
expect(tempToColor(500).toLowerCase()).toBe("#a855f7");

// tempToColorRange(400, 550)
const fn = tempToColorRange(400, 550);
expect(fn(400).toLowerCase()).toBe("#1e3a8a");
expect(fn(550).toLowerCase()).toBe("#a855f7");

// Clamp (range [0,500]: below 0 clamps to 0, above 500 clamps to 500)
expect(tempToColor(-50).toLowerCase()).toBe("#1e3a8a");
expect(tempToColor(800).toLowerCase()).toBe("#a855f7");
expect(tempToColor(0).toLowerCase()).toBe("#1e3a8a");

// Expert/novice purple-ish (replace yellow-ish/red-ish semantics)
// expert ~490°C: purple-ish (b > r)
const rgb490 = { r: parseInt(tempToColor(490).slice(1,3),16), g: parseInt(tempToColor(490).slice(3,5),16), b: parseInt(tempToColor(490).slice(5,7),16) };
expect(rgb490.b).toBeGreaterThan(rgb490.r);
expect(rgb490.r).toBeGreaterThan(100);
// novice ~520°C: purple-ish (b > r, clamped to 500)
const rgb520 = { r: parseInt(tempToColor(520).slice(1,3),16), g: parseInt(tempToColor(520).slice(3,5),16), b: parseInt(tempToColor(520).slice(5,7),16) };
expect(rgb520.b).toBeGreaterThan(rgb520.r);
expect(rgb520.r).toBeGreaterThan(100);
```

**heatmapShaderUtils.test.ts:**
- **"returns cool blue at 0°C"** — Update for new THERMAL_ANCHOR_COLORS_0_1[0] (0.12, 0.23, 0.54):
  ```typescript
  const [r, g, b] = temperatureToColor(0, 500, 10, 0);
  expect(r).toBeCloseTo(0.12, 2);
  expect(g).toBeCloseTo(0.23, 2);
  expect(b).toBeGreaterThan(0.5);
  ```
- **"returns bright red at 500°C"** → **"returns purple at 500°C"** — THERMAL_ANCHOR_COLORS_0_1[7] (0.66, 0.33, 0.97):
  ```typescript
  const [r, g, b] = temperatureToColor(0, 500, 10, 500);
  expect(r).toBeCloseTo(0.66, 2);
  expect(g).toBeCloseTo(0.33, 2);
  expect(b).toBeGreaterThan(0.9);
  ```

**deltaHeatmapData.test.ts:**
- "+50 to red" → "+50 to purple": expect r≈168, g≈85, b≈247 (or b > r)

**Files:** Modify `my-app/src/__tests__/utils/heatmapData.test.ts`, `heatmapShaderUtils.test.ts`, `deltaHeatmapData.test.ts`

**Verification:** All tests pass.

**Time:** 1 h

---

**Phase 1 Total:** ~4.25 h (steps) + buffer 2 h = **6–7 h**

---

## Phase 2 — Components (Detail)

**Time:** 4–5 hours

---

### 🟥 Step 2.1: Update PieChart DEFAULT_COLORS

**What:** Replace with CHART_PALETTE from theme or inline blue/purple hex array.

**Files:** Modify `my-app/src/components/charts/PieChart.tsx`

**Code:** `const DEFAULT_COLORS = ['#2563eb','#4f46e5','#7c3aed','#8b5cf6','#6366f1','#9333ea'];`

**Verification:** Render PieChart with 6 segments; all segments blue/purple; no green/amber/red.

**Time:** 0.25 h

---

### 🟥 Step 2.2: Update BarChart default color

**What:** Change `color = '#10b981'` to `color = '#2563eb'` or theme import.

**Files:** Modify `my-app/src/components/charts/BarChart.tsx`

**Verification:** BarChart renders with blue bars.

**Time:** 0.1 h

---

### 🟥 Step 2.3: Update mockData chart colors

**What:** Replace green (#10b981) and amber (#f59e0b) with blue/purple hex from CHART_PALETTE.

**Files:** Modify `my-app/src/data/mockData.ts`

**Specific changes:**
- Line 79, `color: '#10b981'` (Revenue by Category) → `color: '#2563eb'` or `CHART_PALETTE[0]`
- Line 118, `color: '#f59e0b'` (Top Clicked Elements) → `color: '#6366f1'` or another CHART_PALETTE value
- Verify no other green/amber hex elsewhere in file (lines 65, 102 already use blue/purple; confirm only these two need change)

**Locate old colors (optional, copy-pasteable):**
```bash
rg '#10b981|#f59e0b' my-app/src/data/mockData.ts
```
Line numbers 79 and 118 are correct as of the current codebase; if mockData structure changes, run the command above before editing.

**Verification:** Dashboard charts (if used) show blue/purple; grep mockData.ts for #10b981, #f59e0b returns no hits.

**Time:** 0.25 h

---

### 🟥 Step 2.4: Update HeatMap active column outline

**What:** Replace `rgb(34 197 94)` with `rgb(59 130 246)` (blue-500) or theme ACTIVE_COLUMN_HEX.

**Files:** Modify `my-app/src/components/welding/HeatMap.tsx`

**Code:** `outline: '2px solid rgb(59 130 246)'` or import ACTIVE_COLUMN_HEX.

**Verification:** HeatMap with activeTimestamp shows blue outline on active column.

**Time:** 0.2 h

---

### 🟥 Step 2.5: Update TorchAngleGraph target and stroke

**What:** ReferenceLine stroke #22c55e → #a855f7 (purple). Line stroke #3b82f6 stays (blue). Or use theme constants.

**Files:** Modify `my-app/src/components/welding/TorchAngleGraph.tsx`

**Verification:** Target line is purple; angle line is blue.

**Time:** 0.2 h

---

### 🟥 Step 2.6: Update TorchWithHeatmap3D

**Locate Tailwind classes (optional helper):**
```bash
rg 'cyan|green|amber' my-app/src/components/welding/TorchWithHeatmap3D.tsx
```

**What:** 
- getWeldPoolColor: cold→cyan→yellow→white → cold blue→purple→white. Replace cyan with blue, yellow with purple.
- directionalLight color #22d3ee → #3b82f6 or #6366f1
- Tailwind: border-cyan-400 → border-blue-500, text-cyan-400 → text-blue-400, green-500 → blue-500, amber → violet-500
- Scale gradient: from-blue-600 via-cyan-400 to-amber-400 → from-blue-600 via-indigo-500 to-purple-500
- WebGL context loss overlay: amber → violet

**Files:** Modify `my-app/src/components/welding/TorchWithHeatmap3D.tsx`

**getWeldPoolColor:**
```typescript
function getWeldPoolColor(temp: number): THREE.Color {
  const cold = new THREE.Color(0x1e3a8a);  // blue-900
  const mid = new THREE.Color(0x6366f1);  // indigo-500
  const hot = new THREE.Color(0xa855f7);  // purple-500
  const white = new THREE.Color(0xf5f3ff); // violet-50
  if (temp < 250) return new THREE.Color().lerpColors(cold, mid, temp / 250);
  if (temp < 450) return new THREE.Color().lerpColors(mid, hot, (temp - 250) / 200);
  return new THREE.Color().lerpColors(hot, white, Math.min((temp - 450) / 100, 1));
}
```

**Verification:** 3D torch shows blue→purple weld pool; borders blue; no cyan/green/amber.

**Time:** 1 h

---

### 🟥 Step 2.7: Update HeatmapPlate3D

**What:** border-cyan-400 → border-blue-500; amber overlay → violet; text-cyan-400 → text-blue-400.

**Files:** Modify `my-app/src/components/welding/HeatmapPlate3D.tsx`

**Verification:** 3D heatmap plate has blue borders; context-loss overlay violet.

**Time:** 0.5 h

---

### 🟥 Step 2.8: Update HeatMap.test.tsx

**What:** Step 2 verification currently expects #3b82f6, #eab308, #ef4444 at 20, 310, 600°C. Update to new anchors:
- 0°C → #1e3a8a (dark blue)
- 250°C → #7c3aed (indigo/violet)
- 500°C → #a855f7 (purple)

Use these exact temps and hex for the test data and assertions.

**Files:** Modify `my-app/src/__tests__/components/welding/HeatMap.test.tsx`

**Code change:**
```typescript
// Update data points and assertions
points: [
  { timestamp_ms: 0, distance_mm: 10.0, temp_celsius: 0, direction: "center" },
  { timestamp_ms: 100, distance_mm: 10.0, temp_celsius: 250, direction: "center" },
  { timestamp_ms: 200, distance_mm: 10.0, temp_celsius: 500, direction: "center" },
  ...
],
// Assertions
expect(screen.getByTitle(/0\.0°C/)).toHaveStyle({ backgroundColor: '#1e3a8a' });
expect(screen.getByTitle(/250\.0°C/)).toHaveStyle({ backgroundColor: '#7c3aed' });
expect(screen.getByTitle(/500\.0°C/)).toHaveStyle({ backgroundColor: '#a855f7' });
```

**Verification:** Test passes with new palette.

**Time:** 0.5 h

---

**Phase 2 Total:** ~3 h + buffer 1 h = **4 h**

---

## Phase 3 — Pages (Detail)

**Time:** 4–5 hours

---

### 🟥 Step 3.1: Demo page — branding, expert/novice, accents, error

**Locate Tailwind classes (optional helper):**
```bash
rg 'from-green|to-emerald|green-400|red-400|border-cyan|text-cyan|border-red|border-green|bg-cyan' my-app/src/app/demo
```

**What:**
- "Shipyard Welding — Live Quality Analysis" → "WarpSense — Live Quality Analysis"
- border-cyan-400, text-cyan-400 → border-blue-500, text-blue-400
- Expert: green-400, green-900/20, border-green-400 → blue-400, blue-900/20, border-blue-400
- Novice: red-400, red-900/20, border-red-400 → purple-400, purple-900/20, border-purple-400
- Error panel: red-* → violet-* (border-violet-800, text-violet-400, bg-violet-600)
- Fallback heatmap border red-400 → violet-400
- Playback bar: bg-cyan-950, border-cyan-400, btn bg-cyan-400 → blue-950, border-blue-400, btn bg-blue-500
- Footer text-cyan-400 → text-blue-400

**Files:** Modify `my-app/src/app/demo/page.tsx`

**Verification:** Demo header says WarpSense; expert blue; novice purple; no green/red/cyan.

**Time:** 1 h

---

### 🟥 Step 3.2: Demo layout metadata

**What:** title: 'Live Demo — Shipyard Welding' → 'Live Demo — WarpSense'; description if present.

**Files:** Modify `my-app/src/app/demo/layout.tsx`

**Verification:** Browser tab shows "Live Demo — WarpSense".

**Time:** 0.1 h

---

### 🟥 Step 3.3: Landing page gradients and cards

**Locate Tailwind classes (optional helper):**
```bash
rg 'from-green|to-emerald|green-400|from-orange|to-red|orange-950|red-950|pink-400' my-app/src/app
```

**What:**
- Stats: from-blue-400 to-cyan-400 → from-blue-600 to-blue-400; from-purple-400 to-pink-400 → from-purple-600 to-violet-500; from-green-400 to-emerald-400 → from-indigo-600 to-violet-500
- Cards: from-green-950/40 to-emerald-950/40 → from-indigo-950/40 to-violet-950/40; from-orange-950/40 to-red-950/40 → from-violet-950/40 to-purple-950/40
- Icons: green-400, orange-400 → blue-400, violet-400
- "Major US Shipyards" stays (industry term)

**Files:** Modify `my-app/src/app/(marketing)/page.tsx`

**Verification:** All gradients blue/purple/indigo/violet; no green, orange, red, pink.

**Time:** 1 h

---

### 🟥 Step 3.4: Error/loading states — DemoLayoutClient, replay, compare, dashboard

**What:** All red-* error panels → violet-*; cyan CTA → blue.

**Files:** `DemoLayoutClient.tsx`, `replay/[sessionId]/page.tsx`, `compare/[sessionIdA]/[sessionIdB]/page.tsx`, `dashboard/page.tsx`

**Verification:** Error states use violet; no red.

**Time:** 0.75 h

---

### 🟥 Step 3.5: Seagull welder error and dashboard — red→violet, amber→violet

**What:**
- **seagull welder page** (`my-app/src/app/seagull/welder/[id]/page.tsx`): Error state uses bg-red-50, border-red-200, text-red-900, etc. Replace with violet: bg-violet-50 dark:bg-violet-950/30, border-violet-200 dark:border-violet-800, text-violet-900 dark:text-violet-200, text-violet-800 dark:text-violet-300.
- **seagull dashboard** (`my-app/src/app/seagull/page.tsx`): "Score unavailable" uses text-amber-600 dark:text-amber-400. Replace with text-violet-600 dark:text-violet-400.

**Files:** Modify `my-app/src/app/seagull/welder/[id]/page.tsx`, `my-app/src/app/seagull/page.tsx`

**Specific changes:**

**seagull/welder/[id]/page.tsx (error block, ~lines 132–136):**
```tsx
<div className="bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-800 rounded-lg p-6 max-w-md">
  <h2 className="text-lg font-bold text-violet-900 dark:text-violet-200">
    ⚠️ Error
  </h2>
  <p className="text-violet-800 dark:text-violet-300 mt-2 text-sm">{error}</p>
```

**seagull/page.tsx (line 99):**
```tsx
<span className="text-violet-600 dark:text-violet-400">
  Score unavailable
</span>
```

**Verification:** /seagull shows violet for "Score unavailable"; /seagull/welder/[id] error state uses violet (no red).

**Time:** 0.25 h

---

### 🟥 Step 3.6: AppNav Demo link

**What:** text-cyan-600 dark:text-cyan-400 → text-blue-600 dark:text-blue-400.

**Files:** Modify `my-app/src/components/AppNav.tsx`

**Verification:** Demo link is blue on hover/active.

**Time:** 0.1 h

---

### 🟥 Step 3.7: Compare page delta legend

**What:** "red = A hotter, blue = B hotter" → "purple = A hotter, blue = B hotter".

**Files:** Modify `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`

**Verification:** Legend text updated.

**Time:** 0.1 h

---

### 🟥 Step 3.8: Update demo page.test.tsx

**What:** "Shipyard Welding" → "WarpSense"; waitForDemoContent expects WarpSense.

**Files:** Modify `my-app/src/__tests__/app/demo/page.test.tsx`

**Verification:** Demo tests pass.

**Time:** 0.25 h

---

### 🟥 Step 3.9: Replay page 3D loading and error

**What:** border-cyan-400, text-cyan-400 loading → blue; red error → violet. Empty/error state borders.

**Files:** Modify `my-app/src/app/replay/[sessionId]/page.tsx`

**Verification:** Replay page uses blue/violet only.

**Time:** 0.25 h

---

### 🟥 Step 3.10: Compare page amber warning

**What:** amber-50, amber-900/20, border-amber-* → violet-50, violet-900/20, border-violet-* for warning box.

**Files:** Modify `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx`

**Verification:** Warning box uses violet.

**Time:** 0.1 h

---

**Phase 3 Total:** ~4 h + buffer 1 h = **5 h**

---

## Phase 4 — Docs, Scripts, Final QA

**Time:** 2–3 hours

---

### 🟥 Step 4.1: deploy.sh

**What:** "Shipyard Welding Platform" → "WarpSense Platform".

**Files:** Modify `deploy.sh`

**Verification:** Script runs; banner says WarpSense.

**Time:** 0.1 h

---

### 🟥 Step 4.2: .env.example

**What:** "Shipyard Welding" → "WarpSense".

**Files:** Modify `.env.example`

**Time:** 0.05 h

---

### 🟥 Step 4.3: Dockerfiles

**What:** "Shipyard Welding Frontend/Backend" → "WarpSense Frontend/Backend".

**Files:** Modify `my-app/Dockerfile`, `backend/Dockerfile`

**Time:** 0.1 h

---

### 🟥 Step 4.4: CONTEXT.md, DEPLOY.md

**What:** "WarpSense (Shipyard Welding MVP)" → "WarpSense"; DEPLOY "Shipyard Welding" → "WarpSense". Note: shipyard-welding clone path in DEPLOY can stay (repo name) or update if repo renamed.

**Files:** Modify `CONTEXT.md`, `DEPLOY.md`

**Time:** 0.2 h

---

### 🟥 Step 4.5: Final grep for color keywords

**What:** Grep `green|red|cyan|amber|yellow|orange|pink|emerald|teal|lime` in my-app/src to catch missed implementation code.

**Why exclude tests:** Tests (*.test.*, *.spec.*) are updated in Phases 1–3 to assert the new blue/purple palette. If grep finds old rainbow colors in tests, those tests were missed and should be fixed. The grep targets implementation code only—test files are expected to contain the new colors by design.

**Exclusions:** `.cursor`, `node_modules`, `*.test.*`, `*.spec.*`

**Command:**
```bash
rg 'green|red|cyan|amber|yellow|orange|pink|emerald|teal|lime' my-app/src --glob '!*.test.*' --glob '!*.spec.*'
```
Excluding .cursor and node_modules is implicit when grepping `my-app/src`. Fix any hits outside of intentional usage (e.g. "green" in a comment about "go" is fine).

**Time:** 0.5 h

---

### 🟥 Step 4.6: Visual QA checklist

**What:** Manually verify:
- [ ] /demo: WarpSense header, expert blue, novice purple, playback blue
- [ ] /: stats blue/purple gradients, cards blue/purple
- [ ] /replay/[id]: 3D thermal blue→purple, loading blue, error violet
- [ ] /compare: delta purple (A hotter), blue (B hotter), error violet
- [ ] Dashboard: error violet, CTA blue
- [ ] **/seagull: Score unavailable violet, no amber**
- [ ] **/seagull/welder/[id]: Error state violet, no red**
- [ ] HeatMap: active column blue outline
- [ ] TorchAngleGraph: target purple, line blue
- [ ] PieChart/BarChart: blue/purple segments

**Time:** 0.5 h

---

### 🟥 Step 4.7: Run full test suite and build verification

**What:** Run `npm run build` in my-app (ensures Next.js build succeeds; deploy pipelines typically run build). Then `npm test`. Fix any remaining failures. Verify before merge/deploy.

**Verification:**
- `npm run build` completes without errors
- `npm test` passes

**Time:** 0.5 h

---

**Phase 4 Total:** ~2 h

---

## Rollback Procedure

If thermal changes cause failures after merge:
1. `git revert <PR-commit>`
2. Run `npm test` to confirm reversion is clean
3. Redeploy if already pushed

**Contingency reference:** Risk heatmap (Phase 1 thermal drift) — "Revert thermal changes, fix anchors, re-apply."

---

## Pre-Flight Checklist

### Phase 1
| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Node 18+ | `node --version` | Install Node |
| npm deps | `npm install` in my-app | Run npm install |
| Tests run | `npm test` | Fix env |
| heatmapData exists | File at utils/heatmapData.ts | — |
| GLSL shader exists | heatmapFragment.glsl.ts | — |

### Phase 2
| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 1 complete | theme.ts exists; thermal tests pass | Complete Phase 1 |
| PieChart, BarChart | Components render | — |

### Phase 3
| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 2 complete | Chart colors blue/purple | Complete Phase 2 |
| Demo page loads | Navigate to /demo | — |

### Phase 4
| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phases 1–3 complete | All component changes done | Complete earlier phases |
| Git clean | `git status` | Commit |

---

## Risk Heatmap

| Phase | Step | Risk | Prob | Impact | Mitigation |
|-------|------|------|------|--------|------------|
| 1 | 1.2–1.4 | Thermal drift | 🟡 40% | High | Sync test |
| 1 | 1.7 | Test failures | 🔴 90% | Low | Update assertions |
| 2 | 2.6 | getWeldPoolColor wrong | 🟡 30% | Med | Visual check |
| 3 | 3.3 | Missed gradient | 🟡 50% | Med | Grep |
| 4 | 4.5 | Color leak | 🟡 40% | Med | Grep + QA |

---

## Success Criteria (15+)

| # | Requirement | Verification |
|---|-------------|-------------|
| 1 | Demo header "WarpSense" | `screen.getByText(/WarpSense/)` |
| 2 | Demo metadata "WarpSense" | Document title |
| 3 | Landing blue/purple only | No green, orange, pink in gradients |
| 4 | Expert blue, Novice purple | Tailwind classes |
| 5 | Thermal heatmap blue→purple | tempToColor(0) #1e3a8a, tempToColor(500) #a855f7 |
| 6 | 3D thermal blue→purple | Visual |
| 7 | Error violet | No red-* in error components |
| 8 | PieChart blue/purple | DEFAULT_COLORS |
| 9 | BarChart blue | Default color |
| 10 | HeatMap active blue | Outline color |
| 11 | TorchAngleGraph target purple | stroke |
| 12 | AppNav Demo blue | No cyan |
| 13 | Seagull error violet, score violet | No red, no amber |
| 14 | deploy.sh WarpSense | Grep |
| 15 | All tests pass; build succeeds | npm run build; npm test |
| 16 | No rainbow colors | Grep green\|red\|cyan\|amber\|yellow\|orange\|pink |

---

## Progress Dashboard

| Phase | Steps | Done | Blocked | % |
|-------|-------|------|---------|---|
| 1 | 7 | 0 | 0 | 0 |
| 2 | 8 | 0 | 0 | 0 |
| 3 | 10 | 0 | 0 | 0 |
| 4 | 7 | 0 | 0 | 0 |

---

## Known Issues & Limitations

- **Range [0,500]°C:** Real sensor data >500°C will clamp to max purple. Most welding thermal sensors report within 0–600°C; verify against typical sensor range if your hardware exceeds 500°C.
- **Purple as error:** Some users may not recognize purple as error; use strong violet-600 and clear "Error" label.

---

## Summary

**Total steps:** 32  
**Total estimated time:** 16–20 hours  
**Critical path:** theme.ts → thermal (heatmapData, shader, utils) → delta → charts/components → pages (including seagull) → docs → tests

**Key risks:** Thermal drift (sync test), test brittleness (update all), missed colors (grep).

**Confidence:** 8.5/10 — Exploration and issue are thorough; theme position documentation fixed; seagull routes included; thermal range impact documented.
