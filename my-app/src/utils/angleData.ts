/**
 * Torch angle data extraction for time-series visualization.
 *
 * Transforms canonical Frame data into a simple time series
 * of (timestamp, angle) points for line chart rendering.
 */

import type { Frame } from "@/types/frame";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * Single data point for torch angle graph.
 */
export interface AngleDataPoint {
  /** Timestamp in milliseconds since session start. */
  timestamp_ms: number;
  /** Torch angle in degrees. */
  angle_degrees: number;
}

/**
 * Complete angle dataset extracted from frames.
 */
export interface AngleData {
  /** Time-series data points (only frames with angle data). */
  points: AngleDataPoint[];
  /** Total number of data points. */
  point_count: number;
  /** Minimum angle in the dataset (degrees). Null if no data. */
  min_angle_degrees: number | null;
  /** Maximum angle in the dataset (degrees). Null if no data. */
  max_angle_degrees: number | null;
  /** Average angle in the dataset (degrees). Null if no data. */
  avg_angle_degrees: number | null;
}

// ---------------------------------------------------------------------------
// Extraction
// ---------------------------------------------------------------------------

/**
 * Extract torch angle time-series data from an array of frames.
 *
 * Filters out frames where `angle_degrees` is null (partial frames),
 * then produces a sorted array of (timestamp, angle) points.
 *
 * @param frames - Array of frames to extract from.
 * @returns Angle dataset with statistics, ready for rendering.
 */
export function extractAngleData(frames: Frame[]): AngleData {
  const points: AngleDataPoint[] = [];

  for (const frame of frames) {
    if (frame.angle_degrees === null) continue;
    points.push({
      timestamp_ms: frame.timestamp_ms,
      angle_degrees: frame.angle_degrees,
    });
  }

  // Sort by timestamp (should already be sorted, but be safe)
  points.sort((a, b) => a.timestamp_ms - b.timestamp_ms);

  if (points.length === 0) {
    return {
      points,
      point_count: 0,
      min_angle_degrees: null,
      max_angle_degrees: null,
      avg_angle_degrees: null,
    };
  }

  let min = points[0].angle_degrees;
  let max = points[0].angle_degrees;
  let sum = 0;

  for (const p of points) {
    if (p.angle_degrees < min) min = p.angle_degrees;
    if (p.angle_degrees > max) max = p.angle_degrees;
    sum += p.angle_degrees;
  }

  return {
    points,
    point_count: points.length,
    min_angle_degrees: min,
    max_angle_degrees: max,
    avg_angle_degrees: sum / points.length,
  };
}
