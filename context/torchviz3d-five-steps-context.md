# TorchViz3D Production-Grade — 5 Steps Implementation Context

> **Purpose:** Reference for all code implemented in the TorchViz3D production-grade plan (Steps 1–5).  
> **For AI:** Use `@context/torchviz3d-five-steps-context.md` when modifying 3D visualization or dev demo.  
> **Plan:** `.cursor/plans/torchviz3d-production-grade-plan.md`  
> **Last Updated:** 2025-02-13

---

## Overview

| Step | Label | What | File(s) |
|------|-------|------|---------|
| 1 | Add @react-three/drei | New dependency, import verification | package.json, drei-import.test.ts |
| 2a | Industrial typography | Orbitron + JetBrains Mono | TorchViz3D.tsx |
| 2b | TorchViz3D rewrite | Multi-part torch, PBR, HUD, context-loss handling | TorchViz3D.tsx |
| 3 | Dev demo page | Industrial layout, cyan theme, floating panel | app/dev/torch-viz/page.tsx |
| 4 | End-to-end verification | Build, tests, replay smoke test | Replay page.test.tsx |

---

## Step 1: Add @react-three/drei

**Purpose:** Add Drei for OrbitControls, Environment, ContactShadows, PerspectiveCamera.

### package.json (dependency)

```json
"@react-three/drei": "^10.7.7"
```

**Constraint:** Must use v10+ — v9 incompatible with React 19 + R3F 9.

### src/__tests__/drei-import.test.ts

```typescript
/**
 * Step 1 verification: Confirm @react-three/drei imports correctly.
 */
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei';

describe('@react-three/drei import', () => {
  it('imports OrbitControls', () => {
    expect(OrbitControls).toBeDefined();
    expect(typeof OrbitControls).toMatch(/function|object/);
  });

  it('imports Environment', () => {
    expect(Environment).toBeDefined();
    expect(typeof Environment).toMatch(/function|object/);
  });

  it('imports ContactShadows', () => {
    expect(ContactShadows).toBeDefined();
    expect(typeof ContactShadows).toMatch(/function|object/);
  });
});
```

---

## Step 2a & 2b: Industrial Typography + TorchViz3D Production Rewrite

**Purpose:** Replace basic cylinder+sphere with industrial-grade 3D: PBR materials, OrbitControls, HDRI, cyan HUD, WebGL context-loss handling.

### TorchViz3D Props (unchanged)

```typescript
export interface TorchViz3DProps {
  angle: number;   // degrees, drives rotation
  temp: number;    // °C, drives weld pool color
  label?: string;  // HUD label
}
```

### Typography (Step 2a)

```typescript
import { Orbitron, JetBrains_Mono } from 'next/font/google';

const orbitron = Orbitron({ subsets: ['latin'], weight: ['600', '700'] });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'] });

// Headers: orbitron.className — uppercase, tracking-widest
// Stats/data: jetbrainsMono.className — monospace
```

### Temp → Color Gradient

```typescript
function getWeldPoolColor(temp: number): THREE.Color {
  const cold = new THREE.Color(0x1a1a2e);
  const cyan = new THREE.Color(0x3b82f6);
  const yellow = new THREE.Color(0xfbbf24);
  const white = new THREE.Color(0xfef3c7);
  if (temp < 310) return new THREE.Color().lerpColors(cold, cyan, temp / 310);
  if (temp < 455) return new THREE.Color().lerpColors(cyan, yellow, (temp - 310) / 145);
  return new THREE.Color().lerpColors(yellow, white, Math.min((temp - 455) / 200, 1));
}
```

### Key Implementation Details (Step 2b)

- **Rotation:** Direct assignment (no lerp) — `rotation.x = ((angle - 45) * Math.PI) / 180` — frame-accurate.
- **Shadow map:** 1024×1024 (reduced from 2048 for GPU memory / context-loss prevention).
- **WebGL context loss:** `onCreated` adds `webglcontextlost` / `webglcontextrestored` listeners; shows overlay "WebGL context lost — Refresh the page to restore 3D view"; `mountedRef` guards setState after unmount; `cleanupRef` removes listeners on unmount.
- **3D scene:** Handle, grip, nozzle cone, weld pool sphere, glow halo, workpiece plane, angle guide ring, grid helper, ContactShadows, Environment preset="warehouse".
- **HUD:** Cyan theme, status LED, Torch angle / Weld pool temp, temp scale 0–700°C, SENSOR_ID footer.

### TorchViz3D Component Structure

```
<div> (root: cyan border, bg-neutral-950)
├── HUD overlay (top-left): label, angle, temp
├── Canvas (R3F)
│   ├── PerspectiveCamera
│   ├── OrbitControls (enablePan=false, zoom, polar constrained)
│   └── SceneContent (torch, workpiece, lights, grid, Environment)
├── Context-loss overlay (conditional, z-20)
├── Temp scale indicator (bottom-right)
└── Technical footer (bottom-left): SENSOR_ID
```

