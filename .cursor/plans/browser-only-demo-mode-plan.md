# Browser-Only Demo Mode — Exhaustive Implementation Plan

**Overall Progress:** 100% (9/9 steps completed)

---

## TLDR

Self-contained demo at `/demo` — 100% in-browser, zero backend/DB/seed. Side-by-side expert vs novice welding replays with scores, HeatMap, TorchViz3D, TorchAngleGraph. One URL, ~30s to value, shareable (LinkedIn, prospects). Reuses existing components; new code: `demo-data.ts`, `demo/page.tsx`, `demo/layout.tsx`. Data synthesized in-browser via signal generators that mirror the issue spec (Python parity deferred).

---

## Critical Architectural Decisions

### Decision 1: Thermal Model — Simplified TypeScript

**Choice:** Use simplified model: `base_temp = 150 + arc_power/50`, `distance_factor = exp(-distance_mm/100)`, angle-driven north/south asymmetry.

**Rationale:** Faster to implement; visuals differ slightly from backend-seeded `/replay/sess_expert_001`. Python parity deferred to follow-up.

**Trade-offs:** Accept ~200KB extra bundle; demo-only file is throwaway when sensors arrive.

**Impact:** `generateThermalSnapshot` in `demo-data.ts` drives all thermal readings.

---

### Decision 2: Hardcoded Scores (94/100, 42/100)

**Choice:** Inline score blocks in demo layout instead of ScorePanel (which fetches via API).

**Rationale:** Avoids modifying ScorePanel for demo-only path; no API calls.

**Trade-offs:** Scores are static; cannot A/B test different score algorithms in demo.

**Impact:** Demo page renders `<span className="...">94/100</span>` and `<span>42/100</span>` directly.

---

### Decision 3: New Route `/demo` Only — No Query-Param Fallback

**Choice:** New route `/demo`; no `/replay?demo=1` fallback.

**Rationale:** Avoids API branching and conditional logic in replay page.

**Trade-offs:** Two entry points (replay vs demo) to maintain.

**Impact:** AppNav and Home link to `/demo`; layout metadata for sharing.

---

### Decision 4: Responsive Layout — `md:grid-cols-2` → `grid-cols-1`

**Choice:** Use `grid-cols-1 md:grid-cols-2` (768px breakpoint).

**Rationale:** Mobile-first; columns stack on narrow viewports.

**Impact:** Demo page grid layout; verified at 375px in DevTools.

---

### Decision 5: Playback End — Stop and Reset, No Auto-Loop

**Choice:** At 15.0s, stop playback and reset timestamp to 0; user must click Play to restart.

**Rationale:** Matches plan; avoids infinite loop confusion.

**Impact:** `useEffect` in demo page checks `next >= DURATION_MS` → `setPlaying(false)` and `return 0`.

---

## Dependency Ordering

| Step | Depends On | Blocks | Can Mock? |
|------|-----------|--------|-----------|
| 1.1 Create types (Session, Frame, ThermalSnapshot) | Nothing | Everything | N/A |
| 1.2 Create demo-data.ts | Types | Demo page, tests | N/A |
| 1.3 Unit test demo-data | demo-data | — | No |
| 2.1 Create demo page | demo-data, utils, components | Layout, tests | Yes — mock HeatMap/TorchViz3D |
| 2.2 Create demo layout (metadata) | Nothing | — | N/A |
| 2.3 Add AppNav Demo link | Nothing | — | N/A |
| 2.4 Demo page test | Demo page | — | Yes — mock all viz |
| 3.1 Verification (manual) | All above | — | No |
| 3.2 Zero-API check | Demo page | — | No |

**Critical path:** types → demo-data → demo page → verification.

---

## Risk Heatmap

| Step | Risk | Probability | What Could Go Wrong | Early Detection | Mitigation |
|------|------|-------------|---------------------|-----------------|------------|
| 1.2 demo-data | Thermal model empty heatmap | 🟡 40% | `point_count === 0` | Unit test fails | Assert `point_count > 0` in test |
| 1.2 demo-data | extractHeatmapData shape mismatch | 🟡 35% | "No thermal data" in HeatMap | Manual load `/demo` | Pass `session.frames`, verify `has_thermal_data` |
| 2.1 Demo page | Component prop mismatch | 🟢 15% | TS error or undefined at runtime | Build + lint | Match replay page prop contracts |
| 2.1 Demo page | WebGL context loss on mobile | 🟢 10% | Blank 3D area | ErrorBoundary catches | Wrapper per component |
| 2.2 Layout | Metadata not applied | 🟢 5% | og:title missing in share | Inspect HTML meta | Use Next.js Metadata API |

