
I've created a refined plan at `.cursor/plans/unified-torch-heatmap-refined-plan.md`. Summary:

---

## Current state

Most of the requested behavior is already implemented:

- **Unified 3D view** — `TorchWithHeatmap3D` shows the torch and heat on metal in a single Canvas; there is no separate 3D heatmap.
- **Replay & Demo** — Both use 2× `TorchWithHeatmap3D`.
- **0–500°C scale** — `THERMAL_MIN_TEMP=0`, `THERMAL_MAX_TEMP=500`.
- **Stepped gradient** — 8 anchor colors (blue → cyan → teal → green → yellow → orange → red).
- **Carry-forward** — Same thermal frame is held between samples so the view updates only when new data arrives.

---

## Feedback → actions

### 1. “Color variations too little”

Right now `colorSensitivity=10` (≈50 steps). To get 5° steps:

- Set `THERMAL_COLOR_SENSITIVITY = 5` in `constants/thermal.ts` → 100 steps, clearer differences per 5°C.

If that’s still not enough, the plan outlines a sharper step quantization or a LUT fallback.

### 2. “See heat travel through the metal”

Carry-forward already gives temporal progression: each new thermal sample updates the grid, so heat appears to move as you scrub.  
Because of “exact replay,” we keep showing the last known thermal frame between samples and avoid synthetic interpolation. The plan suggests making sure `colorSensitivity=5` makes each update clearly visible.

### 3. “No separate 3D heatmap”

Already satisfied — heat is rendered on the metal under the torch in `TorchWithHeatmap3D`.

---

## Suggested next steps

1. **Change color sensitivity to 5°C** — one-line change in `constants/thermal.ts`.
2. **Verify heat progression** — scrub on a thermal replay and confirm cool→warm→hot over time.
3. **Optional later** — sharper step edges or a LUT texture for finer resolution.

If you want to proceed with the 5°C change, I can apply it next.
