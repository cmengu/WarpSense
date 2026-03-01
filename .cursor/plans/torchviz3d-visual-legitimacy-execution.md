# TorchViz3D — Visual Legitimacy Execution Plan

**Overall Progress:** `0%`

---

## TLDR

Upgrade the 3D torch from generic (stacked cylinders, flat lighting) to industrial-legitimate: realistic MIG gun geometry, PBR lighting with specular streaks, material variation, HUD/color alignment (green→amber→red). **Critical:** Extract torch+lights into `TorchSceneContent` — do not nest Canvas (architecturally impossible). Extract `getArcColor` to `@/utils/torchColors.ts` first — TorchViz3D HUD and TorchSceneContent both need it. Apply lighting to TorchViz3D first, then extract; refactor before extraction yields new geometry with old lighting on replay (confusing).

---

## Critical Decisions

- **getArcColor:** Create `@/utils/torchColors.ts` with `getArcColor(temp)`. Both TorchViz3D (HUD temp readout color) and TorchSceneContent (arc sphere + under-light) import it. Do NOT define inside TorchSceneContent — TorchViz3D cannot import from a sibling component for HUD color.
- **TorchSceneContent extraction:** Extract torch geometry group + lights into `TorchSceneContent.tsx`. Both TorchViz3D and TorchWithHeatmap3D import and render it. Do NOT extract WeldTrail — it stays in TorchWithHeatmap3D. Do NOT try to compose/nest TorchViz3D — it has its own Canvas; R3F forbids nested Canvas.
- **RectAreaLightUniformsLib.init():** Must live in `TorchSceneContent.tsx` at module level with `if (typeof window !== 'undefined')` guard. If init is in TorchViz3D, it never runs when TorchWithHeatmap3D loads independently (replay page). TorchSceneContent is the shared module both import; init runs when either loads.
- **RectAreaLightUniformsLib import path:** Three.js ≥0.160 uses `three/addons/lights/RectAreaLightUniformsLib.js`; older uses `three/examples/jsm/lights/RectAreaLightUniformsLib.js`. Confirm project version in pre-flight.
- **Build order:** torchColors → geometry → lighting on TorchViz3D → extract TorchSceneContent → TorchWithHeatmap3D import → surface variation → environment. Lighting before extraction so replay page never shows geometry-without-lighting.
- **Arc under-light:** Color reactive, driven by `getArcColor(temp)`. Do not hardcode.
- **Environment:** Stays in TorchViz3D and TorchWithHeatmap3D SceneContent. TorchSceneContent does not render Environment.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Geometry reference output | Embedded in Step 1 spec below | Plan document | Step 1 | ✅ |
| TorchSceneContent scope | Torch meshes + lights only | Spec | Step 3 | Torch + lights only; workpiece, WeldTrail stay in TorchWithHeatmap3D |

---

## Conflict Analysis

**Files this plan touches:**
| File | Step(s) | Change |
|------|---------|--------|
| `my-app/src/utils/torchColors.ts` | 0 | **Create** — getArcColor, getTempReadoutColor |
| `my-app/src/components/welding/TorchViz3D.tsx` | 0, 1, 2, 3, 6 | Import torchColors; geometry; lighting; extract to TorchSceneContent; Environment preset |
| `my-app/src/components/welding/TorchSceneContent.tsx` | 3, 5 | **Create** — torch+lights; surface variation |
| `my-app/src/components/welding/TorchWithHeatmap3D.tsx` | 4, 6 | Replace torch with TorchSceneContent; Environment preset |
| `my-app/src/components/welding/__tests__/heatmapShaders.test.ts` | 7 | Verify no blue hex assertions |

**Overlapping plans (cross-reference):**

