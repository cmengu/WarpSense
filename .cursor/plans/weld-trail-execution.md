# Weld Trail — Execution Plan

**Overall Progress:** `100%` (Step 3 awaiting [MANUAL GATE PASSED])

## TLDR

Add a Weld Trail component inside TorchWithHeatmap3D: a colored point cloud on the workpiece showing torch path up to `activeTimestamp`. Incorporates fixes from spec review: (1) **arc-active only** — filter to `volts > 1 && amps > 1`; (2) **demo data has travel_speed** — add `travel_speed_mm_per_min` to demo-data.ts; (3) **BufferGeometry lifecycle** — useEffect + useRef + useState(ready) for create/dispose; pre-allocate fixed 10000 points; second useEffect updates via .array.set() with overflow bounds check.

---

## Critical Decisions

- **Arc-active filter:** Use `volts > 1 && amps > 1`. Arc-off frames excluded from trail entirely.
- **Demo data:** Add `travel_speed_mm_per_min` to `buildFrames`. Expert: 370–430 mm/min. Novice: 250–550 mm/min (min<300, max>500). Import from `@/constants/aluminum` — do not define locally.
- **Fallback:** If all frames null `travel_speed_mm_per_min`, fall back to timestamp-linear. `computeTrailData` accepts optional `onFallbackWarning?: () => void`; component passes hasWarnedRef-guarded callback. Tests pass `jest.fn()` directly.
- **BufferGeometry:** useEffect create/dispose; useState(ready) triggers re-render when geometry/material ready (mirror ThermalPlate). Pre-allocate fixed 10000 points. Second useEffect updates via .array.set() with overflow bounds check.
- **Render pattern:** Create geometry and material in useEffect; set `ready` via useState when complete (required — refs alone do not trigger re-render). Render `<points ... />` only when ready. Do NOT use `useThree().scene.add`, `<primitive>`, or `useFrame` for scene management.
- **WeldTrail export:** Use named export `export function WeldTrail(...)`. Import as `import { WeldTrail } from './WeldTrail';`.

---

## Clarification Gate

| Unknown | Required | Source | Blocking | Resolved |
|---------|----------|--------|----------|----------|
| Arc-active threshold | volts > 1 && amps > 1 | Codebase grep | Step 2 | ✅ |
| Demo travel_speed range | Expert 370–430, Novice min<300 max>500 | mock_sessions.py | Step 1 | ✅ |
| frameUtils arc helper | Add isArcActive | Codebase | Step 2 | ✅ |

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
Use targeted grep only. Read full file content only when a specific edit anchor is needed.

(1) grep -rn "buildFrames" my-app/src/
(2) grep -En "materialReady|setMaterialReady" my-app/src/components/welding/ThermalPlate.tsx
(3) grep -En "group position=.*WORKPIECE_GROUP_Y|WORKPIECE_GROUP_Y" my-app/src/components/welding/TorchWithHeatmap3D.tsx
(4) grep -En "export interface Frame|heat_dissipation_rate" my-app/src/types/frame.ts
(5) cd my-app && npm test -- 2>&1 | grep -E "Tests:|passing|failing"
(6) wc -l my-app/src/lib/demo-data.ts my-app/src/components/welding/ThermalPlate.tsx my-app/src/components/welding/TorchWithHeatmap3D.tsx

