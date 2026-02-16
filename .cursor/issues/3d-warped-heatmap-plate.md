# [Feature] 3D Warped Heatmap Plate — Replace CSS Grid with Physics-Based Metal Plate Visualization

---

## Phase 0: Mandatory Pre-Issue Thinking Session

### A. Brain Dump (5+ minutes)

**Raw thinking — stream of consciousness:**

The current heatmap is a CSS grid showing time × distance → temperature. It's functional but looks like a basic chart. Industrial welding software that costs tens of thousands per year typically has richer visualizations. We have 5-point thermal data (center, north, south, east, west) per snapshot that we're only using one direction of (center) for the heatmap. We're throwing away spatial information. Metal actually warps when heated — thermal expansion is real physics. If we showed that, we'd be representing something physically accurate. The proposal is a 3D plane with vertex displacement based on temperature — higher temp = more Z displacement (metal bulges when hot). This would use all 5 readings, interpolate to a dense grid, and render with shaders.

What could go wrong? WebGL context limits. We already have TorchViz3D (1-2 per page). If we add HeatmapPlate3D everywhere we have HeatMap, we'd have replay: 2 Canvases (TorchViz3D + HeatmapPlate3D), demo: 4 Canvases (2 TorchViz3D + 2 HeatmapPlate3D), compare: 3 Canvases (3 HeatmapPlate3D). Demo would exceed the 2-Canvas limit. We need a strategy: maybe HeatmapPlate3D only on replay initially, or a toggle to switch between CSS heatmap and 3D plate, or shared Canvas.

Interpolation: 5 points to 100×100 grid. The task suggests inverse distance weighting. Center at (0.5, 0.5), north at (0.5, 0), south at (0.5, 1), east at (1, 0.5), west at (0, 0.5). That's a sparse grid. Bilinear or IDW would spread the values. Need to validate the interpolation doesn't create artifacts.

Which snapshot do we use? Frames have multiple thermal_snapshots at different distances (10, 20, 30, 40, 50mm). The 3D plate represents the weld pool region — probably the closest distance (10mm) or we could let the user pick. The plate is a 2D spatial view at one moment, one distance.

Torch position: the task says show a cone above the hottest point. We have angle_degrees — that gives torch orientation. Hottest point is likely center. Need to position the cone correctly.

Performance: 100×100 plane geometry = 10k vertices. Reasonable for WebGL. Texture upload each frame for thermal data — could be expensive if we're at 5Hz thermal, so only 5 texture updates per second. Acceptable.

Who is affected? Replay users primarily. Demo users see side-by-side expert/novice — would they get 3D plates? That's the Canvas count problem. Compare page has 3 heatmaps (A, Delta, B). Delta heatmap is a different data shape (FrameDelta, not Frame) — 3D warped delta might be harder to interpret. Maybe Phase 1: replay only. Phase 2: demo with toggle or single 3D view. Phase 3: compare if we solve Canvas count.

What don't we know? Exact interpolation algorithm validation. Whether 100×100 is the right resolution. Whether the plate should animate smoothly between thermal frames (we have sparse 5Hz thermal) — probably use extractCenterTemperatureWithCarryForward pattern or interpolate between snapshots. Color gradient: fragment shader uses blue→yellow→orange→white; current HeatMap uses 13-step 50°C anchors. Should we align for consistency?

Urgency: This is a differentiator. "Industrial software look" matters for enterprise sales. Not blocking any other feature. Medium priority.

---

### B. Question Storm (20+ questions)

1. What triggers the 3D plate to render? Same as HeatMap — when thermal_frames exist.
2. When does vertex displacement update? On active frame change; thermal at 5Hz.
3. Who experiences this? Replay users, potentially demo/compare.
4. How often does thermal data arrive? Every 100ms (5Hz).
5. What's the impact if we don't build it? Miss differentiator; heatmap stays "basic chart" look.
6. What's the impact if we do? Professional visualization; potential WebGL context overflow on demo.
7. What are we assuming about user behavior? Users want richer visuals; 3D adds value.
8. What are we assuming about the system? 5-point thermal always present when has_thermal_data; distance_mm in snapshots.
9. What similar issues have we had? TorchViz3D — 6 instances caused context loss; we limited to 2.
10. What did we learn from those? Canvas count matters; add context-loss handlers.
11. Which thermal snapshot (distance) do we use? First? Closest to weld? Configurable?
12. Does extractHeatmapData need to change? No — 3D plate consumes raw Frame[], not HeatmapData.
13. Can we share a Canvas with TorchViz3D? Technically yes with scissor; adds complexity.
14. What about delta heatmap on compare page? Different data (FrameDelta); 3D delta plate is unclear UX.
15. How do we handle frames with no thermal? Show cold plate (20°C default) or last-known?
16. Does the torch cone need to move with playback? Yes — angle_degrees per frame.
17. What's the performance budget? 60fps; 10k vertices + texture update at 5Hz should be fine.
18. Mobile support? WebGL works on mobile; 100×100 may need to reduce on low-end.
19. Accessibility? 3D is inherently less accessible; need fallback (keep HeatMap as option?).
20. Should temperature gradient match HeatMap's 13-step? Consistency suggests yes; shader can mirror.
21. What about sessions with only center direction? Unusual; guard for missing north/south/east/west.
22. How do we test this? Unit test interpolation; integration test render; manual visual check.
23. Can HeatmapPlate3D coexist with HeatMap? Yes — different components; page chooses which to show.
24. ESLint max-torchviz rule — does it apply? Rule counts TorchViz3D; HeatmapPlate3D is different. We need to extend or create new limit for total Canvas count.
25. What if thermal_snapshots has multiple distances? Pick one (e.g. first/closest); document choice.

---

### C. Five Whys Analysis

**Problem:** Current heatmap is a flat CSS grid that doesn't convey the physical reality of thermal expansion or spatial temperature distribution.

**Why #1:** Why is this a problem?
- **Answer:** Users see a 2D chart, not a representation of how metal actually behaves when heated. It looks generic.

