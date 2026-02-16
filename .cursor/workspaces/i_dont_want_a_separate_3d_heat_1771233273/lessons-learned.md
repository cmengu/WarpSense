
Here’s what was added to `LEARNING_LOG.md`:

1. **Header note**  
   Brief description of the unified torch+heatmap pattern.

2. **Quick Reference row**  
   New entry in the incidents table:
   - **2025-02-16 — Unified Torch + Thermal Metal (Replay)** | Frontend | Medium

3. **Section: Frontend / 3D Thermal Visualization**  
   New incident-style entry covering:
   - **What was done:** TorchWithHeatmap3D replaces separate TorchViz3D + HeatmapPlate3D; single Canvas; heat travel 0–500°C; 10°C per visible step.
   - **Impact:** One 3D view per session, `THERMAL_COLOR_SENSITIVITY=10` for ~50 steps; use `5` for finer (5°C) steps.
   - **Patterns:** Before/after code for the unified component.
   - **Do/Don’t:** Use TorchWithHeatmap3D; keep `heatmapShaderUtils.ts` in sync with shader; avoid extra HeatmapPlate3D.
   - **AI guidance:** Prompt for adding thermal visualization.

Color sensitivity note: `THERMAL_COLOR_SENSITIVITY=10` gives one step per 10°C (50 steps over 0–500°C). To see smaller changes (≈5°C), set it to `5` in `my-app/src/constants/thermal.ts`.
