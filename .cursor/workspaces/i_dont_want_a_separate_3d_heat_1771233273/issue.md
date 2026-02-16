
Created the issue document at `.cursor/issues/unified-torch-heatmap-on-metal.md`. Summary:

## Summary

The issue documents three main requests:

### 1. **Unified view (no separate 3D heatmap)**

- **Current:** TorchViz3D (torch + flat gray metal) + separate HeatmapPlate3D (thermal plate) side by side.
- **Desired:** Single view: thermal data rendered on the metal surface under the 3D torch.

**Approach:** Replace the flat workpiece in TorchViz3D with a thermal mesh when `frames` and `activeTimestamp` are provided. Remove HeatmapPlate3D from replay and the demo expert column.

### 2. **Fine color sensitivity (5–10°C)**

- **Current:** ~50°C steps (13 anchors in `heatmapData.ts`) and 4 broad bands in the HeatmapPlate3D fragment shader.
- **Desired:** 5–10°C differences clearly distinguishable.

**Approach:** Use finer anchors (every 5–10°C) or a perceptual gradient (e.g. stretch in the 350–500°C band), or a LUT texture. To be decided in the exploration phase.

### 3. **Heat propagation (0° → 500°C)**

- **Current:** Only spatial thermal distribution at the current frame.
- **Desired:** Heat visibly “traveling” through the metal as playback runs.

**Open question:** Whether “heat travel” means:
- **Spatial:** Spread at one moment (already in place) vs.
- **Temporal:** Accumulated heat over time, possibly using `heat_dissipation_rate`.

The issue assumes starting with spatial only; temporal behavior is marked for exploration.

---

## Benefits

- **Fewer Canvases:** Replay goes from 3 Canvases to 2 (no separate HeatmapPlate3D).
- **Single view:** Torch and thermal data in one scene.
- **More accurate feedback:** 5–10°C differences visible for weld quality.

---

## Next steps

1. Answer open questions in the issue (especially “heat travel”).
2. Move to **Explore Feature** to choose:
   - Gradient approach (LUT vs parametric vs finer anchors).
   - Temporal heat behavior.
   - Workpiece geometry and layout.
3. Create the **Implementation Plan**.

I can start the exploration phase next, or we can refine the issue first—for example, by clarifying what “heat travel” means to you (spatial only vs. temporal accumulation).
