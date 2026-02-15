# Feature Implementation Plan: Browser-Only Demo Mode

**Overall Progress:** `33%` (2/6 steps done)

## TLDR

Self-contained demo at `/demo` — 100% in-browser, zero backend/DB/seed. Side-by-side expert vs novice welding replays with scores. One URL, ~30s to value, shareable (LinkedIn, prospects). Reuses HeatMap, TorchViz3D, TorchAngleGraph with in-browser generated data.

---

## Critical Decisions

- **Decision 1:** Use simplified TypeScript thermal model (issue spec) — `150 + arc_power/50` base temp, `exp(-distance_mm/100)` decay. Faster to implement; visuals differ slightly from backend-seeded `/replay/sess_expert_001`. Python parity deferred.
- **Decision 2:** Hardcode scores 94/100 (expert) and 42/100 (novice) — ScorePanel fetches via API; inline blocks avoid modifying ScorePanel for demo-only path.
- **Decision 3:** New route `/demo` and new files only — no `/replay?demo=1` fallback to avoid API branching.
- **Decision 4:** Responsive `md:grid-cols-2` → `grid-cols-1` on mobile (768px breakpoint).
- **Decision 5:** At playback end: reset to 0 and stop; user clicks Play to restart (no auto-loop).

---

## Tasks

### Phase 1 — Demo Data and Page

**Goal:** User opens `/demo` and sees side-by-side expert vs novice replays with scores, playback controls, and zero API calls.

---

- [x] 🟩 **Step 1: Create demo-data.ts** — *Done: Core data generation, thermal model*

**Context:** Demo must produce `Session` objects with `Frame[]` matching the contract expected by `extractHeatmapData`, `extractAngleData`, and `extractCenterTemperatureWithCarryForward`. No API; all data synthesized in-browser.

```typescript
// my-app/src/lib/demo-data.ts — thermal snapshot and session builders
function generateThermalSnapshot(t_ms, amps, volts, angle_degrees, distance_mm): ThermalSnapshot {
  const arc_power = amps * volts;
  const base_temp = 150 + arc_power / 50;
  const distance_factor = Math.exp(-distance_mm / 100);
  const temp_at_distance = base_temp * distance_factor;
  const angle_offset = angle_degrees - 45;
  const north_delta = angle_offset * 3.0;
  const south_delta = -angle_offset * 3.0;
  const east_boost = 15 * distance_factor;
  const west_penalty = -10 * distance_factor;
  return { distance_mm, readings: [...] };
}
export function generateExpertSession(): Session { /* 1500 frames, thermal every 100ms */ }
export function generateNoviceSession(): Session { /* same structure, novice signals */ }
```

**What it does:** Pure functions producing `Session` with 1500 frames (10ms interval), thermal snapshots every 100ms at 5 distances. Expert: stable amps/volts/angle. Novice: spiky amps, drifting volts, drifting angle.

**Why this approach:** Mirrors issue spec; pure TS is easy to unit test; no export/import of static JSON.

**Assumptions:**
- `Session`, `Frame`, `ThermalSnapshot` types match backend schema
- `extractHeatmapData` filters via `hasThermalData` internally
- `heat_dissipation_rate_celsius_per_sec` can be `null` for demo

**Risks:**
- Thermal model produces empty heatmap → Mitigation: unit test `point_count > 0`
- Bundle size ~200KB → Acceptable per issue

---

**Subtasks:**
- [x] 🟩 Add `generateThermalSnapshot` and signal helpers (expert/novice amps, volts, angle)
- [x] 🟩 Implement `generateExpertSession()` returning full `Session`
- [x] 🟩 Implement `generateNoviceSession()` with novice signals
- [x] 🟩 Add unit test: heatmap data has `point_count > 0` for both sessions

**✓ Verification Test:**

| Item | Detail |
|------|--------|
| **Action** | Run `npm test -- demo-data` |
| **Expected** | All assertions pass; `point_count > 0` for expert and novice |
| **How to Observe** | Jest output |
| **Pass** | Tests green; no type errors |
| **Fail** | `point_count` 0 → check `t % 100 === 0` and `has_thermal_data` |

---

- [ ] 🟥 **Step 2: Create demo page** — *Why it matters: New route, state management, component integration*

**Context:** Demo page must render the same components as replay/compare but with data from `demo-data.ts`. No `fetchSession`/`fetchScore`; no `useFrameData` (fixed 0–15000ms). Playback loop drives `currentTimestamp`; components receive derived heatmap, angle, and temp.

**Code snippet:**

