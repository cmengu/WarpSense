/**
 * Frame type definition for the canonical time-series contract.
 *
 * Mirrors the backend Pydantic model in `backend/models/frame.py` exactly.
 * Field names use snake_case — no conversion layer between backend and frontend.
 *
 * A Frame represents everything the system knows about the weld at a single
 * 10ms instant (100Hz sampling). Not all sensors fire every frame:
 *   - Electrical sensors (volts, amps, angle) may be absent → `null`.
 *   - Thermal snapshots only appear every ~100ms (5Hz) → may be empty array.
 *   - Heat dissipation is pre-calculated on ingestion → `null` for first
 *     frame or when thermal data is missing.
 *
 * WARNING: Always check `has_thermal_data` before accessing `thermal_snapshots`.
 * Always null-check optional fields before arithmetic.
 */

import type { ThermalSnapshot } from "./thermal";
import { validateThermalSnapshot } from "./thermal";

// ---------------------------------------------------------------------------
// Frame
// ---------------------------------------------------------------------------

/**
 * Single sensor frame at 100Hz (10ms interval).
 *
 * Mirrors `backend/models/frame.py → Frame`.
 *
 * @example
 * ```typescript
 * // Frame with thermal data (every ~100ms)
 * const thermalFrame: Frame = {
 *   timestamp_ms: 100,
 *   volts: 22.5,
 *   amps: 150.0,
 *   angle_degrees: 45.0,
 *   thermal_snapshots: [
 *     {
 *       distance_mm: 10.0,
 *       readings: [
 *         { direction: "center", temp_celsius: 425.3 },
 *         { direction: "north",  temp_celsius: 380.1 },
 *         { direction: "south",  temp_celsius: 390.7 },
 *         { direction: "east",   temp_celsius: 370.2 },
 *         { direction: "west",   temp_celsius: 375.0 },
 *       ],
 *     },
 *   ],
 *   has_thermal_data: true,
 *   optional_sensors: null,
 *   heat_dissipation_rate_celsius_per_sec: -5.2,
 * };
 *
 * // Frame without thermal data (majority of frames)
 * const sensorOnlyFrame: Frame = {
 *   timestamp_ms: 10,
 *   volts: 22.4,
 *   amps: 149.5,
 *   angle_degrees: 44.8,
 *   thermal_snapshots: [],
 *   has_thermal_data: false,
 *   optional_sensors: null,
 *   heat_dissipation_rate_celsius_per_sec: null,
 * };
 * ```
 */
export interface Frame {
  /**
   * Timestamp in milliseconds since session start.
   *
   * Invariants (enforced by backend Session validator):
   *   - Must be >= 0.
   *   - Must be unique across all frames in a session.
   *   - Must increase by ~10ms between consecutive frames (1ms tolerance).
   */
  timestamp_ms: number;

  /**
   * Voltage in volts, if available for this frame.
   *
   * WARNING: May be `null` if the sensor did not produce a reading.
   * Always null-check before arithmetic.
   */
  volts: number | null;

  /**
   * Current in amps, if available for this frame.
   *
   * WARNING: May be `null` if the sensor did not produce a reading.
   * Always null-check before arithmetic.
   */
  amps: number | null;

  /**
   * Torch angle in degrees, if available for this frame.
   *
   * WARNING: May be `null` if the sensor did not produce a reading.
   * Always null-check before arithmetic.
   */
  angle_degrees: number | null;

  /**
   * Thermal snapshots for this frame (may be empty).
   *
   * Most frames (9 out of 10 at 100Hz) will have an empty array here,
   * since thermal data is sampled at ~5Hz (every 100ms).
   *
   * Backend invariants:
   *   - Distances must be strictly increasing (no duplicates).
   *   - Each snapshot must have exactly 1 center reading.
   *
   * WARNING: Check `has_thermal_data` before accessing elements.
   */
  thermal_snapshots: ThermalSnapshot[];

  /**
   * Whether this frame contains any thermal data.
   *
   * This is a computed field on the backend (`len(thermal_snapshots) > 0`).
   * Sent as part of the JSON payload — do NOT recompute on the frontend.
   *
   * Usage:
   * ```typescript
   * if (frame.has_thermal_data) {
   *   // Safe to access frame.thermal_snapshots[0]
   * }
   * ```
   */
  has_thermal_data: boolean;

