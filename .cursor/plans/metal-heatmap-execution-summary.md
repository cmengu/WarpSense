# Metal Heatmap Y-Position — Execution Summary

## Steps

1. File: `my-app/src/constants/welding3d.ts`
   - Action: Create with WORKPIECE_BASE_Y, ANGLE_RING_Y, GRID_Y, CONTACT_SHADOWS_Y
   - Key code: `export const WORKPIECE_BASE_Y = -0.85`

2. File: `my-app/src/__tests__/constants/welding3d.test.ts`
   - Action: Assert metal_surface_max_Y < WELD_POOL_CENTER_Y, gap >= 0.1
   - Key code: `expect(metal_surface_max_Y).toBeLessThan(WELD_POOL_CENTER_Y)`

3. File: `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
   - Action: Import welding3d constants; add WORKPIECE_GROUP_Y = WORKPIECE_BASE_Y
   - Key code: `import { ... } from '@/constants/welding3d'`

4. File: `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
   - Action: Search `{/* Workpiece — thermal or flat */}` or `<group position=` → position={[0, WORKPIECE_GROUP_Y, 0]}
   - Key code: `<group position={[0, WORKPIECE_GROUP_Y, 0]}>`

5. File: `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
   - Action: Search `{/* Angle guide ring */}` or `position={[0, -0.59, 0]}` → ANGLE_RING_Y
   - Key code: `position={[0, ANGLE_RING_Y, 0]}`

6. File: `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
   - Action: Search `gridHelper` or `position={[0, -0.6, 0]}` → GRID_Y
   - Key code: `position={[0, GRID_Y, 0]}`

7. File: `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
   - Action: Search `ContactShadows` or `position={[0, -0.59, 0]}` → CONTACT_SHADOWS_Y
   - Key code: `position={[0, CONTACT_SHADOWS_Y, 0]}`

8. File: `my-app/src/components/welding/TorchWithHeatmap3D.tsx`
   - Action: `rg "-0\.(6|59)"` — weld pool meshes (~176,187) ok; workpiece/ring/grid/ContactShadows wrong
   - Key code: Replace any -0.6/-0.59 in those blocks

9. File: `my-app/src/__tests__/components/welding/TorchWithHeatmap3D.test.tsx`
   - Action: Add test: WORKPIECE_GROUP_Y === WORKPIECE_BASE_Y
   - Key code: `expect(WORKPIECE_GROUP_Y).toBe(WORKPIECE_BASE_Y)`

10. File: `my-app/src/components/welding/ThermalPlate.tsx`
    - Action: JSDoc + uMaxDisplacement comment
    - Key code: `// uMaxDisplacement must match MAX_THERMAL_DISPLACEMENT in welding3d.ts`

## Verification

- `npm test -- welding3d` · `npm test -- TorchWithHeatmap3D` · `npm test -- HeatmapPlate3D`
- Phase 2.1 build succeeds; if module not found, fix tsconfig paths per Pre-flight

## Critical Details

- Do NOT change ThermalPlate uMaxDisplacement (0.5)
- Do NOT touch weld pool -0.6 (torch-internal)
- tsconfig: `paths: { "@/*": ["./src/*"] }`
