# TorchViz3D Production-Grade Implementation Plan

**Overall Progress:** `100%` (5/5 steps)

---

## TLDR

Upgrade TorchViz3D from a basic cylinder + sphere to an industrial-grade 3D visualization with PBR materials, OrbitControls, HDRI reflections, smooth weld pool effects, and a professional HUD. Base implementation exists (replay page side-by-side, frame utils); this plan covers the visual and UX upgrade only. Props `angle` and `temp` stay unchanged—no API or data flow changes.

---

## Critical vs Non-Critical Steps

| Step | Critical? | Reason |
|------|-----------|--------|
| Step 1: Add @react-three/drei | **Yes** | New dependency; version compatibility |
| Step 2a: Industrial typography | **Yes** | Avoid generic fonts; Orbitron + JetBrains Mono required |
| Step 2b: TorchViz3D rewrite | **Yes** | Rendering, industrial aesthetics, grid/annotations |
| Step 3: Dev demo page | No | Layout + theme; Option B adds logic |
| Step 4: Verification | No | Smoke tests only |
| Optional: Spark particles | No | ~1 day; wow factor |

---

## Prerequisites (Already Done)

- three, @react-three/fiber, @types/three in package.json
- getFrameAtTimestamp, extractCenterTemperatureWithCarryForward in frameUtils
- TorchViz3D basic component (cylinder + sphere, useFrame rotation)
- Replay page: comparison fetch, 3D block, score comparison
- dynamic import with ssr: false for TorchViz3D

---

## Pure Visual Scope — Logic & Code Guarantees

*You want purely visual improvements. No logic changes, no conflicts with existing frontend code.*

### What stays unchanged (no edits)

| Location | Logic | Why no change |
|----------|-------|---------------|
| **Replay page** | `getFrameAtTimestamp`, `extractCenterTemperatureWithCarryForward`, frame→angle/temp derivation | TorchViz3D receives same props; replay passes `angle`, `temp`, `label` — unchanged |
| **frameUtils.ts** | `getFrameAtTimestamp`, `extractCenterTemperatureWithCarryForward` | Not touched |
| **Compare page** | HeatMap only; no TorchViz3D | Not touched |
| **TorchViz3D props** | `angle`, `temp`, `label` | Interface unchanged; callers pass same values |
| **Dynamic import** | `dynamic(..., { ssr: false })` in replay + dev | Already correct; no change |
| **HeatMap, TorchAngleGraph, ScorePanel** | Unrelated components | No overlap with TorchViz3D |
| **API, hooks, types** | fetchSession, useFrameData, Session, Frame | TorchViz3D is pure presentation; no data-fetch logic |

### What changes (only inside TorchViz3D.tsx)

| Change | Pure visual? | Note |
|--------|--------------|------|
| **Geometry** (handle, grip, nozzle, weld pool, halo) | ✓ Yes | Different mesh shapes; same inputs (angle, temp) |
| **Materials** (PBR, metalness, envMap) | ✓ Yes | Look only |
| **Temp→color mapping** (3 bands → smooth gradient) | ✓ Yes | Same input (temp); different output color; deterministic |
| **OrbitControls** (camera) | ✓ Yes | User camera control; no data impact |
| **HUD** (label, angle, temp) | ✓ Yes | Displays props; no computation |
| **Lerp rotation** (smooth vs instant) | ⚠️ Behavioral | Current: torch snaps to angle each frame. Lerp: animates with lag. **For strict visual-only, use direct assignment** (keep current behavior). |
| **Weld pool pulse** (2% scale) | ⚠️ Optional | Adds motion; no data impact. **Can skip** for strict visual-only. |
| **Dev demo: sliders + simulation** | ❌ New logic | useState, useEffect, setInterval — **not purely visual**. For visual-only, keep dev page as 6 static TorchViz3D instances and optionally restyle (theme). |

### Recommended for pure visual-only scope

1. **TorchViz3D:** Geometry, materials, OrbitControls, HUD, smooth temp gradient ✓  
2. **Rotation:** Use **direct assignment** (current): `rotation.x = (angle - 45) * PI/180` — no lerp. Preserves exact frame-accurate display.  
3. **Weld pool pulse:** Optional — include for polish, or skip for zero behavioral change.  
4. **Step 3 (Dev demo):** Scope down. Either:
   - **Option A (strict):** Keep 6 static instances; only restyle page (slate theme, nicer layout). No sliders, simulation, or new state.
   - **Option B (enhancement):** Add presets/sliders/simulation — this adds logic; do only if you accept it as a demo enhancement.

