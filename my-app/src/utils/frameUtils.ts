/**
 * Safe extraction utilities for Frame data.
 *
 * These functions centralize null-checking and optional-field access
 * so that components don't need scattered `?.` and `??` checks.
 *
 * ALWAYS use these instead of accessing thermal fields directly.
 * They handle every edge case documented in the plan:
 *   - First frame (no previous thermal data)
 *   - Missing thermal frames (empty thermal_snapshots)
 *   - Empty readings array
 *   - Null sensor readings
 *
 * Mirrors the backend utility logic in `backend/services/thermal_service.py`.
 */

import type { Frame } from "@/types/frame";
import type { TemperaturePoint, ThermalDirection } from "@/types/thermal";

// ---------------------------------------------------------------------------
// extractCenterTemperature
// ---------------------------------------------------------------------------

/**
 * Safely extract center temperature from a frame.
 *
 * ALWAYS check `has_thermal_data` before accessing thermal fields!
 * Not all frames have thermal data (only every ~100ms).
 *
 * Edge cases handled:
 *   - Frame has no thermal data → null
 *   - Empty thermal_snapshots array → null
 *   - Empty readings array → null
 *   - No center reading found → null
 *
 * @param frame - Frame to extract temperature from.
 * @returns Center temperature in degrees Celsius, or null if not available.
 */
/**
 * Check if a frame has thermal data.
 * Fallback: when has_thermal_data is undefined (legacy API), use thermal_snapshots length.
 */
export function hasThermalData(frame: Frame): boolean {
  return frame.has_thermal_data ?? (frame.thermal_snapshots?.length ?? 0) > 0;
}

export function extractCenterTemperature(frame: Frame): number | null {
  if (!hasThermalData(frame)) {
    return null;
  }

  // Guard 2: empty thermal_snapshots array
  if (!frame.thermal_snapshots || frame.thermal_snapshots.length === 0) {
    return null;
  }

  // Guard 3: empty readings array in first snapshot
  const firstSnapshot = frame.thermal_snapshots[0];
  if (!firstSnapshot.readings || firstSnapshot.readings.length === 0) {
    return null;
  }

  // Guard 4: find center reading by direction (not by index)
  const center = firstSnapshot.readings.find(
    (r) => r.direction === "center"
  );

  return center?.temp_celsius ?? null;
}

// ---------------------------------------------------------------------------
// extractTemperatureByDirection
// ---------------------------------------------------------------------------

/**
 * Safely extract a temperature reading at a specific direction from a frame.
 *
 * Generalizes `extractCenterTemperature` to any direction.
 *
 * @param frame - Frame to extract from.
 * @param direction - Thermal direction to look up.
 * @param snapshotIndex - Which snapshot to use (default: 0 = primary distance).
 * @returns Temperature in degrees Celsius, or null if not available.
 */
export function extractTemperatureByDirection(
  frame: Frame,
  direction: ThermalDirection,
  snapshotIndex: number = 0
): number | null {
  if (!hasThermalData(frame)) {
    return null;
  }

  if (
    !frame.thermal_snapshots ||
    snapshotIndex >= frame.thermal_snapshots.length
  ) {
    return null;
  }

  const snapshot = frame.thermal_snapshots[snapshotIndex];
  if (!snapshot.readings || snapshot.readings.length === 0) {
    return null;
  }

  const reading = snapshot.readings.find((r) => r.direction === direction);
  return reading?.temp_celsius ?? null;
}

// ---------------------------------------------------------------------------
// extractAllTemperatures
// ---------------------------------------------------------------------------

/**
 * Extract all temperature readings from the primary snapshot of a frame.
 *
 * Returns an empty array if the frame has no thermal data.
 *
 * @param frame - Frame to extract from.
 * @param snapshotIndex - Which snapshot to use (default: 0 = primary distance).
 * @returns Array of TemperaturePoint objects, or empty array.
 */
