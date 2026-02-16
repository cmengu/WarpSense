# Metal Heatmap Y-Position Clipping — Key Facts

## Key Files
- `my-app/src/components/welding/TorchWithHeatmap3D.tsx` - unified torch + thermal plate; workpiece/ring/grid/shadow positions
- `my-app/src/components/welding/TorchViz3D.tsx` - flat torch + workpiece (no thermal); coordinate reference
- `my-app/src/components/welding/ThermalPlate.tsx` - vertex displacement shader; uMaxDisplacement=0.5
- `my-app/src/components/welding/HeatmapPlate3D.tsx` - standalone plate; uses ThermalPlate, no clipping
- `my-app/src/constants/welding3d.ts` - to create: shared geometry constants

## Root Cause
- Workpiece base Y=-0.6 + maxDisplacement=0.5 → metal surface Y=-0.1
- Weld pool center Y = 0.4 - 0.6 = **-0.2**
- Metal surface (-0.1) above weld pool (-0.2) → clips

## Architecture
- ThermalPlate shared by TorchWithHeatmap3D and HeatmapPlate3D; fix via parent position only (do NOT change uMaxDisplacement)
- Torch geometry fixed: weld pool at -0.6 relative to torch group
- Pattern: parent-positions-ThermalPlate; derive ring/grid/shadows from workpiece_base_Y

## Fix (position-only)
| Element | Current | New |
|---------|---------|-----|
| Workpiece | -0.6 | **-0.85** |
| Angle ring | -0.59 | **-0.84** |
| Grid | -0.6 | **-0.85** |
| ContactShadows | -0.59 | **-0.84** |
Max surface = -0.85 + 0.5 = **-0.35**; gap to weld pool ≈ **0.15**

## Integration
- Add `welding3d.ts`; update TorchWithHeatmap3D to use constants
- Same base Y for flat and thermal (no jump when switching)
- TorchViz3D: optional update for consistency (out of scope for this fix)

## Risks
- Torch may appear to float if gap too large (0.15 is target; iterate if needed)
- Alignment drift — mitigated by single constants source
- Do NOT change uMaxDisplacement — would affect HeatmapPlate3D warp

## Effort
~2.5–3 hours (constants + TorchWithHeatmap3D + tests)