**Why #2:** Why is that a problem?
- **Answer:** Industrial buyers expect software that "shows what's really happening" — thermal expansion is real physics; our visualization ignores it. Competitors with richer visuals may win deals.

**Why #3:** Why is that a problem?
- **Answer:** Our product positioning is "safety-adjacent, industrial" — correctness and explainability matter. A visualization that implies physics (warped metal) aligns with that; a flat grid doesn't.

**Why #4:** Why is that a problem?
- **Answer:** We're underutilizing our data. We have 5-point spatial thermal (center + 4 cardinal) but only display center in a time×distance grid. We're discarding information.

**Why #5:** Why is that the real problem?
- **Answer:** We lack a visual differentiator that (a) uses our full thermal data, (b) represents real physics, and (c) elevates perceived product quality to "industrial-grade" rather than "dashboard chart." The root cause is a gap between our data capabilities and our visualization fidelity.

**Root cause identified:** Visualization layer has not evolved to leverage 5-point spatial thermal data or to represent thermal expansion physics, resulting in a generic chart appearance that underperforms for industrial positioning.

---

## 1. Title

**Format:** `[Feature] 3D Warped Heatmap Plate — Replace CSS Grid with Physics-Based Metal Plate Visualization`

**Title Quality Checklist:**
- [x] Starts with type tag
- [x] Specific (describes replacement and physics-based approach)
- [x] Under 100 characters
- [x] No jargon (understandable to stakeholders)
- [x] Action-oriented (replace, visualize)

---

## 2. TL;DR

**Executive Summary (5–7 sentences):**

The current thermal heatmap is a flat CSS grid showing time × distance → temperature, using only the center reading from our 5-point thermal data. This looks like a basic chart and underutilizes the spatial temperature information we collect (center, north, south, east, west). Industrial welding buyers expect visualizations that reflect real physics — metal thermally expands and warps when heated, which our current display ignores. We should replace (or offer as alternative) the CSS heatmap with a 3D metal plate visualization that uses vertex displacement based on temperature (higher temp = more bulge) and a temperature→color gradient, with the torch position shown as a cone above the hottest point. This advances our product vision by making the replay experience look and feel like $50K/year industrial software, using data we already have and infrastructure (Three.js, R3F) we already use. Effort level: medium (approximately 8–16 hours for core implementation), with additional consideration for WebGL context limits on pages that already render multiple 3D views (demo, compare).

---

## 3. Current State (What Exists Today)

### A. What's Already Built

**UI Components:**

1. **HeatMap** — `my-app/src/components/welding/HeatMap.tsx`
   - **What it does:** Renders thermal distribution as CSS grid (columns = timestamps, rows = distances). Single cell per (timestamp, distance) with color from `tempToColor` or custom `colorFn`. Highlights active column at `activeTimestamp` (±50ms).
   - **Current capabilities:** Unlimited points; supports delta heatmap (`deltaTempToColor`); `sessionId`, `label`, `valueLabel` props; `role="img"` with `aria-label` for accessibility.
   - **Limitations:** Uses only one thermal direction (default "center"); no 3D; no thermal expansion; no torch indication; flat 2D chart appearance.
   - **Dependencies:** `HeatmapData` from `extractHeatmapData`; `tempToColor` from `heatmapData.ts`.
   - **Props:** `sessionId`, `data?: HeatmapData | null`, `activeTimestamp?`, `colorFn?`, `label?`, `valueLabel?`.

2. **TorchViz3D** — `my-app/src/components/welding/TorchViz3D.tsx`
   - **What it does:** 3D torch + weld pool with angle and temperature-driven color. Uses R3F/Three.js; dynamic import with `ssr: false`; WebGL context-loss handler; OrbitControls.
   - **Current capabilities:** PBR materials, HDRI, shadows; `angle` (degrees), `temp` (°C), `label` props.
   - **Limitations:** Does not visualize thermal distribution on the plate; only weld pool sphere color.
   - **Pattern:** Must use dynamic import; 1–2 instances max per page (`MAX_TORCHVIZ3D_PER_PAGE`).

3. **TorchAngleGraph** — `my-app/src/components/welding/TorchAngleGraph.tsx`
   - Recharts line chart; not directly relevant to heatmap replacement.

**API Endpoints:** None new. Heatmap data comes from `GET /api/sessions/:id?include_thermal=true`; `Frame[]` includes `thermal_snapshots`.

**Data Models:**

1. **Frame** — `my-app/src/types/frame.ts`
```typescript
interface Frame {
  timestamp_ms: number;
  volts: number | null;
  amps: number | null;
  angle_degrees: number | null;
  thermal_snapshots: ThermalSnapshot[];
  has_thermal_data: boolean;
  // ...
}
```

2. **ThermalSnapshot** — `my-app/src/types/thermal.ts`
```typescript
interface ThermalSnapshot {
  distance_mm: number;
  readings: TemperaturePoint[];  // 5: center, north, south, east, west
}
interface TemperaturePoint {
  direction: ThermalDirection;  // "center"|"north"|"south"|"east"|"west"
  temp_celsius: number;
}
```

3. **HeatmapData** — `my-app/src/utils/heatmapData.ts`
```typescript
interface HeatmapData {
  points: HeatmapDataPoint[];  // { timestamp_ms, distance_mm, temp_celsius, direction }
  timestamps_ms: number[];
  distances_mm: number[];
  point_count: number;
}
```

**Utilities:**

1. **extractHeatmapData** — `my-app/src/utils/heatmapData.ts`
   - **Signature:** `(frames: Frame[], direction?: ThermalDirection) => HeatmapData`
   - **What it does:** Flattens thermal frames to (timestamp, distance, temp) per direction. Default direction "center". Used by HeatMap.
   - **Relevant for this issue:** 3D plate needs raw `Frame[]` with full 5-point data; does not use HeatmapData directly.

2. **extractCenterTemperatureWithCarryForward** — `my-app/src/utils/frameUtils.ts`
   - Carries forward last known center temp for sparse thermal; used for TorchViz3D color continuity. May inform 3D plate behavior when thermal_snapshots missing.

