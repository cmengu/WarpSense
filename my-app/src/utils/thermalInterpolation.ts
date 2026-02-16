/**
 * Thermal data interpolation for 3D heatmap plate.
 *
 * Interpolates 5-point thermal data (center, north, south, east, west) to an
 * N×N grid using Inverse Distance Weighting (IDW). Powers vertex displacement
 * and temperature→color mapping in the 3D warped heatmap.
 *
 * @see .cursor/plans/3d-warped-heatmap-plate-implementation-plan.md
 */

import { DEFAULT_AMBIENT_CELSIUS } from '@/utils/frameUtils';
import { THERMAL_ABSOLUTE_MAX } from '@/constants/thermal';

/**
 * Sanitize a temperature value for interpolation.
 * Replaces NaN/Infinity with DEFAULT_AMBIENT_CELSIUS; clamps to [0, MAX_TEMP_CELSIUS].
 *
 * @param v - Raw temperature value in Celsius.
 * @returns Valid finite temperature in [0, THERMAL_ABSOLUTE_MAX].
 */
export function sanitizeTemp(v: number): number {
  if (!Number.isFinite(v)) return DEFAULT_AMBIENT_CELSIUS;
  return Math.max(0, Math.min(THERMAL_ABSOLUTE_MAX, v));
}

/**
 * Interpolate 5-point thermal data to an N×N grid using Inverse Distance Weighting (IDW).
 *
 * Point mapping:
 *   - center = (0.5, 0.5)
 *   - north  = (0.5, 0)
 *   - south  = (0.5, 1)
 *   - east   = (1, 0.5)
 *   - west   = (0, 0.5)
 *
 * Formula: wi = 1 / (dist_i^power + eps), value = sum(wi * val_i) / sum(wi)
 * power=2, eps=0.01 for smooth falloff.
 *
 * @param centerTemp - Temperature at weld center.
 * @param northTemp - Temperature north of center.
 * @param southTemp - Temperature south of center.
 * @param eastTemp - Temperature east of center.
 * @param westTemp - Temperature west of center.
 * @param gridSize - Output grid resolution (default 100).
 * @returns 2D grid [y][x] of interpolated temperatures in Celsius.
 */
export function interpolateThermalGrid(
  centerTemp: number,
  northTemp: number,
  southTemp: number,
  eastTemp: number,
  westTemp: number,
  gridSize: number = 100
): number[][] {
  const c = sanitizeTemp(centerTemp);
  const n = sanitizeTemp(northTemp);
  const s = sanitizeTemp(southTemp);
  const e = sanitizeTemp(eastTemp);
  const w = sanitizeTemp(westTemp);

  const IDW_EPS = 0.01;
  const IDW_POWER = 2;
  const grid: number[][] = [];

  for (let y = 0; y < gridSize; y++) {
    grid[y] = [];
    for (let x = 0; x < gridSize; x++) {
      const nx = x / gridSize;
      const ny = y / gridSize;
      const distCenter = Math.sqrt((nx - 0.5) ** 2 + (ny - 0.5) ** 2);
      const distNorth = Math.sqrt((nx - 0.5) ** 2 + (ny - 0) ** 2);
      const distSouth = Math.sqrt((nx - 0.5) ** 2 + (ny - 1) ** 2);
      const distEast = Math.sqrt((nx - 1) ** 2 + (ny - 0.5) ** 2);
      const distWest = Math.sqrt((nx - 0) ** 2 + (ny - 0.5) ** 2);

      const wC = 1 / (distCenter ** IDW_POWER + IDW_EPS);
      const wN = 1 / (distNorth ** IDW_POWER + IDW_EPS);
      const wS = 1 / (distSouth ** IDW_POWER + IDW_EPS);
      const wE = 1 / (distEast ** IDW_POWER + IDW_EPS);
      const wW = 1 / (distWest ** IDW_POWER + IDW_EPS);

      const total = wC + wN + wS + wE + wW;
      let val = (c * wC + n * wN + s * wS + e * wE + w * wW) / total;
      val = Math.max(
        0,
        Math.min(THERMAL_ABSOLUTE_MAX, Number.isFinite(val) ? val : c)
      );
      grid[y][x] = val;
    }
  }
  return grid;
}
