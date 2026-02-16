# Metal Heatmap Y-Position Clipping — Exploration Output

**Issue:** `.cursor/issues/metal-heatmap-y-position-clipping-torch.md`  
**Date:** 2025-02-16  
**Status:** Ready for planning

---

## MANDATORY PRE-EXPLORATION THINKING SESSION

### A. Exploration Scope Understanding

**1. Core technical challenge**
- **In one sentence:** The metal workpiece base Y (-0.6) plus maximum vertex displacement (0.5) yields a metal surface at Y=-0.1, which is above the weld pool center at Y=-0.2, causing visual clipping.
- **Why it's hard:** We must satisfy both "metal never clips torch" and "thermal bulge remains visible," with multiple dependent elements (workpiece, angle ring, grid, ContactShadows) that must stay visually aligned.
- **What makes it non-trivial:** TorchViz3D and TorchWithHeatmap3D share geometry conventions; any change must not break the flat-metal case or the thermal case. HeatmapPlate3D shares ThermalPlate (uMaxDisplacement); changing displacement affects it.

**2. Major unknowns**
- Unknown #1: Exact gap (units) that reads as "torch just above metal" — subjective.
- Unknown #2: Whether reducing uMaxDisplacement will make thermal warp barely visible.
- Unknown #3: Whether angle ring/grid should represent "floor" or "metal plane" — affects which elements move.
- Unknown #4: Shadow camera bounds — will lowered metal stay in shadow coverage?
- Unknown #5: Do any tests assert specific Y positions? (Verified: No.)

**3. Questions that must be answered**
- Q1: What workpiece_base_Y satisfies metal_max_surface < weld_pool_Y with acceptable gap?
- Q2: Lower metal only vs. lower + reduce displacement — which?
- Q3: Angle ring Y — move with workpiece or stay fixed?
- Q4: Grid Y — metal plane or floor?
- Q5: ContactShadows Y — align with metal?
- Q6: Extract constants or inline?
- Q7: Will uMaxDisplacement change affect HeatmapPlate3D?
- Q8: Same base Y for flat and thermal (consistency)?
- Q9: TorchViz3D — use shared constants for consistency?
- Q10: Exact gap target — 0.1? 0.15? 0.2?

**4. What could we get wrong**
- Mistake #1: Lower metal too much → torch appears to float unrealistically.
- Mistake #2: Reduce displacement too much → thermal warp invisible.
- Mistake #3: Move angle ring but leave grid at old Y → visual inconsistency.
- Mistake #4: Use different base Y for flat vs thermal → jump when switching.
- Mistake #5: Change uMaxDisplacement globally → HeatmapPlate3D warp changes.

### B. Approach Brainstorm

**Approach A: Lower workpiece only**
- **Description:** Change workpiece group Y from -0.6 to -0.85 (or -0.9). Keep uMaxDisplacement=0.5. Move angle ring, grid, ContactShadows to align.
- **Gut feeling:** Good
- **First concern:** Might look like torch floating if gap too large.

**Approach B: Reduce displacement only**
- **Description:** Keep workpiece at -0.6. Reduce uMaxDisplacement from 0.5 to 0.25–0.35 so max surface ≤ -0.2.
- **Gut feeling:** Uncertain
- **First concern:** Affects HeatmapPlate3D; thermal warp may become barely visible.

**Approach C: Combined (lower + reduce)**
- **Description:** Workpiece at -0.75, uMaxDisplacement 0.35. Max surface = -0.4, gap ≈ 0.2.
- **Gut feeling:** Good
- **First concern:** Two changes; uMaxDisplacement still affects HeatmapPlate3D.

**Approach D: Add maxDisplacement prop to ThermalPlate**
- **Description:** ThermalPlate accepts optional maxDisplacement; TorchWithHeatmap3D passes 0.3, HeatmapPlate3D keeps 0.5.
- **Gut feeling:** Good for isolation
- **First concern:** Extra API surface; YAGNI if position fix suffices.

### C. Constraint Mapping