Do not change anything. Show full output and wait.
```

**Baseline Snapshot (agent fills during pre-flight):**
```
Test count before plan: ____
Line count demo-data.ts:    ____
Line count ThermalPlate.tsx: ____
Line count TorchWithHeatmap3D.tsx: ____
```

**Checks before Step 1:**
- [ ] `buildFrames` pushes frames without `travel_speed_mm_per_min`
- [ ] `Frame` interface lacks `travel_speed_mm_per_min`
- [ ] ThermalPlate uses `const [materialReady, setMaterialReady] = useState(false)` and calls `setMaterialReady(true)` after creating resources
- [ ] Workpiece group at ~lines 199–221 in TorchWithHeatmap3D

---

## Steps Analysis

| Step | Classification | Functional/Hygiene | Idempotent |
|------|----------------|--------------------|------------|
| 1 | Critical | Functional | Yes |
| 2 | Critical | Functional | Yes |
| 3 | Critical | Functional | Yes |
| 4 | Non-critical | Hygiene (doc only) | Yes |

**Rollback note:** Steps 1–3 are functional. Step 4 is documentation. During an incident, revert only Steps 1–3.

---

## Phase 1 — Foundation (demo + constants)

**Goal:** Demo data includes `travel_speed_mm_per_min` with verified variability; Frame type and constants ready.

---

- [x] 🟩 **Step 1: Add travel_speed_mm_per_min to demo-data.ts and Frame type**

  **Idempotent:** Yes.

  **Context:** Demo data currently lacks travel_speed. Add speed so novice shows visible clustering vs expert even spacing.

  **Pre-Read Gate:**
  - `grep -rn "buildFrames" my-app/src/` — list every caller; all must be updated in 1f
  - `grep -n "frames.push" my-app/src/lib/demo-data.ts` — confirm exact structure
  - `grep -n "export interface Frame" my-app/src/types/frame.ts` — confirm Frame start

  **1a — Create `my-app/src/constants/aluminum.ts`:**
  ```typescript
  /** Fallback travel speed when frame has null travel_speed_mm_per_min. Matches backend AL_TRAVEL_SPEED_BASE_MEAN. */
  export const AL_TRAVEL_SPEED_BASE_MEAN = 400;
  export const AL_TRAVEL_SPEED_EXPERT_MIN = 370;
  export const AL_TRAVEL_SPEED_EXPERT_MAX = 430;
  export const AL_TRAVEL_SPEED_NOVICE_MIN = 250;
  export const AL_TRAVEL_SPEED_NOVICE_MAX = 550;
  ```

  **1b — demo-data.ts:** Import from `@/constants/aluminum`. Do NOT define constants locally.

  **1c — buildFrames:** Change signature to accept `travelSpeedFn: (t: number) => number`. In the loop, add `travel_speed_mm_per_min: travelSpeedFn(t)` to each frame object.

  **1d — Expert travel speed:** Deterministic, must reach both 370 and 430. Use: `(t) => AL_TRAVEL_SPEED_EXPERT_MIN + (AL_TRAVEL_SPEED_EXPERT_MAX - AL_TRAVEL_SPEED_EXPERT_MIN) * (0.5 + 0.5 * Math.sin(t / 500))` — spans 370–430.

  **1e — Novice travel speed:** Variable, must span below 300 and above 500. Use: `(t) => Math.min(AL_TRAVEL_SPEED_NOVICE_MAX, Math.max(AL_TRAVEL_SPEED_NOVICE_MIN, 400 + 120 * Math.sin(t / 2000) + 80 * Math.sin(t / 700)))`.

  **1f — Update every buildFrames caller:** Run `grep -rn "buildFrames" my-app/src/` and update every call site. At minimum: generateExpertSession and generateNoviceSession pass the respective travelSpeedFn as fourth argument.

  **1g — Frame type:** Add after `heat_dissipation_rate_celsius_per_sec`:
  ```typescript
  /**
   * Torch travel speed along weld seam in mm/min.
   * Optional — backend sends it; older sessions may lack it.
   */
  travel_speed_mm_per_min?: number | null;
  ```

  **✓ Verification Test (run BEFORE git add):**
  - `cd my-app && npm test -- demo-data.test.ts` — must pass
  - `cd my-app && npx tsc --noEmit` — must exit 0. If tsc fails: fix all type errors, then proceed.
  - Any tsc error means buildFrames callers need updating.

  **Git Checkpoint (only after verification passes):**
  ```bash
  git add my-app/src/constants/aluminum.ts my-app/src/lib/demo-data.ts my-app/src/types/frame.ts
  git commit -m "step 1: add travel_speed_mm_per_min to demo data and Frame type"
  ```
  - Add to demo-data.test.ts:
    - Expert: `expect(Math.min(...expert.frames.map(f => f.travel_speed_mm_per_min!))).toBeGreaterThanOrEqual(AL_TRAVEL_SPEED_EXPERT_MIN)`; `expect(Math.max(...expert.frames.map(f => f.travel_speed_mm_per_min!))).toBeLessThanOrEqual(AL_TRAVEL_SPEED_EXPERT_MAX)`
    - Novice: `expect(Math.min(...novice.frames.map(f => f.travel_speed_mm_per_min!))).toBeLessThan(300)`; `expect(Math.max(...novice.frames.map(f => f.travel_speed_mm_per_min!))).toBeGreaterThan(500)`
    - Every frame: `expect(f.travel_speed_mm_per_min).not.toBeNull(); expect(f.travel_speed_mm_per_min).not.toBeUndefined()`

---

## Phase 2 — WeldTrail Component

**Goal:** WeldTrail.tsx created with arc-active filter, cumulative distance mapping, useState(ready), fixed pre-allocation, overflow bounds check.

---

- [x] 🟩 **Step 2: Create WeldTrail.tsx and WeldTrail.test.tsx**

  **Idempotent:** Yes.

  **Context:** WeldTrail renders arc-active points only. Uses cumulative distance for X. Fixed 10000-point pre-allocation. useState(ready) triggers re-render when geometry/material created.

  **Pre-Read Gate:**
  - `grep -n "isArcActive" my-app/src/utils/frameUtils.ts` — must return 0 matches
  - Read ThermalPlate.tsx: `const [materialReady, setMaterialReady] = useState(false)` and `setMaterialReady(true)` after texture/material creation

  **2a — Add to frameUtils.ts:**
  ```typescript
  export function isArcActive(frame: Frame): boolean {
    return !!(frame.volts != null && frame.volts > 1 && frame.amps != null && frame.amps > 1);
  }
  ```

  **2b — Mandated render pattern (mirror ThermalPlate):**
  - `const [ready, setReady] = useState(false)` — required because setting refs does NOT trigger re-render; component would stay null forever without this.
  - First useEffect: Create BufferGeometry and PointsMaterial. Call `setReady(true)` after creation. Cleanup: dispose both; `setReady(false)`.
  - Render: `if (!ready || count === 0) return null;` then `<points ref={pointsRef} geometry={geometryRef.current} material={materialRef.current} />`.
  - Do NOT use `useThree().scene.add`, `<primitive>`, or `useFrame` for scene management.

  **2c — Pre-allocate attributes (mandatory):**
  - Fixed size only: `const MAX_POINTS = 10000` (10000 * 3 floats ≈ 120KB). Do NOT use `frames.length` — frames is not stable at mount time (compare page loads sessions asynchronously).
  - In first useEffect: `geo.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array(MAX_POINTS * 3), 3));` same for color.

  **2d — Second useEffect (mandatory):**
  When `count === 0`: `geo.setDrawRange(0, 0); return;` — do not skip; reset draws nothing so stale points disappear.
  When `count > 0`: bounds check before `.array.set()`:
  ```typescript
  if (positions.length > geo.attributes.position.array.length) {
    console.error('[WeldTrail] positions overflow pre-allocated buffer');
    return;
  }
  ```
  Same check for colors. Then `geo.attributes.position.array.set(positions); geo.attributes.position.needsUpdate = true;` (same for color); `geo.setDrawRange(0, count)`.

  **2e — Second useEffect behavior:**
  Deps: `[positions, colors, count]`. This fires on every `activeTimestamp` change during playback — intentional; trail must update as playback advances. `.array.set()` is the correct non-allocating update. Do NOT add memoization or early-return optimization that prevents updates during playback.

  **2f — computeTrailData (extract useMemo body):**
  Create standalone exported function:
  ```typescript
  export function computeTrailData(
    frames: Frame[],
    activeTimestamp: number,
    plateSize: number,
    onFallbackWarning?: () => void
  ): { positions: Float32Array; colors: Float32Array; count: number }
  ```
  - Contains all position/color logic (arc-active filter, cumulative distance, timestamp fallback, sampling, X/Z bounds).
  - When `allNullSpeed`: call `onFallbackWarning?.()` (do NOT use hasWarnedRef inside — caller owns that).
  - Component: `const warnRef = useRef(false); const cb = useCallback(() => { if (!warnRef.current) { console.warn('[WeldTrail] ...'); warnRef.current = true; } }, []);` then `useMemo(() => computeTrailData(frames, activeTimestamp, plateSize, cb), [frames, activeTimestamp, plateSize, cb])`. Do NOT add warnRef to useCallback deps — refs are stable objects; .current is read at call time, not captured. Adding warnRef would recreate cb on every render, invalidating useMemo.
  - Reset warn flag on session change: `useEffect(() => { warnRef.current = false; }, [frames]);` — when frames identity changes (new session loaded), reset so fallback can warn again. Note: This is component-level only and cannot be unit tested via computeTrailData. Verify manually in Step 3 gate.
  - Tests: import `computeTrailData` directly from WeldTrail.tsx; pass `jest.fn()` for onFallbackWarning; assert `jest.fn()` called once for all-null travel_speed.
  - Add comment above useMemo: `// CPU-side Float32Array allocation per activeTimestamp is intentional and acceptable at demo scale (~200 points).`

  **2g — Module-level imports and constants (at top of WeldTrail.tsx):**
  - Add to imports: `import { FRAME_INTERVAL_MS } from '@/constants/validation';`
  - Add after imports, at module level (not inside computeTrailData):
  ```typescript
  const FRAME_DURATION_MIN = FRAME_INTERVAL_MS / 60000;
  ```
  Do NOT put either statement inside computeTrailData. Imports are illegal inside functions in TypeScript.

  **Position mapping (inside computeTrailData):**
  - Filter: `arcActive = frames.filter(f => isArcActive(f) && f.timestamp_ms <= activeTimestamp)`. If `arcActive.length < 2` return `{ positions: new Float32Array(0), colors: new Float32Array(0), count: 0 }`.
  - Fallback: `allNullSpeed = arcActive.every(f => f.travel_speed_mm_per_min == null)`. If true: call `onFallbackWarning?.()`.
  - Two-pass normalization (mandatory):
    - **Pass 1:** Iterate arcActive, accumulate cumDist per frame with `cumDist += (f.travel_speed_mm_per_min ?? AL_TRAVEL_SPEED_BASE_MEAN) * FRAME_DURATION_MIN`. Store raw cumDist values (e.g. in array). After pass 1: `totalDist = cumDist || 1`.
    - **Pass 2:** For each stored raw cumDist, compute `xNorm = rawCumDist / totalDist`. Then `x = xNorm * plateSize - (plateSize/2)`.
    - Do NOT compute xNorm inline during Pass 1 — totalDist is not yet known and would produce NaN.
  - Timestamp path (when allNullSpeed): `totalMs = arcActive[last].timestamp_ms - arcActive[0].timestamp_ms || 1`. `xNorm = (f.timestamp_ms - arcActive[0].timestamp_ms) / totalMs`. `x = xNorm * plateSize - (plateSize/2)`.
  - Sample every 5th: `withDist.filter((_, i) => i % 5 === 0)`.
  - X bounds: All x must be in `[-plateSize/2, plateSize/2]`.
  - Z drift: `(angle_degrees ?? 45) * 0.005`, clamped to `[-0.3, 0.3]`.

  **2h — Color (inside computeTrailData):** `extractCenterTemperature(frame)` or 450. `tempToTrailColor`: green <200, orange <400, red >=400.

  **2i — WeldTrail.tsx exports:** `export function WeldTrail(...)` and `export function computeTrailData(...)` (both named).

  **2j — Create `my-app/src/__tests__/components/welding/WeldTrail.test.tsx`:**
  - Import `computeTrailData` from WeldTrail.tsx. Import `isArcActive` from `@/utils/frameUtils`. Import `Frame` from `@/types/frame`.
  - Define `makeFrame` helper before any test cases (required — tests use it):
  ```typescript
  function makeFrame(overrides: Partial<{
    timestamp_ms: number;
    volts: number | null;
    amps: number | null;
    angle_degrees: number;
    travel_speed_mm_per_min: number | null;
    has_thermal_data: boolean;
    thermal_snapshots: unknown[];
  }> = {}): Frame {
    return {
      timestamp_ms: 0,
      volts: 22,
      amps: 150,
      angle_degrees: 45,
      travel_speed_mm_per_min: 400,
      has_thermal_data: false,
      thermal_snapshots: [],
      heat_dissipation_rate_celsius_per_sec: 0,
      ...overrides,
    } as unknown as Frame;
  }

  const singleArcOnFrame = makeFrame({ timestamp_ms: 0, volts: 22, amps: 150 });
  ```
  - isArcActive boundary: `it('returns false when volts === 1 exactly (boundary)', () => { expect(isArcActive(makeFrame({ volts: 1, amps: 150 }))).toBe(false); });` and `it('returns false when amps === 1 exactly (boundary)', () => { expect(isArcActive(makeFrame({ volts: 22, amps: 1 }))).toBe(false); });`
  - Arc-off frames (volts=0 or amps=0): produce zero points
  - Arc-on frames (volts>1, amps>1): produce points
  - Cumulative distance: 12 arc-active frames. `const frames = [...Array.from({ length: 6 }, (_, i) => makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 150, travel_speed_mm_per_min: 200 })), ...Array.from({ length: 6 }, (_, i) => makeFrame({ timestamp_ms: (i + 6) * 10, volts: 22, amps: 150, travel_speed_mm_per_min: 600 }))];` Sampling every 5th gives indices 0, 5, 10 → 3 points. `computeTrailData(frames, 120, 3)`. `lowSpeedStep = x[1] - x[0]`; `highSpeedStep = x[2] - x[1]`. Speed 600 is 3× speed 200 — use ratio with tolerance: `expect(highSpeedStep / lowSpeedStep).toBeGreaterThan(2.5); expect(highSpeedStep / lowSpeedStep).toBeLessThan(3.5);` — not exact equality (floating point).
  - Array length integrity: `it('positions and colors have length exactly count * 3', () => { const frames = Array.from({ length: 20 }, (_, i) => makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 150, travel_speed_mm_per_min: 400 })); const { positions, colors, count } = computeTrailData(frames, 200, 3); expect(positions.length).toBe(count * 3); expect(colors.length).toBe(count * 3); });` — ensures no off-by-one in loop; malformed arrays would shift colors.
  - Color correctness (green for cold, red for hot):
    - `it('cold frames produce green color (R low, G high)', () => { const frames = Array.from({ length: 20 }, (_, i) => makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 150, travel_speed_mm_per_min: 400, has_thermal_data: true, thermal_snapshots: [{ distance_mm: 10, readings: [{ direction: 'center', temp_celsius: 100 }] }] })); const { colors, count } = computeTrailData(frames, 200, 3); expect(count).toBeGreaterThan(0); const r = colors[0]; const g = colors[1]; expect(g).toBeGreaterThan(r); });` — temp 100°C below 200 threshold → green (G > R)
    - `it('hot frames (fallback 450°C) produce red color (R high, G low)', () => { const frames = Array.from({ length: 20 }, (_, i) => makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 150 })); const { colors, count } = computeTrailData(frames, 200, 3); expect(count).toBeGreaterThan(0); const r = colors[0]; const g = colors[1]; expect(r).toBeGreaterThan(g); });` — no thermal → 450°C fallback → red (R > G)
  - X bounds: All computed x values in `[-plateSize/2, plateSize/2]`
  - Z clamp: `it('extreme angle does not push Z outside [-0.3, 0.3]', () => { const frames = Array.from({ length: 20 }, (_, i) => makeFrame({ timestamp_ms: i * 10, volts: 22, amps: 150, angle_degrees: 89.6, travel_speed_mm_per_min: 400 })); const { positions, count } = computeTrailData(frames, 300, 3); for (let i = 0; i < count; i++) { expect(positions[i * 3 + 2]).toBeLessThanOrEqual(0.3); expect(positions[i * 3 + 2]).toBeGreaterThanOrEqual(-0.3); } });`
  - All null travel_speed: `const warnSpy = jest.fn(); computeTrailData(frames, 300, 3, warnSpy); expect(warnSpy).toHaveBeenCalledTimes(1);` — verifies computeTrailData calls onFallbackWarning once per invocation. The component's warnRef guard (preventing repeated warnings during playback) is component-level, not testable here. Verified manually in Step 3 gate.
  - Empty frames: `computeTrailData([], 0, 3)` returns `{ count: 0 }`, no crash
  - Single frame: `computeTrailData([singleArcOnFrame], 10, 3)` returns `{ count: 0 }` (arcActive.length < 2)

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/WeldTrail.tsx my-app/src/__tests__/components/welding/WeldTrail.test.tsx my-app/src/utils/frameUtils.ts
  git commit -m "step 2: create WeldTrail with arc-active filter and cumulative distance"
  ```

  **✓ Verification Test:**
  - **Action:** `cd my-app && npm test -- WeldTrail`
  - **Pass:** All WeldTrail tests pass.
  - **Grep check (no hardcoded FRAME_DURATION_MIN):** `grep -n "10 / 60000\|10/60000" my-app/src/components/welding/WeldTrail.tsx` — must return 0 matches. Confirms `FRAME_INTERVAL_MS` import is used, not magic number.

---

- [ ] 🟨 **Step 3: Integrate WeldTrail into TorchWithHeatmap3D + Manual Gate**

  **Idempotent:** Yes.

  **Pre-Read Gate:**
  - `grep -n "group position=.*WORKPIECE_GROUP_Y" my-app/src/components/welding/TorchWithHeatmap3D.tsx` — exactly 1 match
  - `grep -n "hasThermal \?" my-app/src/components/welding/TorchWithHeatmap3D.tsx` — anchor for insertion

  **Insertion:** Inside the workpiece group, before ThermalPlate/mesh:
  ```tsx
  {frames.length >= 2 && activeTimestamp > (frames[0]?.timestamp_ms ?? 0) && (
    <WeldTrail
      frames={frames}
      activeTimestamp={activeTimestamp}
      plateSize={plateSize ?? 3}
    />
  )}
  ```
  **Import:** `import { WeldTrail } from './WeldTrail';`

  **Git Checkpoint:**
  ```bash
  git add my-app/src/components/welding/TorchWithHeatmap3D.tsx
  git commit -m "step 3: add WeldTrail to TorchWithHeatmap3D workpiece group"
  ```

  **✓ Automated Verification:**
  - **Action:** `cd my-app && npm test -- TorchWithHeatmap3D`
  - **Expected:** All tests pass.

  **✓ Manual Gate (Human Required):**
  1. `cd my-app && npm run dev`
  2. For `/demo` (in-browser): no backend needed. For `/compare`: start backend, run wipe then seed.
  3. Open `http://localhost:3000/demo` and `http://localhost:3000/compare/...` (if using backend seed)
  4. Press Play on each
  5. Verify:
     - [ ] Trail appears and grows as playback advances
     - [ ] Trail is NOT present at timestamp 0
     - [ ] Trail points are colored (green/orange/red visible)
     - [ ] **On /demo only:** Novice trail shows visible clustering (uneven density); expert trail shows even spacing. Density visualization requires travel_speed_mm_per_min — demo-data has it.
     - [ ] **On /compare:** Trail appears and grows. Density is uniform (timestamp-linear fallback) — backend mock_sessions.py does not include travel_speed_mm_per_min in this plan. Do NOT fail the gate for /compare density. Backend update is out of scope.
     - [ ] No console errors during playback
     - [ ] Scrubbing backwards shrinks the trail correctly
     - [ ] **warnRef reset:** On /compare, navigate between two sessions that both have null travel_speed. Console.warn must fire once per session (not silently on second load).
  6. Memory check: Run full playback once. Note total JS heap size. Run full playback a second time without reload. Heap after second must not exceed heap after first by more than 5MB.

  **Output:** `[MANUAL GATE PASSED]` before marking Step 3 done.

