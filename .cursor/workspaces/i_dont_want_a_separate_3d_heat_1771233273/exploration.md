
I’ve finished the technical exploration and wrote it to `.cursor/agents/unified-torch-heatmap-explore-output.md`. Summary:

---

## TL;DR

**Recommended approach:** Add a new **`TorchWithHeatmap3D`** component that combines torch and thermal metal in one Canvas, replacing the separate HeatmapPlate3D.

**Core decisions:**

1. **Unified view** – Single component: torch above thermally-colored metal. No separate HeatmapPlate3D. Canvas count goes from 3 to 2 (replay: 2 TorchWithHeatmap3D).

2. **5–10°C color sensitivity** – Use a stepped gradient in the fragment shader with `uStepCelsius=10` (50 steps over 0–500°C). 8 anchor colors from dark blue → cyan → teal → green → yellow → orange → red. If banding appears, fall back to a LUT texture.

3. **Heat travel** – Treat it as spatial only in Phase 1: show heat spread at the current frame and carry it forward between thermal samples (no temporal accumulation). `getFrameAtTimestamp` already does this by reusing the last frame until the next thermal sample.

**Other decisions:**

- **Workpiece size:** 3×3 (as in TorchViz3D) so the torch stays focal; 100×100 grid keeps thermal detail.
- **extractFivePointFromFrame:** Move to `frameUtils.ts` for shared use.
- **Temperature range:** 0–500°C as requested.
- **Vertex warp:** Keep for thermal expansion.

**Risks and mitigations:**

- Gradient doesn’t meet 5–10° → implement LUT fallback.
- “Heat travel” scope creep → Phase 1 = spatial only; temporal is Phase 2.
- Workpiece too small → Make `plateSize` configurable (default 3).

**Effort:** ~8–12 hours total.

---

There is already an implementation plan at `.cursor/plans/unified-torch-heatmap-replay-plan.md` that matches this exploration. It includes:

- Phase 1: Color sensitivity (stepped gradient)
- Phase 2: TorchWithHeatmap3D and replay/demo integration
- Phase 3: Heat travel verification (carry-forward behavior)
- Phase 4: Deprecation and cleanup

I can:

1. Create a refined implementation plan that folds in the exploration findings.
2. Start implementing by extracting `extractFivePointFromFrame` and the stepped gradient.
3. Do something else you specify.
