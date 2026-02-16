
Phase 2 execution for **Fix metal plane clipping through torch** is already done. The refined plan (Iteration 2) is implemented and matches the execution summary.

## Implementation status

| Step | Action | Status |
|------|--------|--------|
| 1 | `welding3d.ts` with WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y | ✅ Done |
| 2 | Clipping and gap assertions in `welding3d.test.ts` | ✅ Done |
| 3 | Import welding3d constants in TorchWithHeatmap3D; add WORKPIECE_GROUP_Y | ✅ Done |
| 4 | Workpiece group uses `position={[0, WORKPIECE_GROUP_Y, 0]}` | ✅ Done |
| 5 | Angle guide ring uses ANGLE_RING_Y | ✅ Done |
| 6 | Grid uses GRID_Y | ✅ Done |
| 7 | ContactShadows uses CONTACT_SHADOWS_Y | ✅ Done |
| 8 | Only weld pool meshes use -0.6; workpiece/ring/grid/shadows use constants | ✅ Done |
| 9 | TorchWithHeatmap3D.test.tsx asserts WORKPIECE_GROUP_Y === WORKPIECE_BASE_Y | ✅ Done |
| 10 | ThermalPlate JSDoc + uMaxDisplacement comment referencing welding3d | ✅ Done |

**Constraint verification:**
- `metal_surface_max_Y` = -0.85 + 0.5 = **-0.35** &lt; **-0.2** (weld pool center) ✓  
- `METAL_TO_TORCH_GAP` = **0.15** ✓  

---

## Verify locally

```bash
cd my-app
npm test -- welding3d
npm test -- TorchWithHeatmap3D
npm run build
```

Then:

1. `npm run dev` → open `/demo`
2. Use an expert session with thermal data
3. Rotate the view and confirm the metal never clips through the torch
4. Confirm the torch sits just above the metal

There are no remaining tasks in the plan. You can run the commands above to double-check tests and build.