```typescript
'use client';
import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { generateExpertSession, generateNoviceSession } from '@/lib/demo-data';
import { extractHeatmapData } from '@/utils/heatmapData';
import { extractAngleData } from '@/utils/angleData';
import { extractCenterTemperatureWithCarryForward } from '@/utils/frameUtils';
import { ErrorBoundary } from '@/components/ErrorBoundary';

const TorchViz3D = dynamic(() => import('@/components/welding/TorchViz3D').then(m => m.default), { ssr: false });
const HeatMap = dynamic(() => import('@/components/welding/HeatMap'), { ssr: false });
const TorchAngleGraph = dynamic(() => import('@/components/welding/TorchAngleGraph'), { ssr: false });

export default function DemoPage() {
  const [playing, setPlaying] = useState(false);
  const [currentTimestamp, setCurrentTimestamp] = useState(0);
  const [expertSession] = useState(() => generateExpertSession());
  const [noviceSession] = useState(() => generateNoviceSession());

  const expertHeatmap = extractHeatmapData(expertSession.frames);
  const noviceHeatmap = extractHeatmapData(noviceSession.frames);
  const expertAngle = extractAngleData(expertSession.frames);
  const noviceAngle = extractAngleData(noviceSession.frames);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setCurrentTimestamp(prev => {
        const next = prev + 10;
        if (next >= 15000) { setPlaying(false); return 0; }
        return next;
      });
    }, 10);
    return () => clearInterval(id);
  }, [playing]);

  const expertFrame = expertSession.frames.find(f => f.timestamp_ms === currentTimestamp);
  const noviceFrame = noviceSession.frames.find(f => f.timestamp_ms === currentTimestamp);
  const expertTemp = extractCenterTemperatureWithCarryForward(expertSession.frames, currentTimestamp);
  const noviceTemp = extractCenterTemperatureWithCarryForward(noviceSession.frames, currentTimestamp);

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 p-8">
        <div>{/* Expert: TorchViz3D, HeatMap, TorchAngleGraph */}</div>
        <div>{/* Novice: same */}</div>
      </div>
      <div>{/* Playback controls: Play/Pause, time display, slider */}</div>
    </div>
  );
}
```

**What it does:** Mounts two columns (expert/novice), each with score block (94/100, 42/100), TorchViz3D, HeatMap, TorchAngleGraph. Playback controls at bottom. Uses `dynamic(..., { ssr: false })` for WebGL components; wraps in ErrorBoundary per existing pattern.

**Why this approach:** Reuses existing components with same prop contracts. Single page, no query params. Playback pattern copied from replay page.

**Assumptions:**
- HeatMap accepts `data`, `activeTimestamp`, `sessionId`, `label`
- TorchAngleGraph accepts `data`, `activeTimestamp`, `sessionId`
- TorchViz3D accepts `angle`, `temp`, `label`
- ErrorBoundary exists at `@/components/ErrorBoundary`

**Risks:**
- WebGL context loss on mobile → ErrorBoundary catches
- `extractHeatmapData` expects `Frame[]` (filtered internally by `hasThermalData`) — pass `session.frames` directly

---

**Subtasks:**
- [ ] 🟥 Add `my-app/src/app/demo/page.tsx` with header, grid, columns
- [ ] 🟥 Wire playback state (playing, currentTimestamp) and useEffect
- [ ] 🟥 Integrate TorchViz3D, HeatMap, TorchAngleGraph with dynamic import + ErrorBoundary
- [ ] 🟥 Add PlaybackControls (play/pause, time display, slider 0–15000)
- [ ] 🟥 Add hardcoded score blocks (94/100, 42/100) and feedback bullets
- [ ] 🟥 Use `grid-cols-1 md:grid-cols-2` for responsive layout
- [ ] 🟥 Add footer "DEMO MODE - No backend required"

**✓ Verification Test:**

| Item | Detail |
|------|--------|
| **Action** | `npm run dev` → open `http://localhost:3000/demo` → click "PLAY DEMO" → scrub slider |
| **Expected** | Side-by-side expert and novice; TorchViz3D, HeatMap, TorchAngleGraph render; playback 0→15s; slider scrubs; zero API calls |
| **How to Observe** | UI; Network tab (Fetch/XHR) empty |
| **Pass** | All components render; playback runs; slider works; no fetch/XHR |
| **Fail** | 404 → check route; "No thermal data" → Step 1; WebGL error → ErrorBoundary |

---

- [x] 🟩 **Step 3: Unit test for demo data** (non-critical)

**Subtasks:**
- [x] 🟩 Add `__tests__/lib/demo-data.test.ts`
- [x] 🟩 Assert `generateExpertSession().frames.length === 1500`
- [x] 🟩 Assert `extractHeatmapData(...).point_count > 0` for expert and novice
- [x] 🟩 Assert `extractAngleData(...).points.length > 0` for expert and novice

**✓ Verification Test:**

