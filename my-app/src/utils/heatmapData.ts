/**
 * Heatmap data extraction for thermal visualization.
 * extractHeatmapData is a data adapter: it flattens raw thermal frames into a clean (time × distance → temperature) grid that heatmap libraries can render without knowing anything about welding data.
 *
 * Transforms canonical Frame data into a grid format suitable
 * for heatmap rendering (time × distance → temperature).
 *
 * The output is a flat array of data points that any heatmap
 * library (recharts, d3, visx) can consume.
 */

import type { Frame } from "@/types/frame";
import type { ThermalDirection } from "@/types/thermal";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Single data point for heatmap rendering.
 *
 * Represents one temperature reading at a specific time and distance.
 */
export interface HeatmapDataPoint {
  /** Timestamp in milliseconds since session start. */
  timestamp_ms: number;
  /** Distance along weld seam in millimeters. */
  distance_mm: number;
  /** Temperature in degrees Celsius. */
  temp_celsius: number;
  /** Direction of this reading (for filtering by direction). */
  direction: ThermalDirection;
}

/**
 * Complete heatmap dataset extracted from frames.
 */
export interface HeatmapData {
  /** Flat array of data points for rendering. */
  points: HeatmapDataPoint[];
  /** Sorted unique timestamps in the dataset (ms). */
  timestamps_ms: number[];
  /** Sorted unique distances in the dataset (mm). */
  distances_mm: number[];
  /** Total number of data points. */
  point_count: number;
}

// ---------------------------------------------------------------------------
// Extraction
// ---------------------------------------------------------------------------

/**
 * Extract heatmap data from an array of frames.
 *
 * Filters to frames with thermal data, then flattens all thermal
 * snapshots into a grid of (timestamp, distance, temperature) points.
 *
 * @param frames - Array of frames to extract from.
 * @param direction - Which thermal direction to extract. Default: "center".
 * @returns Heatmap dataset ready for rendering.
 */
export function extractHeatmapData(
  frames: Frame[],
  direction: ThermalDirection = "center"
): HeatmapData {
  const points: HeatmapDataPoint[] = [];
  const timestampSet = new Set<number>();
  const distanceSet = new Set<number>();

  for (const frame of frames) {
    if (!frame.has_thermal_data) continue;

    for (const snapshot of frame.thermal_snapshots) {
      if (!snapshot.readings || snapshot.readings.length === 0) continue;
      const reading = snapshot.readings.find(
        (r) => r.direction === direction
      );
      if (!reading) continue;

      points.push({
        timestamp_ms: frame.timestamp_ms,
        distance_mm: snapshot.distance_mm,
        temp_celsius: reading.temp_celsius,
        direction,
      });

      timestampSet.add(frame.timestamp_ms);
      distanceSet.add(snapshot.distance_mm);
    }
  }

  return {
    points,
    timestamps_ms: [...timestampSet].sort((a, b) => a - b),
    distances_mm: [...distanceSet].sort((a, b) => a - b),
    point_count: points.length,
  };
}