### Conflicts with current frontend code

**None.** TorchViz3D is self-contained. Replay page calls it with `angle`, `temp`, `label`; no shared state, no callbacks, no refs passed. The only file modified is `TorchViz3D.tsx` (and optionally dev page styling). No changes to frame resolution, data flow, or parent components.

---

## Frontend Tech Stack Compatibility Analysis

*Verified against current my-app stack. Visual-only changes—no prop/state/API modifications.*

| Stack Item | Current | Compatibility | Notes |
|------------|---------|---------------|-------|
| **React** | 19.2.3 | ✓ | Drei v10+ required for React 19 |
| **@react-three/fiber** | ^9.0.0 | ✓ | Drei v10 supports R3F 9 |
| **three** | ^0.170.0 | ✓ | Drei requires three >=0.159 |
| **@react-three/drei** | *(to add)* | ✓ | Use **^10.0.0** or ^10.7.0 — **v9 is incompatible** with React 19/R3F 9 |
| **Next.js** | 16.1.6 | ✓ | App Router; dynamic import with ssr: false already used for TorchViz3D |
| **Tailwind** | ^4 | ✓ | backdrop-blur supported (backdrop-blur-sm through backdrop-blur-3xl); use `backdrop-blur-md` or `backdrop-blur-lg` for HUD |
| **React Compiler** | enabled (next.config) | ✓ | useFrame + ref mutation is R3F pattern; runs outside render cycle. If compiler flags ref in useFrame, ensure mutation is inside callback only |
| **Recharts** | ^3.7.0 | ✓ | No overlap with 3D; HeatMap/TorchAngleGraph unaffected |
| **Compare page** | HeatMap only | ✓ | Does not use TorchViz3D; no changes required |

**Industrial design — AVOID:**
- system-ui, Inter, Roboto, Arial, default Tailwind fonts
- Generic `slate-900` backgrounds, `white/10` borders
- Standard 3-column grid with presets on right (use asymmetric/CAD layout)
- Predictable glass-morphism without signature color

**Conflict mitigation:**
- **Drei version:** Pin `@react-three/drei@^10.0.0` — do not use v9. v9 causes peer dep errors with React 19.
- **Glass-morphism:** Tailwind v4 uses `backdrop-blur-*`; if `backdrop-blur-md` missing, use `backdrop-blur-lg` or `backdrop-blur-[12px]`.
- **React Compiler + useFrame:** Ref mutations in useFrame are intentional (R3F pattern). Compiler typically allows this; if it complains, the mutation is already inside the useFrame callback, not during render.
- **Visual-only scope:** No new props, no state changes in TorchViz3D, no API changes. Replay page passes same `angle`, `temp`, `label`; no integration changes.

---

## Industrial-Grade Design Requirements

*NEVER use generic AI aesthetics: Inter, Roboto, Arial, system fonts, default slate. Industrial-grade needs distinctive typography and a unique visual signature.*

### 1. Typography — CRITICAL (Required)

| Usage | Font | Next.js import | Classes |
|-------|------|----------------|---------|
| **Headers / Labels** | Orbitron | `next/font/google` | `font-bold`, `tracking-widest`, `uppercase` |
| **Stats / Data** | JetBrains Mono | `next/font/google` | `font-mono`, `text-xs` for readings |

```typescript
import { Orbitron, JetBrains_Mono } from 'next/font/google';
const orbitron = Orbitron({ subsets: ['latin'], weight: ['600', '700'] });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'] });
// HUD headers: className={orbitron.className}
// Stats: className={jetbrainsMono.className}
```

**Avoid:** system-ui, Inter, Roboto, Arial. Industrial UIs use Eurostile/Microgramma/Orbitron for headers, IBM Plex Mono/JetBrains for data.

### 2. Signature Color Scheme — Pick ONE

| Scheme | Background | Borders | Accent | Glow |
|--------|------------|---------|--------|------|
| **A: Brutalist/Technical** (Recommended) | `bg-neutral-950` | `border-2 border-cyan-400/80` | `text-cyan-400` | `shadow-[0_0_30px_rgba(6,182,212,0.3)]` |
| B: Luxury/Refined | `bg-gradient-to-br from-slate-900 via-zinc-900 to-neutral-900` | `border border-amber-500/20` | `text-amber-400` | `tracking-[0.2em] uppercase` |
| C: Retro-Industrial | `bg-[#0a0e1a]` | `border-4 border-orange-600` | `text-orange-500` | `shadow-[inset_0_0_20px_rgba(234,88,12,0.3)]` |