### B. Current User Flows

**Flow 1: Replay Page**
```
User loads /replay/[sessionId]
  → Session fetched; thermal_frames extracted
  → extractHeatmapData(thermal_frames) → HeatmapData
  → HeatMap(data, activeTimestamp) renders CSS grid
  → TorchViz3D(angle, temp) renders 3D torch
  → User scrubs timeline; active column highlights; torch updates
Current limitation: Heatmap is flat; no spatial thermal or thermal expansion.
```

**Flow 2: Demo Page**
```
User loads /demo
  → generateExpertSession() + generateNoviceSession() in-memory
  → extractHeatmapData for each
  → 2× HeatMap + 2× TorchViz3D (dynamic)
  → Playback 0–15s
Current limitation: 2 TorchViz3D already at limit; adding 2 HeatmapPlate3D = 4 Canvases (exceeds limit).
```

**Flow 3: Compare Page**
```
User loads /compare/[sessionIdA]/[sessionIdB]
  → Both sessions fetched; useSessionComparison
  → extractHeatmapData(A), extractHeatmapData(B), extractDeltaHeatmapData(deltas)
  → 3× HeatMap (A, Delta, B)
  → No TorchViz3D on compare
Current limitation: 3 HeatMaps; replacing all with 3D = 3 Canvases (within 8–16 limit but increases risk).
```

### C. Broken/Incomplete User Flows

1. **Flow:** User wants to see spatial temperature distribution (north/south/east/west) at a moment in time.
   - **Current behavior:** HeatMap shows only center temp per (time, distance); no 2D spatial field.
   - **Why it fails:** extractHeatmapData uses single direction; UI has no component for 5-point spatial view.
   - **User workaround:** None.
   - **Frequency:** Every replay/demo session.
   - **Impact:** Lost information; generic appearance.

2. **Flow:** User wants to see thermal expansion (metal warping) represented.
   - **Current behavior:** Flat grid; no displacement.
   - **Why it fails:** No 3D plate component.
   - **User workaround:** None.
   - **Impact:** Missed industrial-grade visualization.

3. **Flow:** User wants torch position overlaid on thermal view.
   - **Current behavior:** TorchViz3D is separate; HeatMap has no torch indicator.
   - **Why it fails:** Components are decoupled.
   - **User workaround:** Mentally correlate two panels.
   - **Impact:** Cognitive load.

### D. Technical Gaps Inventory

**Frontend gaps:**
- No `HeatmapPlate3D` component
- No thermal interpolation utility (5-point → N×N grid)
- No vertex/fragment shaders for heatmap plate
- Missing `thermalInterpolation.ts` (or equivalent)

**Integration gaps:**
- HeatmapPlate3D would consume `Frame[]` directly (different from HeatmapData)
- Need strategy for pages with multiple HeatMaps (Canvas count)

**Data gaps:**
- No utility to extract 5-point readings at a chosen distance from Frame
- No texture/DataTexture creation from interpolated grid for shader

### E. Current State Evidence

- **HeatMap:** 126 lines; CSS grid with `gridTemplateColumns`/`gridTemplateRows`; `tempToColor` for 13-step gradient (20–600°C).
- **extractHeatmapData:** Filters by `hasThermalData`; iterates `thermal_snapshots`; takes single direction.
- **Demo data:** `generateThermalSnapshot` produces 5 readings (center, north, south, east, west) at each distance.
- **Thermal directions:** `THERMAL_DIRECTIONS`, `READINGS_PER_SNAPSHOT = 5` in `types/thermal.ts`.
- **WebGL:** `MAX_TORCHVIZ3D_PER_PAGE = 2`; ESLint rule enforces; `documentation/WEBGL_CONTEXT_LOSS.md` documents limits.

---

## 4. Desired Outcome (What Should Happen)

### A. User-Facing Changes

**Primary User Flow:**
```
User loads replay/demo (or toggle when implemented)
  → HeatmapPlate3D renders 3D metal plate
  → Plate warps (Z displacement) based on temperature at each vertex
  → Color gradient: cold (blue) → hot (white)
  → Torch cone hovers above plate at angle from frame
  → User scrubs timeline; plate and torch update with active frame
  → OrbitControls allow rotation/zoom
Success state: User sees physics-informed 3D thermal visualization.
```

**UI Changes:**
1. **New element:** HeatmapPlate3D container (600px height, dark background, cyan border)
   - **Location:** Same slot as HeatMap on replay (and optionally demo/compare)
   - **Appearance:** 3D scene with plate + torch cone + grid helper
   - **Behavior:** Updates on `activeTimestamp`; OrbitControls
   - **States:** loading (dynamic), default, error (fallback to HeatMap or message)

2. **Modified element:** Replay/demo layout
   - **Current:** HeatMap in thermal section
   - **New:** HeatmapPlate3D (or configurable: HeatMap vs HeatmapPlate3D)
   - **Rationale:** Replace or offer alternative

**UX Changes:**
- **Interaction:** User can orbit/zoom 3D plate (OrbitControls)
- **Before:** Static 2D grid, no spatial exploration
- **After:** 3D exploration, physics-informed warping
- **Why:** Industrial feel; information density

### B. Technical Changes

**New files to create:**
1. `my-app/src/utils/thermalInterpolation.ts`
   - **Type:** Utility
   - **Purpose:** Interpolate 5-point thermal (center, N, S, E, W) to N×N grid
   - **Key responsibilities:** `interpolateThermalGrid(center, north, south, east, west, gridSize)` → `number[][]`
   - **Dependencies:** None
   - **Exported:** `interpolateThermalGrid`

2. `my-app/src/components/welding/shaders/heatmapVertex.glsl`
   - **Type:** GLSL vertex shader
   - **Purpose:** Sample temperature texture; displace vertices along normal

3. `my-app/src/components/welding/shaders/heatmapFragment.glsl`
   - **Type:** GLSL fragment shader
   - **Purpose:** Map temperature to color (blue→yellow→orange→white)