| Plan / Issue | Overlapping Files | Conflict? | Resolution |
|--------------|-------------------|-----------|------------|
| **weld-trail-execution** | TorchWithHeatmap3D | No | Run weld-trail **first**. This plan depends on it. WeldTrail is already in workpiece group; Step 4 keeps it. |
| **thermal-gradient-green-orange-red** | TorchViz3D, TorchWithHeatmap3D (getWeldPoolColor) | Subsumed | Thermal gradient changed getWeldPoolColor to green/orange/red. This plan removes getWeldPoolColor and introduces torchColors.getArcColor with same values. Step 0 replaces in-place color fn with shared util; no revert of thermal work. |
| **weld-pool-temp-39c-fix** | frameUtils, compare page, TorchWithHeatmap3D (displays temp) | No | Weld pool fix changes temp *computation* (frameUtils, mock data). This plan changes temp *display* structure (TorchSceneContent receives temp prop). Different layers. Temp still flows compare→TorchWithHeatmap3D→TorchSceneContent. |
| **compare-remove-heatmaps** | compare page | No | This plan does not touch compare page. |
| **compare-plain-english-summary** | compare page | No | This plan does not touch compare page. |
| **alert_ui_investor_polish** | compare page | No | This plan does not touch compare page. |

---

## Agent Failure Protocol

1. A verification command fails → read the full error output.
2. Cause is unambiguous → make ONE targeted fix → re-run the same verification command.
3. If still failing after one fix → **STOP**. Output full contents of every file modified. Report: (a) command run, (b) full error, (c) fix attempted, (d) current state, (e) why you cannot proceed.
4. Never attempt a second fix without human instruction.
5. Never modify files not named in the current step.

---

## Pre-Flight — Run Before Any Code Changes

```
Use targeted grep; only read full files when a specific edit anchor is needed.
Use -r when grepping directories so matches are found.

(1) grep -n "SceneContent\|function SceneContent" my-app/src/components/welding/TorchViz3D.tsx
(2) grep -n "SceneContent\|function SceneContent" my-app/src/components/welding/TorchWithHeatmap3D.tsx
(3) grep -rn "RectAreaLight\|RectAreaLightUniformsLib" my-app/src/
(4) grep -rn "getWeldPoolColor\|getArcColor" my-app/src/
(5) grep -n "TORCH_GROUP_Y\|WORKPIECE_BASE_Y\|WELD_POOL" my-app/src/constants/welding3d.ts
(6) grep -n "welding3d" my-app/src/components/welding/TorchWithHeatmap3D.tsx
(7) grep "\"three\"" my-app/package.json
(8) grep -n "WeldTrail" my-app/src/components/welding/TorchWithHeatmap3D.tsx
(9) cd my-app && npm test -- 2>&1 | tail -5
(10) wc -l my-app/src/components/welding/TorchViz3D.tsx my-app/src/components/welding/TorchWithHeatmap3D.tsx my-app/src/constants/welding3d.ts

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Three.js version: ____ (from package.json)
Test count before plan: ____
Line count TorchViz3D.tsx: ____
Line count TorchWithHeatmap3D.tsx: ____
Line count welding3d.ts: ____
TorchWithHeatmap3D imports welding3d: Yes / No (grep (6) returns ≥1)
WeldTrail in TorchWithHeatmap3D: Yes / No (grep (8) returns ≥1 — required before Step 4)
```

**Checks before Step 1:**
- [ ] TorchViz3D has internal SceneContent (torch group, lights, workpiece, grid)
- [ ] TorchWithHeatmap3D has its own SceneContent with duplicated torch assembly
- [ ] TorchWithHeatmap3D imports from welding3d (grep (6) returns ≥1 match)
- [ ] WeldTrail is integrated in TorchWithHeatmap3D (grep (8) returns ≥1 match). If 0, run weld-trail plan first.
- [ ] No RectAreaLight or RectAreaLightUniformsLib in codebase yet
- [ ] welding3d.ts exports TORCH_GROUP_Y, WELD_POOL_OFFSET_Y, WELD_POOL_CENTER_Y, WORKPIECE_BASE_Y
- [ ] Existing tests pass

---

## Steps Analysis

| Step | Classification | Idempotent |
|------|----------------|------------|
| 0 | Critical (shared util) | Yes |
| 1 | Critical (geometry) | Yes |
| 2 | Critical (lighting) | Yes |
| 3 | Critical (extraction) | Yes |
| 4 | Critical (integration) | Yes |
| 5 | Non-critical (surface) | Yes |
| 6 | Non-critical (environment) | Yes |
| 7 | Hygiene (docs) | Yes |

---

## Phase 0 — Shared Color Utility

**Goal:** `getArcColor` in shared util so TorchViz3D HUD and TorchSceneContent can both import it.

---

