
I've created the detailed implementation blueprint at `.cursor/plans/unified-torch-heatmap-implementation-blueprint.md`. Summary:

---

## Blueprint Summary

### Structure

**4 phases, 22 steps**

1. **Phase 1 — Color sensitivity (2.5 h)**  
   - Add `uMinTemp`, `uMaxTemp`, `uStepCelsius`  
   - Implement stepped gradient (50 steps at 10°C)  
   - Add `heatmapShaderUtils.ts` TS mirror  
   - Add unit test for 5–10°C color difference  

2. **Phase 2 — TorchWithHeatmap3D + integration (5.75 h)**  
   - Extract `extractFivePointFromFrame` to `frameUtils`  
   - Create ThermalWorkpiece subcomponent  
   - Create SceneContentWithThermal (torch + thermal/flat workpiece)  
   - Build TorchWithHeatmap3D facade  
   - Integrate into replay and demo  
   - Set `MAX_CANVAS_PER_PAGE = 2`  

3. **Phase 3 — Heat travel check (1.5 h)**  
   - Check carry-forward between thermal samples  
   - Manually verify heat progression 0°→500°C  

4. **Phase 4 — Cleanup (2 h)**  
   - Remove HeatmapPlate3D from replay/demo  
   - Update tests and docs  

**Total:** ~11 hours

### Included details

- **Pre-planning:** Synthesis, dependency graph, risk planning  
- **Code examples:** Stepped gradient GLSL, TS mirror, `extractFivePointFromFrame`  
- **Verification tests:** Per step, with setup, actions, expected results  
- **Risks:** 10 main risks plus 10 Red Team points  
- **Success criteria:** 12 P0/P1 items  
- **Pre-flight checklists:** Per phase  
- **Implementability:** 10 “junior engineer” questions with answers  

### Architectural decisions (from exploration)

1. **TorchWithHeatmap3D** — New component instead of modifying TorchViz3D  
2. **Stepped gradient** — 50 steps at 10°C; LUT kept as fallback  
3. **Workpiece size 3×3** — Matches torch view  
4. **Heat travel = spatial + carry-forward** — No temporal accumulation (per exact-replay rule)  
5. **Temperature range 0–500°C** — Per your spec  

### Files covered

- `frameUtils.ts` — `extractFivePointFromFrame`  
- `heatmapFragment.glsl.ts` — Stepped gradient  
- `heatmapShaderUtils.ts` — TS mirror for tests  
- `TorchWithHeatmap3D.tsx` — New component  
- Replay and demo pages — Replace TorchViz3D + HeatmapPlate3D with TorchWithHeatmap3D  

The plan is ready for implementation: follow the phases in order, run each step’s verification tests, and adjust estimates as you go.