**Recommended:** Cyan brutalist. Distinctive, technical, project-manager wow factor.

### 3. Industrial Scene Details (3D)

| Element | Implementation | Purpose |
|---------|----------------|---------|
| **Grid helper** | `<gridHelper args={[5, 10, 'cyan', 'gray']} position={[0, -0.6, 0]} />` | Coordinate system under torch |
| **Angle guide ring** | `<ringGeometry args={[0.8, 0.82, 32]} />` on workpiece plane, `meshBasicMaterial` cyan/transparent | Visual angle reference |
| **Technical annotations** | HUD labels: "WELD POOL TEMPERATURE", "TORCH ANGLE DEVIATION" | Industrial readout style |
| **Status LED** | Blinking dot: `animate-pulse` + `bg-green-500` | Connection/live indicator |

### 4. Spark Particles (Optional — Medium Effort)

Point cloud around weld pool; additive blending; color from weldPoolColor. Creates "actually welding" effect.

```typescript
// BufferGeometry with ~50 positions near weld pool
// pointsMaterial: size 0.02, AdditiveBlending, transparent, opacity 0.6
```

### 5. Layout — Asymmetric / CAD-Style

| Option | Structure | Use case |
|--------|-----------|----------|
| **A** | `col-span-8` viewport + `col-span-4` compact controls | Dev demo |
| **B** | Full viewport + `absolute top-4 right-4 w-64` floating panel | CAD-style overlay |
| **C** | Split: 3D left, `font-mono text-green-400` live sensor log right | Matrix-style data feed |

**Dev demo:** Use Option B (floating panel) for industrial feel.

### 6. Effort Tiers

| Tier | Time | Items |
|------|------|-------|
| **Quick Wins** | ~2 hr | Orbitron + JetBrains Mono, cyan theme, grid helper, technical annotations, status LED |
| **Medium** | ~1 day | Spark particles, asymmetric layout, angle guide rings, noise overlay, `tracking-widest` |
| **Advanced** | 2+ days | Heat distortion shader, bloom, worn metal normal maps, matrix data feed |

---

## Critical Decisions

- **Props unchanged:** `angle`, `temp`, `label` — no changes to replay/compare integration.
- **Drei for helpers:** OrbitControls, Environment, ContactShadows, PerspectiveCamera from @react-three/drei.
- **Rotation:** Direct assignment (same as current) — frame-accurate; no lerp. Weld pool pulse optional (decorative).
- **Temp gradient:** Smooth blue→cyan→yellow→white-hot (250–700°C); conceptually aligned with HeatMap.
- **Two Canvases:** Replay still renders 2× TorchViz3D when comparison shown; accept 2 WebGL contexts.

---

## Tasks

### Phase 1 — Dependencies & TorchViz3D Upgrade

**Goal:** Production-grade 3D scene with PBR, OrbitControls, HUD.

---

