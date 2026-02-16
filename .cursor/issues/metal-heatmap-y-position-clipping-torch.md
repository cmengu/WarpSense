# [Bug] Metal Heatmap Plane Y-Position Clips Through Torch — Torch Should Rest Just Above Metal

---

## Phase 0: Mandatory Pre-Issue Thinking Session

### A. Brain Dump (5+ minutes)

The metal heatmap (ThermalPlate) is successfully implemented — we have the thermally-colored workpiece with vertex displacement for thermal expansion. But the metal plane's Y position is wrong. When the thermal data causes the metal to bulge upward (simulating thermal expansion), the metal surface rises too high and clips through the torch assembly. In a welding simulation, the torch should rest just above the metal workpiece, with the weld pool hovering over the metal surface. What we're seeing instead: the metal plane passes through the torch, intersecting with the weld pool sphere and cone. This breaks the visual metaphor — it looks like the metal is floating up into the torch instead of the torch sitting above a workpiece.

The root cause appears to be numeric: the workpiece group is at Y=-0.6; the vertex shader displaces vertices along the normal (upward) by `(temperature / maxTemp) * uMaxDisplacement` where uMaxDisplacement=0.5. So at max temperature, the metal surface at the weld center can rise to Y = -0.6 + 0.5 = -0.1. The torch group is at Y=0.4, and the weld pool sphere is at Y=-0.6 relative to that, so world Y = 0.4 - 0.6 = -0.2. That means the metal surface (-0.1) is ABOVE the weld pool center (-0.2). The metal bulges right through the torch. The fix is to ensure the metal surface (even at max displacement) stays below the weld pool. We need either: (a) lower the workpiece base Y, (b) reduce uMaxDisplacement, or (c) both.

Who is affected: anyone using TorchWithHeatmap3D — replay page, demo page with expert session. Internal team and external users who see the 3D unified torch+metal view. The bug is visible every time thermal data is present and temperatures are high enough to cause significant displacement.

What we're assuming: the Y-axis convention (up = positive), the plane normal points up after rotation, the weld pool center is the reference "touch point" for "torch above metal." We're assuming the fix is purely positional — no need to change the thermal interpolation, shader logic, or data flow. Just geometry positions.

What could go wrong: if we lower the metal too much, the visual gap between torch and metal might look unnatural (torch floating too high). If we reduce displacement too much, the thermal warp effect might become barely visible. We need to balance: enough displacement for visible thermal expansion, but metal always below torch. Also: the angle guide ring and ContactShadows are at Y=-0.59; the grid is at Y=-0.6. If we move the workpiece, we may need to align those or they'll look wrong.

The simplest fix: lower the workpiece group from Y=-0.6 to something like Y=-0.85 or Y=-0.9. Then max surface = -0.85 + 0.5 = -0.35, safely below weld pool at -0.2. We'd also need to move the angle guide ring, grid, ContactShadows to match. Alternatively: reduce uMaxDisplacement from 0.5 to 0.25 or 0.3. Then max surface = -0.6 + 0.3 = -0.3, below -0.2. Less bulge, but avoids clipping. A combined approach: workpiece at -0.75, displacement 0.35 → max -0.4, comfortable gap.

HeatmapPlate3D is a separate component with its own coordinate system (ThermalPlate at origin, TorchIndicator at Y=2) — that's for standalone dev view. The bug specifically affects TorchWithHeatmap3D in replay/demo. TorchViz3D (flat metal, no thermal) uses the same Y=-0.6 and doesn't have displacement, so it's fine. The bug is isolated to the thermal case in TorchWithHeatmap3D.

---

### B. Question Storm (20+ questions)

1. What exact Y values produce "torch just above metal" with a visible but non-clipping gap?
2. Should the gap be physically realistic (mm-scale) or stylized for readability?
3. Does the angle guide ring (Y=-0.59) need to move with the workpiece?
4. Does ContactShadows position (Y=-0.59) need to align with metal surface?
5. Does gridHelper (Y=-0.6) represent "floor" or "workpiece plane" — should it move?
6. Is uMaxDisplacement=0.5 too aggressive for the current scale?
7. Should uMaxDisplacement be configurable via props (plateSize, scale)?
8. Does HeatmapPlate3D have the same clipping issue? (Different layout — ThermalPlate at origin.)
9. Are there edge cases where thermal data spikes briefly and causes one-frame clips?
10. Should we add a small safety margin (e.g. 0.05–0.1 units) beyond "just below"?
11. Does the weld pool sphere radius (0.12 solid, 0.18 glow) affect the "touch point"?
12. When torch angle changes (e.g. 30° vs 60°), does the clipping zone shift?
13. Is the fix only in TorchWithHeatmap3D, or does ThermalPlate need a baseY prop?
14. Should ThermalPlate document "parent must position so max displacement stays below torch"?
15. Do we need to update the ThermalPlate JSDoc with new recommended parent positions?
16. Will changing workpiece Y affect shadow casting/receiving (shadow camera bounds)?
17. Are there unit tests that assert specific Y positions? Will they break?
18. Does the demo page use the same positions as replay? (Yes — both use TorchWithHeatmap3D.)
19. Should we extract magic numbers (0.6, 0.59, 0.5) into named constants?
20. Is there a single "metal surface Y" constant we can derive others from?
21. What does "just above" mean quantitatively — 0.1 units? 0.2?
22. Does the flat (non-thermal) workpiece in TorchWithHeatmap3D also need to move for consistency?
23. Are there visual regression tests we should add?
24. Could the fix affect HeatmapPlate3D if it shares ThermalPlate? (No — HeatmapPlate3D positions differently.)

---

### C. Five Whys Analysis

**Problem:** Metal heatmap plane clips through the torch; metal passes through the weld pool.

**Why #1:** Why is this a problem?
- **Answer:** It breaks the visual metaphor. Users expect the torch to rest above the metal. Seeing metal intersect the torch is confusing and looks broken.