- [ ] 🟥 **Step 0: Create @/utils/torchColors.ts**

  **Idempotent:** Yes.

  **Context:** TorchViz3D HUD temp readout needs temp→color for live styling. TorchSceneContent needs it for arc sphere and under-light. Defining it inside TorchSceneContent would require TorchViz3D to import from a sibling — bad pattern. Extract to shared util.

  **Pre-Read Gate:**
  - `grep -n "getWeldPoolColor\|0x22c55e\|0xf97316" my-app/src/components/welding/TorchViz3D.tsx` — confirm current implementation

  **0a — Create `my-app/src/utils/torchColors.ts`:**
  ```typescript
  import * as THREE from 'three';

  /** Arc color: cold green → orange → red. IR-style thermal. Matches heatmapFragment.glsl anchor colors. */
  export function getArcColor(temp: number): THREE.Color {
    const cold = new THREE.Color(0x22c55e);
    const mid = new THREE.Color(0xf97316);
    const hot = new THREE.Color(0xef4444);
    const hotEnd = new THREE.Color(0xfa0505);
    if (temp < 200) return new THREE.Color().lerpColors(cold, mid, temp / 200);
    if (temp < 400) return new THREE.Color().lerpColors(mid, hot, (temp - 200) / 200);
    return new THREE.Color().lerpColors(hot, hotEnd, Math.min((temp - 400) / 150, 1));
  }

  /** HUD temp readout color: green <250, amber 250–500, red >500. */
  export function getTempReadoutColor(temp: number): string {
    if (temp < 250) return 'text-green-500';
    if (temp < 500) return 'text-amber-500';
    return 'text-red-500';
  }
  ```

  **0b — TorchViz3D.tsx:**
  - Remove local `getWeldPoolColor`. Import: `import { getArcColor, getTempReadoutColor } from '@/utils/torchColors';`
  - Arc sphere + halo: use `getArcColor(temp)`
  - HUD temp span: apply `getTempReadoutColor(temp)` as className

  **Git Checkpoint:**
  ```bash
  git add my-app/src/utils/torchColors.ts my-app/src/components/welding/TorchViz3D.tsx
  git commit -m "step 0: extract getArcColor to torchColors.ts"
  ```

  **✓ Verification Test:**
  - **Action:** `cd my-app && npm test -- TorchViz3D`
  - **Pass:** All tests pass.

---

## Phase 1 — Geometry

**Goal:** TorchViz3D has correct MIG geometry and green→amber→red color system.

---

