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
import { hasThermalData } from "@/utils/frameUtils";

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
// Color mapping: visible change every 50°C (20°C → 600°C)
// ---------------------------------------------------------------------------

/**
 * Anchors every 50°C from 20 to 600 for a varied gradient:
 * blue → sky → cyan → teal → green → lime → yellow → amber → orange → red → dark red.
 * [temp_celsius, r, g, b]
 */
const TEMP_COLOR_ANCHORS: [number, number, number, number][] = [
  [20, 59, 130, 246],    // blue
  [70, 14, 165, 233],    // sky
  [120, 6, 182, 212],    // cyan
  [170, 20, 184, 166],   // teal
  [220, 34, 197, 94],    // green
  [270, 132, 204, 22],   // lime
  [320, 234, 179, 8],    // yellow
  [370, 245, 158, 11],   // amber
  [420, 249, 115, 22],   // orange
  [470, 239, 68, 68],    // red
  [520, 220, 38, 38],    // red-600
  [570, 185, 28, 28],    // red-700
  [600, 239, 68, 68],    // red (same as 470 for consistent “max”)
];

/**
 * Map temperature in Celsius to hex color with a varied scale: visible change every 50°C.
 * Progression: blue → sky → cyan → teal → green → lime → yellow → amber → orange → red → dark red.
 * Clamps to [20, 600]°C. Linear interpolation between consecutive anchors.
 */
export function tempToColor(temp_celsius: number): string {
  const t = Math.max(20, Math.min(600, temp_celsius));
  for (let i = 0; i < TEMP_COLOR_ANCHORS.length - 1; i++) {
    const [t0, r0, g0, b0] = TEMP_COLOR_ANCHORS[i];
    const [t1, r1, g1, b1] = TEMP_COLOR_ANCHORS[i + 1];
    if (t >= t0 && t <= t1) {
      const p = (t - t0) / (t1 - t0);
      const r = Math.round(r0 + (r1 - r0) * p);
      const g = Math.round(g0 + (g1 - g0) * p);
      const b = Math.round(b0 + (b1 - b0) * p);
      return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
    }
  }
  const [_, r, g, b] = TEMP_COLOR_ANCHORS[TEMP_COLOR_ANCHORS.length - 1];
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

/**
 * Create a color function that maps a specific temperature range to blue→yellow→red.
 * Use on compare page so Session A and Session B share the same scale: min (both) → blue,
 * max (both) → red. Makes small differences between sessions visible (otherwise both
 * sit in the same 400–550°C band and look similar).
 *
 * @param minTemp - Temperature that maps to blue (cold).
 * @param maxTemp - Temperature that maps to red (hot). Must be > minTemp.
 * @returns (temp_celsius: number) => string, or tempToColor if range is invalid.
 */
export function tempToColorRange(
  minTemp: number,
  maxTemp: number
): (temp_celsius: number) => string {
  const span = maxTemp - minTemp;
  if (span <= 0 || !Number.isFinite(span)) {
    return tempToColor;
  }
  return (temp_celsius: number) => {
    const p = Math.max(0, Math.min(1, (temp_celsius - minTemp) / span));
    const t = 20 + p * (600 - 20);
    return tempToColor(t);
  };
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
    if (!hasThermalData(frame)) continue;

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