---

## Implementation Phases

### Phase 1 — Demo Data Generation

**Goal:** `generateExpertSession()` and `generateNoviceSession()` return valid `Session` objects with non-empty heatmap and angle data.

**Why this phase first:** Demo page and tests depend on this data.

**Time Estimate:** 2–3 hours

**Risk Level:** 🟡 40%

---

#### 🟩 Step 1.1: Create demo-data.ts — *Critical: Data contract drives all downstream*

**Why this is critical:** Produces the core data that HeatMap, TorchAngleGraph, TorchViz3D, and frameUtils consume. Incorrect shape breaks entire demo.

**Context:** Demo must produce `Session` objects with `Frame[]` matching the contract expected by `extractHeatmapData`, `extractAngleData`, `extractCenterTemperatureWithCarryForward`, and `getFrameAtTimestamp`. No API; all data synthesized in-browser. Frames must have `has_thermal_data: true` and non-empty `thermal_snapshots` every 100ms.

**Code Implementation (key excerpts):**

```typescript
// my-app/src/lib/demo-data.ts

import type { Session } from "@/types/session";
import type { Frame } from "@/types/frame";
import type { ThermalSnapshot } from "@/types/thermal";

const DURATION_MS = 15000;
const FRAME_INTERVAL_MS = 10;
const THERMAL_INTERVAL_MS = 100;
const DISTANCES_MM = [10, 20, 30, 40, 50];

function generateThermalSnapshot(
  _t_ms: number,
  amps: number,
  volts: number,
  angle_degrees: number,
  distance_mm: number
): ThermalSnapshot {
  const arc_power = amps * volts;
  const base_temp = 150 + arc_power / 50;
  const distance_factor = Math.exp(-distance_mm / 100);
  const temp_at_distance = base_temp * distance_factor;
  const angle_offset = angle_degrees - 45;
  const north_delta = angle_offset * 3.0;
  const south_delta = -angle_offset * 3.0;
  const east_boost = 15 * distance_factor;
  const west_penalty = -10 * distance_factor;
  return {
    distance_mm,
    readings: [
      { direction: "center", temp_celsius: temp_at_distance },
      { direction: "north", temp_celsius: temp_at_distance + north_delta },
      { direction: "south", temp_celsius: temp_at_distance + south_delta },
      { direction: "east", temp_celsius: temp_at_distance + east_boost },
      { direction: "west", temp_celsius: temp_at_distance + west_penalty },
    ],
  };
}

function expertAmps(t_ms: number): number {
  const t_sec = t_ms / 1000;
  const warmup = t_sec < 0.5 ? Math.sin(t_sec * 10) * 10 : 0;
  return 150 + warmup + Math.sin(t_sec * 2) * 2;
}

function expertVolts(_t_ms: number): number {
  return 22.5;
}

function expertAngle(t_ms: number): number {
  const t_sec = t_ms / 1000;
  return 45 + Math.sin(t_sec * 5) * 0.5;
}

function noviceAmps(t_ms: number): number {
  const t_sec = t_ms / 1000;
  const spike = Math.sin(t_sec * Math.PI) > 0.95 ? 30 : 0;
  return 150 + spike + Math.sin(t_sec * 3) * 10;
}

function noviceVolts(t_ms: number): number {
  const t_sec = t_ms / 1000;
  return 22 - (t_sec / 15) * 4;
}

function noviceAngle(t_ms: number): number {
  const t_sec = t_ms / 1000;
  return 45 + (t_sec / 15) * 20;
}

function buildFrames(
  ampsFn: (t: number) => number,
  voltsFn: (t: number) => number,
  angleFn: (t: number) => number
): Frame[] {
  const frames: Frame[] = [];
  for (let t = 0; t < DURATION_MS; t += FRAME_INTERVAL_MS) {
    const amps = ampsFn(t);
    const volts = voltsFn(t);
    const angle = angleFn(t);
    const thermal_snapshots =
      t % THERMAL_INTERVAL_MS === 0
        ? DISTANCES_MM.map((d) =>
            generateThermalSnapshot(t, amps, volts, angle, d)
          )
        : [];
    frames.push({
      timestamp_ms: t,
      amps,
      volts,
      angle_degrees: angle,
      thermal_snapshots,
      has_thermal_data: thermal_snapshots.length > 0,
      heat_dissipation_rate_celsius_per_sec: null,
      optional_sensors: null,
    });
  }
  return frames;
}

export function generateExpertSession(): Session {
  const frames = buildFrames(expertAmps, expertVolts, expertAngle);
  return {
    session_id: "demo_expert",
    operator_id: "expert_er",
    start_time: new Date().toISOString(),
    weld_type: "stainless_steel_304",
    frames,
    thermal_sample_interval_ms: THERMAL_INTERVAL_MS,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10,
    sensor_sample_rate_hz: 100,
    status: "complete",
    frame_count: frames.length,
    expected_frame_count: frames.length,
    last_successful_frame_index: frames.length - 1,
    validation_errors: [],
    completed_at: new Date().toISOString(),
    disable_sensor_continuity_checks: false,
  };
}

export function generateNoviceSession(): Session {
  const frames = buildFrames(noviceAmps, noviceVolts, noviceAngle);
  return {
    session_id: "demo_novice",
    operator_id: "novice_nr",
    start_time: new Date().toISOString(),
    weld_type: "stainless_steel_304",
    frames,
    thermal_sample_interval_ms: THERMAL_INTERVAL_MS,
    thermal_directions: ["center", "north", "south", "east", "west"],
    thermal_distance_interval_mm: 10,
    sensor_sample_rate_hz: 100,
    status: "complete",
    frame_count: frames.length,
    expected_frame_count: frames.length,
    last_successful_frame_index: frames.length - 1,
    validation_errors: [],
    completed_at: new Date().toISOString(),
    disable_sensor_continuity_checks: true,
  };
}
```

