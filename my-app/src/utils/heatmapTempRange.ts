/**
 * Compute min/max temperature from heatmap points with fallback.
 *
 * Extracted for reuse across team report, compare, replay.
 * Handles: empty array, null/undefined points, invalid temp_celsius.
 */

import { THERMAL_MIN_TEMP, THERMAL_ABSOLUTE_MAX } from "@/constants/thermal";

/**
 * Returns { min, max } from points, or fallback when empty/invalid.
 * Fallbacks from thermal constants (0°C, 600°C).
 * Filters out null, undefined, NaN, Infinity.
 */
export function computeMinMaxTemp(
  points:
    | Array<{ temp_celsius?: number | null }>
    | null
    | undefined,
  fallbackMin: number = THERMAL_MIN_TEMP,
  fallbackMax: number = THERMAL_ABSOLUTE_MAX
): { min: number; max: number } {
  if (!points || !Array.isArray(points) || points.length === 0) {
    return { min: fallbackMin, max: fallbackMax };
  }
  const temps = points
    .map((p) => p?.temp_celsius)
    .filter((t): t is number => t != null && Number.isFinite(t));
  if (temps.length === 0) {
    return { min: fallbackMin, max: fallbackMax };
  }
  const min = Math.min(...temps);
  const max = Math.max(...temps);
  if (min > max || !Number.isFinite(min) || !Number.isFinite(max)) {
    return { min: fallbackMin, max: fallbackMax };
  }
  return { min, max };
}
