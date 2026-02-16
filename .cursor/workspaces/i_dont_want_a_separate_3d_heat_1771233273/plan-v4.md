
The plan has been refined in place. Summary of edits:

**Critical fix (execution order):**
- Added explicit execution order: **1.1 → 1.3 → 1.2 → 1.4 → 1.5**  
- Moved Step 1.3 (wire uniforms) before Step 1.2 (stepped gradient) so `uStepCelsius` is set before the shader uses it  
- Added warning that Step 1.2 must not be verified in isolation  
- Updated dependency table: 1.2 depends on 1.1 and 1.3; 1.3 depends on 1.1  
- Adjusted Phase 1 risk text and progress tracking

**Minor refinements:**
1. **Step 1.1 verification:** Use “existing replay page with a session that has thermal_frames” instead of “Open HeatmapPlate3D in browser”  
2. **Step 2.2b:** Replaced line references with a structural description: “Copy function SceneContent and its dependencies (ambientLight, directionalLights, pointLights, torch group, weld pool, angle guide ring, gridHelper, ContactShadows, Environment) from TorchViz3D.tsx”  
3. **Step 3.3:** Added TorchViz3D mock reference: “Copy mock setup from `my-app/src/__tests__/components/welding/TorchViz3D.test.tsx` (Canvas, OrbitControls, Environment, ContactShadows, PerspectiveCamera, next/font)”  
4. **Section 7:** Added rollback procedure: revert to TorchViz3D + HeatmapPlate3D; keep ThermalPlate and frameUtils extraction  
5. **Step 2.4:** Added note that both expert and novice have thermal data from demo-data  

The updated plan is in `.cursor/plans/unified-torch-heatmap-implementation-blueprint.md`.