**Technical constraints:**
1. React Three Fiber / Three.js — position in world units.
2. ThermalPlate shared by TorchWithHeatmap3D and HeatmapPlate3D.
3. Torch geometry fixed (weld pool at -0.6 relative to torch group at 0.4).
4. Same coordinate system as TorchViz3D (Y up).
5. Max 2 Canvas per page (WebGL limits).

**How constraints shape solution:**
- Constraint "ThermalPlate shared" eliminates Approach B/C if we change uMaxDisplacement globally without prop — use Approach A or D.
- Constraint "Torch geometry fixed" means weld pool Y = 0.4 - 0.6 = -0.2; metal must stay below.

### D. Risk Preview

1. **Metal lowered too much → torch floats**
   - Why scary: Users may perceive scene as wrong.
   - Likelihood: 30%
   - Could kill project: No

2. **uMaxDisplacement change breaks HeatmapPlate3D**
   - Why scary: Standalone heatmap view loses warp effect.
   - Likelihood: 50% if we change it
   - Could kill project: No

3. **Angle ring / grid misalignment**
   - Why scary: Scene looks incoherent.
   - Likelihood: 20%
   - Could kill project: No

---

## 1. Research Existing Solutions

### A. Internal Codebase Research

**Similar Implementation #1: TorchViz3D**
- **Location:** `my-app/src/components/welding/TorchViz3D.tsx`
- **What it does:** 3D torch + flat gray workpiece (no thermal). Same torch geometry.
- **Key positions:** Torch group 0.4; weld pool -0.6 rel → world -0.2; workpiece -0.6; angle ring -0.59; grid -0.6; ContactShadows -0.59.
- **What we can reuse:** Coordinate convention. TorchViz3D has no displacement, so -0.6 works.
- **What we should avoid:** Copying -0.6 for thermal case without accounting for displacement.

**Similar Implementation #2: TorchWithHeatmap3D**
- **Location:** `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
- **What it does:** Unified torch + ThermalPlate (or flat metal). Uses same positions as TorchViz3D for workpiece, ring, grid, shadows.
- **Key code:**
```tsx
<group position={[0, -0.6, 0]}>
  {hasThermal ? <ThermalPlate ... /> : <mesh ... />}