  /**
   * Optional sensor availability flags for partial frames.
   *
   * Maps sensor names to availability booleans. `null` means all
   * expected sensors were present. A non-null value indicates
   * which sensors were available vs missing.
   *
   * Example: `{ "ir_sensor": false, "gyroscope": true }`
   */
  optional_sensors: Record<string, boolean> | null;

  /**
   * Heat dissipation rate in degrees Celsius per second.
   *
   * Pre-calculated on ingestion by the backend thermal service.
   * Positive = cooling, Negative = heating.
   *
   * Will be `null` when:
   *   - This is the first frame (no previous frame to compare).
   *   - This frame has no thermal data.
   *   - The previous frame had no thermal data.
   *
   * WARNING: Do not recompute — use the backend-provided value.
   */
  heat_dissipation_rate_celsius_per_sec: number | null;
}

// ---------------------------------------------------------------------------
// Runtime validation
// ---------------------------------------------------------------------------

/**
 * Validate that a `Frame` satisfies the canonical contract at runtime.
 *
 * Checks performed:
 *   1. `timestamp_ms` is a non-negative integer.
 *   2. `has_thermal_data` is consistent with `thermal_snapshots` length.
 *   3. Thermal snapshot distances are strictly increasing.
 *   4. Each thermal snapshot passes `validateThermalSnapshot`.
 *   5. Optional numeric fields are either `null` or a finite number.
 *
 * @param frame - The frame to validate.
 * @returns An array of error messages (empty if valid).
 */
export function validateFrame(frame: Frame): string[] {
  const errors: string[] = [];

  // 1. timestamp_ms: non-negative integer
  if (
    typeof frame.timestamp_ms !== "number" ||
    !Number.isInteger(frame.timestamp_ms) ||
    frame.timestamp_ms < 0
  ) {
    errors.push(
      `timestamp_ms must be a non-negative integer, got ${frame.timestamp_ms}`
    );
  }

  // 2. has_thermal_data consistency
  const hasThermal = frame.thermal_snapshots.length > 0;
  if (frame.has_thermal_data !== hasThermal) {
    errors.push(
      `has_thermal_data is ${frame.has_thermal_data} but thermal_snapshots ` +
        `has ${frame.thermal_snapshots.length} elements`
    );
  }

  // 3. Thermal snapshot distances strictly increasing
  if (frame.thermal_snapshots.length > 1) {
    for (let i = 1; i < frame.thermal_snapshots.length; i++) {
      const prev_distance_mm = frame.thermal_snapshots[i - 1].distance_mm;
      const curr_distance_mm = frame.thermal_snapshots[i].distance_mm;
      if (curr_distance_mm <= prev_distance_mm) {
        errors.push(
          `Thermal snapshot distances must be strictly increasing: ` +
            `distance[${i - 1}]=${prev_distance_mm}mm >= distance[${i}]=${curr_distance_mm}mm`
        );
      }
    }
  }

  // 4. Validate each thermal snapshot
  for (let i = 0; i < frame.thermal_snapshots.length; i++) {
    const snapshotErrors = validateThermalSnapshot(frame.thermal_snapshots[i]);
    for (const err of snapshotErrors) {
      errors.push(`thermal_snapshots[${i}]: ${err}`);
    }
  }

  // 5. Optional numeric fields: null or finite number
  const optionalNumericFields: Array<{
    name: string;
    value: number | null;
  }> = [
    { name: "volts", value: frame.volts },
    { name: "amps", value: frame.amps },
    { name: "angle_degrees", value: frame.angle_degrees },
    {
      name: "heat_dissipation_rate_celsius_per_sec",
      value: frame.heat_dissipation_rate_celsius_per_sec,
    },
  ];

  for (const { name, value } of optionalNumericFields) {
    if (value !== null && (typeof value !== "number" || !Number.isFinite(value))) {
      errors.push(`${name} must be null or a finite number, got ${value}`);
    }
  }

  return errors;
}
