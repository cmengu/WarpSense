# Issue: Thermal Gradient — Blue/Purple → Green/Orange/Red

**Type:** Improvement  
**Priority:** Normal  
**Effort:** Small (~15 min)  
**Labels:** `frontend` `3d` `thermals` `ux`

---

## TL;DR

Replace the WarpSense blue→purple thermal gradient with a green→orange→red gradient. Cold temps = green, mid = orange, hot = red. Matches intuitive heat-mapping (IR camera style). Two files to edit; four pages pick it up automatically. Zero risk.

---

## Current State vs Expected Outcome

### Current State
- **Thermal plate (shader):** 8 anchor colors in `heatmapFragment.glsl.ts` — blue (cold) → purple (hot)
- **Weld pool sphere:** `getWeldPoolColor` in TorchViz3D and TorchWithHeatmap3D — cold blue (0x1e3a8a), mid indigo (0x6366f1), hot purple (0xa855f7), white (0xf3e8ff)
- WarpSense theme reads industrial but doesn't match thermal intuition (IR cameras = green→yellow→red)

### Expected Outcome
- Thermal plate: cold = green, mid = orange, hot = red
- Weld pool: cold = green, mid = orange, hot = red (consistent with plate)
- Gradient reads intuitively as "heat" for investors and operators

---

## Files to Edit (2 + 1)

| File | Change |
|------|--------|
| `my-app/src/components/welding/shaders/heatmapFragment.glsl.ts` | Replace 8 `anchorCol` vec3 values |
| `my-app/src/components/welding/TorchViz3D.tsx` | Update `getWeldPoolColor` cold/mid/hot/white |
| `my-app/src/components/welding/TorchWithHeatmap3D.tsx` | Update `getWeldPoolColor` — same logic, duplicated implementation |

---

## New Anchor Colors

```glsl
// Cold → mid → hot: green → orange → red
// Gray default handled by cold end being desaturated
anchorCol[0] = vec3(0.55, 0.55, 0.55);  // cool gray (ambient)
anchorCol[1] = vec3(0.18, 0.72, 0.38);  // green (cold weld)
anchorCol[2] = vec3(0.40, 0.78, 0.22);  // yellow-green
anchorCol[3] = vec3(0.85, 0.75, 0.10);  // yellow
anchorCol[4] = vec3(0.95, 0.55, 0.05);  // orange
anchorCol[5] = vec3(0.95, 0.30, 0.05);  // orange-red
anchorCol[6] = vec3(0.85, 0.10, 0.05);  // red
anchorCol[7] = vec3(0.98, 0.05, 0.05);  // hot red
```

For `getWeldPoolColor`: cold = green, mid = orange, hot = red. Keep same temp thresholds (200, 400°C) and lerp logic.

---

## Visual Blast Radius (no edits needed)

These consume the shader or torch and get the new gradient automatically:
- `TorchWithHeatmap3D.tsx` — renders both; new colors show up
- `app/demo/page.tsx`
- `app/replay/[sessionId]/page.tsx`
- `app/compare/[sessionIdA]/[sessionIdB]/page.tsx`
- `ThermalPlate.tsx`, `HeatmapPlate3D.tsx` — consume shader; no interface change

---

## Tests

- `heatmapShaders.test.ts` — does **not** assert RGB values; only ShaderMaterial construction and varying declarations. Should pass unchanged.
- Torch tests mock WebGL/Canvas; no color assertions. Safe.

---

## Risk / Notes

- **Lowest-risk change in codebase.** Shader constants only; no API or logic changes.
- **Worst case:** Heatmap looks wrong → visible instantly on `/dev/torch-viz`.
- **Single source of truth:** `getWeldPoolColor` is duplicated in TorchViz3D and TorchWithHeatmap3D. Must update both to keep weld pool and thermal plate in sync. Consider extracting to shared util later.

---

## Vision Alignment

From `vision.md`:
- "Technical credibility" — thermal viz that reads intuitively reinforces confidence
- "The story told visually" — green→red reads as heat to anyone; investor-forwardable

---

## Acceptance Criteria

- [ ] `heatmapFragment.glsl.ts` uses new 8 anchor colors
- [ ] `getWeldPoolColor` in TorchViz3D and TorchWithHeatmap3D uses green→orange→red
- [ ] Visual check on `/dev/torch-viz` and `/demo` — thermal plate and weld pool gradient consistent
- [ ] `heatmapShaders.test.ts` passes
