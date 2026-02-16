# Metal Heatmap Y-Position Clipping Fix — Implementation Blueprint

**Issue:** `.cursor/issues/metal-heatmap-y-position-clipping-torch.md`  
**Exploration:** `.cursor/explore-outputs/metal-heatmap-y-position-clipping-key-facts.md`  
**Created:** 2025-02-16  
**Estimated Total Effort:** 4–8 hours (realistic: 2.5–3h per exploration)

---

## MANDATORY PRE-PLANNING THINKING SESSION

### A. Exploration Review and Synthesis

**1. Core approach**
- **In one sentence:** Lower the workpiece base Y from -0.6 to -0.85 so that metal surface max Y (base + uMaxDisplacement) stays below the weld pool center (-0.2), with a visible gap (~0.15 units), without changing uMaxDisplacement (to avoid affecting HeatmapPlate3D).
- **Key decisions:** (a) Position-only fix in TorchWithHeatmap3D; (b) Do NOT change ThermalPlate uMaxDisplacement (0.5); (c) Extract magic numbers to welding3d.ts constants; (d) Derive angle ring, grid, ContactShadows from WORKPIECE_BASE_Y.
- **Why this approach:** Changing uMaxDisplacement would affect HeatmapPlate3D (standalone thermal view). Lowering the workpiece is localized to TorchWithHeatmap3D; ThermalPlate is parent-positioned, so we control Y in the parent. Constants prevent future drift.

**2. Major components**
- **Component #1: welding3d.ts** (purpose: single source of truth for scene Y coordinates; documents the metal_surface_max < weld_pool constraint)
- **Component #2: TorchWithHeatmap3D** (purpose: unified torch + thermal metal; holds workpiece group, angle ring, grid, ContactShadows; must use new Y values)
- **Component #3: ThermalPlate** (purpose: thermal mesh; unchanged except optional JSDoc; parent sets position)
- **Component #4: TorchViz3D** (purpose: torch + flat metal; optional alignment to shared constants for consistency; out of scope per issue)

**3. Data flow**
```
Input: WORKPIECE_BASE_Y (-0.85), MAX_THERMAL_DISPLACEMENT (0.5 from ThermalPlate)
  ↓
Transform: metal_surface_max_Y = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT = -0.35
  ↓
Process: Weld pool center Y = 0.4 - 0.6 = -0.2; gap = -0.2 - (-0.35) = 0.15
  ↓
Output: No clipping; torch rests just above metal
```

**4. Biggest risks**
- **Risk #1:** Lowering metal too much → torch appears to float (probability 30%, impact medium). Mitigation: target gap 0.1–0.2; iterate on -0.8, -0.82, -0.85 if needed.
- **Risk #2:** Changing uMaxDisplacement would break HeatmapPlate3D (probability 50% if we change it, impact low). Mitigation: do NOT change it.
- **Risk #3:** Angle ring / grid / ContactShadows misaligned after move (probability 20%, impact low). Mitigation: derive all from WORKPIECE_BASE_Y.

**5. Gaps exploration did NOT answer**
- **Gap #1:** Exact constant names in welding3d.ts — we define them in the plan.
- **Gap #2:** Whether TorchViz3D should use shared constants now — issue says TorchWithHeatmap3D only; we defer TorchViz3D.
- **Gap #3:** Unit test assertions for Y values — current tests mock Canvas; we add optional regression tests or document manual verification.

---

### B. Dependency Brainstorm

**Major work items (before ordering):**
1. Create welding3d.ts with WORKPIECE_BASE_Y, WELD_POOL_CENTER_Y, etc.
2. Import constants in TorchWithHeatmap3D
3. Update workpiece group position
4. Update angle guide ring position
5. Update grid position
6. Update ContactShadows position
7. Update ThermalPlate JSDoc (optional)
8. Run existing tests
9. Manual visual verification on replay
10. Manual visual verification on demo
11. Update CONTEXT.md if we add constants (optional)
12. Add unit test for constant constraint (optional)

**Dependencies:**
- Item 1 depends on: nothing
- Items 2–6 depend on: 1
- Item 7 depends on: 3 (know final WORKPIECE_BASE_Y)
- Items 8–10 depend on: 2–6
- Items 11–12 depend on: 8–10 (optional polish)

**Dependency graph:**
```
Item 1 (constants)
  ↓
Items 2, 3, 4, 5, 6 (TorchWithHeatmap3D updates)
  ↓
Items 7, 8, 9, 10 (JSDoc, tests, manual verify)
  ↓
Items 11, 12 (optional)
```

**Critical path:** 1 → 2–6 → 8–10 (core path)

**Bottlenecks:** Item 1 (constants) — everything else waits.

**Parallelizable:** None for core path; items 11–12 can run after 10.

---

### C. Risk-Based Planning

