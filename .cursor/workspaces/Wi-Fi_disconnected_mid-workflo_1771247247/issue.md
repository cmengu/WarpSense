
Implementation for **Fix metal plane clipping through torch** is done according to the plan. Summary:

## Summary of Changes

### Phase 1: Foundation

1. **`my-app/src/constants/welding3d.ts`**
   - Constants: `TORCH_GROUP_Y`, `WELD_POOL_OFFSET_Y`, `WELD_POOL_CENTER_Y`, `MAX_THERMAL_DISPLACEMENT`, `METAL_TO_TORCH_GAP`, `WORKPIECE_BASE_Y`, `ANGLE_RING_Y`, `GRID_Y`, `CONTACT_SHADOWS_Y`
   - Math: `WORKPIECE_BASE_Y = -0.85` so max metal surface ≈ -0.35, below weld pool at -0.2, with a 0.15 gap

2. **`my-app/src/__tests__/constants/welding3d.test.ts`**
   - Checks `metal_surface_max_Y < WELD_POOL_CENTER_Y`
   - Checks gap ≥ 0.1
   - Checks `METAL_TO_TORCH_GAP` matches derived gap

### Phase 2: TorchWithHeatmap3D

3. **`my-app/src/components/welding/TorchWithHeatmap3D.tsx`**
   - Imports `WORKPIECE_BASE_Y`, `ANGLE_RING_Y`, `GRID_Y`, `CONTACT_SHADOWS_Y`
   - Defines `WORKPIECE_GROUP_Y = WORKPIECE_BASE_Y` and exports it for tests
   - Updates positions:
     - Workpiece group: `[0, -0.6, 0]` → `[0, WORKPIECE_GROUP_Y, 0]`
     - Angle ring: `[0, -0.59, 0]` → `[0, ANGLE_RING_Y, 0]`
     - Grid: `[0, -0.6, 0]` → `[0, GRID_Y, 0]`
     - ContactShadows: `[0, -0.59, 0]` → `[0, CONTACT_SHADOWS_Y, 0]`
   - Torch internal -0.6 left as-is (weld pool sphere relative position)

### Phase 3: Verification & docs

4. **`my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx`**
   - New test ensures `WORKPIECE_GROUP_Y === WORKPIECE_BASE_Y` and `=== -0.85`

5. **`my-app/src/components/welding/ThermalPlate.tsx`**
   - JSDoc updated to reference `WORKPIECE_BASE_Y` from welding3d
   - Comment added for `uMaxDisplacement` to link it to `welding3d.ts`

---

## Verification

Run:

```bash
cd my-app && npm test -- welding3d TorchWithHeatmap3D HeatmapPlate3D
```

Visual checks (per plan):

- Replay page with thermal data: scrub to a hot frame (e.g. 400°C+), rotate the view, confirm no metal clipping
- Demo page with expert session: same check

The metal base is now at Y = -0.85 instead of -0.6, so the maximum metal surface (with 0.5 displacement) is about -0.35, below the weld pool at -0.2, with a 0.15 gap between metal and torch.
