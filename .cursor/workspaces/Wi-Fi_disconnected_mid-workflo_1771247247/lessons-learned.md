
Updated `LEARNING_LOG.md` with the metal plane clipping fix. Summary:

## Changes to LEARNING_LOG.md

1. **Top summary**
   - Entry count: 3 → 4 incidents
   - New line: Metal plane clipping fix and `metal_surface_max_Y < weld_pool_center_Y` constraint

2. **Quick Reference**
   - New row: "Metal Plane Clipping Through Torch", Frontend / 3D, Medium

3. **New full entry**
   - Category: Frontend / 3D
   - What: Metal workpiece clipping through torch due to scattered Y values
   - Root cause: No central source of truth for Y positions
   - Fix: Centralize Y coordinates in `welding3d.ts` (WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y)
   - Prevention: Use welding3d constants; assert constraints in tests
   - AI guidance for future 3D Y-position changes

4. **Lessons section**
   - Added `welding3d.ts` to the “Single source of truth” note for Y coordinates

Verification commands (`npm test -- welding3d` etc.) failed to run in this environment, so run them locally:

```bash
cd my-app
npm test -- welding3d
npm test -- TorchWithHeatmap3D
npm test -- HeatmapPlate3D
npm run build
```

Then check `/demo` with an expert session and confirm no clipping when rotating the view.