**Subtasks:**
- [x] 🟩 Create `my-app/src/lib/demo-data.ts`
- [x] 🟩 Add `generateThermalSnapshot` and signal helpers
- [x] 🟩 Implement `generateExpertSession()` and `generateNoviceSession()`

**✓ Verification Test:**

| Item | Detail |
|------|--------|
| **Action** | Run `npm test -- demo-data` |
| **Expected** | All tests pass; `point_count > 0` for expert and novice |
| **How to Observe** | Jest output |
| **Pass Criteria** | `generateExpertSession().frames.length === 1500`, `extractHeatmapData(...).point_count > 0`, `extractAngleData(...).points.length > 0` |
| **Common Failures** | `point_count` 0 → check `t % 100 === 0` and `has_thermal_data`; thermal frames every 100ms |

---

### Phase 2 — Demo Page and Integration

**Goal:** User opens `/demo` and sees side-by-side expert vs novice with playback controls; zero API calls.

**Why this phase second:** Depends on demo-data and existing components.

**Time Estimate:** 3–4 hours

**Risk Level:** 🟢 15%

---

#### 🟩 Step 2.1: Create demo page — *Critical: Main user-facing surface*

**Why this is critical:** Central demo experience; integrates all components and playback logic.

**Context:** Demo page renders two columns (expert/novice). Each column: score block, TorchViz3D (dynamic, ssr:false), HeatMap, TorchAngleGraph. Playback loop advances `currentTimestamp` every 10ms. Uses `getFrameAtTimestamp` and `extractCenterTemperatureWithCarryForward` from frameUtils.

**Subtasks:**
- [x] 🟩 Add `my-app/src/app/demo/page.tsx`
- [x] 🟩 Wire playback state (`playing`, `currentTimestamp`) and `useEffect`
- [x] 🟩 Integrate TorchViz3D (dynamic + loading fallback), HeatMap, TorchAngleGraph
- [x] 🟩 Wrap viz components in ErrorBoundary
- [x] 🟩 Add PlaybackControls (play/pause, time display, slider 0–15000)
- [x] 🟩 Add hardcoded score blocks (94/100, 42/100) and feedback bullets
- [x] 🟩 Use `grid-cols-1 md:grid-cols-2` and footer "DEMO MODE — No backend required"

**✓ Verification Test:**

| Item | Detail |
|------|--------|
| **Action** | `npm run dev` → open `http://localhost:3000/demo` → click "PLAY DEMO" → scrub slider |
| **Expected** | Side-by-side columns; TorchViz3D, HeatMap, TorchAngleGraph render; playback 0→15s; slider scrubs |
| **How to Observe** | UI; Network tab (Fetch/XHR) empty |
| **Pass Criteria** | All components render; playback runs; slider works; no fetch/XHR |
| **Common Failures** | 404 → check route; "No thermal data" → Step 1.2; WebGL error → ErrorBoundary |

---

#### 🟩 Step 2.2: Create demo layout with shareable metadata (non-critical)

