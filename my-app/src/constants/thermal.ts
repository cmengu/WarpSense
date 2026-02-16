/**
 * Thermal visualization constants — shared across replay, demo, and 3D components.
 * Single source of truth for temperature scale and color sensitivity.
 *
 * Override at call site or via env for materials with different melt points.
 *
 * @see .cursor/plans/unified-torch-heatmap-replay-plan.md
 */

/** Maximum temperature for color scale (°C). */
export const THERMAL_MAX_TEMP = 500;

/** Minimum temperature for color scale (°C). */
export const THERMAL_MIN_TEMP = 0;

/** Degrees per visible color step. Lower = finer gradient. */
export const THERMAL_COLOR_SENSITIVITY = 10;

/** Ceiling for interpolation/sanitization (°C). Sensors may report up to 600; display scale is 0–500. */
export const THERMAL_ABSOLUTE_MAX = 600;