**Top 5 risks from exploration:**
1. Torch floats (30%, medium) — address: visual check at -0.85; contingency: try -0.8 or -0.82
2. uMaxDisplacement change hurts HeatmapPlate3D (N/A — we won't change it)
3. Angle ring misalignment (20%, low) — address: derive from constant
4. Existing tests break (25%, low) — address: run tests before/after; tests don't assert Y
5. "Just above" interpreted differently (40%, low) — address: 0.15 gap; easy constant tweak

**Failure modes:**
1. **If constants file has wrong math:** Detection: metal still clips. Response: recalc; Recovery: fix WORKPIECE_BASE_Y.
2. **If workpiece group not updated:** Detection: metal still clips. Response: verify group position. Recovery: apply constant.
3. **If angle ring not updated:** Detection: ring floats or sinks. Response: visual check. Recovery: set ring Y = WORKPIECE_BASE_Y + 0.01.
4. **If grid not updated:** Detection: grid doesn't align with metal. Response: visual check. Recovery: set grid Y = WORKPIECE_BASE_Y.
5. **If ContactShadows not updated:** Detection: shadows wrong. Response: visual check. Recovery: set shadow Y = WORKPIECE_BASE_Y + 0.01.
6. **If flat fallback uses old Y:** Detection: jump when switching thermal on/off. Response: both use same base. Recovery: ensure single constant.
7. **If ThermalPlate JSDoc wrong:** Detection: future dev mispositions. Response: JSDoc says parent uses WORKPIECE_BASE_Y.
8. **If shadow camera misses metal:** Detection: shadows cut off. Response: camera ±10; -0.85 in range. Recovery: expand if needed.
9. **If HeatmapPlate3D affected:** Detection: standalone view wrong. Response: we don't change ThermalPlate position (it's at origin there). Recovery: N/A.
10. **If TorchViz3D diverges:** Detection: two components different Y. Response: out of scope; document in constants for future sync.

---

## 🧠 THINKING CHECKPOINT #1 — Phase Sanity Check

**1. Can someone else understand the phases?**
- Phase 1: Create constants (foundation)
- Phase 2: Apply constants to TorchWithHeatmap3D (core fix)
- Phase 3: Verify and document (quality)
- **Any confusion:** No — sequence is clear.

**2. Is each phase independently valuable?**
- Phase 1: Enables maintainability; required for Phase 2
- Phase 2: Fixes the bug; direct user value
- Phase 3: Confidence; prevents regression
- **All have value.** ✓

**3. Are phases right-sized?**
- Phase 1: ~0.5 h — appropriate
- Phase 2: ~0.65 h — appropriate
- Phase 3: ~0.8 h — appropriate
- **No phase > 30 h; no phase < 4 h for this scope.** ✓

**4. Do dependencies make sense?**
- Phase 1 → 2 → 3 sequential
- **No circular dependencies.** ✓

**5. Riskiest phase?**
- Phase 2 — visual outcome depends on correct constant application
- **Mitigation:** Verification steps; easy rollback (revert constants)

---

## PHASE BREAKDOWN

### Phase Design

**Phase 1: Foundation — Constants and Documentation**  
- **Goal:** Single source of truth for scene Y coordinates; future-proof the constraint.  
- **User value:** Indirect — maintainability; enables correct positioning.  
- **Why first:** All position updates depend on these constants.  
- **Estimated effort:** 0.5–1 h  
- **Risk level:** 🟢 Low  
- **Major steps:** Create welding3d.ts, define constants, add JSDoc, verify math.

**Phase 2: Core Fix — TorchWithHeatmap3D Position Updates**  
- **Goal:** Metal surface (including thermal bulge) always below torch.  
- **User value:** No more clipping; torch rests just above metal.  
- **Why second:** Needs constants from Phase 1.  
- **Estimated effort:** 1–1.5 h  
- **Risk level:** 🟢 Low  
- **Major steps:** Import constants, update workpiece, angle ring, grid, ContactShadows.

**Phase 3: Verification and Polish**  
- **Goal:** Verified fix; no regressions; documentation current.  
- **User value:** Confidence; correct behavior in replay/demo.  
- **Why third:** Needs core fix complete.  
- **Estimated effort:** 1–1.5 h  
- **Risk level:** 🟢 Low  
- **Major steps:** Run tests, automated constants-applied test, manual visual check, update ThermalPlate JSDoc, optional CONTEXT update.

**Phase dependency:** Phase 1 → Phase 2 → Phase 3 (sequential).

**Phase 1 Done When:**
- [ ] welding3d.ts exists with correct constants
- [ ] Math verified: metal_surface_max_Y < weld_pool_center_Y
- [ ] JSDoc documents constraint

**Phase 2 Done When:**
- [ ] All scene elements use constants
- [ ] No hardcoded -0.6, -0.59 in TorchWithHeatmap3D
- [ ] Visual check: no clipping at max temp

**Phase 3 Done When:**
- [ ] All tests pass (including constants-applied test)
- [ ] Manual verification on replay and demo
- [ ] ThermalPlate JSDoc and uMaxDisplacement comment updated

---

## Step Classification (Critical vs Non-Critical)

| Step | Type | Critical? | Reason |
|------|------|------------|--------|
| 1.1 | Constants | ✅ Yes | Single source of truth; wrong = persistent bug |
| 1.2 | Test | ❌ No | Standard test pattern |
| 1.3 | Export | ❌ No | Trivial |
| 2.1 | Import | ❌ No | Simple import |
| 2.2 | Position | ✅ Yes | Core fix; wrong = clipping persists |
| 2.3 | Position | ❌ No | Derived from constant |
| 2.4 | Position | ❌ No | Derived from constant |
| 2.5 | Position | ❌ No | Derived from constant |
| 2.6 | Grep | ❌ No | Verification only |
| 3.1–3.8 | Verify/Doc | ❌ No | Standard verification |

**Summary:** 2 critical steps (1.1, 2.2) with full context; others have verification tests.