4. `my-app/src/components/welding/HeatmapPlate3D.tsx`
   - **Type:** Component
   - **Purpose:** 3D plate + torch indicator; consumes `Frame[]`, `activeTimestamp`
   - **Dependencies:** R3F, Three.js, thermalInterpolation, shaders
   - **Exported:** default

**Existing files to modify:**
1. `my-app/src/app/replay/[sessionId]/page.tsx`
   - **Current state:** Renders HeatMap with heatmapData
   - **Changes needed:** Add HeatmapPlate3D (replace or toggle); dynamic import with `ssr: false`; ensure Canvas count ≤2 (TorchViz3D + HeatmapPlate3D = 2)
   - **Risk:** Low
   - **Lines affected:** Import block, JSX heatmap section

2. `my-app/src/app/demo/page.tsx` (optional Phase 2)
   - **Current state:** 2 HeatMap + 2 TorchViz3D
   - **Changes needed:** If adding HeatmapPlate3D, must reduce Canvas count (e.g. single shared Canvas, or HeatMap fallback for one column)
   - **Risk:** Medium (context limit)

3. `my-app/src/constants/webgl.ts` (if extending limits)
   - **Current state:** `MAX_TORCHVIZ3D_PER_PAGE = 2`
   - **Changes needed:** Possibly `MAX_CANVAS_PER_PAGE` to include HeatmapPlate3D; update ESLint rule
   - **Risk:** Low

**Data model changes:** None. Uses existing `Frame`, `ThermalSnapshot`, `TemperaturePoint`.

### C. Success Criteria (12+ Acceptance Criteria)

**User can criteria:**
1. **[ ]** User can see a 3D metal plate that warps (vertex displacement) based on temperature
   - **Verification:** Visual inspection; hot regions bulge upward
   - **Expected behavior:** Z displacement proportional to temp; cold regions flat

2. **[ ]** User can see temperature as color gradient (blue→white) on the plate
   - **Verification:** Visual; color matches temp
   - **Expected behavior:** Cold=blue, hot=white; gradient smooth

3. **[ ]** User can see torch cone above the plate at correct angle
   - **Verification:** Cone rotation matches `angle_degrees`; position above plate
   - **Expected behavior:** Cone follows frame angle; visible from orbit

4. **[ ]** User can orbit and zoom the 3D view (OrbitControls)
   - **Verification:** Mouse drag rotates; scroll zooms
   - **Expected behavior:** No pan (or limited); min/max distance enforced

5. **[ ]** User can scrub timeline and see plate/torch update with active frame
   - **Verification:** Playback; manual scrub
   - **Expected behavior:** Plate texture and torch update when `activeTimestamp` changes

6. **[ ]** User sees loading fallback while HeatmapPlate3D loads (dynamic import)
   - **Verification:** Network throttling or slow load
   - **Expected behavior:** "Loading 3D heatmap…" or similar

**System does criteria:**
7. **[ ]** System interpolates 5-point thermal data to 100×100 grid
   - **Verification:** Unit test `interpolateThermalGrid`
   - **Expected behavior:** Center at (0.5,0.5), N/S/E/W at edges; smooth interpolation

8. **[ ]** System uses `has_thermal_data` guard before accessing thermal_snapshots
   - **Verification:** Code review; test with frames lacking thermal
   - **Expected behavior:** No crash; show cold default plate

9. **[ ]** System picks thermal snapshot at configurable distance (default: first/closest)
   - **Verification:** Multi-distance session
   - **Expected behavior:** Single snapshot used per frame; documented

10. **[ ]** System uses dynamic import with `ssr: false` for HeatmapPlate3D
    - **Verification:** No SSR error
    - **Expected behavior:** Client-only render

11. **[ ]** System respects WebGL context limit (≤2 Canvas on replay if TorchViz3D + HeatmapPlate3D)
    - **Verification:** Replay page Canvas count; ESLint if rule updated
    - **Expected behavior:** No context loss under normal use

12. **[ ]** System shows context-loss overlay if WebGL context lost (per WEBGL_CONTEXT_LOSS.md)
    - **Verification:** Trigger context loss; overlay visible
    - **Expected behavior:** "Refresh to restore" message; button works

**Quality criteria:**
- **[ ]** Performance: 60fps on mid-range device; 100×100 geometry
- **[ ]** Accessibility: `role="img"` or `aria-label` for 3D view; keyboard if possible
- **[ ]** Browser: Chrome 90+, Firefox 88+, Safari 14+
- **[ ]** Error handling: Fallback to HeatMap or message on failure
- **[ ]** Security: No user input in shaders; temp values from trusted API

### D. Detailed Verification (Top 5 Criteria)

**Criterion 1: 3D plate warps based on temperature**
- Plate uses PlaneGeometry with 100×100 segments
- Vertex shader samples `uTemperatureMap` at `uv`
- `displacement = (temp / uMaxTemp) * uMaxDisplacement`
- `newPosition = position + normal * displacement`
- Hot regions (high temp) → larger displacement → bulge
- Cold regions (20°C) → near-zero displacement → flat
- Edge case: All same temp → uniform flat or uniform bulge

**Criterion 2: Temperature color gradient**
- Fragment shader `temperatureToColor(t)` maps 0–1 to blue→cyan→yellow→orange→white
- Anchors: t<0.2 blue→cyan; 0.2–0.5 cyan→yellow; 0.5–0.8 yellow→orange; 0.8–1 orange→white
- `uMaxTemp` uniform scales raw temp to 0–1
- Align with HeatMap 20–600°C range for consistency

**Criterion 3: Torch cone above plate**
- Cone at `position={[0, 2, 0]}` (above plate center)
- `rotation.x = (angle_degrees - 45) * PI/180` (45° = neutral)
- Cone geometry: radius 0.2, height 1, segments 8
- Material: emissive cyan; visible in dark scene

