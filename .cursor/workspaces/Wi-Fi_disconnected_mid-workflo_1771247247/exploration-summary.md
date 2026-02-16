
```markdown
## Key Files

- `my-app/src/constants/welding3d.ts` - WORKPIECE_BASE_Y=-0.85, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y
- `my-app/src/__tests__/constants/welding3d.test.ts` - Constraint, gap ≥ 0.1, METAL_TO_TORCH_GAP tests
- `my-app/src/components/welding/TorchWithHeatmap3D.tsx` - Uses welding3d constants, WORKPIECE_GROUP_Y
- `my-app/src/components/welding/HeatmapPlate3D.tsx` - Heatmap plate component
- `my-app/src/components/welding/ThermalPlate.tsx` - JSDoc links to WORKPIECE_BASE_Y and welding3d
- `my-app/src/components/welding/shaders/` - uMaxDisplacement tied to MAX_THERMAL_DISPLACEMENT in welding3d

## Architecture

- Y-axis: metal base -0.85, metal max -0.35, weld pool -0.2, gap 0.15
- Single source: WORKPIECE_GROUP_Y = WORKPIECE_BASE_Y for workpiece, ring, grid, shadows
- Torch internal Y kept at -0.6; no magic numbers in workpiece/ring/grid/shadows

## Integration

- TorchWithHeatmap3D imports WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y
- ThermalPlate JSDoc references welding3d; uMaxDisplacement shader comment references welding3d

## Risks

- Metal clipping possible if math constraints broken (e.g. hot frames 400°C+, rotated view)
- Manual checks still needed on replay and `/demo` despite tests passing
```