export function extractAllTemperatures(
  frame: Frame,
  snapshotIndex: number = 0
): TemperaturePoint[] {
  if (!hasThermalData(frame)) {
    return [];
  }

  if (
    !frame.thermal_snapshots ||
    snapshotIndex >= frame.thermal_snapshots.length
  ) {
    return [];
  }

  return frame.thermal_snapshots[snapshotIndex].readings ?? [];
}

// ---------------------------------------------------------------------------
// extractHeatDissipation
// ---------------------------------------------------------------------------

/**
 * Safely extract heat dissipation rate from a frame.
 *
 * Edge cases handled:
 *   - First frame: no prev_frame → dissipation = null
 *   - Missing thermal frames: dissipation = null
 *
 * @param frame - Frame to extract dissipation from.
 * @returns Dissipation rate in °C/sec, or null if not available.
 *          Positive = cooling. Negative = heating.
 */
export function extractHeatDissipation(frame: Frame): number | null {
  // Backend pre-calculates this. Just null-guard it.
  return frame.heat_dissipation_rate_celsius_per_sec ?? null;
}

// ---------------------------------------------------------------------------
// hasRequiredSensors
// ---------------------------------------------------------------------------

/**
 * Check if a frame has all required sensor data (volts, amps, angle).
 *
 * A frame missing any of the core electrical sensor readings is considered
 * a partial frame. This is valid (the backend allows it) but components
 * should handle the missing data gracefully.
 *
 * @param frame - Frame to check.
 * @returns True if all three core sensors (volts, amps, angle) are present.
 */
export function hasRequiredSensors(frame: Frame): boolean {
  return (
    frame.volts !== null &&
    frame.amps !== null &&
    frame.angle_degrees !== null
  );
}

// ---------------------------------------------------------------------------
// extractFivePointFromFrame
// ---------------------------------------------------------------------------

/** Fallback temperature (°C) when a cardinal direction is missing from readings. */
export const DEFAULT_AMBIENT_CELSIUS = 20;

/**
 * Extract 5-point thermal readings from a frame's first thermal snapshot.
 *
 * Used by HeatmapPlate3D and TorchWithHeatmap3D for thermal workpiece rendering.
 * Reads thermal_snapshots[0].readings and maps direction → temp_celsius.
 *
 * @param frame - Frame with thermal data.
 * @returns { center, north, south, east, west } in Celsius, or null if no thermal.
 */
export function extractFivePointFromFrame(
  frame: Frame | null
): {
  center: number;
  north: number;
  south: number;
  east: number;
  west: number;
} | null {
  if (!frame?.has_thermal_data || !frame.thermal_snapshots?.[0]) return null;
  const readings = frame.thermal_snapshots[0].readings ?? [];
  const get = (d: ThermalDirection) =>
    readings.find((r) => r.direction === d)?.temp_celsius ?? DEFAULT_AMBIENT_CELSIUS;
  return {
    center: get("center"),
    north: get("north"),
    south: get("south"),
    east: get("east"),
    west: get("west"),
  };
}

// ---------------------------------------------------------------------------
// filterThermalFrames
// ---------------------------------------------------------------------------

/**
 * Filter a frame array to only those with thermal data.
 *
 * Useful for thermal-specific visualizations (heatmaps) where
 * you need to skip the 9/10 frames that lack thermal snapshots.
 *
 * Fallback: if `has_thermal_data` is undefined (legacy/incomplete API response),
 * treat frames with non-empty thermal_snapshots as having thermal data.
 *
 * @param frames - Array of frames to filter.
 * @returns Only frames where `has_thermal_data === true` or thermal_snapshots has data.
 */
export function filterThermalFrames(frames: Frame[]): Frame[] {
  return frames.filter((f) => hasThermalData(f));
}

// ---------------------------------------------------------------------------
// getFrameAtTimestamp
// ---------------------------------------------------------------------------