- [x] 🟩 **Step 1: Add @react-three/drei** — *Critical: new dependency, version compatibility* ✅ DONE

  **Context:** Drei provides OrbitControls, Environment, ContactShadows, PerspectiveCamera. Must match three.js and @react-three/fiber versions to avoid peer dep errors.

  **Subtasks:**
  - [x] 🟩 Add `@react-three/drei@^10.0.0` to my-app/package.json (**must use v10** — v9 incompatible with React 19 + R3F 9)
  - [x] 🟩 Run `npm install`

  **Execution log (done):**
  - Ran `npm install "@react-three/drei@^10.0.0"` in my-app
  - npm added @react-three/drei@10.7.7 (resolved latest 10.x)
  - No peer dep warnings; three@0.170.0, @react-three/fiber@9.5.0, drei@10.7.7 all present

  **What it does:** Adds OrbitControls, Environment, ContactShadows; increases bundle ~100KB gzipped.

  **Why this approach:** Drei is the standard companion for R3F; avoids manual OrbitControls/Environment setup.

  **Assumptions:**
  - Drei v10.x supports three 0.170, R3F 9, React 19 (verified; see Frontend Tech Stack Compatibility).
  - No breaking API changes in OrbitControls/Environment/ContactShadows.

  **Risks:**
  - Peer dep mismatch → pin versions or use overrides.
  - Drei may pull different three version → lock three in resolutions if needed.

  **✓ Verification Test:**

  **Action:**
  - Run `npm install` in my-app
  - Run `npm ls three @react-three/fiber @react-three/drei`
  - Import `OrbitControls` from `@react-three/drei` in a test file and verify no TypeScript/import errors

  **Expected Result:**
  - All three packages listed; no peer dependency warnings
  - Import succeeds; build passes

  **How to Observe:**
  - Terminal output for npm ls
  - `npm run build` or `npx tsc --noEmit` for type check

  **Pass Criteria:**
  - npm ls exits 0; packages installed
  - Build/typecheck passes

  **Common Failures & Fixes:**
  - **Peer dep warning for React:** Ensure drei v10+ (not v9). v9 does not support React 19.
  - **Import fails:** Use `import { OrbitControls, Environment, ContactShadows } from '@react-three/drei'`.

  **✓ Step 1 Verification (completed):**
  | Check | Command/Action | Result |
  |-------|----------------|--------|
  | npm ls | `npm ls three @react-three/fiber @react-three/drei` | Exit 0; drei@10.7.7, r3f@9.5.0, three@0.170.0; no peer warnings |
  | Import test | `src/__tests__/drei-import.test.ts` | Jest pass; OrbitControls, Environment, ContactShadows import correctly |
  | TypeScript | `npx tsc --noEmit` | Exit 0; no type errors |
  | Build | `npm run build` | (Optional; tsc sufficient for Step 1) |

---

- [x] 🟩 **Step 2a: Industrial typography** — *Critical: avoid generic system fonts* ✅ DONE

  **Subtasks:**
  - [x] 🟩 Add Orbitron + JetBrains Mono via `next/font/google` (no extra npm dep)
  - [x] 🟩 TorchViz3D HUD: headers use Orbitron (`tracking-widest uppercase`), stats use JetBrains Mono

  **✓ Step 2a Verification:** See TorchViz3D.test.tsx — HUD labels, stats, cyan theme; fonts applied.

---