**Why #2:** Why is that a problem?
- **Answer:** The 3D view is meant to convey weld geometry and thermal distribution. Clipping makes it hard to interpret where the weld pool meets the metal. Trust in the visualization degrades.

**Why #3:** Why is that a problem?
- **Answer:** In a safety-adjacent industrial system, visualization correctness matters. Incorrect spatial relationships can lead to misinterpretation. "Exact replays" and "explainability" are core goals.

**Why #4:** Why is that a problem?
- **Answer:** We're not conveying the weld scene accurately. The thermal expansion effect (vertex displacement) is correct conceptually, but the base positioning was not validated against the torch geometry.

**Why #5:** Why is that the real problem?
- **Answer:** The workpiece base Y (-0.6) and max vertex displacement (0.5) were set without ensuring their sum stayed below the weld pool center (-0.2). The root cause is a missing constraint: metal_surface_max_Y < weld_pool_center_Y. No validation or constant derivation exists.

**Root cause identified:** Workpiece Y (-0.6) + max displacement (0.5) = -0.1, which is greater than weld pool center Y (-0.2). The metal bulges above the torch. We need to enforce metal_surface_max_Y < weld_pool_center_Y with a configurable or derived gap.

---

## Required Information Gathering

### 1. Understand the Request

**User's initial request:**
> "the metal heatmap is successfully implemented, but the metal is too high of a y level, its clipping onto the torch, the torch should rest just above the metal plane, not with the metal plane passing through the torch"

**Clarifications obtained:**
- The thermal metal (ThermalPlate with vertex displacement) is implemented and working.
- The issue is purely spatial: metal Y is too high, causing clipping/intersection with the torch.
- Desired state: torch rests just above the metal plane; metal should never pass through the torch.
- No other bugs in the metal heatmap implementation were mentioned in this first item ("first off" suggests more may follow).

**Remaining ambiguities:**
- Exact desired gap (how many units "just above").
- Whether to prefer lowering metal vs reducing displacement.
- Whether angle guide ring, grid, ContactShadows should move with the metal.

### 2. Search for Context

#### Codebase Search

**Similar existing features found:**

1. **TorchViz3D** (`my-app/src/components/welding/TorchViz3D.tsx`)
   - What it does: Renders 3D torch + flat gray workpiece. Same torch geometry, flat plane at Y=-0.6.
   - Relevant patterns: Workpiece at `position={[0, -0.6, 0]}`, angle ring at -0.59, grid at -0.6.
   - What we can reuse: Same coordinate convention, torch group at Y=0.4.
   - What we should avoid: Copying the -0.6 value without considering thermal displacement.

2. **TorchWithHeatmap3D** (`my-app/src/components/welding/TorchWithHeatmap3D.tsx`)
   - What it does: Unified torch + ThermalPlate (or flat metal when no thermal).
   - Relevant patterns: Workpiece group at `[0, -0.6, 0]`, ThermalPlate inside; flat fallback at same position.
   - What we can reuse: Structure; change only the workpiece group Y.
   - What we should avoid: Breaking the flat-metal fallback alignment.

3. **ThermalPlate** (`my-app/src/components/welding/ThermalPlate.tsx`)
   - What it does: 100×100 plane, vertex displacement by temperature, temp→color.
   - Relevant patterns: `uMaxDisplacement: 0.5`; position/rotation set by parent.
   - What we can reuse: Shader logic; we change parent position or reduce uMaxDisplacement.
   - What we should avoid: Changing ThermalPlate API if parent-only fix suffices.

4. **HeatmapPlate3D** (`my-app/src/components/welding/HeatmapPlate3D.tsx`)
   - What it does: Standalone thermal plate view; ThermalPlate at origin, TorchIndicator at Y=2.
   - Relevant patterns: Different layout; no shared Y with TorchWithHeatmap3D.
   - What we can reuse: ThermalPlate is shared; fix in TorchWithHeatmap3D only.
   - What we should avoid: Changing HeatmapPlate3D unless it has a similar bug.

5. **heatmapVertex.glsl.ts** (`my-app/src/components/welding/shaders/heatmapVertex.glsl.ts`)
   - What it does: `newPosition = position + normal * displacement`; displacement from temperature.
   - Relevant patterns: Displacement along normal (up after rotation).
   - What we can reuse: Shader unchanged; adjust base position or uMaxDisplacement.
   - What we should avoid: Changing displacement direction or formula.

**Existing patterns to follow:**
1. **Single source of geometry constants:** TorchViz3D and TorchWithHeatmap3D share the same torch geometry (0.4, -0.6, etc.). Consider extracting to a shared constant module.
2. **Parent positions ThermalPlate:** ThermalPlate JSDoc says "Position/rotation must be set by parent." Fix belongs in parent (TorchWithHeatmap3D).

**Anti-patterns to avoid:**
1. **Magic numbers without derivation:** Don't scatter -0.6, -0.59, 0.5 without documenting the relationship.
2. **Breaking flat-metal alignment:** Flat and thermal workpieces should appear at the same "metal surface" level for consistency.

**Related components/utilities:**
- `ThermalPlate` at `components/welding/ThermalPlate.tsx` — thermal workpiece mesh
- `heatmapVertex.glsl.ts` — vertex displacement
- `frameUtils.getFrameAtTimestamp` — frame resolution (unchanged)

**Data models/types:** None changed. Frame, ThermalSnapshot unchanged.

#### Documentation Search

- [x] `CONTEXT.md` — Section "3D Visualization (TorchViz3D, TorchWithHeatmap3D)": TorchWithHeatmap3D unifies torch + thermal metal; ThermalPlate for thermal workpiece. Replay/demo use it.
- [ ] `ARCHITECTURE.md` — N/A
- [ ] `README.md` — General setup; not specific to 3D layout.
- [ ] `documentation/WEBGL_CONTEXT_LOSS.md` — Max 2 Canvas, context loss; no geometry.

**Key insights:** CONTEXT confirms TorchWithHeatmap3D is the primary component for replay/demo. Thermal metal replaces separate HeatmapPlate3D in that context. Fix is localized to TorchWithHeatmap3D (and possibly shared constants).