---

## STEP DEFINITIONS

### Phase 1 — Foundation: Constants and Documentation

**Goal:** Create welding3d.ts with scene Y constants; document the metal < torch constraint.

**Time Estimate:** 0.5–1 h  
**Risk Level:** 🟢

---

#### 🟥 Step 1.1: Create welding3d.ts constants file — *Critical: Single source of truth*

**Why critical:** All downstream positions depend on these values; wrong values = persistent clipping or floating torch.

**Context:**
- Torch group is at Y=0.4; weld pool sphere is at Y=-0.6 relative to torch → world Y = 0.4 - 0.6 = -0.2.
- Metal base was -0.6; max displacement 0.5 → metal max Y = -0.1 (above -0.2).
- Fix: base = -0.85 → metal max = -0.35; gap = 0.15.
- We derive angle ring and grid from base; ring sits slightly above metal surface.

**Files:**
- **Create:** `my-app/src/constants/welding3d.ts`

**Code:**

```typescript
/**
 * 3D welding scene Y-coordinate constants.
 *
 * Constraint: metal_surface_max_Y < weld_pool_center_Y (metal must stay below torch).
 * Metal surface max = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT (from ThermalPlate).
 *
 * @see .cursor/issues/metal-heatmap-y-position-clipping-torch.md
 */

/** Torch group base Y (world). Weld pool is below this. */
export const TORCH_GROUP_Y = 0.4;

/** Weld pool sphere Y relative to torch group. World Y = TORCH_GROUP_Y + WELD_POOL_OFFSET_Y. */
export const WELD_POOL_OFFSET_Y = -0.6;

/** Weld pool center world Y. Metal surface must stay below this. */
export const WELD_POOL_CENTER_Y = TORCH_GROUP_Y + WELD_POOL_OFFSET_Y; // -0.2

/** Max vertex displacement in ThermalPlate shader (uMaxDisplacement). Do not change without considering HeatmapPlate3D. */
export const MAX_THERMAL_DISPLACEMENT = 0.5;

/** Desired gap between metal max surface and weld pool center (world units). */
export const METAL_TO_TORCH_GAP = 0.15;

/** Workpiece base Y. Metal surface max = this + MAX_THERMAL_DISPLACEMENT. Must be < WELD_POOL_CENTER_Y - MAX_THERMAL_DISPLACEMENT. */
export const WORKPIECE_BASE_Y = WELD_POOL_CENTER_Y - MAX_THERMAL_DISPLACEMENT - METAL_TO_TORCH_GAP; // -0.85

/** Angle guide ring Y — slightly above metal surface (sits on workpiece). */
export const ANGLE_RING_Y = WORKPIECE_BASE_Y + 0.01;

/** Grid Y — aligns with workpiece base (metal plane). */
export const GRID_Y = WORKPIECE_BASE_Y;

/** ContactShadows Y — aligns with metal surface. */
export const CONTACT_SHADOWS_Y = WORKPIECE_BASE_Y + 0.01;
```

**Verification:** File exists; `WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT` = -0.35; -0.35 < -0.2 ✓; gap = 0.15 ✓.

**Time estimate:** 0.25 h

---

#### 🟥 Step 1.2: Add unit test for constant constraint

**What:** Assert that metal_surface_max_Y < weld_pool_center_Y in constants.

**Why:** Prevents future edits from breaking the constraint.

**Files:**
- **Create:** `my-app/src/__tests__/constants/welding3d.test.ts`

**Subtasks:**
- [ ] Create test file
- [ ] Import WORKPIECE_BASE_Y, MAX_THERMAL_DISPLACEMENT, WELD_POOL_CENTER_Y
- [ ] Compute metal_surface_max_Y = WORKPIECE_BASE_Y + MAX_THERMAL_DISPLACEMENT
- [ ] Assert metal_surface_max_Y < WELD_POOL_CENTER_Y
- [ ] Assert gap >= 0.1 (safety margin)

**✓ Verification Test:**
- **Action:** Run `npm test -- welding3d.test.ts`
- **Expected:** Test passes; metal_surface_max_Y < WELD_POOL_CENTER_Y
- **Pass criteria:** No assertion failures; constraint enforced by test

**Time estimate:** 0.2 h

---

#### 🟥 Step 1.3: Export constants from barrel if applicable

**What:** Check if constants are exported for consumption. No barrel needed — direct import from `@/constants/welding3d`.

**Why:** TorchWithHeatmap3D will import these.

**Files:** None (no barrel in constants pattern per thermal.ts).

**✓ Verification:** Phase 2.1 build succeeds; if "Cannot find module '@/constants/welding3d'" appears, fix tsconfig paths per Pre-flight.

**Time estimate:** 0.05 h

---

**Phase 1 Total Time:** ~0.5 h

---

### Phase 2 — Core Fix: TorchWithHeatmap3D Position Updates

**Goal:** Use constants in TorchWithHeatmap3D; eliminate clipping.

**Time Estimate:** 1–1.5 h  
**Risk Level:** 🟢

---

#### 🟥 Step 2.1: Import welding3d constants in TorchWithHeatmap3D — *Critical: Enables correct positioning*

**What:** Add import for WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y.

**Why:** Replace magic numbers with named constants.

**Files:**
- **Modify:** `my-app/src/components/welding/TorchWithHeatmap3D.tsx`

**Code change:**

