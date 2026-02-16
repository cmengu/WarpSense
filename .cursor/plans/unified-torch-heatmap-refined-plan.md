# Unified Torch + 3D Heatmap — Refined Plan (Post-Implementation)

**Task:** One 3D view with torch + heat on metal (no separate heatmap). Visible color changes at 5–10°C. Heat clearly progressing from 0° → 500° over replay.

**Date:** 2025-02-16  
**Status:** Core implementation done; tuning and verification per user feedback.  
**Reference:** `.cursor/plans/unified-torch-heatmap-replay-plan.md`

---

## What’s Already Done

| Item | Status | Location |
|------|--------|----------|
| **Unified component** | ✅ | `TorchWithHeatmap3D` — torch + thermal metal in one Canvas |
| **Replay integration** | ✅ | 2× TorchWithHeatmap3D (current vs comparison); no separate HeatmapPlate3D |
| **Demo integration** | ✅ | 2× TorchWithHeatmap3D (expert vs novice) |
| **5–10° color sensitivity** | ✅ | `colorSensitivity=10` → 50 steps over 0–500°C; stepped gradient in shader |
| **0–500°C scale** | ✅ | `THERMAL_MIN_TEMP=0`, `THERMAL_MAX_TEMP=500` in `constants/thermal.ts` |
| **Stepped gradient** | ✅ | 8 anchors (dark blue → cyan → teal → green → yellow → orange → red) |
| **Thermal carry-forward** | ✅ | `getFrameAtTimestamp` reuses last thermal frame between samples; no flicker |
| **Canvas limit** | ✅ | 2 Canvases per page; WebGL context-loss handling |

---

## User Feedback → Action Items

### 1. “Variations in heat color is too little”

**Current:** `colorSensitivity=10` → 50 steps (10°C per visible step).

**Options:**

| Action | Change | Result |
|--------|--------|--------|
| **A. Finer steps** | Set `THERMAL_COLOR_SENSITIVITY=5` | 100 steps; 5°C per visible step. More distinct colors. |
| **B. Sharper banding** | Increase step quantization in shader | Stronger visual contrast between adjacent temps (may look more “blocky”). |
| **C. LUT fallback** | 1D texture with 500 entries | One color per °C; maximum resolution. Use if A/B insufficient. |

**Recommended:** Start with **A** (5° per step). If still not enough, add **B** (stronger step edges) or **C** (LUT).

**Implementation:**  
- Change `THERMAL_COLOR_SENSITIVITY` from `10` to `5` in `my-app/src/constants/thermal.ts`.  
- No shader changes needed; `uStepCelsius` already controls step size.

---

### 2. “I want to see heat travel through the metal, 0° → 500°”

**Current:** Carry-forward shows the latest thermal frame until the next sample. As the timeline advances, new thermal samples update the grid → heat appears to move with time.

**Already working:**

1. At t=0: cool (blue) metal.
2. Scrubbing forward: each new thermal sample updates colors.
3. Heat spreads spatially (5-point IDW interpolation).
4. Scrub back: frame at or before timestamp is shown.

**If heat feels like it “teleports” instead of “travels”:**

- Thermal samples are sparse (~5 Hz). Between samples, the same frame is kept (exact replay).
- Temporal smoothing (e.g. blending current + previous frame) would add synthetic transitions and breaks “exact replay.”
- **Recommendation:** Keep exact replay. Improve perceived travel by:
  - Confirming thermal sample rate is sufficient.
  - Making sure `colorSensitivity=5` (or lower) makes each incremental update clearly visible.
  - Optionally: subtle animation of new heat spreading (future enhancement, with clear accuracy caveats).

**Verification steps:**

1. Open replay with thermal data.
2. t=0: mostly blue.
3. Scrub to mid-session: warmer center, cooler edges.
4. Scrub to end: hottest zones expanded.
5. Scrub back/forth: colors update without flicker, heat holds until next sample.

---

### 3. “No separate 3D heatmap — heat on metal with torch”

**Status:** ✅ Implemented.  
- TorchWithHeatmap3D shows torch above thermally-colored metal in a single view.  
- HeatmapPlate3D is deprecated on replay/demo; kept only for dev/standalone.

---

## Concrete Next Steps

### Step 1: Increase color sensitivity to 5°C (≈30 min)

1. In `my-app/src/constants/thermal.ts`:
   ```ts
   export const THERMAL_COLOR_SENSITIVITY = 5;  // was 10
   ```
2. Visual check: two regions differing by ~5°C (e.g. 100 vs 105) should be distinguishable.
3. If banding is too strong, consider a softer step transition (e.g. small smooth zone around step boundaries).

### Step 2: Verify heat progression (≈30 min)

1. Run demo or replay with thermal data.
2. Scrub: cool → warm → hot over time.
3. Note any flicker or abrupt “teleporting.”
4. Document any remaining UX issues.

### Step 3 (optional): Sharper step edges

If 5° steps still look too smooth:

- In fragment shader: add a small dead zone around each step boundary so adjacent steps are more distinct.
- Or: clamp `stepNorm` more aggressively before segment lookup.
- Balance: sharpness vs visible banding.

### Step 4 (optional): LUT texture fallback

If both 5° and sharper steps are insufficient:

- Generate a 500-entry 1D texture (0–500°C → color).
- Sample by `floor(vTemperature)` in the shader.
- One color per °C; highest resolution.

---

## Quick Reference

| Prop / constant | Purpose |
|-----------------|---------|
| `THERMAL_COLOR_SENSITIVITY` | Degrees per visible step (5 or 10) |
| `THERMAL_MAX_TEMP` | Top of scale (500°C) |
| `THERMAL_MIN_TEMP` | Bottom of scale (0°C) |
| `maxTemp`, `minTemp`, `colorSensitivity` | Per-component overrides |

---

## Verification Checklist

- [ ] `colorSensitivity=5` gives clearly visible 5° differences
- [ ] Heat progresses from blue (0°C) to red (500°C) over replay timeline
- [ ] No separate 3D heatmap block; heat is on the metal under the torch
- [ ] Scrub back/forth: no flicker, carry-forward works
- [ ] 2 Canvases max on replay/demo