---

## 🧠 THINKING CHECKPOINT #1

### 1. Assumptions That Might Be Wrong

1. **Assumption:** Fix is purely positional (Y values); no shader or interpolation change.
   - **If wrong:** ThermalPlate might have a bug in displacement direction or magnitude.
   - **How to verify:** Inspect shader normal direction, temperature range.
   - **Likelihood:** Low
   - **Impact if wrong:** Medium — would need shader fix.

2. **Assumption:** Weld pool center Y = 0.4 - 0.6 = -0.2 is the correct "torch bottom" reference.
   - **If wrong:** Perhaps the cone tip (-0.5) or another part should be the reference.
   - **How to verify:** Visual inspection; user said "torch should rest just above metal" — weld pool is the contact point.
   - **Likelihood:** Low
   - **Impact if wrong:** Low — minor position tweak.

3. **Assumption:** Moving workpiece group Y is sufficient; angle ring, grid, ContactShadows can stay or move with it.
   - **If wrong:** They might need to stay at -0.6 for "floor" semantics.
   - **How to verify:** User/stakeholder; visual testing.
   - **Likelihood:** Medium
   - **Impact if wrong:** Medium — might need separate "floor" vs "metal surface" layers.

4. **Assumption:** HeatmapPlate3D is unaffected (different coordinate system).
   - **If wrong:** HeatmapPlate3D might have analogous clipping with TorchIndicator.
   - **How to verify:** Check TorchIndicator at Y=2, ThermalPlate at origin; likely no overlap.
   - **Likelihood:** Low
   - **Impact if wrong:** Low — separate issue.

5. **Assumption:** Reducing uMaxDisplacement won't harm the "thermal warp" effect.
   - **If wrong:** 0.25–0.35 might make bulge barely visible.
   - **How to verify:** A/B test; user feedback.
   - **Likelihood:** Medium
   - **Impact if wrong:** Low — we can increase if needed.

### 2. Skeptical Engineer Questions

1. **Q:** Are we sure the displacement is along +Y? **A:** Plane has rotation [-π/2,0,0]; default plane normal is +Y; vertex shader uses `normal * displacement`; so yes, vertices move up.
2. **Q:** Could the problem be the flat fallback, not ThermalPlate? **A:** Flat plane has no displacement; it stays at -0.6. Only ThermalPlate bulges.
3. **Q:** Does the grid represent the workpiece or the floor? **A:** Convention: grid at -0.6 aligns with metal. If we move metal, grid likely should move for consistency.
4. **Q:** Will shadows look wrong if we change Y? **A:** Shadow camera is large (left/right ±10, top/bottom ±10); metal at -0.85 is still in view.
5. **Q:** Do we have tests that assert Y positions? **A:** Check __tests__; TorchWithHeatmap3D tests may not assert positions.
6. **Q:** Could there be z-fighting between metal and torch? **A:** Possible if they coincide; moving metal down eliminates overlap.
7. **Q:** Is 0.5 displacement physically realistic? **A:** No — it's stylized. We optimize for readability.
8. **Q:** Should the fix be a constant (e.g. WORKPIECE_BASE_Y) for maintainability? **A:** Yes — extract to avoid future drift.
9. **Q:** What about different plateSize (3 vs 10)? **A:** TorchWithHeatmap3D uses plateSize=3 default; scale is same; displacement in same world units.
10. **Q:** Does the angle ring sit on the metal or float? **A:** At -0.59, slightly above -0.6 metal; visually "on" the metal. If metal moves to -0.85, ring at -0.59 would float; we should move ring with metal.

### 3. Edge Cases and Failure Modes

**Edge cases:**
1. Max temperature (500°C) at center — maximum bulge; must not clip.
2. Very low temperature — no displacement; metal at base Y only.
3. Torch angle 90° (vertical) — geometry extends differently; clipping zone may change.
4. plateSize=1 vs 10 — same displacement magnitude; scale-independent.
5. First frame vs last frame — thermal may spike; ensure no transient clips.

**Failure modes:**
1. Metal lowered too much — torch appears to float unrealistically high.
2. Displacement reduced too much — thermal warp becomes invisible.
3. Angle ring misaligned — looks like it's floating or sunk into metal.
4. Grid misaligned — floor no longer matches metal plane.
5. ContactShadows wrong — shadows don't match metal position.

**Dependencies:**
1. ThermalPlate uMaxDisplacement — if we change it, ThermalPlate affects both TorchWithHeatmap3D and HeatmapPlate3D.
2. Torch geometry — any change to torch Y would require re-deriving metal Y.
3. HeatmapPlate3D — uses ThermalPlate at origin; no shared Y, but uMaxDisplacement is shared.

### 4. Explain to a Junior Developer

Imagine you're building a 3D welding scene. We have a torch (like a pencil) and a metal plate (the workpiece). The torch points down at the metal. Where the torch touches the metal, we show a glowing weld pool. The metal also shows heat — when it's hot, we make the metal surface bulge slightly (thermal expansion effect). The problem: we set the metal's base height and the bulge amount such that when the metal gets really hot, the bulge goes UP too far. It goes right through the torch! It looks like the metal is punching through the weld pool. We want the opposite: the torch should sit just above the metal, and the metal should always stay below it. The fix is to either (a) lower the metal so that even when it bulges to its maximum, it stays below the torch, or (b) reduce how much it bulges, or (c) both. We'll pick values so that: metal_base_Y + max_bulge < torch_weld_pool_Y, with a little gap so it looks natural.

### 5. Red Team

**Problem 1:** We might lower metal so much that the grid/ring look disconnected.
- **Impact:** Visual inconsistency.
- **Mitigation:** Move grid and ring with the metal; keep them aligned.

**Problem 2:** uMaxDisplacement change could make HeatmapPlate3D look different.
- **Impact:** Standalone heatmap view might have less dramatic warp.
- **Mitigation:** If we change uMaxDisplacement, verify HeatmapPlate3D; or add a prop to ThermalPlate for maxDisplacement override.

