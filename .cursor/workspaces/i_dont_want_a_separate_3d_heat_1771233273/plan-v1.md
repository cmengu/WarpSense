
Refinements based on the critique are complete and saved in `.cursor/plans/unified-torch-heatmap-implementation-blueprint.md`. Summary:

**Critical fixes**

1. **Step 2.3 layout spec**  
   - Row 1: `grid-cols-2` for TorchWithHeatmap3D (expert | comparison)  
   - Row 2 (thermal): TorchAngleGraph full-width  
   - Row 2 (no thermal): `grid-cols-2` with HeatMap left, TorchAngleGraph right  

2. **Step 2.2a shared ThermalPlate**  
   - Extract shared `ThermalPlate.tsx` instead of copying Plate logic. HeatmapPlate3D and TorchWithHeatmap3D both use this single implementation and a documented sync contract.

**Minor fixes**

- **Step 1.1b merged into 1.3** — all Plate uniforms wired in one step  
- **Step 2.2d merged into 2.3/2.4** — dynamic import handled during integration  
- **Step 2.2b** — added reference: `TorchViz3D.tsx` (lines ~63–130) for `SceneContent`  
- **Step 4.3** — clarified demo test path: `my-app/src/__tests__/app/demo/page.test.tsx`  
- **Step 2.6** — new required step: ESLint rule updated to count TorchWithHeatmap3D  
- **Phase 3.3** — added automated smoke test for TorchWithHeatmap3D with thermal frames  
- **Part 0 Gap 1 and Step 1.2** — added LUT fallback spec (512×1 DataTexture, sampling by `t`)
