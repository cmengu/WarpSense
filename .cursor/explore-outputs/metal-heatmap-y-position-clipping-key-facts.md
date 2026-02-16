# Metal Heatmap Y-Position Clipping — Key Facts

## Key Files
- `my-app/src/components/welding/TorchWithHeatmap3D.tsx` — torch + ThermalPlate/flat metal; positions at ~189, 212, 222, 225
- `my-app/src/components/welding/TorchViz3D.tsx` — torch + flat workpiece only; workpiece at -0.6
- `my-app/src/components/welding/HeatmapPlate3D.tsx` — standalone thermal plate; TorchIndicator at Y=2
- `my-app/src/components/welding/ThermalPlate.tsx` — shared plane with uMaxDisplacement 0.5; parent positions it
- `my-app/src/components/welding/shaders/heatmapVertex.glsl.ts` — vertex displacement along normal
- `my-app/src/constants/welding3d.ts` — NEW: scene Y constants (WORKPIECE_BASE_Y, etc.)

## Root Cause
- Metal max surface Y = -0.6 + 0.5 = -0.1; weld pool center Y = -0.2; metal above pool → clipping

## Architecture
- **Approach A chosen:** Lower workpiece only; do NOT change uMaxDisplacement (avoids HeatmapPlate3D impact)
- ThermalPlate shared by TorchWithHeatmap3D and HeatmapPlate3D — parent sets position
- Pattern: derive angle ring (-0.84), grid (-0.85), ContactShadows (-0.84) from WORKPIECE_BASE_Y
- Same base Y for flat and thermal — no jump when switching
- Torch geometry: weld pool at -0.2 (fixed)

## Fix
- Workpiece base Y: -0.6 → -0.85; metal max = -0.35; gap to weld pool = 0.15
- Replace magic numbers in TorchWithHeatmap3D with constants from welding3d.ts
- Optional: ThermalPlate JSDoc update

## Risks
- Torch may appear to float (gap 0.15); mitigate: iterate on WORKPIECE_BASE_Y (-0.8, -0.82)
- Angle ring/grid/shadows misalignment; mitigate: derive all from single constant
- Changing uMaxDisplacement would break HeatmapPlate3D warp — avoid

## Effort
~2.5–3 h
