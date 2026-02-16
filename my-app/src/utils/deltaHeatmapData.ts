/**
 * Delta heatmap data extraction for session comparison.
 *
 * Flattens FrameDelta.thermal_deltas into the same HeatmapData shape as
 * heatmapData.ts so the same grid component can render with deltaTempToColor.
 * Blue = session B hotter; white = same; purple = session A hotter.
 */

import type { FrameDelta } from "@/types/comparison";
import type { HeatmapData, HeatmapDataPoint } from "@/utils/heatmapData";
import type { ThermalDirection } from "@/types/thermal";

// ---------------------------------------------------------------------------
// Delta color scale: blue (-50) → white (0) → purple (+50)
// ---------------------------------------------------------------------------

/**
 * Map temperature delta in Celsius to hex color.
 * Blue = session B hotter (negative delta); white = same; purple = session A hotter.
 * Linear interpolation between -50°C and +50°C.
 */
export function deltaTempToColor(delta_celsius: number): string {
  if (Number.isNaN(delta_celsius)) return '#ffffff';
  const d = Math.max(-50, Math.min(50, delta_celsius));
  let r: number, g: number, b: number;
  if (d <= 0) {
    // blue (-50) → white (0)
    const p = (d + 50) / 50;
    r = Math.round(59 + (255 - 59) * p);
    g = Math.round(130 + (255 - 130) * p);
    b = Math.round(246 + (255 - 246) * p);
  } else {
    // white (0) → purple (+50) #a855f7
    const p = d / 50;
    r = Math.round(255 - (255 - 168) * p);
    g = Math.round(255 - (255 - 85) * p);
    b = Math.round(255 - (255 - 247) * p);
  }
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

// ---------------------------------------------------------------------------
// Extraction
// ---------------------------------------------------------------------------

/**
 * Extract heatmap-shaped data from frame deltas for the delta column.
 *
 * Flattens thermal_deltas to points with temp_celsius = delta_temp_celsius
 * so the same HeatMap component can render using deltaTempToColor.
 *
 * @param deltas - Frame deltas from useSessionComparison.
 * @param direction - Which thermal direction to extract. Default: "center".
 * @returns HeatmapData (same shape as extractHeatmapData) for grid rendering.
 */
export function extractDeltaHeatmapData(
  deltas: FrameDelta[],
  direction: ThermalDirection = "center"
): HeatmapData {
  const points: HeatmapDataPoint[] = [];
  const timestampSet = new Set<number>();
  const distanceSet = new Set<number>();

  for (const delta of deltas) {
    if (!delta.thermal_deltas || delta.thermal_deltas.length === 0) continue;

    for (const td of delta.thermal_deltas) {
      if (!td.readings || td.readings.length === 0) continue;
      const reading = td.readings.find((r) => r.direction === direction);
      if (!reading) continue;

      points.push({
        timestamp_ms: delta.timestamp_ms,
        distance_mm: td.distance_mm,
        temp_celsius: reading.delta_temp_celsius,
        direction: reading.direction as ThermalDirection,
      });

      timestampSet.add(delta.timestamp_ms);
      distanceSet.add(td.distance_mm);
    }
  }

  return {
    points,
    timestamps_ms: [...timestampSet].sort((a, b) => a - b),
    distances_mm: [...distanceSet].sort((a, b) => a - b),
    point_count: points.length,
  };
}
