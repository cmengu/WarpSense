
Refinements to the plan are done. Summary of updates:

1. **Step 2.2 (line reference):** Replaced `line ~189` with: search for `{/* Workpiece — thermal or flat */}` or `<group position=` (typically lines 197–199).

2. **Step 1.3 (verification):** Clarified the verification: if Phase 2 build fails with "Cannot find module '@/constants/welding3d'", the export path is wrong and should be fixed before continuing.

3. **Manual visual verification rationale:** Added a note that 3D clipping (“metal never intersects torch”) can’t be fully automated without WebGL pixel/snapshot tests, which are out of scope for this MVP, so manual checks remain the practical option.

4. **Pre-flight tsconfig:** Added a prerequisite that `@/*` resolves to `./src/*` in `tsconfig.json`, and updated the COMMON FAILURES section to reference `tsconfig.json` paths.

5. **Step 2.6 (grep verification):** Added a warning that if rg finds matches in workpiece/ring/grid/shadow code, those values must be replaced with the constants.
