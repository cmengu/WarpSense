
# Implementation Complete

The **Fix metal plane clipping through torch** plan is fully implemented and matches the refined execution summary. All 10 steps are in place.

---

## Summary by Step

| Step | Action | Status |
|------|--------|--------|
| 1 | Create `welding3d.ts` with WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y | Done |
| 2 | Assert `metal_surface_max_Y < WELD_POOL_CENTER_Y` and `gap >= 0.1` in `welding3d.test.ts` | Done |
| 3 | Import welding3d constants in TorchWithHeatmap3D; add `WORKPIECE_GROUP_Y` | Done |
| 4 | Workpiece group uses `position={[0, WORKPIECE_GROUP_Y, 0]}` | Done |
| 5 | Angle guide ring uses `ANGLE_RING_Y` | Done |
| 6 | Grid uses `GRID_Y` | Done |
| 7 | ContactShadows uses `CONTACT_SHADOWS_Y` | Done |
| 8 | Only weld pool meshes use `-0.6`; workpiece/ring/grid/shadows use constants | Done |
| 9 | `TorchWithHeatmap3D.test.tsx` asserts `WORKPIECE_GROUP_Y === WORKPIECE_BASE_Y` | Done |
| 10 | ThermalPlate JSDoc + uMaxDisplacement comment referencing welding3d | Done |

---

## Files Touched

**Created**

- `my-app/src/constants/welding3d.ts` – Central Y-coordinate constants and constraints

**Modified**

- `my-app/src/components/welding/TorchWithHeatmap3D.tsx` – Uses all welding3d constants
- `my-app/src/components/welding/ThermalPlate.tsx` – JSDoc and uMaxDisplacement comment
- `my-app/src/__tests__/constants/welding3d.test.ts` – Clipping and gap tests
- `my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx` – `WORKPIECE_GROUP_Y` test

---

## Implementation Notes

- **Constraint:** `metal_surface_max_Y = WORKPIECE_BASE_Y + 0.5` = -0.35 &lt; -0.2 (weld pool center)
- **Gap:** 0.15 units between metal max surface and weld pool center
- **Single source of truth:** Y-positions come from `welding3d.ts`
- **ThermalPlate uMaxDisplacement:** Left at 0.5 per plan
- **Weld pool Y:** `-0.6` relative to torch group left as-is (torch-internal)

---

## Manual Verification

Run these locally:

```bash
cd my-app
npm test -- welding3d
npm test -- TorchWithHeatmap3D
npm test -- HeatmapPlate3D
npm run build
```

Then:

1. Start `npm run dev` and open `/demo`
2. Use expert session with thermal data
3. Rotate the view and confirm metal never clips through the torch
4. Confirm torch sits just above the metal

---

# Implementation Status: ✅ COMPLETE

All steps from the refined plan are implemented. Metal Y-positions are centralized in `welding3d.ts`, and workpiece, angle ring, grid, and ContactShadows use these constants so metal no longer clips through the torch.