</group>
<mesh ... position={[0, -0.59, 0]}>  // angle ring
<gridHelper ... position={[0, -0.6, 0]} />
<ContactShadows position={[0, -0.59, 0]} />
```
- **Patterns:** Workpiece group contains ThermalPlate; ThermalPlate has vertex displacement. Bug: no offset for max displacement.
- **What we can reuse:** Structure. Change only Y values.
- **Edge cases NOT handled:** metal_surface_max_Y < weld_pool_Y constraint.

**Similar Implementation #3: HeatmapPlate3D**
- **Location:** `my-app/src/components/welding/HeatmapPlate3D.tsx`
- **What it does:** Standalone thermal plate; ThermalPlate at origin; TorchIndicator at Y=2.
- **Layout:** No shared Y with TorchWithHeatmap3D. ThermalPlate at [0,0,0]; indicator above.
- **What we can reuse:** ThermalPlate component. No clipping in this layout.
- **What we should avoid:** Changing uMaxDisplacement if it would reduce HeatmapPlate3D warp.

**Similar Implementation #4: ThermalPlate**
- **Location:** `my-app/src/components/welding/ThermalPlate.tsx`
- **What it does:** 100×100 plane, vertex displacement by temperature, temp→color.
- **Key:** `uMaxDisplacement: { value: 0.5 }` (line 78). Parent sets position.
- **What we can reuse:** Shader logic unchanged. Fix via parent position or optional prop.
- **What we should avoid:** Changing hardcoded 0.5 without considering HeatmapPlate3D.

### B. Pattern Analysis

**Pattern #1: Parent-positions-ThermalPlate**
- **Used in:** TorchWithHeatmap3D, HeatmapPlate3D
- **Description:** ThermalPlate has no position prop; parent group positions it.
- **When to use:** Any ThermalPlate usage.
- **Applicability:** High — fix belongs in TorchWithHeatmap3D parent.

**Pattern #2: Derived Y values**
- **Used in:** TorchViz3D, TorchWithHeatmap3D (implicit)
- **Description:** Angle ring at workpiece_Y + 0.01 (slightly above metal). Grid at workpiece_Y. ContactShadows at metal surface.
- **Applicability:** High — when we change workpiece Y, derive ring/grid/shadows from it.

**Pattern #3: Single source of geometry constants**
- **Description:** Extract WORKPIECE_BASE_Y, WELD_POOL_CENTER_Y, etc. to constants.
- **Applicability:** Medium — improves maintainability; not required for minimal fix.

### C. External Research

**Research Query #1:** "Three.js plane geometry vertex displacement shader normal direction"
- **Key insights:** PlaneGeometry default normal is +Y; rotation [-π/2,0,0] makes it horizontal with normal +Z (up in view). Displacement along normal moves vertices up.
- **Applicability:** High — confirms our understanding.

**Research Query #2:** "R3F ContactShadows position"
- **Key insights:** ContactShadows renders a soft shadow plane at the given position. Should align with receiving surface (metal).
- **Applicability:** High — move ContactShadows with metal.

**No new libraries needed** — position-only change.

---

## 2. Prototype Critical Paths

### A. Critical Paths Identified

1. **CP1: Math validation** — workpiece_base_Y + uMaxDisplacement < weld_pool_Y
   - Confidence: High
   - Need to prototype: Yes (validate numbers)

2. **CP2: Visual gap** — 0.1–0.2 units reads as "just above"
   - Confidence: Medium
   - Need to prototype: Yes (manual check after fix)

3. **CP3: HeatmapPlate3D unaffected** — if we change uMaxDisplacement
   - Confidence: Medium
   - Need to prototype: N/A if we don't change it

4. **CP4: Angle ring alignment** — ring at base_Y + 0.01
   - Confidence: High
   - Need to prototype: No

5. **CP5: Shadow camera** — metal at -0.85 within ±10 bounds
   - Confidence: High
   - Need to prototype: No (math: -0.85 >> -10)

### B. Prototype: Math Validation

**Purpose:** Verify fix values satisfy constraint.

**Constraint:** metal_surface_max_Y < weld_pool_center_Y - gap

**Given:**
- weld_pool_center_Y = 0.4 - 0.6 = -0.2
- uMaxDisplacement = 0.5 (unchanged)
- Target gap: 0.1–0.2 units

**Option 1: Lower workpiece only**
- metal_surface_max_Y = workpiece_base_Y + 0.5
- Require: workpiece_base_Y + 0.5 ≤ -0.2 - 0.15 = -0.35
- So: workpiece_base_Y ≤ -0.85
- **Choice: workpiece_base_Y = -0.85**
- Max surface = -0.85 + 0.5 = **-0.35**
- Gap = -0.2 - (-0.35) = **0.15** ✓

**Option 2: Lower + reduce displacement**
- workpiece_base_Y = -0.75, uMaxDisplacement = 0.35
- Max surface = -0.75 + 0.35 = **-0.4**
- Gap = **0.2** ✓
- **Downside:** Changes ThermalPlate; affects HeatmapPlate3D.

**Prototype result:** Option 1 (lower only) is sufficient. No ThermalPlate change.

**Angle ring, grid, ContactShadows:** All move to align with new metal surface:
- workpiece_base_Y = -0.85
- angle_ring_Y = -0.85 + 0.01 = **-0.84**
- grid_Y = **-0.85**
- ContactShadows_Y = **-0.84** (slightly above metal for shadow plane)

---

## 3. Evaluate Approaches

### Approach Comparison Matrix

| Criterion            | Weight | A: Lower only | B: Reduce disp | C: Combined | D: Prop |
|---------------------|--------|---------------|----------------|-------------|---------|
| Implementation       | 20%    | Low (5)       | Medium (4)     | Medium (3)   | High (2) |
| HeatmapPlate3D safe  | 20%    | Yes (5)       | No (2)         | No (2)      | Yes (5) |
| Maintainability      | 15%    | Good (4)      | Good (4)       | Good (4)    | Good (4) |
| Thermal warp visible | 15%    | Yes (5)       | Maybe (3)      | Maybe (3)   | Yes (5) |
| Risk                 | 15%    | Low (5)       | Medium (3)     | Medium (3)   | Low (4) |
| Reversibility        | 15%    | Easy (5)      | Easy (5)       | Medium (4)  | Easy (5) |
| **TOTAL**            | 100%   | **4.6**       | 3.4            | 3.1         | 3.9     |

**Winner:** Approach A (lower workpiece only)

**Final recommendation:** Lower workpiece group Y from -0.6 to -0.85. Move angle ring to -0.84, grid to -0.85, ContactShadows to -0.84. Do NOT change uMaxDisplacement. This satisfies the constraint (max surface -0.35 < weld pool -0.2) with ~0.15 gap, avoids HeatmapPlate3D impact, and keeps thermal warp fully visible.

---

## 4. Architectural Decisions

### Decision #1: Primary Approach
- **Choice:** Lower workpiece group Y only; do not change uMaxDisplacement.
- **Rationale:** Satisfies constraint; zero impact on HeatmapPlate3D; thermal warp unchanged; minimal change surface.

### Decision #2: Constants
- **Choice:** Extract to `my-app/src/constants/welding3d.ts` — WORKPIECE_BASE_Y, ANGLE_RING_OFFSET, etc.
- **Rationale:** Prevents future drift; documents constraint (metal_max < weld_pool - gap).

### Decision #3: Flat vs thermal base Y
- **Choice:** Same base Y (-0.85) for both flat and thermal. Flat has no displacement so stays at -0.85.
- **Rationale:** No jump when switching; consistent metal surface level.

### Decision #4: TorchViz3D
- **Choice:** Optionally use shared WORKPIECE_BASE_Y from constants for TorchViz3D. Scope: TorchWithHeatmap3D only for this fix; TorchViz3D can be updated separately for consistency.
- **Rationale:** Minimal scope; TorchViz3D has no displacement so -0.6 works. Updating TorchViz3D to -0.85 would make flat workpiece lower — acceptable for consistency but out of scope for bug fix.

### Decision #5: Angle ring offset
- **Choice:** angle_ring_Y = workpiece_base_Y + 0.01 (-0.84 when base is -0.85)
- **Rationale:** Ring sits slightly on metal; matches current -0.59 vs -0.6 relationship.

### Decision #6: Grid position
- **Choice:** grid_Y = workpiece_base_Y (-0.85)
- **Rationale:** Grid represents metal/floor plane; align with workpiece.

### Decision #7: ContactShadows position
- **Choice:** Same as angle ring (workpiece_base_Y + 0.01 = -0.84)
- **Rationale:** Shadows cast onto metal surface; align with receiving plane.

### Decision #8: ThermalPlate
- **Choice:** No changes to ThermalPlate. Keep uMaxDisplacement 0.5. Update JSDoc example position from [0,-0.6,0] to note parent responsibility.
- **Rationale:** Fix is in parent; ThermalPlate API unchanged.

---

## 5. Document Edge Cases

### Data Edge Cases
- Empty/undefined frames → flat metal at -0.85; no displacement; no clip. ✓
- Null frame → ThermalPlate handles; ambient fill. ✓
- Max temp 500°C at center → max displacement; our fix ensures no clip. ✓

### User Interaction
- Rapid scrubbing → thermal data changes; displacement updates; no transient clip with fix. ✓
- Torch angle 30°–60° → weld pool center Y unchanged; fix holds. ✓

### State
- Switch thermal on/off (e.g. session change) → same base Y; no jump. ✓

### Performance
- No new draw calls; position-only. ✓
- Shadow camera ±10; -0.85 well within bounds. ✓

### Priority edge cases (must handle)
1. Max temp at center — fixed by math (base -0.85 + 0.5 = -0.35 < -0.2)
2. Flat vs thermal consistency — same base Y
3. Angle ring alignment — derived from base Y
4. Grid alignment — same as base Y
5. ContactShadows alignment — same as ring

---

## 6. Risk Analysis

### Technical Risks

**R1: Torch appears to float**
- Probability: 30%
- Impact: Medium
- Mitigation: Gap 0.15 is "just above"; iterate if feedback says too high.

**R2: HeatmapPlate3D affected**
- Probability: 0% (we don't change uMaxDisplacement)
- Mitigation: N/A

**R3: Angle ring/grid misalignment**
- Probability: 20%
- Mitigation: Derive all from WORKPIECE_BASE_Y; single change propagates.

**R4: Existing tests break**
- Probability: 0% (tests don't assert Y positions; verified)
- Mitigation: Run npm test after change.

**R5: Shadow camera doesn't cover**
- Probability: 0% (-0.85 >> -10)
- Mitigation: N/A

### Risk Matrix
- P0: None
- P1: R1 (torch floats) — monitor; easy to tweak
- P2: R3 (alignment) — mitigated by constants

---

## Exploration Summary

### TL;DR

The metal heatmap clips through the torch because workpiece base Y (-0.6) plus max vertex displacement (0.5) yields surface Y=-0.1, above weld pool center Y=-0.2. Exploration validated the fix: lower workpiece group Y to -0.85 and move angle ring, grid, and ContactShadows to align. Do NOT change uMaxDisplacement (avoids HeatmapPlate3D impact). Extract constants for maintainability. Approach: position-only in TorchWithHeatmap3D. Confidence: High. Ready for planning.

### Recommended Approach

**Name:** Lower workpiece position only

**Description:** Change workpiece group Y from -0.6 to -0.85 in TorchWithHeatmap3D; move angle ring to -0.84, grid to -0.85, ContactShadows to -0.84. Extract constants.

**Why:**
1. Satisfies metal_surface_max < weld_pool_Y with ~0.15 gap.
2. No ThermalPlate/HeatmapPlate3D impact.
3. Thermal warp remains fully visible.
4. Minimal change; easy to revert.

**Key decisions:**
1. WORKPIECE_BASE_Y = -0.85
2. ANGLE_RING_Y = WORKPIECE_BASE_Y + 0.01 = -0.84
3. Same base Y for flat and thermal
4. No uMaxDisplacement change

**Major risks:**
1. Torch may appear to float (mitigation: 0.15 gap is standard "just above"; iterate)
2. Alignment drift (mitigation: constants)

### Files to Create/Modify

**New files:**
1. `my-app/src/constants/welding3d.ts` — WORKPIECE_BASE_Y, WELD_POOL_REL_Y, ANGLE_RING_OFFSET, etc.

**Files to modify:**
1. `my-app/src/components/welding/TorchWithHeatmap3D.tsx` — import constants; replace -0.6, -0.59 with constant references
2. `my-app/src/components/welding/ThermalPlate.tsx` — JSDoc update (optional); parent position example

### Critical Path

1. Create welding3d.ts with constants
2. Update TorchWithHeatmap3D SceneContent to use constants
3. Run tests; manual visual verify on replay/demo
4. Update ThermalPlate JSDoc if needed

### Effort Estimate

- Constants file: 0.5 h
- TorchWithHeatmap3D changes: 1 h
- Testing/verification: 1 h
- **Total: ~2.5–3 hours** (issue estimated 4–8 h; exploration shows simpler)

### Success Criteria

- [ ] Metal surface (max displacement) never clips torch
- [ ] Torch appears "just above" metal
- [ ] Angle ring, grid, ContactShadows aligned
- [ ] Flat and thermal at same base level
- [ ] HeatmapPlate3D unchanged
- [ ] All tests pass

---

## Quality Metrics

| Metric                       | Minimum | Actual | Pass |
|-----------------------------|---------|--------|------|
| Similar implementations     | 3       | 4      | ✅   |
| Approaches evaluated        | 3       | 4      | ✅   |
| Architectural decisions     | 8       | 8      | ✅   |
| Edge cases documented       | 5+      | 5+     | ✅   |
| Risks identified            | 5+      | 5+     | ✅   |
| Ready for planning          | Yes     | Yes    | ✅   |
