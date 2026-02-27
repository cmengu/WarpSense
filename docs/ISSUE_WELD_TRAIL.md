# Issue: Weld Trail — torch path + thermal history on workpiece

**Type:** Feature  
**Priority:** Normal  
**Effort:** ~90 min (highest visual impact)  
**Labels:** `frontend` `3d` `replay` `ux` `weld-trail`

---

## TL;DR

Add a Weld Trail component inside TorchWithHeatmap3D that renders a colored point cloud on the workpiece surface, showing where the torch has traveled up to `activeTimestamp`. Each point's color encodes temperature (green = cold, orange = mid, red = hot). **Position uses cumulative distance (travel_speed), not timestamp** — point density reveals slow/fast sections (novice vs expert). Trail renders for any session with 2+ frames; does NOT require thermal data.

---

## Current State vs Expected Outcome

### Current State
- TorchWithHeatmap3D shows torch + thermally-colored workpiece (ThermalPlate)
- No visualization of *where* the torch has been during the session
- Replay scrubbing shows current frame state only — no spatial history
- Variable travel speed (novice defect signal) is hidden from view

### Expected Outcome
- A trail of colored points on the workpiece surface
- **X-position maps to cumulative distance traveled** (not timestamp) — slow sections cluster points, fast sections spread them; trail itself becomes defect visualization
- Each point colored by center temperature: green <200°C, orange <400°C, red ≥400°C
- Trail grows as `activeTimestamp` advances during replay
- Points sampled every 5th frame for performance
- Trail appears even when session lacks thermal snapshots (use fallback temp for color)

---

## Position Mapping Clarification (Critical)

**Do NOT use timestamp-linear X mapping.**

The naïve spec maps `x = (timestamp_ms / total) * plateSize - half`.
This assumes constant travel speed, which is incorrect and hides defect information.

**Use cumulative distance instead:**

```typescript
// Compute cumulative distance traveled using travel_speed_mm_per_min
// travel_speed is mm/min; frame interval is 10ms = 1/6000 min
const FRAME_DURATION_MIN = 10 / 60000;

let cumulativeDistance = 0;
const pointsWithDistance = relevant.map((f) => {
  const speed = f.travel_speed_mm_per_min ?? AL_TRAVEL_SPEED_BASE_MEAN; // fallback
  cumulativeDistance += speed * FRAME_DURATION_MIN;
  return { frame: f, distance: cumulativeDistance };
});

const totalDistance = cumulativeDistance || 1; // guard division by zero

// Map distance → X on plate
const x = (point.distance / totalDistance) * plateSize - half;
```

**Why this matters:**
- Point density becomes a visual — slow sections cluster, fast sections spread
- Novice trail will show uneven density; expert trail will be evenly spaced
- `travel_speed_mm_per_min` is optional — fallback to 400 (`AL_TRAVEL_SPEED_BASE_MEAN`) when null so trail still renders for sessions without speed data

**Arc-Active Filter:** Trail includes only frames where `volts > 1 && amps > 1`. Arc-off/repositioning not drawn.

**Guard:** Add travel_speed to demo before shipping; fallback only for legacy sessions. Log fallback warning once per mount.

---

## Trail Render Condition

**Render trail when `frames.length >= 2` AND `activeTimestamp > firstTimestamp`.**

Do NOT gate on `hasThermal` — trail is about torch path, not thermal data.

- Use thermal color if available; fallback 450°C (red) if not.
- This means trail appears even on sessions without thermal snapshots.
- Trail and ThermalPlate are independent: ThermalPlate only shows when `hasThermal`; WeldTrail shows whenever there is a meaningful path to draw.

---

## Files to Create/Edit

| File | Change |
|------|--------|
| `my-app/src/components/welding/WeldTrail.tsx` | **Create** — new R3F component |
| `my-app/src/components/welding/TorchWithHeatmap3D.tsx` | Add `<WeldTrail>` to workpiece group in SceneContent |
| `my-app/src/types/frame.ts` | Add `travel_speed_mm_per_min?: number | null` (optional, mirrors backend) |
| `my-app/src/constants/thermal.ts` (or new `constants/aluminum.ts`) | Add `AL_TRAVEL_SPEED_BASE_MEAN = 400` |

---

## Implementation Details

### 1. Create `WeldTrail.tsx`

