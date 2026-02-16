
Here’s the enhanced exploration write-up for the metal heatmap Y-position clipping bug.

## Location

`.cursor/explore-outputs/metal-heatmap-y-position-clipping-exploration-enhanced.md`

## Summary

### Root cause

- Metal surface max Y = -0.6 + 0.5 = **-0.1**
- Weld pool center Y = **-0.2**
- Metal surface is above the weld pool → clipping

### Recommended approach: lower workpiece only

1. Move workpiece base Y from **-0.6** to **-0.85**
2. Metal max surface = -0.85 + 0.5 = **-0.35**
3. Gap to weld pool = **0.15** units

### Decisions

| Decision | Choice |
|---------|--------|
| Approach | **A: Lower workpiece only** — do not change `uMaxDisplacement` |
| `HeatmapPlate3D` | Unchanged — keep `uMaxDisplacement` at 0.5 |
| Constants | Add `welding3d.ts` with `WORKPIECE_BASE_Y`, `ANGLE_RING_Y`, etc. |
| Alignment | Angle ring -0.84, grid -0.85, ContactShadows -0.84 |
| Flat vs thermal | Same base Y for both |

### Files to change

1. **New:** `my-app/src/constants/welding3d.ts` — scene Y constants
2. **Modify:** `TorchWithHeatmap3D.tsx` — replace magic numbers with constants (lines ~189, 212, 222, 225)
3. **Optional:** Update `ThermalPlate` JSDoc

### Effort

~2.5–3 hours (issue estimate was 4–8 h)

### Quality metrics

- 5 similar implementations reviewed  
- 5 approaches compared (A, B, C, D, E)  
- 3 prototypes (math validation, constants layout, integration)  
- 8 architectural decisions  
- 5 checkpoints  
- Confidence: 8/10  

The document is ready for the Planning phase. Should I draft the implementation plan next?