**Criterion 4: OrbitControls**
- `enablePan={false}` per task
- `minDistance={5}`, `maxDistance={20}`
- `maxPolarAngle={PI/2 - 0.1}` (prevent flipping below)
- No enableRotate=false

**Criterion 5: Active frame updates**
- `activeFrame = frames.find(f => f.timestamp_ms === activeTimestamp) || frames[0]`
- Thermal data extracted from `activeFrame.thermal_snapshots[0]` (or chosen distance)
- Texture updated via `temperatureTexture.needsUpdate = true` when thermalData changes
- Torch angle from `activeFrame.angle_degrees`

---

## 5. Scope Boundaries

### In Scope
1. **[ ]** HeatmapPlate3D component with vertex/fragment shaders (8h)
   - **Why:** Core feature
   - **User value:** Physics-based 3D thermal view
   - **Effort:** 8h

2. **[ ]** Thermal interpolation utility (5-point → 100×100 grid) (2h)
   - **Why:** Required for shader input
   - **User value:** Enables smooth displacement
   - **Effort:** 2h

3. **[ ]** Integration on replay page only (Phase 1) (1h)
   - **Why:** Replay has 1 TorchViz3D; adding 1 HeatmapPlate3D = 2 Canvases (safe)
   - **User value:** Replay gets new visualization
   - **Effort:** 1h

4. **[ ]** Torch cone indicator above plate (1h)
   - **Why:** Task specifies it; improves spatial understanding
   - **User value:** See torch position relative to heat
   - **Effort:** 1h

5. **[ ]** Dynamic import, loading fallback, context-loss handler (1h)
   - **Why:** Per WEBGL_CONTEXT_LOSS.md; consistent with TorchViz3D
   - **User value:** No white screen; clear feedback
   - **Effort:** 1h

**Total in-scope: ~13 hours**

### Out of Scope
1. **[ ]** Demo page 3D plates (2× HeatmapPlate3D would add 2 Canvases; total 4)
   - **Why:** Exceeds MAX_TORCHVIZ3D_PER_PAGE guidance; needs shared Canvas or fallback
   - **When:** Phase 2 after solving Canvas consolidation
   - **Workaround:** Keep HeatMap on demo for Phase 1

2. **[ ]** Compare page 3D plates (3 HeatmapPlate3D)
   - **Why:** Delta heatmap has different data shape; 3 Canvases increases risk; lower ROI
   - **When:** Phase 3 if replay/demo success
   - **Workaround:** Compare keeps CSS HeatMap

3. **[ ]** Distance-based displacement scaling (snapshot.distance_mm)
   - **Why:** Task lists as "Advanced"; not core
   - **When:** Optional enhancement
   - **Workaround:** Fixed displacement scale

4. **[ ]** Ripple effect (radial waves)
   - **Why:** Task lists as optional
   - **When:** Polish phase
   - **Workaround:** Static displacement

5. **[ ]** Heat trail (historical path)
   - **Why:** Task lists as optional; complex state
   - **When:** Future iteration
   - **Workaround:** Current frame only

6. **[ ]** Comparison mode (2 plates side-by-side in one view)
   - **Why:** Out of scope for Phase 1
   - **When:** Phase 2+
   - **Workaround:** Use existing compare page layout

### Scope Justification
- **Optimizing for:** Speed to market, replay experience, WebGL safety
- **Deferring:** Demo/compare 3D, advanced effects
- **Deferred:** Demo 3D plates → Phase 2 (shared Canvas or toggle)

### Scope Examples
1. **In scope:** Replay page uses HeatmapPlate3D. **Out of scope:** Demo page uses HeatmapPlate3D. **Why:** Canvas count.
2. **In scope:** 5-point interpolation for single snapshot. **Out of scope:** Multi-distance layered plate. **Why:** Single distance sufficient for MVP.
3. **In scope:** Torch cone at frame angle. **Out of scope:** Torch cone at "hottest point" (would need centroid of temp field). **Why:** Angle is available; centroid adds complexity.

---

## 6. Known Constraints & Context

### Technical Constraints

**Must use:**
1. **Three.js + @react-three/fiber** — 3D rendering
   - **Why:** Already in stack (TorchViz3D)
   - **Version:** As in package.json
   - **Documentation:** threejs.org, docs.pmnd.rs/react-three-fiber

2. **GLSL shaders** — Vertex and fragment for plate
   - **Why:** Custom displacement and color
   - **Pattern:** Raw shader strings or glsl-loader

3. **snake_case** — Data fields from API
   - **Why:** Project rule; no conversion layer

**Must work with:**
- **Frame type** — `thermal_snapshots`, `has_thermal_data`, `angle_degrees`
- **ThermalSnapshot** — `distance_mm`, `readings` (5 directions)

**Cannot change:**
- **Backend Frame structure** — No API changes
- **extractHeatmapData contract** — HeatMap and compare still use it

**Must support:**
- **Browsers:** Chrome 90+, Firefox 88+, Safari 14+
- **WebGL 2** (or WebGL 1 fallback)
- **Node:** Per Next.js 16

**Performance constraints:**
- 100×100 plane = 10k vertices — acceptable
- Texture update at 5Hz thermal — low
- 60fps target

### Business Constraints

**Timeline:** No hard deadline; medium priority.
**Resources:** Single developer assumed.
**Dependencies:** None blocking.

### Design Constraints