- **Props:** `frames`, `activeTimestamp`, `plateSize` (same as SceneContent already has)
- **Position mapping:** Use cumulative distance (see Position Mapping Clarification above)
- **Y:** `0.02` (relative to workpiece group — sits just above metal surface per `welding3d.ts`)
- **Z:** slight drift from `angle_degrees` (e.g. `* 0.005`) for depth variation
- **Color:** Use `extractCenterTemperature(frame)` from `frameUtils.ts` when available; fallback 450°C when null
- **tempToTrailColor:** green (0x22c55e), orange (0xf97316), red (0xef4444) at 200/400°C thresholds — aligns with ISSUE_THERMAL_GRADIENT_GREEN_ORANGE_RED when that ships
- **Sampling:** every 5th frame in `relevant` to limit point count
- **Geometry:** useEffect + useRef + useState(ready) for create/dispose; pre-allocate fixed 10000-point BufferAttribute; second useEffect updates via .array.set() with overflow bounds check
- **Material:** `pointsMaterial` with `size={0.04}`, `vertexColors`, `transparent`, `opacity={0.85}`, `sizeAttenuation`
- **Early return:** `null` when `positions.length === 0` (fewer than 2 relevant frames or no points after sampling)
- **Guard:** If all frames have null `travel_speed_mm_per_min`, use timestamp-linear mapping and log warning

### 2. Integrate into TorchWithHeatmap3D

In `SceneContent`, add `<WeldTrail>` inside the workpiece group, alongside `ThermalPlate`:

```tsx
{/* Workpiece — thermal or flat */}
<group position={[0, WORKPIECE_GROUP_Y, 0]}>
  {frames.length >= 2 && activeTimestamp > (frames[0]?.timestamp_ms ?? 0) && (
    <WeldTrail
      frames={frames}
      activeTimestamp={activeTimestamp}
      plateSize={plateSize ?? 3}
    />
  )}
  {hasThermal ? (
    <ThermalPlate ... />
  ) : (
    <mesh ... />
  )}
</group>
```

Note: WeldTrail render condition is independent of `hasThermal`.

### 3. Frame type and constants

- Add `travel_speed_mm_per_min?: number | null` to `Frame` interface (backend sends it; frontend may not have declared it)
- Add `AL_TRAVEL_SPEED_BASE_MEAN = 400` constant (matches `backend/data/mock_sessions.py`)

---

## Edge Cases

- **Empty frames:** Early return, no crash
- **Single frame:** `relevant.length < 2` → return null
- **No thermal in frame:** Use `extractCenterTemperature` → null → fallback 450°C (red)
- **totalDistance = 0:** Guard with `|| 1` to avoid division by zero
- **All frames null travel_speed:** Fall back to timestamp-linear; log warning
- **Frames without thermal_snapshots:** Trail still renders; color = fallback 450°C

---

## Risk / Notes

- **WebGL:** No new Canvas — WeldTrail is another Three.js object in existing TorchWithHeatmap3D scene. Stays within `MAX_TORCHVIZ3D_PER_PAGE`.
- **Performance:** Sampling every 5th frame; ~200 points for 1000-frame session. Acceptable for 90 min effort; can tune sampling rate later.
- **Y alignment:** Trail y=0.02 is relative to workpiece group at `WORKPIECE_GROUP_Y` (-0.85). Points float just above metal — correct.
- **Color consistency:** When ISSUE_THERMAL_GRADIENT_GREEN_ORANGE_RED ships, `getWeldPoolColor` and thermal plate will use green→orange→red. `tempToTrailColor` already matches; consider extracting shared util later.
- **Demo data:** `demo-data.ts` does not currently include `travel_speed_mm_per_min`. Demo sessions will use fallback 400 (evenly spaced trail). To showcase defect visualization, mock sessions with variable speed would need to be added later.

---

## Vision Alignment

From `vision.md`:

- *"The story told visually — expert vs novice comparison that makes the value self-evident"* — Weld trail with density mapping makes torch path and travel-speed variation legible at a glance; novice uneven density vs expert even spacing tells the story without charts.
- *"Technical credibility — system handles 3000-frame sessions without lag"* — Sampled point cloud keeps render cost bounded; aligns with exact-replay contract (no guessing).
- *"Alerts that catch real technique deviations before they become defects"* — Variable travel speed is a defect signal; the trail visualizes it directly.

---

## Acceptance Criteria

- [ ] `WeldTrail.tsx` created with props `frames`, `activeTimestamp`, `plateSize`
- [ ] **Position uses cumulative distance** (travel_speed_mm_per_min) when available; fallback to 400 when null
- [ ] **Guard:** All frames null travel_speed → timestamp-linear mapping + warning
- [ ] Trail renders when `frames.length >= 2` and `activeTimestamp > firstTimestamp` — NOT gated on hasThermal
- [ ] Points use `extractCenterTemperature` or fallback 450°C; color via tempToTrailColor (green/orange/red)
- [ ] Trail integrated into TorchWithHeatmap3D workpiece group
- [ ] Visual check on `/replay/[sessionId]` and `/demo` — trail appears and grows as timeline scrubs
- [ ] `Frame` type includes `travel_speed_mm_per_min`; `AL_TRAVEL_SPEED_BASE_MEAN` constant added
- [ ] `TorchWithHeatmap3D.test.tsx` still passes
- [ ] No new WebGL Canvas; stays within 2×TorchWithHeatmap3D limit
