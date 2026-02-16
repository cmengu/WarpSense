
Refinements are done. Summary:

**Applied refinements**

1. **Step 2.2a** – Removed TorchWithHeatmap3D from Files and Subtasks. Step 2.2a only creates `ThermalPlate.tsx` and updates `HeatmapPlate3D.tsx`. TorchWithHeatmap3D ThermalPlate usage is documented in Step 2.2b.

2. **Step 1.1 verification** – Added fallback for setups without thermal data: run `python backend/scripts/seed_demo_data.py` or use `/demo` for in-browser thermal data.

3. **Step 2.2b** – Documented ThermalPlate import and usage (including file creation and ThermalPlate props) as part of creating `TorchWithHeatmap3D.tsx`.

4. **Step 2.6 ESLint** – Added verification command: `cd my-app && npx eslint src/app/replay/ src/app/demo/` to confirm the rule enforces limits on both paths.

5. **Steps 4.2 and 4.3** – Specified that mocks must match the dynamic import path `import('@/components/welding/TorchWithHeatmap3D')`.

6. **Section 7 Rollback** – Clarified that ThermalPlate and frameUtils extraction are kept; only replay/demo imports and JSX revert to TorchViz3D + HeatmapPlate3D.

7. **Step 2.2a verification** – Updated the verification test so it only checks HeatmapPlate3D (TorchWithHeatmap3D verification stays in 2.2b).