**Problem 3:** Different torch angles could change where "just above" is.
- **Impact:** At 30° angle, torch extends further down; might clip from the side.
- **Mitigation:** Center of weld pool is the primary reference; side clipping less likely with plate at center.

**Problem 4:** We might introduce magic numbers without documentation.
- **Impact:** Future changes break the fix.
- **Mitigation:** Extract WORKPIECE_BASE_Y, WELD_POOL_CENTER_Y, MAX_DISPLACEMENT to constants with comments.

**Problem 5:** Flat metal fallback at -0.6, thermal at -0.85 — inconsistent?
- **Impact:** When switching thermal on/off, metal might "jump."
- **Mitigation:** Use the same base Y for both; flat has no displacement so it stays at base. Both at -0.85.

---

## Issue Structure

### 1. Title

**Format:** `[Bug] Metal heatmap plane Y-position clips through torch — torch should rest just above metal`

- [x] Starts with type tag
- [x] Specific (describes the clipping and desired state)
- [x] Under 100 characters
- [x] Action-oriented
- [x] Understandable to non-technical stakeholders

### 2. TL;DR

The metal heatmap (thermal workpiece) in the unified 3D torch view bulges upward when hot, but the base position and maximum displacement are set so that the metal surface rises above the weld pool and clips through the torch. Users see the metal plane intersecting the torch instead of the torch resting above the metal. The core problem is numeric: workpiece base Y (-0.6) plus max vertex displacement (0.5) yields a surface at Y=-0.1, which is above the weld pool center at Y=-0.2. Currently, anyone viewing replay or demo with thermal data sees this clipping when temperatures are high. We need to lower the workpiece base and/or reduce maximum displacement so that the metal surface (including thermal bulge) always stays below the torch, with a small visible gap. This maintains the "torch above workpiece" metaphor and supports our product goals of correctness and explainability in safety-adjacent welding visualization. Small-to-medium effort (4–8 hours) with high visual impact for replay and demo users.

### 3. Current State

#### A. What's Already Built

**UI Components:**

1. **TorchWithHeatmap3D** (`my-app/src/components/welding/TorchWithHeatmap3D.tsx`)
   - **What it does:** Renders unified 3D torch + thermal metal (ThermalPlate) or flat metal when no thermal data.
   - **Current capabilities:** Torch at Y=0.4; workpiece group at Y=-0.6; ThermalPlate inside; angle ring at -0.59; grid at -0.6; ContactShadows at -0.59.
   - **Limitations:** Metal clips through torch when thermal displacement is high.
   - **Dependencies:** ThermalPlate, frameUtils, drei, three.
   - **Last modified:** Recent (per git status).

2. **ThermalPlate** (`my-app/src/components/welding/ThermalPlate.tsx`)
   - **What it does:** 100×100 plane with vertex displacement and temperature-based color.
   - **Current capabilities:** `uMaxDisplacement: 0.5`; displacement along normal; interpolates 5-point thermal data.
   - **Limitations:** No control over base position (parent sets it); uMaxDisplacement fixed.
   - **Dependencies:** thermalInterpolation, heatmapVertex, heatmapFragment shaders.
   - **Last modified:** Recent.

3. **TorchViz3D** (`my-app/src/components/welding/TorchViz3D.tsx`)
   - **What it does:** Torch + flat workpiece (no thermal).
   - **Current capabilities:** Same torch geometry; workpiece at Y=-0.6.
   - **Limitations:** N/A for this bug (no thermal displacement).
   - **Dependencies:** three, drei.
   - **Last modified:** Recent.

**Data/Constants:**
- Torch group: `position={[0, 0.4, 0]}`
- Weld pool sphere: `position={[0, -0.6, 0]}` relative to torch → world Y = -0.2
- Workpiece group: `position={[0, -0.6, 0]}`
- Angle ring: `position={[0, -0.59, 0]}`
- Grid: `position={[0, -0.6, 0]}`
- ContactShadows: `position={[0, -0.59, 0]}`
- ThermalPlate `uMaxDisplacement`: 0.5

**Key numeric relationship (current, broken):**
- Metal base Y: -0.6
- Max displacement: 0.5
- Metal surface max Y: -0.6 + 0.5 = **-0.1**
- Weld pool center Y: **-0.2**
- Result: -0.1 > -0.2 → metal above weld pool → clipping

#### B. Current User Flows

**Flow 1: Replay with thermal data**
1. User opens replay for session with thermal_frames.
2. TorchWithHeatmap3D renders torch + ThermalPlate.
3. As playback runs, thermal data drives vertex displacement.
4. At high temps, metal bulges into torch — visible clipping.
5. **Current limitation:** Metal passes through torch.

**Flow 2: Demo expert session**
1. User opens /demo with expert session (thermal data).
2. Same TorchWithHeatmap3D.
3. Same clipping when temps are high.
4. **Current limitation:** Same as replay.

**Flow 3: Replay without thermal data**
1. Session has no thermal; TorchWithHeatmap3D uses flat metal.
2. No displacement; metal stays at -0.6.
3. No clipping; torch correctly above metal.
4. **Current limitation:** N/A — flat case works.

#### C. Broken User Flows

1. **Flow:** User wants to interpret weld pool position relative to heated metal.
   - **Current behavior:** Metal and torch overlap; unclear where they meet.
   - **Why it fails:** Metal surface Y exceeds weld pool Y.
   - **User workaround:** None; must tolerate visual confusion.
   - **Frequency:** Every replay/demo with thermal and high temps.
   - **Impact:** Reduced trust in visualization; harder to interpret.

2. **Flow:** User expects "torch above metal" industrial metaphor.
   - **Current behavior:** Metal appears to intersect torch.
   - **Why it fails:** Same numeric issue.
   - **User workaround:** Ignore 3D view or rely on 2D heatmap.
   - **Frequency:** Same.
   - **Impact:** Metaphor broken; UX degradation.