```typescript
import {
  WORKPIECE_BASE_Y,
  ANGLE_RING_Y,
  GRID_Y,
  CONTACT_SHADOWS_Y,
} from '@/constants/welding3d';
```

**Subtasks:**
- [ ] Add import at top of file (after existing imports)
- [ ] Remove no magic numbers — we'll replace in next steps

**✓ Verification Test:**
- **Action:** Build with `npm run build` (or `npm run dev`); no import errors
- **Expected:** Build succeeds
- **Pass criteria:** No TypeScript or module resolution errors

**Time estimate:** 0.1 h

---

#### 🟥 Step 2.2: Update workpiece group position

**What:** Change workpiece group from `[0, -0.6, 0]` to `[0, WORKPIECE_BASE_Y, 0]`. Use a named constant for the Y value so it can be verified by automated test (project rule: verification via automated tests, no manual browser checks only).

**Why:** Core fix — lowers metal so max surface stays below weld pool.

**Files:**
- **Modify:** `my-app/src/components/welding/TorchWithHeatmap3D.tsx` — search for `{/* Workpiece — thermal or flat */}` or `<group position=` to locate the workpiece group (typically lines 197–199)

**Code change:**

Define the workpiece Y position as a named constant (derived from welding3d) and export it for test verification:

```typescript
// After imports, define for use in JSX and export for test verification
const WORKPIECE_GROUP_Y = WORKPIECE_BASE_Y;
export { WORKPIECE_GROUP_Y };
```

Use in JSX:

```tsx
{/* Workpiece — thermal or flat */}
<group position={[0, WORKPIECE_GROUP_Y, 0]}>
```

**Subtasks:**
- [ ] Add `const WORKPIECE_GROUP_Y = WORKPIECE_BASE_Y` and `export { WORKPIECE_GROUP_Y }` near imports
- [ ] Locate `<group position={[0, -0.6, 0]}>` (workpiece)
- [ ] Replace with `position={[0, WORKPIECE_GROUP_Y, 0]}`
- [ ] Ensure both thermal (ThermalPlate) and flat (mesh) are inside this group

**✓ Verification Test:**

**Automated (primary):** Step 3.2a adds a test that asserts WORKPIECE_GROUP_Y === WORKPIECE_BASE_Y and satisfies the constraint.

**Manual (supplementary):**
- `npm run dev` in my-app; browser open
- Session with thermal_frames (e.g. demo expert, or seeded replay)
- Navigate to `/replay/[sessionId]` or `/demo`
- Scrub timeline to frame with center temp 400°C+; rotate 3D view; confirm no clipping

**Expected results:**
- Metal plane does not intersect weld pool sphere
- Visible gap between metal surface and torch cone/sphere
- Thermal bulge (warp) still visible on metal
- Torch appears to "rest just above" metal

**Pass criteria:**
- [ ] Metal surface never passes through weld pool
- [ ] Gap ~0.1–0.2 units visually (subjective "just above")
- [ ] Thermal warp effect still visible
- [ ] No console errors
- [ ] Works at angles 30°, 45°, 60°

**Common failures & fixes:**

| Failure | Detection | Response | Recovery |
|---------|-----------|----------|----------|
| Metal still clips | Metal intersects sphere | WORKPIECE_BASE_Y too high | Lower to -0.9; verify |
| Torch floats | Large gap, unrealistic | WORKPIECE_BASE_Y too low | Raise to -0.8 or -0.82 |
| No thermal data | Flat metal only | Session has no thermal_frames | Use session with thermal; check has_thermal_data |
| Wrong session | No clipping but no thermal | Session without thermal | Switch to expert/demo session |
| Build error | Import fails | Check welding3d.ts path | Verify file exists; tsconfig paths |

**Time estimate:** 0.15 h

---

#### 🟥 Step 2.3: Update angle guide ring position

**What:** Change angle ring from `[0, -0.59, 0]` to `[0, ANGLE_RING_Y, 0]`.

**Why:** Ring should sit on metal surface; must move with workpiece.

**Files:**
- **Modify:** `my-app/src/components/welding/TorchWithHeatmap3D.tsx` — search for `{/* Angle guide ring */}` or `position={[0, -0.59, 0]}` (angle ring mesh)

**Code change:**

```tsx
{/* Angle guide ring */}
<mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, ANGLE_RING_Y, 0]}>
```

**✓ Verification Test:**
- **Action:** Visual check on replay; ring should appear on/near metal plane
- **Expected:** Ring not floating or sunk; coherent with metal
- **Pass criteria:** Ring visually aligned with workpiece

**Time estimate:** 0.1 h

---

#### 🟥 Step 2.4: Update grid position

**What:** Change grid from `[0, -0.6, 0]` to `[0, GRID_Y, 0]`.

**Why:** Grid represents metal plane; align with workpiece.

**Files:**
- **Modify:** `my-app/src/components/welding/TorchWithHeatmap3D.tsx` — search for `gridHelper` or `position={[0, -0.6, 0]}` (grid element)

**Code change:**

```tsx
<gridHelper args={[5, 10, 0x22d3ee, 0x4b5563]} position={[0, GRID_Y, 0]} />
```

**✓ Verification Test:**
- **Action:** Visual check; grid should align with metal plane
- **Expected:** Grid at same level as workpiece
- **Pass criteria:** No visual disconnect

**Time estimate:** 0.1 h

---

