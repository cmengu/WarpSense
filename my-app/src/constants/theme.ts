/**
 * WarpSense theme — blue/purple-only dark palette.
 * Single source of truth for thermal gradient, chart colors, semantic colors.
 * Thermal: 8 anchors, 0–500°C, blue (cold) → purple (hot).
 *
 * THERMAL_ANCHOR_COLORS_0_1: Array index i maps to shader anchorPos[i].
 * Shader positions are [0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0] (not 0.125, 0.25, etc.).
 * Keep heatmapData, heatmapShaderUtils, and GLSL aligned using these positions.
 */

/** 8 anchors [temp_celsius, r, g, b] for thermal gradient. Range [0, 500]°C. */
export const THERMAL_COLOR_ANCHORS: [number, number, number, number][] = [
  [0, 30, 58, 138],    // blue-900 #1e3a8a
  [62, 37, 99, 235],   // blue-600 #2563eb
  [125, 79, 70, 229],  // indigo-600 #4f46e5
  [187, 99, 102, 241], // indigo-500 #6366f1
  [250, 124, 58, 237], // violet-600 #7c3aed
  [312, 139, 92, 246], // purple-500 #8b5cf6
  [375, 168, 85, 247], // purple-500 #a855f7
  [500, 168, 85, 247], // purple-500 (max)
];

/**
 * 0–1 RGB at 8 positions for heatmapShaderUtils and GLSL shader.
 * Array index i maps to shader anchorPos[i]; positions are [0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0].
 */
export const THERMAL_ANCHOR_COLORS_0_1: readonly [number, number, number][] = [
  [0.12, 0.23, 0.54],  // position 0
  [0.15, 0.39, 0.92],  // position 0.1
  [0.31, 0.27, 0.90],  // position 0.2
  [0.39, 0.40, 0.95],  // position 0.3
  [0.49, 0.23, 0.93],  // position 0.5
  [0.55, 0.36, 0.96],  // position 0.7
  [0.66, 0.33, 0.97],  // position 0.9
  [0.66, 0.33, 0.97],  // position 1.0
];

/** Chart palette: 6 blue/purple hex values. */
export const CHART_PALETTE = [
  '#2563eb', '#4f46e5', '#7c3aed', '#8b5cf6', '#6366f1', '#9333ea',
];

/** Expert welder accent (blue). */
export const EXPERT_HEX = '#2563eb';

/** Novice welder accent (purple). */
export const NOVICE_HEX = '#a855f7';

/** Error/danger (violet). */
export const ERROR_HEX = '#7c3aed';

/** HeatMap active column outline. */
export const ACTIVE_COLUMN_HEX = '#3b82f6';

/** TorchAngleGraph target line. */
export const TARGET_LINE_HEX = '#a855f7';