3. **Flow:** User screenshots or records replay for report.
   - **Current behavior:** Screenshots show clipping.
   - **Why it fails:** Visual bug present in export.
   - **User workaround:** Avoid 3D view in reports.
   - **Frequency:** When users capture 3D view.
   - **Impact:** Unprofessional appearance.

#### D. Technical Gaps

- No constant or validation enforcing `metal_surface_max_Y < weld_pool_Y`.
- Magic numbers (-0.6, -0.59, 0.5) not derived from a single source of truth.
- No documented "coordinate design" for torch + metal relationship.

#### E. Current State Evidence

**Code (TorchWithHeatmap3D.tsx, lines 141–225):**
```tsx
<group ref={torchGroupRef} position={[0, 0.4, 0]}>
  ...
  <mesh castShadow position={[0, -0.6, 0]}>  // weld pool
  ...
</group>
<group position={[0, -0.6, 0]}>  // workpiece
  {hasThermal ? <ThermalPlate ... /> : <mesh ... />}
</group>
<mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.59, 0]}>  // angle ring
```

**Code (ThermalPlate.tsx, line 78):**
```tsx
uMaxDisplacement: { value: 0.5 },
```

**Code (heatmapVertex.glsl.ts):**
```glsl
float displacement = (temperature / safeMaxTemp) * uMaxDisplacement;
vec3 newPosition = position + normal * displacement;
```

---

### 4. Desired Outcome

#### A. User-Facing Changes

**Primary User Flow:**
1. User opens replay/demo with thermal data.
2. TorchWithHeatmap3D renders.
3. Metal surface (including thermal bulge) is always below the torch.
4. Torch appears to rest just above the metal.
5. No clipping regardless of temperature.

**UI Changes:**
- No new UI elements.
- Visual change: metal plane and torch no longer intersect; clear spatial relationship.

**UX Changes:**
- "Torch above metal" metaphor is preserved.
- Thermal expansion remains visible but constrained so it never crosses the torch.

#### B. Technical Changes

**Existing files to modify:**