| Item | Detail |
|------|--------|
| **Action** | Run `npm test -- demo-data` |
| **Expected** | All assertions pass |
| **How to Observe** | Jest output |
| **Pass** | Tests green |
| **Fail** | `point_count` 0 → thermal logic bug; check `t % 100 === 0` |

---

- [ ] 🟥 **Step 4: Responsive layout** (non-critical)

**Subtasks:**
- [ ] 🟥 Ensure grid uses `grid-cols-1 md:grid-cols-2`
- [ ] 🟥 Verify on narrow viewport (375px) columns stack vertically

**✓ Verification Test:**

| Item | Detail |
|------|--------|
| **Action** | Resize browser to 375px; load `/demo` |
| **Expected** | Columns stack vertically; no horizontal overflow; controls usable |
| **How to Observe** | DevTools responsive mode |
| **Pass** | Layout adapts; no scroll overflow |
| **Fail** | Two columns on mobile → use `md:` (768px) |

---

### Phase 2 — Polish and Validation

**Goal:** Demo is production-ready; zero-setup verification passes.

---

- [ ] 🟥 **Step 5: ErrorBoundary and edge cases** (non-critical)

**Subtasks:**
- [ ] 🟥 Wrap TorchViz3D, HeatMap, TorchAngleGraph in ErrorBoundary
- [ ] 🟥 Handle `expertFrame`/`noviceFrame` undefined → `angle ?? 45`

**✓ Verification Test:**

| Item | Detail |
|------|--------|
| **Action** | Load `/demo`; verify no uncaught errors |
| **Expected** | ErrorBoundary catches WebGL failures; no white screen |
| **How to Observe** | Console |
| **Pass** | Graceful degradation |
| **Fail** | White screen → ensure ErrorBoundary wraps 3D/viz components |

---

- [ ] 🟥 **Step 6: Zero-API verification** (non-critical)

**Subtasks:**
- [ ] 🟥 Verify Network tab shows no fetch to backend when on `/demo`

**✓ Verification Test:**

| Item | Detail |
|------|--------|
| **Action** | Open `/demo`; DevTools → Network → filter Fetch/XHR |
| **Expected** | Zero requests to `/api` or backend URL |
| **How to Observe** | Network panel |
| **Pass** | Zero API calls from demo page |
| **Fail** | API calls present → remove any fetch/useEffect that hits backend |

---

## Pre-Flight Checklist (Print & Check Each Phase)

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Next.js app runs | `npm run dev` → localhost:3000 loads | ⬜ |
| | Types: Session, Frame, ThermalSnapshot | Import from `@/types` without error | ⬜ |
| | extractHeatmapData, extractAngleData, extractCenterTemperatureWithCarryForward | Import from utils | ⬜ |
| | HeatMap, TorchViz3D, TorchAngleGraph | Components exist; accept data/sessionId props | ⬜ |
| | ErrorBoundary | Import from `@/components/ErrorBoundary` | ⬜ |
| **Phase 2** | Demo route | `/demo` loads without 404 | ⬜ |
| | No backend/DB | Demo works with backend stopped | ⬜ |

---

## Risk Heatmap (Where You'll Get Stuck)

| Phase | Risk Level | What Could Go Wrong | How to Detect Early |
|-------|-----------|----------------------|---------------------|
| Phase 1 | 🟡 40% | Thermal model produces empty heatmap | Unit test `point_count > 0` fails |
| Phase 1 | 🟡 35% | extractHeatmapData expects different frame shape | HeatMap shows "No thermal data" — verify heatmapData API and pass `frames` |
| Phase 1 | 🟢 15% | Component prop mismatch | TypeScript errors or runtime "undefined" |
| Phase 2 | 🟢 10% | WebGL context loss on mobile | ErrorBoundary catches; add context-loss handler later |

---

## Success Criteria (End-to-End Validation)

| Feature | Target Behavior | Verification Method |
|---------|-----------------|---------------------|
| Demo loads | User opens `/demo` → side-by-side expert vs novice | **Test:** Open `/demo` → **Expect:** Two columns, scores 94/100 and 42/100 → **Location:** UI |
| Playback | Play advances time 0→15s; stops at end; resets to 0 | **Test:** Click Play → **Expect:** Time display updates; stops at 15.0s → **Location:** UI |
| Zero API | No backend calls from demo page | **Test:** Load `/demo` with Network tab open → **Expect:** Zero fetch/XHR → **Location:** DevTools Network |
| Responsive | Columns stack on mobile | **Test:** Resize to 375px → **Expect:** Single column layout → **Location:** UI |
| Shareable link | Demo works without backend | **Test:** Stop uvicorn/Postgres; open `/demo` → **Expect:** Page works → **Location:** Browser |

---

⚠️ **Do not mark a step as 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.**
