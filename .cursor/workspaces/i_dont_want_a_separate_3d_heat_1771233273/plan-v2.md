
All five refinements are applied and saved in `.cursor/plans/unified-torch-heatmap-implementation-blueprint.md`:

1. **Step 2.2a — ThermalPlate props interface** — Added explicit `ThermalPlateProps` (`frame`, `maxTemp?`, `minTemp?`, `plateSize?`, `colorSensitivity?`).

2. **Step 2.3 — Row 2 layout** — Documented that the primary session’s `thermal_frames` alone controls Row 2 layout; comparison session thermal is ignored.

3. **Step 2.1 — extractFivePointFromFrame unit tests** — Added instructions for `frameUtils.test.ts` covering: null frame, `has_thermal_data: false`, empty snapshots/readings, missing directions (fallback to DEFAULT_AMBIENT_CELSIUS), and full 5-point readings.

4. **Step 2.5 — webgl constants comments** — Added subtask to update `MAX_TORCHVIZ3D_PER_PAGE` comment to: “TorchViz3D or TorchWithHeatmap3D (Canvas-equivalent) per page.”

5. **Step 3.3 vs 4.4 — Test file sequencing** — Clarified that `TorchWithHeatmap3D.test.tsx` is created in Step 3.3 with the smoke test, and Step 4.4 extends it with mount, flat, thermal, and context-loss tests. Dependency table updated: 4.4 depends on 3.3.