**Must match:**
- Temperature scale 20–600°C (align with HeatMap anchors conceptually)
- Cyan/industrial theme (TorchViz3D, existing palette)
- Dark background (#0a0a0a) for 3D scenes

**Must follow:**
- `documentation/WEBGL_CONTEXT_LOSS.md` — context-loss handlers, loading fallback
- `constants/webgl.ts` — Canvas count guidance
- `.cursorrules` — Data integrity; never silently fail

### Organizational Constraints

**Approval:** None specified.
**Documentation:** Update CONTEXT.md with HeatmapPlate3D when implemented.

---

## 7. Related Context

### Similar Features in Codebase

**Feature 1: TorchViz3D**
- **Location:** `my-app/src/components/welding/TorchViz3D.tsx`
- **What it does:** 3D torch + weld pool; angle and temp drive rotation and color
- **Similar because:** R3F, Three.js, WebGL, dynamic import
- **Patterns to reuse:** Dynamic import with loading; `onCreated` for context-loss; OrbitControls; `getWeldPoolColor`-style temperature→color
- **Mistakes to avoid:** Multiple instances without Canvas limit; no context-loss overlay
- **Code:** Same dynamic import pattern; same ErrorBoundary usage

**Feature 2: HeatMap**
- **Location:** `my-app/src/components/welding/HeatMap.tsx`
- **What it does:** CSS grid thermal visualization
- **Similar because:** Thermal data consumption; activeTimestamp highlight
- **Patterns to reuse:** `activeTimestamp` prop; empty state ("No thermal data"); sessionId/label
- **Mistakes to avoid:** Assuming HeatmapData shape for 3D plate (we need raw Frame)

**Feature 3: extractHeatmapData**
- **Location:** `my-app/src/utils/heatmapData.ts`
- **What it does:** Frame[] → HeatmapData (time×distance→temp, single direction)
- **Similar because:** Thermal extraction
- **Patterns to reuse:** `hasThermalData` guard; iterate thermal_snapshots
- **Difference:** We need 5-point extraction at one distance; new utility or inline

### Related Issues
- **webgl-context-lost-consistent-project-wide.md** — Context-loss handlers; Canvas limits
- **browser-only-demo-mode.md** — Demo uses HeatMap, TorchViz3D; same component contracts

### Past Attempts
None documented for 3D heatmap specifically.

### External References
- **R3F Context Lost #2109** — Context loss handling
- **Three.js PlaneGeometry** — Vertex displacement patterns
- **IDW (Inverse Distance Weighting)** — Interpolation for 5-point→grid

### Dependency Tree
```
3D Warped Heatmap Plate
  ↑ Depends on: Frame type, ThermalSnapshot, R3F, Three.js (all exist)
  ↓ Blocks: Demo 3D plates (Phase 2), Compare 3D (Phase 3)
  Related: TorchViz3D (shares WebGL budget), HeatMap (replacement target)
```

---

## 8. Open Questions & Ambiguities

**Question #1:** Which thermal snapshot (distance_mm) should we use when frame has multiple snapshots?
- **Why unclear:** Demo has 10,20,30,40,50mm; backend may vary
- **Impact if wrong:** Wrong region of weld represented
- **Who can answer:** Product/domain
- **When needed:** Before implementation
- **Current assumption:** First snapshot (closest distance)
- **Confidence:** Medium
- **Risk if wrong:** Low (still valid for one distance)

**Question #2:** Should HeatmapPlate3D replace HeatMap entirely on replay, or be a toggle?
- **Why unclear:** User preference; accessibility (3D less accessible)
- **Impact if wrong:** Replace→some users lose 2D; Toggle→more code
- **Who can answer:** Product
- **When needed:** Before implementation
- **Current assumption:** Replace on replay for Phase 1; keep HeatMap available if 3D fails
- **Confidence:** Medium
- **Risk if wrong:** Low

**Question #3:** How should we handle frames with thermal_snapshots but missing one or more of north/south/east/west?
- **Why unclear:** Backend invariant says 5 readings; edge cases possible
- **Impact if wrong:** Interpolation artifact or crash
- **Who can answer:** Backend contract; defensive coding
- **Current assumption:** Guard; use center as fallback for missing; or skip frame
- **Confidence:** High
- **Risk if wrong:** Low

**Question #4:** Should temperature gradient in fragment shader exactly match HeatMap's 13-step 50°C anchors?
- **Why unclear:** Visual consistency vs. shader simplicity
- **Impact if wrong:** Slight color difference between HeatMap and 3D plate
- **Current assumption:** Approximate in shader (blue→yellow→orange→white); close enough
- **Confidence:** Medium
- **Risk if wrong:** Low

**Question #5:** What is the maximum displacement (uMaxDisplacement) in world units?
- **Why unclear:** Arbitrary without real thermal expansion coefficient
- **Impact if wrong:** Too subtle or too exaggerated
- **Current assumption:** 0.5 units (tunable)
- **Confidence:** Low
- **Risk if wrong:** Medium (tune post-implementation)

**Question #6:** Should HeatmapPlate3D be in the ESLint max-torchviz rule or a new total-Canvas rule?
- **Why unclear:** Rule currently counts TorchViz3D only
- **Impact if wrong:** Could exceed limit without lint failure
- **Current assumption:** Extend to count all R3F Canvas; or add HeatmapPlate3D to limit
- **Confidence:** Low
- **Risk if wrong:** Medium

**Question #7:** For demo page Phase 2 — shared Canvas with scissor, or keep HeatMap for one column?
- **Why unclear:** Trade-off complexity vs. consistency
- **Current assumption:** Defer to Phase 2 exploration
- **Confidence:** Low
- **Risk if wrong:** N/A for Phase 1

**Question #8:** Should we support multiple distances as "layers" or animation through distances?
- **Why unclear:** UX value
- **Current assumption:** No; single distance for Phase 1
- **Confidence:** High
- **Risk if wrong:** Low

**Question #9:** Interpolation algorithm: IDW vs. bilinear with 5 anchor points — which is better for 5-point?
- **Why unclear:** IDW can have singularity; bilinear needs more anchors
- **Current assumption:** IDW with epsilon to avoid div-by-zero; or barycentric
- **Confidence:** Low
- **Risk if wrong:** Medium (visual artifacts)

**Question #10:** What should happen when activeTimestamp has no thermal frame (e.g. between 5Hz samples)?
- **Why unclear:** Sparse thermal
- **Current assumption:** Use getFrameAtTimestamp (nearest before); or carry forward last thermal texture
- **Confidence:** Medium
- **Risk if wrong:** Low

**Blockers (need answers before starting):**
- 🔴 **BLOCKER:** Question #1 — Which distance to use (or document clearly)
- 🟡 **IMPORTANT:** Question #2 — Replace vs. toggle
- 🟡 **IMPORTANT:** Question #6 — ESLint/Canvas count
- 🟢 **NICE TO KNOW:** Questions #4, #5, #9 — Can decide during implementation

---

## 9. Initial Risk Assessment

**Risk #1: Technical — WebGL context overflow on demo if we add HeatmapPlate3D**
- **Description:** Demo has 2 TorchViz3D; adding 2 HeatmapPlate3D = 4 Canvases
- **Why risky:** Browsers limit ~8–16; 4 is within but combined with other tabs/HMR increases risk
- **Probability:** 30%
- **Impact:** High (white screen on demo)
- **Consequence:** Demo unusable; user refresh
- **Early warning:** Context lost in console; white canvas
- **Mitigation:** Phase 1 replay only; defer demo 3D to Phase 2 with shared Canvas or fallback
- **Contingency:** Keep HeatMap on demo; never add 3D there until solved
- **Owner:** Frontend

**Risk #2: Technical — Interpolation produces visual artifacts**
- **Description:** 5-point IDW may create rings or discontinuities
- **Why risky:** Sparse sampling; interpolation model choice
- **Probability:** 40%
- **Impact:** Medium (ugly but functional)
- **Consequence:** Plate looks wrong; distrust
- **Early warning:** Visible bands or spikes in displacement
- **Mitigation:** Unit test interpolation; try multiple algorithms; tune weights
- **Contingency:** Simpler interpolation (e.g. radial from center)
- **Owner:** Frontend

**Risk #3: Technical — Shader performance on low-end mobile**
- **Description:** 100×100 vertices + texture sample per vertex
- **Why risky:** Mobile GPUs weaker
- **Probability:** 25%
- **Impact:** Medium (frame drops)
- **Consequence:** Choppy replay on mobile
- **Early warning:** FPS drops in dev tools
- **Mitigation:** Reduce segments (50×50) on mobile; detect or config
- **Contingency:** Fallback to HeatMap on low capability
- **Owner:** Frontend

**Risk #4: Execution — Scope creep into demo/compare**
- **Description:** Desire to add 3D everywhere
- **Why risky:** Canvas count; delta heatmap complexity
- **Probability:** 50%
- **Impact:** Medium (delayed delivery; context issues)
- **Consequence:** Phase 1 slips; demo breaks
- **Early warning:** PR adds demo/compare changes in Phase 1
- **Mitigation:** Strict Phase 1 = replay only; document Phase 2/3
- **Contingency:** Revert demo/compare changes
- **Owner:** Dev

**Risk #5: User — 3D less accessible than 2D**
- **Description:** Screen readers, motor impairment; 3D controls harder
- **Why risky:** Accessibility requirement
- **Probability:** 80% (inherent)
- **Impact:** Medium (excludes some users)
- **Consequence:** A11y regression if we remove HeatMap
- **Early warning:** A11y audit flags 3D
- **Mitigation:** Keep HeatMap as fallback or toggle; aria-label on 3D; keyboard OrbitControls
- **Contingency:** Ensure HeatMap always available
- **Owner:** Frontend

**Risk #6: Technical — Texture upload every frame at 100fps**
- **Description:** If we update texture on every playback tick (not just thermal frames)
- **Why risky:** Unnecessary GPU uploads
- **Probability:** 20% (if we mistakenly update every tick)
- **Impact:** Low (wasted cycles)
- **Consequence:** Slight perf hit
- **Early warning:** Profiler shows texture upload spam
- **Mitigation:** Only update texture when thermalData changes (memo)
- **Contingency:** Throttle updates
- **Owner:** Frontend

**Risk #7: Execution — Interpolation algorithm takes longer than 2h**
- **Description:** Tuning IDW/bilinear for good visuals
- **Why risky:** Unknown best approach
- **Probability:** 35%
- **Impact:** Low (schedule slip)
- **Consequence:** +1–2h
- **Early warning:** Iteration 3+ on interpolation
- **Mitigation:** Start simple (e.g. center-blur); refine if needed
- **Contingency:** Ship simpler version
- **Owner:** Dev

**Risk #8: Business — Priority change**
- **Description:** Other work deprioritizes this
- **Why risky:** Not P0
- **Probability:** 30%
- **Impact:** Low (deferred)
- **Consequence:** Feature ships later
- **Mitigation:** Document value; align with roadmap
- **Owner:** Product

**Risk Matrix:**

| Risk | Probability | Impact | Priority | Owner | Status |
|------|------------|--------|----------|-------|--------|
| #1 WebGL overflow demo | 30% | High | 🔴 P0 | Frontend | Not Started |
| #2 Interpolation artifacts | 40% | Medium | 🟡 P1 | Frontend | Not Started |
| #3 Mobile perf | 25% | Medium | 🟡 P1 | Frontend | Not Started |
| #4 Scope creep | 50% | Medium | 🟡 P1 | Dev | Not Started |
| #5 A11y | 80% | Medium | 🟡 P1 | Frontend | Not Started |
| #6 Texture upload | 20% | Low | 🟢 P2 | Frontend | Not Started |
| #7 Interpolation time | 35% | Low | 🟢 P2 | Dev | Not Started |
| #8 Priority change | 30% | Low | 🟢 P2 | Product | Not Started |

**Top 3 Risks:**
1. **#1 WebGL overflow** — Plan: Phase 1 replay only; no demo 3D
2. **#2 Interpolation artifacts** — Plan: Unit test; try 2–3 algorithms
3. **#5 A11y** — Plan: Keep HeatMap fallback; aria-label on 3D

---

## 10. Classification & Metadata

**Type:** feature

**Priority:** P2 (Normal)
- **Justification:** This is a valuable differentiator that elevates perceived product quality and uses data we already have. It is not blocking users (current HeatMap works) and is not on a hard deadline. It aligns with industrial positioning and investor demo appeal. High impact for enterprise/prospect demos but not critical path for core recording/replay workflow. Response time: within 1 month is reasonable.

**Effort Estimate:** Medium (12–16 hours)

**Breakdown:**
- Thermal interpolation utility: 2h
- Vertex shader: 1h
- Fragment shader: 1h
- HeatmapPlate3D component: 4h
- Torch indicator: 1h
- Replay integration: 1h
- Dynamic import, loading, context-loss: 1h
- Testing (unit + integration): 2h
- Buffer (tuning, fixes): 2h
- **Total:** ~15h

**Confidence:** Medium — Interpolation and shader integration may take longer; WebGL is familiar from TorchViz3D.

**Category:** Frontend (UI components, client-side logic)

**Tags:**
- [x] user-facing
- [ ] breaking-change
- [ ] needs-migration
- [ ] needs-feature-flag
- [ ] experimental
- [ ] technical-debt
- [ ] quick-win
- [x] high-impact
- [ ] low-effort
- [ ] needs-design
- [ ] needs-research
- [ ] needs-approval

---

## 11. Strategic Context

### Product Roadmap Fit
- **Q2 Goal (assumed):** Industrial-grade replay experience
- **This supports by:** Adding physics-informed 3D thermal visualization
- **Contribution:** Significant for visual differentiator
- **Metric impact:** Demo conversion, enterprise perception

- **Product vision:** Reliable MVP for recording, replaying, scoring welding sessions; industrial quality
- **This advances by:** Replay visualization that reflects thermal expansion and spatial distribution
- **Strategic importance:** High

### Capabilities Unlocked
1. **Future: Multi-distance 3D plate** — Show multiple plates or animate through distances
2. **Future: Comparison mode** — Expert vs novice 3D plates side-by-side in one Canvas
3. **Future: Export 3D view** — Screenshot or video of 3D plate for reports

### User Feedback Themes
- **Theme:** "Looks like a chart" (from internal review)
  - **How this resolves:** 3D physics-based visualization

- **Theme:** "Industrial software should show real behavior" (positioning)
  - **How this resolves:** Thermal expansion = real physics

### User Impact
- **Segment:** Replay users (welders, supervisors, QA)
  - **Benefit:** Richer understanding of thermal distribution
  - **Value:** Trust, professionalism

- **Segment:** Prospects/investors (demo)
  - **Benefit:** "Wow" factor when we add to demo (Phase 2)
  - **Value:** Differentiation vs. competitors

### Technical Impact
- **Improves:** Visualization fidelity; data utilization (5-point)
- **Maintains:** Frame contract; API; HeatMap for fallback
- **Degrades:** None if HeatMap retained

- **Technical debt:** Adds ~400 LOC (component + shaders + util); acceptable for feature value
- **Net impact:** Positive

### Trade-offs
1. **Accepting:** Replay only in Phase 1 (demo/compare keep HeatMap)
   - **To gain:** Safe WebGL budget; faster delivery
   - **Worth it:** Yes — replay is primary use case

2. **Accepting:** Possible interpolation artifacts
   - **To gain:** Simpler implementation
   - **Worth it:** Yes — can tune later

### Alternatives Considered
1. **Improve CSS HeatMap with 5-direction toggle** — Why not: Still flat; no thermal expansion
2. **2D SVG heatmap with warp effect (CSS transform)** — Why not: Fake; not true 3D
3. **Use Recharts 3D** — Why not: No suitable 3D heatmap; custom shaders better

---

## Thinking Checkpoint #2 — Self-Critique

### 1. Would a new team member understand this?
- **Unclear points:** (1) "5-point" — explain center+N/S/E/W; (2) "distance" — which snapshot; (3) Canvas count — why replay safe, demo not
- **Added:** Clarified in Current State (ThermalSnapshot structure); Scope (which distance); Risk #1 (Canvas count)

### 2. Can someone explore without asking?
- **Might ask:** Exact interpolation formula; shader uniform names
- **Answer in issue:** Interpolation described in Desired Outcome; shader uniforms in task prompt (uTemperatureMap, uMaxTemp, uMaxDisplacement)

### 3. Quantified impact
- **Numbers used:** 100×100, 5Hz, 10k vertices, 8–16 WebGL limit, 2 Canvas max, ~15h effort, 20–600°C, 5 readings
- **Count:** 12+ — sufficient

### 4. Evidence provided
- File paths, line references, type definitions, component props
- HeatMap 126 lines; extractHeatmapData structure; ThermalSnapshot; WEBGL doc
- **Count:** 8+ — sufficient

### 5. Failure considered
- **Risks:** 8 documented
- **Edge cases:** No thermal, missing readings, sparse data, context loss, mobile perf

### 6. Strategic connections
- Product vision, roadmap, user segments, alternatives, trade-offs
- **Count:** 6+ — sufficient

### 7. Detail level
- **Word count:** ~4500+ words
- **Depth:** All sections filled; no placeholders

### 8. Assumptions challenged
- Which distance? — Open question
- Replace vs toggle? — Open question
- Interpolation algorithm? — Open question
- Demo Canvas? — Risk, deferred

---

## Quality Metrics

| Metric | Minimum | Count | Pass? |
|--------|---------|-------|-------|
| Total words | 3,000 | ~4,500 | ✅ |
| Pre-thinking words | 500 | ~700 | ✅ |
| Acceptance criteria | 12 | 12+ | ✅ |
| Open questions | 10 | 10 | ✅ |
| Risks identified | 8 | 8 | ✅ |
| Similar features | 3 | 3 | ✅ |
| Related issues | 2 | 2 | ✅ |
| Assumptions | 5 | 6+ | ✅ |
| Evidence pieces | 5 | 8+ | ✅ |
| Quantified impacts | 10 | 12+ | ✅ |

---

## After Issue Creation

**Immediate next steps:**
1. [ ] Resolve blocker: Which thermal snapshot distance to use (or document default)
2. [ ] Decide: Replace vs. toggle for HeatMap on replay
3. [ ] Proceed to Phase 2: Explore Feature (technical exploration)
4. [ ] Assign explorer (or same person)

**This issue becomes the foundation for exploration and planning.**