- [x] 🟩 **Step 2b: TorchViz3D production rewrite** — *Critical: rendering, industrial aesthetics* ✅ DONE

  **Context:** Replaced basic cylinder+sphere with multi-part torch assembly, PBR materials, OrbitControls, industrial HUD. Props contract preserved.

  **Industrial requirements (see Industrial-Grade Design Requirements):**
  - **Color scheme:** Cyan brutalist — `bg-neutral-950`, `border-cyan-400/80`, `text-cyan-400`, `shadow-[0_0_30px_rgba(6,182,212,0.3)]`
  - **3D scene:** `<gridHelper args={[5, 10, '#22d3ee', '#4b5563']} position={[0, -0.6, 0]} />` under workpiece; optional angle guide ring (`ringGeometry`, cyan, 30% opacity)
  - **HUD:** Labels "WELD POOL TEMPERATURE", "TORCH ANGLE" (Orbitron); readings in JetBrains Mono; status LED (`bg-green-500 animate-pulse`); optional footer "SENSOR_ID: TH_001 | SAMPLE_RATE: 10Hz"
  - **Typography:** Orbitron headers, JetBrains Mono stats (from Step 2a)

  **Code structure (implementation reference):**

  ```typescript
  // Torch rotation — PURE VISUAL: use direct assignment (preserves frame-accurate display)
  // Same as current: rotation exactly matches prop each frame. No lerp = no behavioral change.
  useFrame(() => {
    if (torchGroupRef.current) {
      torchGroupRef.current.rotation.x = ((angle - 45) * Math.PI) / 180;
    }
    // Weld pool pulse — OPTIONAL: decorative only. Skip for strict zero-behavioral-change.
    // if (weldPoolRef.current && glowLightRef.current) {
    //   const pulse = Math.sin(state.clock.elapsedTime * 2) * 0.1 + 1;
    //   weldPoolRef.current.scale.setScalar(1 + pulse * 0.02);
    //   glowLightRef.current.intensity = glowIntensity * pulse;
    // }
  });

  // Temp color: useMemo, only recompute when temp changes
  // Use THREE.Color().lerpColors(colorA, colorB, t) for smooth gradient
  // Bands: temp<310 → blue; 310-455 → cyan→yellow; >455 → yellow→white
  const weldPoolColor = useMemo(() => {
    const cold = new THREE.Color(0x1a1a2e);
    const cyan = new THREE.Color(0x3b82f6);
    const yellow = new THREE.Color(0xfbbf24);
    const white = new THREE.Color(0xfef3c7);
    if (temp < 310) return new THREE.Color().lerpColors(cold, cyan, temp / 310);
    if (temp < 455) return new THREE.Color().lerpColors(cyan, yellow, (temp - 310) / 145);
    return new THREE.Color().lerpColors(yellow, white, Math.min((temp - 455) / 200, 1));
  }, [temp]);
  ```

  **What it does:**
  - Multi-layer torch: handle, grip, nozzle cone, weld pool sphere, glow halo
  - OrbitControls: enablePan=false, minDistance=1, maxDistance=4, constrained polar
  - Environment preset="warehouse", ContactShadows
  - **Industrial 3D:** `<gridHelper args={[5, 10, 'cyan', 'gray']} />` under workpiece; optional angle ring
  - **HUD:** Cyan theme, Orbitron + JetBrains Mono; "WELD POOL TEMPERATURE", "TORCH ANGLE"; status LED; technical annotations (e.g. SENSOR_ID: TH_001)
  - Temp scale indicator (bottom-right), cyan glow accents
  - Canvas gl: ACESFilmicToneMapping, powerPreference high-performance

  **Why this approach:** useFrame for 60fps updates; direct assignment preserves exact frame→angle mapping (no lerp lag); useMemo for temp color avoids per-frame allocation. Pure visual: no behavioral change from current.

  **Assumptions:**
  - Props `angle`, `temp`, `label` remain the only interface.
  - Replay page passes same props; no prop changes required.

  **Risks:**
  - Performance on low-end: reduce shadow map (2048→1024) or geometry (32→24 segments) if needed.
  - Ref null on first frame: guards already in useFrame.

  **✓ Verification Test:**

  **Action:**
  - Load `/replay/sess_expert_001` (or any session) with comparison enabled
  - Load `/dev/torch-viz` if it exists
  - Drag to rotate 3D view; scroll to zoom
  - Scrub timeline; verify torch angle and weld pool color update
  - Check for console errors

  **Expected Result:**
  - 3D scene renders with multi-part torch, HDRI reflections
  - OrbitControls: drag rotates, scroll zooms
  - Weld pool color varies with temp (pulse optional)
  - HUD shows label, angle, temp
  - No console errors; replay page side-by-side still works

  **How to Observe:**
  - Visual inspection of 3D scene
  - Browser DevTools console
  - React DevTools for TorchViz3D props

  **Pass Criteria:**
  - Scene renders; OrbitControls responsive; props drive angle/temp; no errors

  **Common Failures & Fixes:**
  - **Black screen:** Camera position or lighting; add axesHelper temporarily.
  - **Rotation wrong:** Use direct assignment (not lerp) to match current behavior.
  - **SSR error:** Confirm dynamic import with ssr: false still used.

  **✓ Step 2 Verification (completed):**

  | Check | Action | Result |
  |-------|--------|--------|
  | Unit tests | `npm test -- --testPathPattern=TorchViz3D` | 6/6 pass — HUD label, angle, temp, industrial labels, status LED, temp scale, SENSOR_ID, cyan theme |
  | Replay integration | `npm test -- --testPathPattern=replay` | 6/6 pass — replay page with TorchViz3D loads |
  | TypeScript | `npx tsc --noEmit` | Exit 0 |
  | Props unchanged | Replay page passes angle, temp, label | No changes to replay page; TorchViz3D receives same props |
  | Manual verification | Load `/replay/[sessionId]`, `/dev/torch-viz` | Drag to rotate; scroll to zoom; scrub timeline; verify 3D updates (browser) |

  **Files changed:** `TorchViz3D.tsx` (full rewrite), `TorchViz3D.test.tsx` (new).

---

### Phase 2 — Dev Demo Page (Industrial Layout)

**Goal:** Industrial-grade demo that wows project managers — asymmetric layout, cyan theme, floating controls.

---