**Subtasks:**
- [x] 🟩 Add `my-app/src/app/demo/layout.tsx`
- [x] 🟩 Export `metadata` with `title`, `description`, `openGraph`

**✓ Verification Test:**

| Item | Detail |
|------|--------|
| **Action** | Open `/demo` → View Page Source → inspect `<meta property="og:title">` |
| **Expected** | `og:title` = "Live Demo — Shipyard Welding" |
| **How to Observe** | HTML source or DevTools Elements |

---

#### 🟩 Step 2.3: Ensure Demo link in AppNav (non-critical)

**Subtasks:**
- [x] 🟩 AppNav has `<Link href="/demo">Demo</Link>`
- [x] 🟩 Home page has "Try demo" link in loading/error states

**✓ Verification Test:** Navigate from Home → Demo; click Demo in AppNav.

---

#### 🟩 Step 2.4: Demo page unit test (non-critical)

**Subtasks:**
- [x] 🟩 Add `__tests__/app/demo/page.test.tsx`
- [x] 🟩 Mock next/dynamic, HeatMap, TorchAngleGraph
- [x] 🟩 Assert header, scores, playback button, footer, play/pause toggle

**✓ Verification Test:** Run `npm test -- demo/page`.

---

### Phase 3 — Validation and Polish

**Goal:** Demo is production-ready; zero-setup verification passes.

**Time Estimate:** 1 hour

---

#### 🟩 Step 3.1: Manual verification

**Action:**
1. Stop backend (if running)
2. Run `npm run dev`
3. Open `http://localhost:3000/demo`
4. Click "PLAY DEMO" → observe playback
5. Scrub slider → observe time update
6. Resize to 375px → columns stack

**Expected:** Page loads; playback works; responsive; no backend.

---

#### 🟩 Step 3.2: Zero-API verification

**Action:** Open `/demo` with DevTools → Network → filter Fetch/XHR.

**Expected:** Zero requests to `/api` or backend URL.

---

## Pre-Flight Checklist

| Phase | Dependency Check | How to Verify | Status |
|-------|------------------|---------------|--------|
| **Phase 1** | Node.js v18+ | `node --version` | ⬜ |
| | Dependencies installed | `npm install` | ⬜ |
| | Types: Session, Frame, ThermalSnapshot | Import from `@/types` | ⬜ |
| | extractHeatmapData, extractAngleData, frameUtils | Import from utils | ⬜ |
| **Phase 2** | HeatMap, TorchViz3D, TorchAngleGraph | Components exist | ⬜ |
| | ErrorBoundary | Import from `@/components/ErrorBoundary` | ⬜ |
| | Phase 1 complete | demo-data tests pass | ⬜ |
| **Phase 3** | Phase 2 complete | Demo page loads | ⬜ |
| | No backend/DB | Demo works with backend stopped | ⬜ |

---

## Success Criteria (End-to-End)

| Feature | Target Behavior | Verification Method |
|---------|-----------------|---------------------|
| Demo loads | User opens `/demo` → side-by-side expert vs novice | Open `/demo` → two columns, scores 94/100 and 42/100 |
| Playback | Play advances time 0→15s; stops at end; resets to 0 | Click Play → time updates; stops at 15.0s |
| Zero API | No backend calls from demo page | Network tab: zero fetch/XHR |
| Responsive | Columns stack on mobile | Resize to 375px → single column |
| Shareable link | Demo works without backend | Stop uvicorn/Postgres; open `/demo` → works |
| Share metadata | Rich preview when sharing link | og:title present in page metadata |

---

## Progress Tracking

| Phase | Steps | Completed | Percentage |
|-------|-------|-----------|------------|
| Phase 1 | 1 | 1 | 100% |
| Phase 2 | 4 | 4 | 100% |
| Phase 3 | 2 | 2 | 100% |
| **Total** | **9** | **9** | **100%** |

---

## Notes & Learnings

- Demo page uses direct import for HeatMap and TorchAngleGraph (same as replay); only TorchViz3D is dynamic with `ssr: false` and loading fallback.
- `getFrameAtTimestamp` (frameUtils) used instead of `frames.find(f => f.timestamp_ms === currentTimestamp)` for nearest-frame resolution when exact match missing.
- Demo layout adds shareable metadata for LinkedIn/prospects without changing root layout.

---

⚠️ **IMPORTANT:** Do not mark a step 🟩 Done until its verification test passes. If blocked, mark 🟨 In Progress and document what failed.