---

- [x] 🟩 **Step 4: Update ISSUE_WELD_TRAIL.md with spec corrections (Hygiene)**

  **Idempotent:** Yes.

  **Edits to docs/ISSUE_WELD_TRAIL.md:**
  1. Add **Arc-Active Filter** section: "Trail includes only frames where `volts > 1 && amps > 1`. Arc-off/repositioning not drawn."
  2. Replace "Guard: fallback to timestamp-linear" with: "Add travel_speed to demo before shipping; fallback only for legacy sessions. Log fallback warning once per mount."
  3. Replace "useMemo for BufferGeometry" with: "useEffect + useRef + useState(ready) for create/dispose; pre-allocate fixed 10000-point BufferAttribute; second useEffect updates via .array.set() with overflow bounds check."

  **Git Checkpoint:**
  ```bash
  git add docs/ISSUE_WELD_TRAIL.md
  git commit -m "step 4: update issue spec with arc-active, demo speed, and geometry lifecycle fixes"
  ```

  **✓ Verification Test:**
  - `grep -cE "Arc-Active Filter" docs/ISSUE_WELD_TRAIL.md` — must be >= 1
  - `grep -cE "volts > 1 && amps > 1" docs/ISSUE_WELD_TRAIL.md` — must be >= 1
  - `grep -cE "\.array\.set" docs/ISSUE_WELD_TRAIL.md` — must be >= 1