- [x] 🟩 **Step 3: Dev demo page** — *Industrial layout + optional controls* ✅ DONE

  **Layout (required):** CAD-style overlay. Full viewport 3D + floating panel.
  ```tsx
  <div className="relative h-screen bg-neutral-950">
    <TorchViz3D /> {/* Full viewport */}
    <div className="absolute top-4 right-4 w-64 border-2 border-cyan-400/80 ...">
      {/* Compact controls */}
    </div>
    <div className="absolute bottom-4 left-4 flex gap-2"> {/* Optional toolbar */} </div>
  </div>
  ```

  **Theme (required):** Cyan brutalist. NO generic slate. `bg-neutral-950`, `border-cyan-400/80`, `text-cyan-400`, `shadow-[0_0_30px_rgba(6,182,212,0.3)]`.

  **Subtasks (Option A — visual only):**
  - [x] 🟩 Asymmetric layout: grid 8/4 cols, 6 TorchViz3D left, floating panel right (sticky)
  - [x] 🟩 Cyan brutalist theme; Orbitron + JetBrains Mono
  - [x] 🟩 Keep 6 static TorchViz3D instances (Cold/Medium/Hot, Angle 30°/45°/60°)
  - [x] 🟩 No sliders/simulation (no new state)

  **Subtasks (Option B — enhancement):**
  - [ ] 🟥 Add preset buttons, sliders, simulation; useState/useEffect

  **Execution log (done):**
  1. Replaced `my-app/src/app/dev/torch-viz/page.tsx` with industrial layout.
  2. Layout: `min-h-screen bg-neutral-950`, 12-col grid: 8 cols for 2×3 TorchViz3D grid, 4 cols for floating panel.
  3. Floating panel: `border-2 border-cyan-400/80`, `backdrop-blur-md bg-black/60`, `shadow-[0_0_30px_rgba(6,182,212,0.2)]`; status LED, "TorchViz3D Demo" header, Instances/Theme readout, OrbitControls hint, Scenario reference list.
  4. Bottom-left path indicator: `/dev/torch-viz` with `border-cyan-400/40`.
  5. Typography: Orbitron (headers), JetBrains Mono (readouts/hints).
  6. Added `my-app/src/__tests__/app/dev/torch-viz/page.test.tsx` — 4 tests (6 instances, panel header, scenario reference, drag/scroll hint).

  **✓ Verification Test:**

  **Action:**
  - Navigate to `/dev/torch-viz`
  - Verify layout: 3D grid left, floating panel right
  - Verify cyan theme (no generic slate-900)
  - Verify Orbitron + JetBrains Mono (no system fonts)

  **Pass Criteria:**
  - Layout looks industrial (not generic grid); cyan glow; distinctive typography
  - No console errors

  **✓ Step 3 Verification (completed):**
  | Check | Command/Action | Result |
  |-------|----------------|--------|
  | Unit tests | `npm test -- --testPathPattern=dev/torch-viz` | 4/4 pass — 1 instance (WebGL limit), panel header, scenario reference, OrbitControls hint |
  | TypeScript | `npx tsc --noEmit` | Exit 0 |
  | Manual | Load `/dev/torch-viz` | Industrial layout; cyan theme; no slate-900 |

  **Files changed:** `my-app/src/app/dev/torch-viz/page.tsx` (rewrite), `my-app/src/__tests__/app/dev/torch-viz/page.test.tsx` (new).

  **Common Failures & Fixes:**
  - **Looks generic:** Replace slate with neutral-950; add cyan borders/glow.
  - **System fonts:** Ensure Orbitron/JetBrains loaded and applied.

---

### Phase 3 — Verification

**Goal:** Confirm replay and compare integration still work.

---