/**
 * Return the frame at or before a given timestamp for replay consistency.
 *
 * Used by the replay page and 3D visualization to resolve the single frame
 * that represents the weld state at `currentTimestamp`. Deterministic: no
 * interpolation; exact replay contract.
 *
 * Assumption: `frames` is sorted by `timestamp_ms` ascending (backend guarantee).
 *
 * Logic:
 *   1. Exact match: frame where timestamp_ms === timestamp.
 *   2. Else: nearest frame with timestamp_ms <= timestamp (latest at or before).
 *   3. Else: all frames are after timestamp (e.g. timestamp before session start)
 *      → return frames[0].
 *
 * @param frames - Sorted array of frames (timestamp_ms ascending).
 * @param timestamp - Target time in milliseconds.
 * @returns The resolved frame, or null if frames array is empty.
 */
export function getFrameAtTimestamp(
  frames: Frame[],
  timestamp: number
): Frame | null {
  if (frames.length === 0) {
    return null;
  }

  // Exact match first
  const exact = frames.find((f) => f.timestamp_ms === timestamp);
  if (exact) {
    return exact;
  }

  // Nearest frame with timestamp_ms <= timestamp (walk backwards from end)
  for (let i = frames.length - 1; i >= 0; i--) {
    if (frames[i].timestamp_ms <= timestamp) {
      return frames[i];
    }
  }

  // All frames are after timestamp → use first frame
  return frames[0];
}

// ---------------------------------------------------------------------------
// extractCenterTemperatureWithCarryForward
// ---------------------------------------------------------------------------

/** Fallback center temperature (°C) when no thermal data is available. */
const CENTER_TEMP_FALLBACK_CELSIUS = 450;

/**
 * Center temperature at currentTimestamp with carry-forward from last thermal frame.
 *
 * Thermal data is sparse (~100 ms); weld pool color should not flash on every
 * non-thermal frame. This walks backwards from the frame at currentTimestamp
 * to the most recent frame with thermal data and uses its center temperature.
 *
 * Assumption: `frames` sorted by `timestamp_ms` ascending.
 *
 * @param frames - Sorted array of frames.
 * @param currentTimestamp - Current replay time in milliseconds.
 * @returns Center temperature in °C, or CENTER_TEMP_FALLBACK_CELSIUS (450) if
 *   no thermal data found or frames empty.
 */
export function extractCenterTemperatureWithCarryForward(
  frames: Frame[],
  currentTimestamp: number
): number {
  if (frames.length === 0) {
    return CENTER_TEMP_FALLBACK_CELSIUS;
  }

  // Find index of frame at or before currentTimestamp (same logic as getFrameAtTimestamp)
  let idx = -1;
  for (let i = frames.length - 1; i >= 0; i--) {
    if (frames[i].timestamp_ms <= currentTimestamp) {
      idx = i;
      break;
    }
  }
  if (idx < 0) {
    idx = 0;
  }

  // Walk backwards from idx to find last frame with thermal data
  for (let i = idx; i >= 0; i--) {
    if (hasThermalData(frames[i])) {
      const temp = extractCenterTemperature(frames[i]);
      return temp ?? CENTER_TEMP_FALLBACK_CELSIUS;
    }
  }

  return CENTER_TEMP_FALLBACK_CELSIUS;
}

// ---------------------------------------------------------------------------
// filterFramesByTimeRange
// ---------------------------------------------------------------------------

/**
 * Filter frames to a specific time range (inclusive).
 *
 * @param frames - Array of frames to filter.
 * @param startMs - Start of range in milliseconds (inclusive). Null = no lower bound.
 * @param endMs - End of range in milliseconds (inclusive). Null = no upper bound.
 * @returns Frames within the specified time range.
 */
export function filterFramesByTimeRange(
  frames: Frame[],
  startMs: number | null,
  endMs: number | null
): Frame[] {
  return frames.filter((f) => {
    if (startMs !== null && f.timestamp_ms < startMs) return false;
    if (endMs !== null && f.timestamp_ms > endMs) return false;
    return true;
  });
}
