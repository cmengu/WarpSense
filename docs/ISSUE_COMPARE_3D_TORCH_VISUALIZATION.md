# Issue: Compare Page 3D Torch Visualization

**Type:** Feature  
**Priority:** Normal  
**Effort:** Small  
**Labels:** `frontend` `compare` `3d` `WebGL` `TorchWithHeatmap3D`

---

## TL;DR

Add side-by-side 3D torch visualizations (TorchWithHeatmap3D) to the compare page, driven by the shared timeline slider. Each column shows Session A and Session B with angle and temperature synced to `currentTimestamp`. Uses dynamic import with `ssr: false` and a loading placeholder. Stays within WebGL context limit (2 instances = max per page).

---

## Current State vs Expected Outcome

### Current State
- Compare page shows 2D heatmaps (Session A | Delta | Session B) and alert feed
- No 3D torch visualization on compare page
- Replay and demo pages each use 2× TorchWithHeatmap3D

### Expected Outcome
- Compare page shows 3D torch + thermal workpiece for Session A and Session B in a side-by-side grid (lg:grid-cols-2)
- Both 3D views sync to `currentTimestamp` (angle from frame at timestamp, center temp with carry-forward)
- Loading state: "Loading 3D…" placeholder while TorchWithHeatmap3D hydrates
- Renders only when `currentTimestamp != null` and both sessions have frames

---

## Relevant Files

| File | Action |
|------|--------|
| [my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx](my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.tsx) | Add imports, dynamic TorchWithHeatmap3D, 3D block |
| `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx` | New — add 6 test cases (see Tests section) |

---

## Exact Implementation

### 1. Add imports at top (alongside existing)

```typescript
import dynamic from 'next/dynamic';
import { getFrameAtTimestamp, extractCenterTemperatureWithCarryForward } from '@/utils/frameUtils';
import { THERMAL_MAX_TEMP, THERMAL_MIN_TEMP, THERMAL_COLOR_SENSITIVITY } from '@/constants/thermal';
```

### 2. Add dynamic import after imports block

```typescript
const TorchWithHeatmap3D = dynamic(
  () => import('@/components/welding/TorchWithHeatmap3D').then((m) => m.default),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-64 w-full items-center justify-center rounded-xl border-2 border-blue-400/40 bg-neutral-900">
        <span className="text-blue-400/80 animate-pulse">Loading 3D…</span>
      </div>
    ),
  }
);
```

### 3. Add 3D block inside `ComparePageInner`

**Insert point:** Immediately after the closing `</div>` of the timeline/slider block, and before the `{heatmapDataA?.point_count && heatmapDataB?.point_count && (...)}` legend paragraph. (Use this text anchor — do not rely on line numbers.)

```tsx
{/* 3D Torch Visualization — side-by-side */}
{currentTimestamp != null && sessionA?.frames && sessionB?.frames && (
  <ErrorBoundary>
    <div className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div>
        {(() => {
          const frame = getFrameAtTimestamp(sessionA.frames, currentTimestamp);
          const angle = frame?.angle_degrees ?? 45;
          const temp = extractCenterTemperatureWithCarryForward(sessionA.frames, currentTimestamp);
          return (
            <TorchWithHeatmap3D
              angle={angle}
              temp={temp}
              label={`Session A (${sessionIdA})`}
              frames={frameDataA.thermal_frames}
              activeTimestamp={currentTimestamp}
              maxTemp={THERMAL_MAX_TEMP}
              minTemp={THERMAL_MIN_TEMP}
              colorSensitivity={THERMAL_COLOR_SENSITIVITY}
            />
          );
        })()}
      </div>
      <div>
        {(() => {
          const frame = getFrameAtTimestamp(sessionB.frames, currentTimestamp);
          const angle = frame?.angle_degrees ?? 45;
          const temp = extractCenterTemperatureWithCarryForward(sessionB.frames, currentTimestamp);
          return (
            <TorchWithHeatmap3D
              angle={angle}
              temp={temp}
              label={`Session B (${sessionIdB})`}
              frames={frameDataB.thermal_frames}
              activeTimestamp={currentTimestamp}
              maxTemp={THERMAL_MAX_TEMP}
              minTemp={THERMAL_MIN_TEMP}
              colorSensitivity={THERMAL_COLOR_SENSITIVITY}
            />
          );
        })()}
      </div>
    </div>
  </ErrorBoundary>
)}
```

---

## Alignment Decisions

**2D heatmaps:** Keep all three (Session A | Delta | Session B). The Delta heatmap has no 3D equivalent and is uniquely useful for comparing thermal differences between sessions. Do not hide or replace them.

**Score display:** No score blocks on the compare page. The compare page does not fetch or display scores. Do not add score UI; Cursor must not improvise.

---

## Tests

**File:** `my-app/src/app/compare/[sessionIdA]/[sessionIdB]/page.test.tsx`

Mock `TorchWithHeatmap3D` as `<div data-testid="torch-3d" data-label={label} />` (same pattern as replay page tests — mock the module so label prop can be asserted).

**Cases to add:**

1. Does not render torch block when `currentTimestamp` is null
2. Does not render torch block when sessionA frames are empty
3. Does not render torch block when sessionB frames are empty
4. Renders two torch instances when both sessions loaded and timestamp set
5. Session A torch receives correct label (`Session A (sess_expert_001)`)
6. Session B torch receives correct label (`Session B (sess_novice_001)`)

---

## Acceptance Criteria

- [ ] Both torch views render and sync when timeline slider moves
- [ ] 3D block is absent when loading or sessions have no frames
- [ ] No console errors about WebGL context limit
- [ ] Existing heatmap/delta/alert sections are unchanged
- [ ] ESLint max-torchviz3d-per-page passes (exactly 2 instances)

---

## Risk / Notes

- **WebGL context limit:** Compare page adds 2× TorchWithHeatmap3D = 2 Canvases. `MAX_TORCHVIZ3D_PER_PAGE = 2` — we are at the limit. No other 3D on the same page. OK per [my-app/src/constants/webgl.ts](my-app/src/constants/webgl.ts).
- **ESLint:** `max-torchviz3d-per-page` allows max 2; compare page will have exactly 2. Passes.
- **Dynamic import:** Required — TorchWithHeatmap3D uses Three.js/WebGL and must not run during SSR.

---

## Product Vision

Brings the 3D weld torch + thermal workpiece visualization to the comparison flow. Supervisors can see expert vs novice torch angle and thermal state side-by-side at any moment in playback, complementing the existing 2D heatmap and alert feed.