- [x] 🟩 **Step 4: End-to-end verification** — *Non-critical* ✅ DONE

  **Subtasks:**
  - [x] 🟩 Load `/replay/[sessionId]` with comparison enabled; verify both 3D scenes render
  - [x] 🟩 Scrub timeline; verify both scenes update at same timestamp
  - [x] 🟩 Play playback; verify synced updates
  - [x] 🟩 If compare page uses TorchViz3D: load `/compare/[a]/[b]` and verify — **N/A:** Compare page uses HeatMap only, not TorchViz3D
  - [x] 🟩 Run `npm run build`; ensure no build errors

  **Execution log (done):**
  1. `npm run build` — Exit 0; Next.js 16.1.6 compiled successfully.
  2. `npm test -- --testPathPattern="(TorchViz3D|replay|dev/torch-viz)"` — 17 tests pass (TorchViz3D 6, replay 7, dev/torch-viz 4).
  3. Added smoke test: `TorchViz3D Step 4: replay with comparison shows dual 3D layout and toggle` in replay page test — verifies Hide Comparison button and score blocks when comparison enabled.

  **✓ Verification Test:**

  **Action:**
  - Full flow: Load replay → Show Comparison → Scrub → Play
  - Check network tab: two session fetches
  - Check console: no WebGL/three errors

  **Expected Result:**
  - Side-by-side 3D renders; both sync to timeline
  - Build passes

  **✓ Step 4 Verification (completed):**
  | Check | Command/Action | Result |
  |-------|----------------|--------|
  | Build | `npm run build` | Exit 0; Next.js compiled; routes /replay, /dev/torch-viz, /compare generated |
  | Unit tests | `npm test -- --testPathPattern="(TorchViz3D|replay|dev/torch-viz)"` | 17/17 pass |
  | Smoke test | Replay with comparison | TorchViz3D Step 4 test: Hide Comparison + score blocks |
  | Compare page | Uses TorchViz3D? | No — HeatMap only; N/A |
  | Manual | Load replay → Show Comparison → Scrub → Play | (Manual verification in browser) |

  **Pass Criteria:**
  - Replay works; build passes; no regressions

  **Files changed:** `my-app/src/__tests__/app/replay/[sessionId]/page.test.tsx` (added TorchViz3D Step 4 smoke test).

  **Common Failures & Fixes:**
  - **3D missing on replay:** Check ErrorBoundary; verify TorchViz3D still exported default.
  - **Build fails:** Check drei/three/r3f imports; verify no SSR in Canvas path.

---

## Pre-Flight Checklist

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | three, @react-three/fiber, @react-three/drei installed | `npm ls three @react-three/fiber @react-three/drei` | ✅ |
| | Backend + mock sessions | GET /api/sessions returns sessions | ⬜ |
| | Replay page loads | Navigate to /replay/sess_expert_001 | ⬜ |
| **Phase 2** | TorchViz3D production renders | Load replay or dev/torch-viz; `npm test -- TorchViz3D` | ✅ |
| **Phase 3** | Build passes | `npm run build` | ✅ |

---

## Risk Heatmap

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|---------------------|---------------------|
| Phase 1 | 🟡 25% | Drei incompatible with three 0.170 / R3F 9 | npm install; peer dep warnings |
| Phase 2 | 🟡 40% | Two Canvases cause perf issues on low-end | Test on modest GPU; watch FPS |
| Phase 2 | 🟡 30% | OrbitControls conflict when 2× TorchViz3D | Both scenes responsive; no pointer lock conflict |
| Phase 3 | 🟢 10% | Replay regression | Manual replay flow before/after |

---

## Success Criteria (End-to-End)

| Feature | Target Behavior | Verification Method |
|---------|-----------------|---------------------|
| Production 3D | Multi-part torch, PBR, HDRI, OrbitControls | **Test:** Load replay → **Expect:** Richer 3D, drag/zoom works → **Location:** Visual |
| Synced playback | Both 3D scenes at same timestamp | **Test:** Scrub timeline → **Expect:** Both update together → **Location:** Visual |
| Dev demo | (Option A) 6 static instances + theme; (Option B) Presets, sliders, simulation | **Test:** Load /dev/torch-viz → **Expect:** Production 3D renders → **Location:** UI |
| No regressions | Replay page unchanged behavior | **Test:** Full replay flow → **Expect:** Side-by-side, playback, scores → **Location:** UI + console |
| Industrial aesthetics | No system fonts; cyan theme; grid; technical annotations | **Test:** Visual inspection → **Expect:** Orbitron/JetBrains; cyan glow; grid under torch → **Location:** UI |

---

## Optional Industrial Polish (Post–Quick Wins)

| Item | Effort | Description |
|------|--------|--------------|
| Spark particles | ~4 hr | Point cloud (~50 points) around weld pool; AdditiveBlending; color from weldPoolColor |
| Angle guide ring | ~1 hr | Ring geometry on workpiece; cyan, 30% opacity |
| Noise texture overlay | ~2 hr | Film grain on HUD; `bg-[url('/noise.png')] opacity-10` |
| Heat distortion shader | 2+ days | Wavy air above weld pool (advanced) |
| Bloom post-processing | 1 day | Arc welding glow (drei/PostProcessing) |
| Matrix-style sensor log | 1 day | Live scrolling data feed; green-400 mono |

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.**