- [ ] 🟥 **Step 1: Apply geometry and HUD updates to TorchViz3D**

  **Idempotent:** Yes.

  **Context:** Replace simple cylinder/cone/sphere with realistic MIG gun. Spec below is self-contained; no external reference required.

  **Pre-Read Gate:**
  - `grep -n "cylinderGeometry\|coneGeometry\|sphereGeometry" my-app/src/components/welding/TorchViz3D.tsx`
  - Confirm Step 0 completed — TorchViz3D imports getArcColor from torchColors

  **1a — Geometry spec (implement verbatim):**
  - **Gooseneck:** 3 nested `<group>` elements, each rotated on X: `-0.45`, `-0.35`, `-0.15` rad. Creates bent neck. Handle barrel inside innermost group.
  - **Handle barrel:** Cylinder r=0.05 bottom, r=0.045 top, height 0.9. Color #2a2a2a, metalness 0.9, roughness 0.18. Position relative to torch group.
  - **Grip bands:** 4 thin cylinders at y = [0.06, 0.16, 0.25, 0.34]. Color #1a1a1a, metalness 0, roughness 0.98 (rubber).
  - **Trigger housing:** Box geometry with finger guard below. Rubber material. Separate from handle.
  - **Cable collar:** Entry collar + rubber shroud at handle top (y ≈ 0.34).
  - **Nozzle:** Two-part — (1) flared body, brass-tinted (#b8860b or similar), roughness 0.35; (2) chamfered tip. Position at end of gooseneck.
  - **Contact tip:** Copper (#b87333), radius 0.0065, shoulder + shaft. Protrudes from nozzle center.
  - **Arc point:** Sphere radius 0.018 (not 0.12). Glow halo radius 0.055, opacity ~0.08, BackSide.
  - **Arc emissiveIntensity:** Clamp max at 4.0. Formula: `Math.min(4, 0.5 + (temp / 700) * 2.5)`.
  - **Workpiece:** Plane with weld seam line. Angle guide ring (outer). Add inner target ring alongside.
  - **Torch group position:** Use `TORCH_GROUP_Y` from welding3d. Weld pool Y = `TORCH_GROUP_Y + WELD_POOL_OFFSET_Y`.

  **1b — HUD:**
  - Border: `border-slate-700/60` (replace blue).
  - Temp readout: apply `getTempReadoutColor(temp)` to the temp span.
  - Gradient bar: `from-green-600 via-amber-500 to-red-500` (replace blue→violet).
  - Footer: `TH_001 · 10Hz` (replace `SENSOR_ID: TH_001 | SAMPLE_RATE: 10Hz`).
  - Slate tones throughout: `text-slate-400`, `border-slate-700/60`, etc.

  **1c — Materials:** 4 distinct — gunmetal (handle/neck), rubber (grip/trigger), copper (contact tip), brass (nozzle).

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchViz3D.tsx
  git commit -m "step 1: apply MIG geometry and slate HUD to TorchViz3D"
  ```

  **✓ Verification Test:**
  - **Action:** `cd my-app && npm test -- TorchViz3D`
  - **Pass:** All tests pass.
  - **Manual:** Open `/dev/torch-viz` — gooseneck reads as bent, contact tip visible, arc pinpoint at high temp, gradient bar green→amber→red.

---

## Phase 2 — Lighting (Before Extraction)

**Goal:** RectAreaLight + hardened key + dim fill + reactive arc under-light. Verify on TorchViz3D dev page before extracting.

---

- [ ] 🟥 **Step 2: Add Phase 1 lighting to TorchViz3D**

  **Idempotent:** Yes.

  **Context:** Lighting reveals whether surface work is needed. Do this step before extracting TorchSceneContent so replay never shows new geometry with old flat lighting.

  **Pre-Read Gate:**
  - `grep "\"three\"" my-app/package.json` — capture version. If ≥0.160 use `three/addons/lights/RectAreaLightUniformsLib.js`; else `three/examples/jsm/lights/RectAreaLightUniformsLib.js`.
  - `grep -n "ambientLight\|directionalLight\|pointLight" my-app/src/components/welding/TorchViz3D.tsx`

  **2a — RectAreaLightUniformsLib init (temporary in TorchViz3D):**
  Import path: `three/addons/...` for three ≥0.160 (this project 0.170). Add: `import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';`
  At module level: `if (typeof window !== 'undefined') { RectAreaLightUniformsLib.init(); }`
  This is temporary — Step 3 moves init to TorchSceneContent and removes it from here.

  **2b — Lights in SceneContent:**
  - RectAreaLight: position `[0, 3, -1]`, width 4, height 0.4, intensity ~1
  - Key directional: position `[4, 8, 3]`, intensity `2.2`
  - Fill: position `[-4, 2, -4]`, intensity `0.15`
  - Arc under-light: point light `[0, WELD_POOL_CENTER_Y - 0.05, 0.1]`, intensity `0.3`, color from `getArcColor(temp)` — reactive with temp

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchViz3D.tsx
  git commit -m "step 2: add RectAreaLight and PBR lighting to TorchViz3D"
  ```

  **✓ Verification Test:**
  - **Action:** `cd my-app && npm test -- TorchViz3D`
  - **Manual:** Open `/dev/torch-viz` — barrel has visible specular streak, shadow side goes dark, arc under-light bounces onto nozzle.
  - **Pass:** Tests pass; visual checklist items for lighting satisfied.

---

## Phase 3 — Extract TorchSceneContent

**Goal:** Single source of truth for torch geometry + lights. TorchViz3D and TorchWithHeatmap3D both import it.

---

- [ ] 🟥 **Step 3: Create TorchSceneContent.tsx and extract torch+lights**

  **Idempotent:** Yes.

  **Context:** Extract the torch geometry group and lights from TorchViz3D SceneContent. Environment stays in each Canvas's SceneContent. TorchSceneContent does NOT render Environment. WeldTrail stays in TorchWithHeatmap3D — do NOT extract WeldTrail.

  **Pre-Read Gate:**
  - `grep -n "return (\|<>" my-app/src/components/welding/TorchViz3D.tsx` — identify boundary of torch+lights vs workpiece/grid/Environment
  - Confirm workpiece, grid, ContactShadows, Environment are in SceneContent after the torch group

  **3a — Create `my-app/src/components/welding/TorchSceneContent.tsx`:**
  - At module level: `import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';` (or examples/jsm if three <0.160) and `if (typeof window !== 'undefined') { RectAreaLightUniformsLib.init(); }`. Init must live here — TorchWithHeatmap3D loads this file on replay page without loading TorchViz3D.
  - Import from `@/constants/welding3d`: `TORCH_GROUP_Y`, `WELD_POOL_OFFSET_Y`, `WELD_POOL_CENTER_Y`. Use for all Y positions — no hardcoded values.
  - Import from `@/utils/torchColors`: `getArcColor`
  - Export: `export function TorchSceneContent({ angle, temp }: { angle: number; temp: number })`
  - Contents: lights (ambient, directional, RectAreaLight, fill, arc under-light) + torch group with useFrame for rotation. Torch geometry from Step 1 spec.

  **3b — TorchViz3D.tsx:**
  - Remove RectAreaLightUniformsLib import and init entirely (moved to TorchSceneContent)
  - Import TorchSceneContent
  - SceneContent: render `<TorchSceneContent angle={angle} temp={temp} />` plus workpiece, grid, angle ring, ContactShadows, Environment
  - Remove duplicated torch meshes and lights

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchSceneContent.tsx my-app/src/components/welding/TorchViz3D.tsx
  git commit -m "step 3: extract TorchSceneContent from TorchViz3D"
  ```

  **✓ Verification Test:**
  - **Action:** `cd my-app && npm test -- TorchViz3D`
  - **Action:** `grep -n "RectAreaLightUniformsLib" my-app/src/components/welding/TorchViz3D.tsx` — must return 0 matches (init removed)
  - **Manual:** `/dev/torch-viz` — identical appearance to Step 2. No regression.
  - **Pass:** Tests pass; grep returns nothing; visual unchanged.

---

- [ ] 🟥 **Step 4: Integrate TorchSceneContent into TorchWithHeatmap3D**

  **Idempotent:** Yes.

  **Context:** TorchWithHeatmap3D has duplicated torch assembly. Replace with TorchSceneContent.

  **Pre-Read Gate:**
  - `grep -n "welding3d" my-app/src/components/welding/TorchWithHeatmap3D.tsx` — must return ≥1 match. If 0, STOP; alignment cannot be assumed.
  - `grep -n "torchGroupRef\|cylinderGeometry\|coneGeometry\|mesh castShadow" my-app/src/components/welding/TorchWithHeatmap3D.tsx`
  - `grep -n "group position=.*WORKPIECE_GROUP_Y\|hasThermal" my-app/src/components/welding/TorchWithHeatmap3D.tsx`

  **4a — TorchWithHeatmap3D.tsx:**
  - Import: `import { TorchSceneContent } from './TorchSceneContent';`
  - Remove: duplicated torch meshes, torch-specific lights
  - Add: `<TorchSceneContent angle={angle} temp={temp} />` inside SceneContent, before workpiece group
  - Keep: workpiece group, ThermalPlate, WeldTrail, grid, ContactShadows, Environment

  **4b — Workpiece alignment:** TorchSceneContent and TorchWithHeatmap3D both import welding3d. Pre-flight confirmed TorchWithHeatmap3D imports it. No further alignment needed.

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchWithHeatmap3D.tsx
  git commit -m "step 4: replace duplicated torch with TorchSceneContent in TorchWithHeatmap3D"
  ```

  **✓ Verification Test:**
  - **Action:** `cd my-app && npm test -- TorchWithHeatmap3D`
  - **Manual:** Open `/replay/[sessionId]` — gooseneck geometry and green→amber→red arc visible; lighting matches Step 2.
  - **Pass:** Tests pass; replay page shows polished torch.

---

## Phase 4 — Surface Variation (If Needed)

**Goal:** Material roughness variation — rubber grips, brass nozzle, copper tip. Only if lighting alone insufficient.

---

- [ ] 🟥 **Step 5: Phase 2 surface variation in TorchSceneContent**

  **Idempotent:** Yes.

  **Context:** Grip bands roughness 0.98, metalness 0; handle barrel upper 0.28; nozzle 0.35; contact tip 0.18; arc emissiveIntensity max 4.0.

  **Pre-Read Gate:**
  - `grep -n "roughness\|metalness" my-app/src/components/welding/TorchSceneContent.tsx`

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchSceneContent.tsx
  git commit -m "step 5: add surface variation to TorchSceneContent"
  ```

  **✓ Verification Test:**
  - **Manual:** Replay page — rubber reads matte, brass nozzle slightly oxidized.
  - **Pass:** Visual checklist satisfied.

---

## Phase 5 — Environment

**Goal:** Harder reflections via `preset="city"`. Environment stays in TorchViz3D and TorchWithHeatmap3D SceneContent (per Step 3; TorchSceneContent does not render Environment).

---

- [ ] 🟥 **Step 6: Switch Environment preset to city**

  **Idempotent:** Yes.

  **Context:** Change `preset="warehouse"` to `preset="city"` in both TorchViz3D and TorchWithHeatmap3D. Environment is in each file's SceneContent, not in TorchSceneContent.

  **Pre-Read Gate:**
  - `grep -n "Environment preset" my-app/src/components/welding/TorchViz3D.tsx my-app/src/components/welding/TorchWithHeatmap3D.tsx`

  **6a — TorchViz3D.tsx:** `<Environment preset="city" />`
  **6b — TorchWithHeatmap3D.tsx:** `<Environment preset="city" />`

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchViz3D.tsx my-app/src/components/welding/TorchWithHeatmap3D.tsx
  git commit -m "step 6: switch Environment preset to city"
  ```

  **✓ Verification Test:**
  - **Manual:** Nozzle reflections harder, more directional.
  - **Pass:** No regression.

---

## Phase 6 — Hygiene

---

- [ ] 🟥 **Step 7: Verify heatmapShaders.test.ts and update docs**

  **Idempotent:** Yes.

  **Context:** Confirm heatmapShaders.test.ts does not assert on old blue hex values. Update docs if spec changed.

  **7a — heatmapShaders.test.ts:**
  - Run: `cd my-app && npm test -- heatmapShaders`
  - If any assertion uses blue/purple hex from getWeldPoolColor → update to green/amber/red
  - Do not assume "no changes"; verify

  **7b — docs/ISSUE_TORCH_VIZ3D_VISUAL_LEGITIMACY.md:**
  - If plan is tracked here, update Build Order / Verification Checklist to reflect completed state (optional)

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/__tests__/heatmapShaders.test.ts
  git commit -m "step 7: verify heatmapShaders test and update if needed"
  ```

  **✓ Verification Test:**
  - **Action:** `cd my-app && npm test -- heatmapShaders`
  - **Pass:** All tests pass.

---

## Regression Guard

**Regression verification:**
- `npm test -- TorchViz3D` — passes
- `npm test -- TorchWithHeatmap3D` — passes
- `npm test -- heatmapShaders` — passes

**Test count:** Must be ≥ pre-flight baseline.

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| torchColors.ts | getArcColor, getTempReadoutColor exported | TorchViz3D and TorchSceneContent import from @/utils/torchColors |
| TorchSceneContent extracted | Single source for torch+lights; uses welding3d | Both files import it; TorchSceneContent imports TORCH_GROUP_Y, WELD_POOL_OFFSET_Y; no hardcoded Y |
| RectAreaLightUniformsLib | Init in TorchSceneContent only | grep TorchViz3D returns 0; runs when replay loads TorchWithHeatmap3D |
| Init removed from TorchViz3D | No RectAreaLightUniformsLib in TorchViz3D | grep -n "RectAreaLightUniformsLib" TorchViz3D.tsx → 0 matches |
| TorchWithHeatmap3D imports welding3d | Confirmed before Step 4 | Pre-flight grep (6) ≥1 match |
| WeldTrail | Stays in TorchWithHeatmap3D | Not in TorchSceneContent |
| Lighting before extraction | Replay never shows geometry-only | Build order: Step 2 before Step 4 |
| Arc under-light reactive | Color from getArcColor(temp) | Changes with temp during replay |
| Environment | preset city in both files | TorchSceneContent does not render it |
| Replay page | Gooseneck + green→amber→red visible | Manual check on /replay/[sessionId] |
| heatmapShaders | No old blue hex assertions | Test passes after verify |
| WebGL context loss | Unchanged | TorchViz3D context-loss flow still works |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Do not batch steps into one commit.**
⚠️ **Step 2 and Step 4 require manual visual verification.**
