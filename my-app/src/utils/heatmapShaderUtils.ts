/**
 * TypeScript mirror of the heatmap fragment shader temperature→color algorithm.
 *
 * Used for unit tests and documentation. The GLSL shader remains the runtime
 * source of truth. This implementation must match heatmapFragment.glsl.ts exactly.
 *
 * WarpSense theme: blue (cold) → purple (hot). Anchors from constants/theme.
 *
 * @see my-app/src/components/welding/shaders/heatmapFragment.glsl.ts
 * @see my-app/src/constants/theme.ts
 */

import { THERMAL_ANCHOR_COLORS_0_1 } from '@/constants/theme';

/** 8 anchor positions (normalized 0..1) for stepped gradient. */
const ANCHOR_POSITIONS: readonly number[] = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0];

/** RGB colors (0–1) at each anchor. Blue (cold) → purple (hot). From theme. */
const ANCHOR_COLORS = THERMAL_ANCHOR_COLORS_0_1;

/**
 * Map temperature to RGB color using stepped gradient.
 *
 * Mirrors GLSL temperatureToColor() exactly: normalize temp to [0,1], quantize
 * into steps, map stepNorm through 8 anchors with segment interpolation.
 *
 * @param minTemp - Minimum temperature in Celsius (default 0).
 * @param maxTemp - Maximum temperature in Celsius (default 500).
 * @param stepCelsius - Degrees per visible step (default 10).
 * @param temp - Temperature in Celsius.
 * @returns [r, g, b] in 0–1 range.
 */
export function temperatureToColor(
  minTemp: number,
  maxTemp: number,
  stepCelsius: number,
  temp: number
): [number, number, number] {
  // Clamp range to avoid div-by-zero (matches shader: range = max(1.0, ...))
  const range = Math.max(1, maxTemp - minTemp);
  const t = Math.max(0, Math.min(1, (temp - minTemp) / range));

  // NaN guard — use cool blue if temp is invalid
  const safeT = Number.isFinite(t) ? t : 0;

  const numSteps = Math.max(1, range / stepCelsius);
  const stepIndex = Math.max(0, Math.min(numSteps - 1, Math.floor(safeT * numSteps)));
  const stepNorm = stepIndex / numSteps;

  // Find segment: largest i such that anchorPos[i] <= stepNorm
  let segIdx = 0;
  for (let i = 0; i < ANCHOR_POSITIONS.length - 1; i++) {
    if (stepNorm >= ANCHOR_POSITIONS[i]) segIdx = i;
  }
  // Clamp for stepNorm=1 edge case (avoids out-of-bounds on cHigh)
  segIdx = Math.min(segIdx, ANCHOR_POSITIONS.length - 2);

  const low = ANCHOR_POSITIONS[segIdx];
  const high = ANCHOR_POSITIONS[segIdx + 1];
  const denom = high - low;
  const mixFactor =
    denom < 0.001
      ? 1
      : Math.max(0, Math.min(1, (stepNorm - low) / denom));

  const cLow = ANCHOR_COLORS[segIdx];
  const cHigh = ANCHOR_COLORS[segIdx + 1];
  const r = Math.max(0, Math.min(1, cLow[0] + (cHigh[0] - cLow[0]) * mixFactor));
  const g = Math.max(0, Math.min(1, cLow[1] + (cHigh[1] - cLow[1]) * mixFactor));
  const b = Math.max(0, Math.min(1, cLow[2] + (cHigh[2] - cLow[2]) * mixFactor));
  return [r, g, b];
}