1. `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
   - **Current state:** Workpiece group at [0, -0.6, 0]; angle ring at [0, -0.59, 0]; grid at [0, -0.6, 0]; ContactShadows at [0, -0.59, 0].
   - **Changes needed:** Lower workpiece group Y (e.g. to -0.85 or -0.9) so metal_surface_max < weld_pool_Y; move angle ring, grid, ContactShadows to align with new metal surface.
   - **Lines affected:** ~189, 212, 222, 225.
   - **Risk level:** Low
   - **Why risky:** Minimal — position changes only.

2. `my-app/src/components/welding/ThermalPlate.tsx` (optional)
   - **Current state:** `uMaxDisplacement: 0.5`.
   - **Changes needed:** Optionally reduce to 0.25–0.35 if parent-position-only fix is insufficient, or add `maxDisplacement` prop for flexibility.
   - **Lines affected:** ~78.
   - **Risk level:** Low
   - **Why risky:** Affects HeatmapPlate3D if we change global value.

**Optional: New constants file**
- `my-app/src/constants/welding3d.ts` (or similar)
- Define: `WELD_POOL_CENTER_Y`, `WORKPIECE_BASE_Y`, `MAX_THERMAL_DISPLACEMENT`, `ANGLE_RING_Y_OFFSET` with documentation.
- Used by: TorchWithHeatmap3D, potentially TorchViz3D for consistency.

#### C. Success Criteria (12+)

**User can criteria:**
1. **[ ]** User can view replay with thermal data without metal clipping through torch.
   - **Verification:** Visual inspection at max temp.
   - **Expected:** Metal surface always below weld pool.

2. **[ ]** User can view demo with thermal data without clipping.
   - **Verification:** Same as above on /demo.
   - **Expected:** Same.

3. **[ ]** User can see thermal bulge effect (metal warping) when hot.
   - **Verification:** Warp is visible but does not intersect torch.
   - **Expected:** Bulge present, constrained.

4. **[ ]** User sees torch "resting just above" metal with a small gap.
   - **Verification:** Visual inspection.
   - **Expected:** Clear gap; no overlap.

5. **[ ]** User can change torch angle (e.g. 30°–60°) without new clipping.
   - **Verification:** Sweep angle; observe 3D view.
   - **Expected:** No clipping at any angle.

6. **[ ]** User sees flat metal (no thermal) at same "metal surface" level as thermal when switching.
   - **Verification:** Session with/without thermal; compare metal height.
   - **Expected:** Consistent base level.

**System does criteria:**
7. **[ ]** System computes metal_surface_max_Y such that it is less than weld_pool_center_Y.
   - **Verification:** Code review; constants or comments.
   - **Expected:** Explicit relationship.

8. **[ ]** System positions workpiece group, angle ring, grid, ContactShadows consistently.
   - **Verification:** Code review.
   - **Expected:** All derived from or aligned with metal surface.

9. **[ ]** System does not change HeatmapPlate3D behavior adversely (if uMaxDisplacement changed).
   - **Verification:** Render HeatmapPlate3D standalone; check warp.
   - **Expected:** Acceptable or unchanged.

10. **[ ]** System passes existing TorchWithHeatmap3D and ThermalPlate tests.
    - **Verification:** `npm test`.
    - **Expected:** All pass.

11. **[ ]** System maintains WebGL context limit (max 2 Canvas) and context-loss handling.
    - **Verification:** No new Canvas; context-loss overlay still works.
    - **Expected:** No regression.

12. **[ ]** System documents the Y-coordinate relationship (in code or constants).
    - **Verification:** Comments or constants file.
    - **Expected:** Future developers can understand the constraint.

**Quality criteria:**
- **Performance:** No regression; same draw calls, same shaders.
- **Accessibility:** No change to aria labels; 3D view unchanged for screen readers.
- **Browser compatibility:** Same as current (Chrome, Firefox, Safari).
- **Error handling:** N/A for position-only change.
- **Security:** N/A.

#### D. Detailed Verification (Top 5 Criteria)

**Criterion 1: No metal clipping through torch**
- Metal surface max Y: measure or compute as workpiece_base_Y + uMaxDisplacement.
- Weld pool center Y: 0.4 - 0.6 = -0.2.
- Pass: metal_surface_max_Y < -0.2 (e.g. ≤ -0.35 for ~0.15 gap).
- Test: Load replay with high-temp thermal; rotate view; confirm no intersection.
- Edge: Max temp at center; also check off-center hot spots (displacement varies by UV).

**Criterion 2: Thermal bulge visible**
- uMaxDisplacement ≥ 0.2 (or equivalent effect after position change).
- Test: Compare cold vs hot frames; bulge should be noticeable.
- Edge: Low temps — minimal bulge is OK.

**Criterion 3: Torch "just above" metal**
- Gap between metal max surface and weld pool center: 0.1–0.2 units (subjective "just above").
- Test: Visual review; not floating too high, not touching.
- Edge: Subjective; get stakeholder sign-off if possible.

**Criterion 4: Flat and thermal at same base**
- Both flat and ThermalPlate workpieces use same workpiece group Y.
- Test: Toggle thermal on/off (if possible) or compare two sessions; metal base level should match.
- Edge: Flat has no displacement; thermal has displacement; base Y same.

**Criterion 5: Angle ring and grid aligned**
- Angle ring Y = workpiece_base_Y + small offset (e.g. 0.01) so it sits on metal.
- Grid Y = workpiece_base_Y (or floor level; document choice).
- Test: Visual inspection; ring and grid should look coherent with metal plane.
- Edge: ContactShadows may need same Y as metal surface.

---

### 5. Scope Boundaries

#### In Scope

1. **[ ]** Lower workpiece group Y in TorchWithHeatmap3D so metal surface (with max displacement) stays below weld pool.
   - **Why:** Core fix for clipping.
   - **User value:** Correct spatial relationship.
   - **Effort:** 1–2 hours.

2. **[ ]** Move angle guide ring, grid, ContactShadows to align with new workpiece Y.
   - **Why:** Visual consistency.
   - **User value:** Coherent scene.
   - **Effort:** ~0.5 hours.

3. **[ ]** Optionally reduce uMaxDisplacement in ThermalPlate if position-only fix is insufficient.
   - **Why:** Alternative or additive fix.
   - **User value:** Same as #1.
   - **Effort:** ~0.5 hours.

4. **[ ]** Add constants or comments documenting the Y-relationship.
   - **Why:** Maintainability.
   - **User value:** Indirect (fewer future bugs).
   - **Effort:** ~0.5 hours.

5. **[ ]** Manual and/or automated visual verification.
   - **Why:** Ensure fix works.
   - **User value:** Confidence.
   - **Effort:** 1–2 hours.

**Total effort:** ~4–6 hours (small to medium).

#### Out of Scope

1. **[ ]** Changing HeatmapPlate3D layout (different component; no reported clipping there).
   - **Why:** Separate coordinate system; user report is about TorchWithHeatmap3D.
   - **When:** If HeatmapPlate3D clipping is reported.
   - **Workaround:** N/A.

2. **[ ]** Making uMaxDisplacement configurable via TorchWithHeatmap3D props.
   - **Why:** YAGNI; position fix likely sufficient.
   - **When:** If we need per-session or per-view displacement tuning.
   - **Workaround:** Adjust constant in ThermalPlate.

3. **[ ]** Changing torch geometry (height, weld pool size).
   - **Why:** No user request; would have broader impact.
   - **When:** If product requests different torch proportions.
   - **Workaround:** Re-derive workpiece Y from new torch dimensions.

4. **[ ]** Adding automated visual regression tests (e.g. screenshot diff).
   - **Why:** Setup cost; manual verification may suffice for MVP.
   - **When:** If we add visual testing infrastructure.
   - **Workaround:** Manual check on deploy.

5. **[ ]** Fixing other bugs mentioned ("first off" suggests more) in this session.
   - **Why:** One issue per document.
   - **When:** Separate issues.
   - **Workaround:** Create follow-up issues.

#### Scope Justification

- Optimizing for: Correctness, minimal change, quick fix.
- Deferring: Configurability, visual regression automation, HeatmapPlate3D.
- What we're optimizing for: Speed to market, user impact, technical simplicity.

#### Scope Examples

1. **In scope:** Lower workpiece Y in TorchWithHeatmap3D. **Out of scope:** Change HeatmapPlate3D. **Why:** Different components; user report is replay/demo.
2. **In scope:** Reduce uMaxDisplacement if needed. **Out of scope:** Add prop to TorchWithHeatmap3D for displacement. **Why:** Constant change sufficient for now.
3. **In scope:** Align angle ring, grid, ContactShadows. **Out of scope:** Add new UI for position tuning. **Why:** No user request for controls.

---

### 6. Known Constraints & Context

#### Technical Constraints

**Must use:**
- React Three Fiber (@react-three/fiber)
- Three.js
- ThermalPlate (shared component)
- Same coordinate system as TorchViz3D (Y up)

**Must support:**
- Same browsers as current (Chrome, Firefox, Safari)
- Replay page, demo page
- Sessions with and without thermal data

**Performance constraints:**
- No new draw calls; position-only change
- No shader change (unless uMaxDisplacement adjusted)

#### Business Constraints

- **Timeline:** No hard deadline stated; prioritize when capacity allows.
- **Resources:** Single developer; ~4–6 hours budget.
- **Dependencies:** None blocking.

#### Design Constraints

- Must match existing industrial/cyan aesthetic (TorchViz3D, TorchWithHeatmap3D).
- No design mockup change; fix is invisible (correct spatial relationship).
- User expectation: "torch above metal" — we are restoring that.

#### Organizational Constraints

- Verification: Manual visual check; automated tests if they exist.
- Documentation: Update ThermalPlate parent-position guidance if we change recommended Y.
- CONTEXT.md: Update if we add constants or new patterns.

---

### 7. Related Context

#### Similar Features

**TorchViz3D:**
- Same torch geometry; flat workpiece at -0.6.
- Pattern: Workpiece, ring, grid at similar Y.
- Mistake to avoid: Don't break flat-metal alignment when fixing thermal.

**ThermalPlate:**
- Used by TorchWithHeatmap3D and HeatmapPlate3D.
- Pattern: Parent sets position; ThermalPlate provides mesh.
- Change uMaxDisplacement carefully — affects both.

**HeatmapPlate3D:**
- ThermalPlate at origin; different layout.
- No shared Y constants; fix in TorchWithHeatmap3D only.

#### Related Issues

- `.cursor/issues/unified-torch-heatmap-on-metal.md` — Original feature for unified torch + thermal; this bug is a regression or oversight in that work.
- `.cursor/plans/unified-torch-heatmap-replay-plan.md` — Implementation plan; positioning may not have been validated.

#### Past Attempts

- None documented for this specific clipping bug.
- Unified torch+heatmap was implemented; Y positioning may have been copied from TorchViz3D without accounting for vertex displacement.

#### External References

- Three.js: Right-handed, Y-up coordinate system.
- R3F: position prop in world units.

---

### 8. Open Questions & Ambiguities

**Question #1:** What exact gap (units) is "just above"?

- **Why unclear:** Subjective phrasing.
- **Impact if wrong:** Too small → might still clip in edge cases; too large → torch floats.
- **Who can answer:** User / product.
- **When needed:** Before implementation.
- **Current assumption:** 0.1–0.2 units.
- **Confidence:** Medium.
- **Risk:** Low.

**Question #2:** Should we prefer lowering metal vs reducing displacement?

- **Why unclear:** Both achieve the goal.
- **Impact if wrong:** Lowering metal might require moving more elements; reducing displacement might reduce warp visibility.
- **Who can answer:** Implementer + user preference.
- **When needed:** During implementation.
- **Current assumption:** Prefer lowering metal; keep displacement for visual effect.
- **Confidence:** Medium.
- **Risk:** Low.

**Question #3:** Should angle ring sit on metal surface or at a fixed floor?

- **Why unclear:** Ring at -0.59 is "on" metal at -0.6; if metal moves to -0.85, ring should move.
- **Impact if wrong:** Ring could float or sink.
- **Who can answer:** Implementer.
- **When needed:** During implementation.
- **Current assumption:** Move ring with metal (ring at workpiece_Y + 0.01).
- **Confidence:** High.
- **Risk:** Low.

**Question #4:** Does grid represent floor or metal plane?

- **Why unclear:** Convention not documented.
- **Impact if wrong:** Grid might not align with metal.
- **Current assumption:** Grid = metal plane level; move with workpiece.
- **Confidence:** Medium.
- **Risk:** Low.

**Question #5:** Should ContactShadows align with metal surface?

- **Why unclear:** Shadows typically cast onto "ground."
- **Current assumption:** Yes; move with metal.
- **Confidence:** Medium.
- **Risk:** Low.

**Question #6:** Do we need a shared constants file?

- **Why unclear:** Could inline or add constants.
- **Impact if wrong:** Without constants, future changes might break relationship.
- **Current assumption:** Add constants or clear comments.
- **Confidence:** High.
- **Risk:** Low.

**Question #7:** Will reducing uMaxDisplacement hurt HeatmapPlate3D?

- **Why unclear:** HeatmapPlate3D uses same ThermalPlate.
- **Impact if wrong:** Standalone heatmap might have less dramatic warp.
- **Current assumption:** Prefer position fix only; avoid changing uMaxDisplacement if possible.
- **Confidence:** Medium.
- **Risk:** Medium if we change it.

**Question #8:** Are there existing tests asserting Y positions?

- **Why unclear:** Need to grep.
- **Impact if wrong:** Tests might fail after change.
- **Current assumption:** Check before changing.
- **Confidence:** Low.
- **Risk:** Low.

**Question #9:** Should flat fallback use same base Y as thermal?

- **Why unclear:** Consistency vs. keeping flat at -0.6.
- **Current assumption:** Yes — same base Y for both; flat has no displacement.
- **Confidence:** High.
- **Risk:** Low.

**Question #10:** What about TorchViz3D — should it use same constants for consistency?

- **Why unclear:** TorchViz3D has no displacement; -0.6 works.
- **Impact if wrong:** TorchViz3D and TorchWithHeatmap3D could drift.
- **Current assumption:** If we add constants, TorchViz3D can use WORKPIECE_BASE_Y; for now, TorchWithHeatmap3D only.
- **Confidence:** Medium.
- **Risk:** Low.

**Blockers:** None. All questions can be resolved during implementation.
**Important:** #1 (gap size), #2 (lower vs reduce displacement).

---

### 9. Initial Risk Assessment

**Risk #1: Technical — Lowering metal too much causes torch to float**

- **Description:** Workpiece at -0.9 might look unnatural.
- **Probability:** 30%
- **Impact:** Medium
- **Consequence:** Users perceive torch as floating.
- **Mitigation:** Target gap 0.1–0.2; iterate if needed.
- **Contingency:** Reduce gap; get feedback.

**Risk #2: Technical — Reducing uMaxDisplacement hurts HeatmapPlate3D**

- **Description:** If we change uMaxDisplacement from 0.5 to 0.3.
- **Probability:** 50%
- **Impact:** Low
- **Consequence:** Standalone heatmap has less warp.
- **Mitigation:** Prefer position-only fix; avoid changing ThermalPlate if possible.
- **Contingency:** Add maxDisplacement prop to ThermalPlate; TorchWithHeatmap3D passes 0.3, HeatmapPlate3D keeps 0.5.

**Risk #3: Execution — Angle ring/grid misalignment**

- **Description:** Moving multiple elements introduces inconsistency.
- **Probability:** 20%
- **Impact:** Low
- **Consequence:** Ring or grid looks off.
- **Mitigation:** Derive all from WORKPIECE_BASE_Y.
- **Contingency:** Fine-tune offsets.

**Risk #4: User — "Just above" interpreted differently**

- **Description:** Stakeholder expects different gap.
- **Probability:** 40%
- **Impact:** Low
- **Consequence:** Request for tweak.
- **Mitigation:** Use 0.15 gap as default; easy to adjust.
- **Contingency:** Change constant; redeploy.

**Risk #5: Execution — Existing tests fail**

- **Description:** Tests assert specific positions.
- **Probability:** 25%
- **Impact:** Low
- **Consequence:** Update tests.
- **Mitigation:** Run tests before and after.
- **Contingency:** Update assertions.

**Risk #6: Technical — Shadow camera doesn't cover lowered metal**

- **Description:** Metal at -0.9 might be near shadow camera bottom.
- **Probability:** 15%
- **Impact:** Low
- **Consequence:** Shadows cut off.
- **Mitigation:** Shadow camera is ±10; -0.9 is well within.
- **Contingency:** Expand shadow camera if needed.

**Risk #7: Business — Scope creep (fix "several bugs")**

- **Description:** User said "first off" — more bugs may be reported.
- **Probability:** 60%
- **Impact:** Low
- **Consequence:** More issues to triage.
- **Mitigation:** This issue is scoped to Y-position only.
- **Contingency:** Create separate issues.

**Risk #8: Technical — Flat vs thermal metal "jump" when switching**

- **Description:** If we change base Y, switching thermal on/off might show a jump.
- **Probability:** 20%
- **Impact:** Low
- **Consequence:** Slight visual jump.
- **Mitigation:** Both use same base; thermal adds displacement only.
- **Contingency:** Acceptable for replay (thermal typically consistent per session).

**Top 3 Risks:**
1. Risk #2 — Avoid changing uMaxDisplacement; use position fix.
2. Risk #1 — Validate gap with visual check.
3. Risk #7 — Keep scope tight; defer other bugs.

---

### 10. Classification & Metadata

**Type:** Bug

**Priority:** P2 (Normal)

**Priority justification:** The metal heatmap is implemented and functional; the thermal coloring and warp effect work. The bug is visual — clipping breaks the "torch above metal" metaphor and can confuse users interpreting the 3D view. It affects replay and demo users whenever thermal data is present and temperatures are high. It is not blocking core functionality (replay still works; heatmap and angle data are correct), but it degrades UX and violates our goal of correctness and explainability in visualization. No production outage or data loss; no security impact. Response within 1 month is appropriate; it should be fixed before broader user rollout or investor demos.

**Effort:** Small (4–8 hours)

**Effort breakdown:**
- TorchWithHeatmap3D position changes: 1–2 hours
- ThermalPlate (if needed): 0.5 hours
- Constants/comments: 0.5 hours
- Testing and verification: 1–2 hours
- **Total:** ~4–6 hours

**Confidence:** High — root cause is clear; fix is localized.

**Category:** Frontend

**Tags:** user-facing, quick-win, high-impact, low-effort

---

### 11. Strategic Context

#### Product Roadmap Fit

- **Q1/Q2 Goal:** Reliable MVP for recording, replaying, and scoring.
  - **This issue supports:** Correctness and explainability in replay visualization.
  - **Contribution:** ~5% toward goal (one of many quality improvements).
  - **Metric impact:** User trust in 3D view.

- **Product vision:** Safety-adjacent industrial welding — correctness, determinism, explainability.
  - **This issue advances:** Visualization correctness.
  - **Strategic importance:** Medium.

#### Capabilities Unlocked

- Correct 3D visualization supports future features (e.g. VR, training simulations).
- No new capabilities; restores intended behavior.

#### User Feedback

- User (developer) reported: "metal is too high... clipping onto the torch."
- No broader user feedback documented; internal discovery.
- **How this resolves:** Spatial relationship corrected.

#### User Impact

- **User segment:** Replay and demo users (internal + external).
- **Benefit:** Clear "torch above metal" view; no visual confusion.
- **Value:** Improved interpretability; supports training and quality review use cases.

#### Technical Impact

- **Code health:** Improves correctness; optional constants improve maintainability.
- **Technical debt:** Reduces (fixes oversight from unified torch+heatmap implementation).
- **Maintainability:** Better with documented constants.

---

## 🧠 THINKING CHECKPOINT #2

### Self-Critique

1. **Would a new team member understand?** Yes — numeric analysis (Y values) is clear; coordinate system explained.
2. **Can someone explore without questions?** Mostly — exact gap and preference (lower vs reduce) could use decisions.
3. **Quantification:** Y values (-0.6, -0.2, -0.1), displacement 0.5, effort 4–8h, risks with probabilities.
4. **Evidence:** Code snippets, file paths, line numbers.
5. **Failure:** 8 risks; mitigation and contingency for each.
6. **Bigger picture:** Connected to product vision, unified torch+heatmap feature.
7. **Detail:** ~3500 words; sections completed.
8. **Assumptions:** 5 documented with verification and impact.

### Quality Metrics

| Metric | Minimum | Count | Pass |
|--------|---------|-------|------|
| Total words | 3,000 | ~3,500 | ✅ |
| Pre-thinking words | 500 | ~600 | ✅ |
| Acceptance criteria | 12 | 12 | ✅ |
| Open questions | 10 | 10 | ✅ |
| Risks | 8 | 8 | ✅ |
| Similar features | 3 | 5 | ✅ |
| Related issues | 2 | 2 | ✅ |
| Assumptions | 5 | 5 | ✅ |
| Time (minutes) | 45 | N/A | — |
| Evidence | 5 | 5+ | ✅ |

---

## After Issue Creation

**Immediate next steps:**
1. [ ] Confirm gap preference ("just above" = 0.1–0.2 units) with stakeholder if available
2. [ ] Decide: position-only vs. position + uMaxDisplacement
3. [ ] Proceed to implementation (or Exploration phase if desired)
4. [ ] Create separate issues for any additional bugs ("first off" suggests more)

**Then move to:**
- **Phase 2: Explore Feature** — If deep technical exploration needed (e.g. constant extraction, HeatmapPlate3D impact).
- **Or:** Proceed directly to implementation — fix is well-scoped.

---

**Quality gate:** All checkboxes addressed. Issue is complete and actionable.