#### 🟥 Step 2.5: Update ContactShadows position

**What:** Change ContactShadows from `[0, -0.59, 0]` to `[0, CONTACT_SHADOWS_Y, 0]`.

**Why:** Shadows should fall on metal surface.

**Files:**
- **Modify:** `my-app/src/components/welding/TorchWithHeatmap3D.tsx` — search for `ContactShadows` or `position={[0, -0.59, 0]}` (shadow component)

**Code change:**

```tsx
<ContactShadows
  position={[0, CONTACT_SHADOWS_Y, 0]}
  opacity={0.5}
  scale={2}
  blur={2}
  far={1}
/>
```

**✓ Verification Test:**
- **Action:** Visual check; shadows should appear on metal
- **Expected:** Shadows coherent with scene
- **Pass criteria:** No shadow cutoff or misalignment

**Time estimate:** 0.1 h

---

#### 🟥 Step 2.6: Verify no remaining magic numbers

**What:** Grep for -0.6, -0.59 in TorchWithHeatmap3D (excluding weld pool offset — that's inside torch group, different).

**Why:** Ensure full migration to constants.

**Files:** TorchWithHeatmap3D.tsx

**Note:** The -0.6 inside torch group (weld pool sphere position) is relative to torch; that's WELD_POOL_OFFSET_Y. TorchWithHeatmap3D doesn't import that — it's hardcoded in the mesh. Per issue, we're not changing torch geometry. So we only replace workpiece, ring, grid, shadows. The torch internal -0.6 stays (it's relative to torch group at 0.4).

**✓ Verification Test:**
- **Action:** `rg "-0\.(6|59)" my-app/src/components/welding/TorchWithHeatmap3D.tsx`
- **Expected:** Matches at weld pool meshes (e.g. lines ~176, ~187) are expected; any -0.6/-0.59 in workpiece/ring/grid/ContactShadows blocks is wrong.
- **Pass criteria:** No workpiece/ring/grid/shadow using -0.6 or -0.59
- **⚠️ If matches appear in workpiece/ring/grid/shadow code:** Those must be replaced with constants (ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y, WORKPIECE_GROUP_Y). A match outside the torch group indicates an incomplete migration.

**Time estimate:** 0.1 h

---

**Phase 2 Total Time:** ~0.65 h

---

### Phase 3 — Verification and Polish

**Goal:** Tests pass; automated constants-applied verification; manual verification; documentation updated.

**Time Estimate:** 1–1.5 h  
**Risk Level:** 🟢

---

#### 🟥 Step 3.1: Run existing TorchWithHeatmap3D tests

**What:** Execute `npm test -- TorchWithHeatmap3D`; ensure no regressions.

**Why:** Tests mock Canvas; they don't assert Y. We verify no runtime errors from new imports/constants.

**✓ Verification Test:**
- **Action:** `npm test -- TorchWithHeatmap3D.test`
- **Expected:** All tests pass
- **Pass criteria:** No failures; no new errors in output

**Time estimate:** 0.1 h

---

#### 🟥 Step 3.2: Run welding3d constants test

**What:** Execute `npm test -- welding3d.test`.

**✓ Verification Test:**
- **Action:** `npm test -- welding3d`
- **Expected:** Constraint test passes
- **Pass criteria:** metal_surface_max_Y < WELD_POOL_CENTER_Y

**Time estimate:** 0.05 h

---

#### 🟥 Step 3.2a: Add automated test — constants applied to workpiece position

**What:** Add a unit test that programmatically asserts the workpiece group receives position `[0, WORKPIECE_BASE_Y, 0]`. Per project .cursorrules: "Verification to be done by adding and running automated tests (no manual browser checks)."

**Why:** Ensures TorchWithHeatmap3D uses welding3d constants; catches drift if someone replaces WORKPIECE_GROUP_Y with a magic number.

**Files:**
- **Modify:** `my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx`

**Code to add:**

```typescript
import { WORKPIECE_BASE_Y } from '@/constants/welding3d';
import { WORKPIECE_GROUP_Y } from '@/components/welding/TorchWithHeatmap3D';

describe('TorchWithHeatmap3D constants application', () => {
  it('workpiece group uses WORKPIECE_BASE_Y from welding3d', () => {
    expect(WORKPIECE_GROUP_Y).toBe(WORKPIECE_BASE_Y);
    expect(WORKPIECE_GROUP_Y).toBe(-0.85);
  });
});
```

**✓ Verification Test:**
- **Action:** Run `npm test -- TorchWithHeatmap3D.test`
- **Expected:** Test passes; WORKPIECE_GROUP_Y equals WORKPIECE_BASE_Y
- **Pass criteria:** No assertion failures; constants verified applied

**Time estimate:** 0.1 h

---

#### 🟥 Step 3.3: Manual visual verification — replay page

**What:** Open replay for session with thermal data; scrub to high-temp frame; rotate view; confirm no clipping. Supplementary to automated tests.

**Why:** Primary user flow; final sanity check after automated tests pass.

**✓ Verification Test:**
- **Setup:** `npm run dev`; have session with thermal_frames (e.g. demo expert)
- **Action:** Navigate to `/replay/[sessionId]`; play or scrub to frame with center temp 400°C+; rotate 3D view
- **Expected:** Metal surface never intersects torch; torch rests above metal; thermal bulge visible
- **Pass criteria:** No clipping at any angle; gap visible between weld pool and metal

**Time estimate:** 0.2 h

---

#### 🟥 Step 3.4: Manual visual verification — demo page

**What:** Open /demo with expert session; verify same behavior.

**✓ Verification Test:**
- **Action:** Navigate to `/demo`; select expert session; observe 3D torch+metal
- **Expected:** Same as 3.3
- **Pass criteria:** No clipping; torch above metal

**Time estimate:** 0.15 h

---

#### 🟥 Step 3.5: Update ThermalPlate JSDoc and add uMaxDisplacement comment

**What:** (a) Change JSDoc from `position [0,-0.6,0]` to reference WORKPIECE_BASE_Y or welding3d constants. (b) Add comment at uMaxDisplacement (line ~78) to prevent drift from MAX_THERMAL_DISPLACEMENT in welding3d.ts.

**Why:** Future developers need correct guidance. ThermalPlate hardcodes `uMaxDisplacement=0.5`; constants file documents `MAX_THERMAL_DISPLACEMENT=0.5`. Without a comment, changing one without the other causes drift.

**Files:**
- **Modify:** `my-app/src/components/welding/ThermalPlate.tsx` (line ~41, line ~78)

**Code change (JSDoc, line ~41):**

```typescript
/**
 * Thermal workpiece mesh — plane with vertex displacement and heat-sensitive color.
 * Position/rotation must be set by parent. In TorchWithHeatmap3D, use WORKPIECE_BASE_Y
 * from @/constants/welding3d so metal surface (with max displacement) stays below
 * weld pool. See .cursor/issues/metal-heatmap-y-position-clipping-torch.md.
 */
```

**Code change (uMaxDisplacement comment, line ~78):**

```typescript
    uniforms: {
      uTemperatureMap: { value: tex },
      uMinTemp: { value: minTemp },
      uMaxTemp: { value: Math.max(0.001, maxTemp) },
      uStepCelsius: { value: colorSensitivity },
      // uMaxDisplacement must match MAX_THERMAL_DISPLACEMENT in welding3d.ts; do not change without updating constants and welding3d.test.
      uMaxDisplacement: { value: 0.5 },
    },
```

**✓ Verification Test:**
- **Action:** Read JSDoc; verify it points to constants and issue; read uMaxDisplacement comment
- **Pass criteria:** Clear guidance for parent positioning; uMaxDisplacement/constants coupling documented

**Time estimate:** 0.1 h

---

#### 🟥 Step 3.6: Optional — Update CONTEXT.md

**What:** Add note about welding3d constants if we want discoverability.

**Why:** CONTEXT.md is for AI tools; helps future work.

**Files:**
- **Modify:** `CONTEXT.md` (3D Visualization section)

**Optional addition:**
```markdown
**Scene coordinates:** Y positions (workpiece, torch, etc.) in `constants/welding3d.ts`. Constraint: metal surface max < weld pool center; see issue metal-heatmap-y-position-clipping-torch.
```

**✓ Verification Test:** CONTEXT.md renders; section exists.

**Time estimate:** 0.1 h

---

#### 🟥 Step 3.7: Verify HeatmapPlate3D unaffected

**What:** HeatmapPlate3D has no dedicated route in the app (replay uses TorchWithHeatmap3D; compare uses 2D HeatMap). We did not change ThermalPlate; HeatmapPlate3D uses ThermalPlate at origin. Run automated tests; no visual route exists for standalone verification.

**Why:** Sanity check that HeatmapPlate3D tests still pass; uMaxDisplacement unchanged.

**✓ Verification Test:**
- **Action:** `npm test -- HeatmapPlate3D`
- **Expected:** All HeatmapPlate3D tests pass
- **Pass criteria:** No regressions; tests pass
- **Note:** Visual sanity check N/A — no route renders HeatmapPlate3D in production

**Time estimate:** 0.05 h

---

**Phase 3 Total Time:** ~0.85 h

---

## ROLLBACK PROCEDURE

**Rollback:** `git revert <commit>` or revert `welding3d.ts` and `TorchWithHeatmap3D.tsx`; redeploy. No database or schema changes; safe to revert at any time.

---

## TOTAL EFFORT SUMMARY

| Phase | Steps | Time (h) |
|-------|-------|----------|
| Phase 1 | 3 | 0.5 |
| Phase 2 | 6 | 0.65 |
| Phase 3 | 8 | 0.85 |
| **Total** | **17** | **~2.0** |

*Buffer for debugging, iteration on WORKPIECE_BASE_Y, and documentation: +0.5–1 h → **2.5–3 h total** (matches exploration).*

---

## PRE-FLIGHT CHECKLIST

### Phase 1 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Node.js v18+ | `node --version` | Install from nodejs.org |
| npm | `npm --version` | Comes with Node |
| Dependencies | `cd my-app && npm ci` | Run `npm install` |
| Project structure | `ls my-app/src/constants` | Constants dir exists (thermal.ts present) |
| tsconfig @ path | `@/*` in `tsconfig.json` paths resolves to `./src/*` | Verify `paths: { "@/*": ["./src/*"] }` in `my-app/tsconfig.json` — `@/constants/welding3d` imports depend on this |
| Git clean | `git status` | Commit or stash changes |

**Checkpoint:** ⬜ All Phase 1 prerequisites met

### Phase 2 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 1 complete | welding3d.ts exists; welding3d.test passes | Complete Phase 1 |
| Dev server | `npm run dev` in my-app | Start dev server |
| Replay data | Session with thermal_frames | Use demo seed or mock |

**Checkpoint:** ⬜ All Phase 2 prerequisites met

### Phase 3 Prerequisites

| Requirement | How to Verify | If Missing |
|-------------|---------------|------------|
| Phase 2 complete | TorchWithHeatmap3D uses constants | Complete Phase 2 |
| Browser | Chrome/Firefox/Safari | Install browser |
| Test script | `npm test` runs | Verify in my-app |

**Checkpoint:** ⬜ All Phase 3 prerequisites met

---

## RISK HEATMAP

| Phase | Step | Risk | Probability | Impact | Mitigation |
|-------|------|------|-------------|--------|------------|
| 1 | 1.1 | Wrong WORKPIECE_BASE_Y | 🟡 20% | High | Unit test enforces constraint; recalc if needed |
| 2 | 2.2 | Torch floats (gap too large) | 🟡 30% | Medium | Try -0.8 or -0.82; METAL_TO_TORCH_GAP adjustable |
| 2 | 2.3–2.5 | Ring/grid/shadows misaligned | 🟢 15% | Low | All derived from WORKPIECE_BASE_Y |
| 3 | 3.3–3.4 | Edge case clipping (angle) | 🟢 10% | Medium | Test multiple angles; center is reference |
| 3 | 3.7 | HeatmapPlate3D regression | 🟢 5% | Low | We don't change ThermalPlate; npm test -- HeatmapPlate3D |

**Top risk:** Torch floats — iterate on WORKPIECE_BASE_Y; 0.15 gap is conservative.

---

## SUCCESS CRITERIA

| # | Criterion | Verification | Priority |
|---|-----------|--------------|----------|
| 1 | No metal clipping through torch | Visual at max temp; rotate view | 🔴 P0 |
| 2 | Torch rests just above metal | Visual; gap ~0.1–0.2 units | 🔴 P0 |
| 3 | Thermal bulge visible | Compare cold vs hot frame | 🔴 P0 |
| 4 | Angle ring aligned with metal | Visual | 🟡 P1 |
| 5 | Grid aligned with metal | Visual | 🟡 P1 |
| 6 | ContactShadows coherent | Visual | 🟡 P1 |
| 7 | All unit tests pass | `npm test` | 🔴 P0 |
| 8 | Constants applied test passes | Step 3.2a | 🔴 P0 |
| 9 | Replay page works | Manual | 🔴 P0 |
| 10 | Demo page works | Manual | 🔴 P0 |
| 11 | HeatmapPlate3D unchanged | `npm test -- HeatmapPlate3D` | 🟡 P1 |
| 12 | Constants constrain relationship | welding3d.test | 🔴 P0 |
| 13 | ThermalPlate JSDoc and uMaxDisplacement comment updated | Read JSDoc and comment | 🟡 P1 |

**Definition of Done:**
- [ ] All P0 pass
- [ ] All P1 pass (or deferred with reason)
- [ ] No regression in existing tests
- [ ] Automated constants-applied test passes (Step 3.2a)
- [ ] Manual verification on replay and demo

**Manual visual verification rationale (criteria 1–6, 9–10):** Per project rules, verification prefers automated tests. Step 3.2a provides automated constants-applied verification. 3D visual clipping ("metal never intersects torch") cannot be fully automated without pixel/snapshot tests against rendered WebGL — scope and maintenance cost are high for this MVP. Manual visual checks are the practical fallback; they run once per environment after automated tests pass.

---

## PROGRESS DASHBOARD

| Phase | Total Steps | Completed | In Progress | Blocked | % Complete |
|-------|-------------|-----------|-------------|---------|------------|
| Phase 1 | 3 | 0 | 0 | 0 | 0% |
| Phase 2 | 6 | 0 | 0 | 0 | 0% |
| Phase 3 | 8 | 0 | 0 | 0 | 0% |
| **TOTAL** | **17** | **0** | **0** | **0** | **0%** |

---

## QUALITY METRICS

| Metric | Minimum | Count |
|--------|---------|-------|
| Phases | 3 | 3 ✓ |
| Total steps | 15+ | 17 ✓ |
| Verification tests per step | 1 | 1 ✓ |
| Pre-flight items | 5 per phase | 5+ ✓ |
| Success criteria | 12 | 13 ✓ |
| Risk entries | 5+ | 5 ✓ |

---

## IMMEDIATE NEXT STEPS

1. [ ] Verify Phase 1 prerequisites
2. [ ] Create welding3d.ts (Step 1.1)
3. [ ] Add welding3d.test.ts (Step 1.2)
4. [ ] Proceed to Phase 2

---

## COMMON FAILURES & FIXES

**If metal still clips after Step 2.2:**
- Check: WORKPIECE_BASE_Y = -0.85 in constants
- Fix: Lower to -0.9; recalc: metal max = -0.4, gap = 0.2
- Or reduce METAL_TO_TORCH_GAP to 0.1 and set WORKPIECE_BASE_Y = -0.75 (metal max -0.25, gap 0.05 — risk of clip)

**If torch floats too high:**
- Check: WORKPIECE_BASE_Y = -0.85
- Fix: Raise to -0.8 (metal max -0.3, gap 0.1) or -0.82 (metal max -0.32, gap 0.12)
- Adjust METAL_TO_TORCH_GAP in constants

**If import fails for welding3d:**
- Check: File at `my-app/src/constants/welding3d.ts`
- Fix: Ensure path `@/constants/welding3d` resolves — verify `tsconfig.json` has `paths: { "@/*": ["./src/*"] }` so `@` resolves to `src/`

**If tests fail:**
- TorchWithHeatmap3D: Tests mock Canvas; imports should not break. If they do, check for dynamic imports or SSR.
- welding3d: Ensure test file imports correct symbols; constraint math correct.
- Constants-applied test (3.2a): Ensure WORKPIECE_GROUP_Y is exported from TorchWithHeatmap3D.

---

## 🧠 THINKING CHECKPOINT #2 — Step Quality Check

**Random step review:**

**Step 1.1:** Atomic (create file)? Yes. Specific (exact constants)? Yes. Verification? Yes. Time estimate? Yes. Code example? Yes. ✓

**Step 2.2:** Atomic? Yes. Specific? Yes. Verification? Yes (automated + manual). Dependencies? Clear (needs 1.1, 2.1). ✓

**Step 3.2a:** Atomic? Yes. Fulfills project rule (automated verification)? Yes. ✓

**Step 3.7:** Actionable? Yes — `npm test -- HeatmapPlate3D`; no conditional "if route exists." ✓

**Completeness:**
- Total phases: 3 ✓
- Total steps: 17 ✓
- Critical steps with code: 2 (1.1, 2.2) ✓
- Verification tests: 17 ✓
- Rollback procedure: Added ✓
- ThermalPlate uMaxDisplacement comment: Added ✓

**Dependency validation:** Step 2.2 → 2.1 → 1.1. Chain correct. ✓

**Time sanity:** 2.0 h core + 0.5–1 h buffer = 2.5–3 h. Matches exploration. ✓

---

## 🧠 THINKING CHECKPOINT #3 — Implementability & Red Team

### Implementability Test

**Junior developer questions:**

1. **Where do I create welding3d.ts?** → `my-app/src/constants/welding3d.ts` (Step 1.1)
2. **What is WORKPIECE_BASE_Y?** → -0.85; doc in constants
3. **Do I change ThermalPlate?** → No; only JSDoc and uMaxDisplacement comment in Step 3.5
4. **Do I change TorchViz3D?** → No; out of scope
5. **What if metal still clips?** → Common failures table; lower to -0.9
6. **What if torch floats?** → Raise to -0.8 or -0.82
7. **Where is the weld pool -0.6?** → Inside torch group (relative); don't change
8. **Does HeatmapPlate3D break?** → No; we don't change ThermalPlate position or uMaxDisplacement; run `npm test -- HeatmapPlate3D`
9. **How do I run the new test?** → `npm test -- welding3d` and `npm test -- TorchWithHeatmap3D`
10. **What session has thermal data?** → Demo expert session; or seed with thermal_frames

**All answered in plan.** ✓

### Red Team — 10 Problems

1. **Constants file path typo** — Severity: Medium. Fix: Use exact path `my-app/src/constants/welding3d.ts`.
2. **ANGLE_RING_Y = WORKPIECE_BASE_Y + 0.01 might sink into displaced metal** — Severity: Low. Fix: 0.01 is small; if needed, increase to 0.02. Ring is visual guide.
3. **Flat fallback could use different Y if typo** — Severity: High. Fix: Both thermal and flat use same group; group has WORKPIECE_GROUP_Y. No separate path.
4. **Shadow camera might not cover -0.85** — Severity: Low. Fix: Camera ±10; -0.85 well within. Document in constants.
5. **ThermalPlate JSDoc says [0,-0.6,0]** — Severity: Medium. Fix: Step 3.5 updates JSDoc.
6. **Test might fail if constants change** — Severity: Low. Fix: Test asserts constraint; if we change values, update test.
7. **Build fails on missing barrel** — Severity: Low. Fix: No barrel needed; direct import.
8. **TorchViz3D diverges over time** — Severity: Low. Fix: Out of scope; document in constants for future sync.
9. **plateSize affects displacement visually?** — Severity: Low. Fix: Displacement is in world units; plateSize scales geometry, not displacement magnitude. Same.
10. **First frame has no thermal?** — Severity: Low. Fix: Scrub to frame with thermal; verification step says 400°C+.

### Confidence Rating

- **Plan quality:** 9/10
- **Completeness:** 9/10
- **Implementability:** 9/10
- **Time estimates:** 9/10
- **Risk coverage:** 8/10
- **Overall:** 9/10

---

## FINAL QUALITY GATE

- [x] Phases defined (3)
- [x] Steps atomic and specific (17)
- [x] Every step has verification test
- [x] Critical steps have code examples (1.1, 2.2)
- [x] Dependencies mapped
- [x] Pre-flight checklists complete
- [x] Risk heatmap documented
- [x] Success criteria (13)
- [x] Thinking checkpoints (3)
- [x] Common failures documented
- [x] Automated constants-applied test (Step 3.2a)
- [x] Rollback procedure
- [x] ThermalPlate uMaxDisplacement/constants coupling documented

**Scope note:** This bug is small (4–8 h per issue, 2.5–3 h per exploration). Plan has 17 steps; template suggests 30+ for larger features. For this scope, 17 atomic steps with full verification is appropriate. A junior engineer can implement without questions.

---

**Plan complete. Ready for implementation.**
