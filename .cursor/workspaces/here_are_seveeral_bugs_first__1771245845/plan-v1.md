
The refined plan is written to `.cursor/plans/metal-heatmap-y-position-clipping-fix-plan.md`. All four minor items from the critique are covered:

1. **Automated constants verification** — Step 3.2a adds a unit test that checks `WORKPIECE_GROUP_Y` equals `WORKPIECE_BASE_Y`, and Step 2.2 introduces the exported `WORKPIECE_GROUP_Y` constant.

2. **Step 3.7** — Verification is now explicit: run `npm test -- HeatmapPlate3D`; it’s noted that no route renders HeatmapPlate3D, so no visual check is needed.

3. **Rollback** — A dedicated Rollback Procedure section is added with a clear revert instruction.

4. **ThermalPlate drift risk** — Step 3.5 expands to include a comment next to `uMaxDisplacement` in `ThermalPlate.tsx` that references `welding3d.ts` and the test.