---

## Regression Guard

**Regression verification:**
- `npm test -- demo-data` — passes
- `npm test -- WeldTrail` — passes
- `npm test -- TorchWithHeatmap3D` — passes
- `npm test -- frameUtils` — passes

**Test count:** Must be ≥ pre-flight baseline.

---

## Rollback Procedure

**Functional steps (1–3):**
```bash
git revert <step3-commit>
git revert <step2-commit>
git revert <step1-commit>
cd my-app && npm test
```

**Hygiene step (4):** Optional; doc-only, no runtime impact.

---

## Success Criteria

| Feature | Target | Verification |
|---------|--------|--------------|
| useState(ready) | Re-render when geometry/material created | WeldTrail renders on screen; ThermalPlate pattern mirrored |
| Fixed 10000 pre-allocation | No frames.length in first useEffect | Code review; no overflow on compare page |
| Overflow bounds check | .array.set() guarded | Second useEffect has length check |
| Arc-active only | Trail excludes volts≤1 or amps≤1 frames; boundary volts=1/amps=1 returns false | WeldTrail.test.tsx; isArcActive boundary tests |
| Demo travel_speed | Expert 370–430, Novice min<300 max>500 | demo-data.test.ts |
| Cumulative distance | 12-frame test: highSpeedStep/lowSpeedStep in [2.5, 3.5]; two-pass normalization (Pass 1 accumulate, Pass 2 xNorm) | WeldTrail.test.tsx |
| X bounds | All x in [-plateSize/2, plateSize/2] | WeldTrail.test.tsx |
| Z drift clamped | [-0.3, 0.3] | WeldTrail.test: extreme angle 89.6° → all Z in range |
| Memory | Heap after 2× playback ≤ heap after 1× + 5MB | Manual gate |
| Named export | import { WeldTrail } from './WeldTrail' | TorchWithHeatmap3D import |
| computeTrailData | Exported; onFallbackWarning param; tests import directly | WeldTrail.test.tsx uses jest.fn() |
| drawRange(0,0) on empty | Second useEffect resets when count===0 | No stale trail after scrub to start |
| FRAME_DURATION_MIN | Import FRAME_INTERVAL_MS from validation; no hardcode | grep returns 0 matches for 10/60000 |
| positions/colors length | positions.length === count * 3, colors.length === count * 3 | WeldTrail.test.tsx |
| Color correctness | Cold (100°C) → green (G > R); hot fallback (450°C) → red (R > G) | WeldTrail.test.tsx |
| warnRef reset on session | useEffect([frames]) resets warnRef | Session-change observability |

---

⚠️ **Do not mark a step 🟩 Done until its verification test passes.**
⚠️ **Step 3 requires manual gate — output [MANUAL GATE PASSED] before marking done.**
⚠️ **Do not batch steps into one commit.**