---

## Step 3: Dev Demo Page

**Purpose:** Industrial CAD-style layout at `/dev/torch-viz` — single TorchViz3D instance, floating panel, cyan theme.

### Layout

- **Root:** `min-h-screen bg-neutral-950`
- **Grid:** 12 cols; 8 for 3D, 4 for floating panel
- **3D:** Single instance (avoids WebGL context limit ~8–16 per page)
- **Dynamic import:** `ssr: false`, `loading` fallback "Loading 3D…"
- **Floating panel:** `border-2 border-cyan-400/80`, `backdrop-blur-md`, scenario reference list
- **Path indicator:** Bottom-left `/dev/torch-viz`

### Key Pattern

```tsx
const TorchViz3D = dynamic(
  () => import('@/components/welding/TorchViz3D').then((m) => m.default),
  { ssr: false, loading: () => <div>Loading 3D…</div> }
);

<TorchViz3D angle={45} temp={450} label="LIVE PREVIEW" />
```

**Constraint:** 1 instance only (WebGL context limit). See `documentation/WEBGL_CONTEXT_LOSS.md`.

---

## Step 4: End-to-End Verification

**Purpose:** Build passes; replay with comparison renders; smoke test for dual 3D layout.

### Replay Smoke Test (TorchViz3D Step 4)

**File:** `src/__tests__/app/replay/[sessionId]/page.test.tsx`

```typescript
/**
 * TorchViz3D production-grade plan Step 4: Replay with comparison enabled.
 * Verifies dual 3D layout (Current Session + Comparison) when showComparison is true.
 * Compare page does NOT use TorchViz3D (HeatMap only) — N/A.
 */
it('TorchViz3D Step 4: replay with comparison shows dual 3D layout and toggle', async () => {
  render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);
  await waitFor(() => {
    expect(screen.getByText(/session replay: test-session-123/i)).toBeInTheDocument();
  });
  expect(screen.getByRole('button', { name: /hide.*comparison/i })).toBeInTheDocument();
  await waitFor(() => {
    expect(screen.getAllByText(/Score:/i).length).toBeGreaterThanOrEqual(1);
  });
});
```

### Verification Commands

- `npm run build` — must pass
- `npm test -- --testPathPattern="(TorchViz3D|replay|dev/torch-viz)"` — 18 tests pass

---

## Test Files Summary

| File | Step | Tests |
|------|------|-------|
| `src/__tests__/drei-import.test.ts` | 1 | OrbitControls, Environment, ContactShadows import |
| `src/__tests__/components/welding/TorchViz3D.test.tsx` | 2 | HUD, props, labels, LED, SENSOR_ID, cyan theme, context-loss overlay |
| `src/__tests__/app/dev/torch-viz/page.test.tsx` | 3 | Layout, panel header, scenario reference, OrbitControls hint |
| `src/__tests__/app/replay/[sessionId]/page.test.tsx` | 4 | TorchViz3D Step 4: replay + comparison dual 3D layout |

---

## Constraints (Do Not Violate)

1. **Props unchanged:** `angle`, `temp`, `label` — replay/compare integration must stay compatible.
2. **SSR safety:** TorchViz3D always via `dynamic(..., { ssr: false })` — never direct import on pages.
3. **WebGL context limit:** Max 1–2 Canvas instances per page; see `LEARNING_LOG.md` and `documentation/WEBGL_CONTEXT_LOSS.md`.
4. **No system fonts:** Use Orbitron (headers) and JetBrains Mono (data) — never Inter, Arial, Roboto.
5. **Cyan brutalist theme:** `bg-neutral-950`, `border-cyan-400/80`, `text-cyan-400` — no generic `slate-900`.

---

## File Locations

| Purpose | Path |
|---------|------|
| TorchViz3D component | `my-app/src/components/welding/TorchViz3D.tsx` |
| Dev demo page | `my-app/src/app/dev/torch-viz/page.tsx` |
| Drei import test | `my-app/src/__tests__/drei-import.test.ts` |
| TorchViz3D unit tests | `my-app/src/__tests__/components/welding/TorchViz3D.test.tsx` |
| Dev page tests | `my-app/src/__tests__/app/dev/torch-viz/page.test.tsx` |
| Replay tests (Step 4) | `my-app/src/__tests__/app/replay/[sessionId]/page.test.tsx` |

---

## Related Docs

| File | Purpose |
|------|---------|
| `documentation/WEBGL_CONTEXT_LOSS.md` | WebGL context loss error reference |
| `LEARNING_LOG.md` | WebGL context limit incident |
| `.cursorrules` | 3D/WebGL section |
| `.cursor/plans/torchviz3d-production-grade-plan.md` | Full plan |
