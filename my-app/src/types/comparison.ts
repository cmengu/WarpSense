/**
 * Comparison type definitions for session-to-session deltas.
 *
 * Mirrors the backend Pydantic models in `backend/models/comparison.py` exactly.
 * Field names use snake_case — no conversion layer between backend and frontend.
 *
 * These types are generic: they represent the delta between any two sessions
 * (session_a - session_b). There is no binary role assumption (e.g. expert
 * vs novice). The caller decides which session is "a" and which is "b".
 *
 * Sign convention:
 *   positive delta = session_a value is higher than session_b
 *   negative delta = session_a value is lower than session_b
 *
 * Deltas are aligned by timestamp. If one session has a frame at a given
 * timestamp and the other does not, no delta is produced for that timestamp.
 */

import type { ThermalDirection } from "./thermal";

// ---------------------------------------------------------------------------
// TemperatureDelta
// ---------------------------------------------------------------------------

/**
 * Delta between two temperature readings at a single direction.
 *
 * Mirrors `backend/models/comparison.py → TemperatureDelta`.
 *
 * @example
 * ```typescript
 * const delta: TemperatureDelta = {
 *   direction: "center",
 *   delta_temp_celsius: 15.2, // session_a was 15.2°C hotter
 * };
 * ```
 */
export interface TemperatureDelta {
  /** Thermal direction label (e.g. "center", "north"). */
  direction: string;

  /**
   * Temperature delta in Celsius (session_a - session_b).
   * Positive = session_a is hotter. Negative = session_a is cooler.
   */
  delta_temp_celsius: number;
}

// ---------------------------------------------------------------------------
// ThermalDelta
// ---------------------------------------------------------------------------

/**
 * Delta between two thermal snapshots at a fixed distance along the weld.
 *
 * Mirrors `backend/models/comparison.py → ThermalDelta`.
 *
 * Contains per-direction temperature deltas for the given distance.
 * Only distances that exist in both sessions are compared.
 *
 * @example
 * ```typescript
 * const thermalDelta: ThermalDelta = {
 *   distance_mm: 10.0,
 *   readings: [
 *     { direction: "center", delta_temp_celsius: 15.2 },
 *     { direction: "north",  delta_temp_celsius: 8.7  },
 *     { direction: "south",  delta_temp_celsius: 12.1 },
 *     { direction: "east",   delta_temp_celsius: -3.4 },
 *     { direction: "west",   delta_temp_celsius: 5.6  },
 *   ],
 * };
 * ```
 */
export interface ThermalDelta {
  /** Distance along weld seam in millimeters for this comparison. */
  distance_mm: number;

  /** Per-direction temperature deltas. May be empty if no readings align. */
  readings: TemperatureDelta[];
}

// ---------------------------------------------------------------------------
// FrameDelta
// ---------------------------------------------------------------------------

/**
 * Delta between two frames aligned by timestamp.
 *
 * Mirrors `backend/models/comparison.py → FrameDelta`.
 *
 * All delta fields follow (session_a - session_b) sign convention.
 * Optional fields are `null` when one or both sessions lack the sensor
 * reading at this timestamp.
 *
 * @example
 * ```typescript
 * const frameDelta: FrameDelta = {
 *   timestamp_ms: 100,
 *   amps_delta: 5.0,
 *   volts_delta: -1.2,
 *   angle_degrees_delta: 3.5,
 *   heat_dissipation_rate_celsius_per_sec_delta: -0.8,
 *   thermal_deltas: [
 *     {
 *       distance_mm: 10.0,
 *       readings: [
 *         { direction: "center", delta_temp_celsius: 15.2 },
 *       ],
 *     },
 *   ],
 * };
 * ```
 */
export interface FrameDelta {
  /**
   * Timestamp in milliseconds since session start.
   * Must be >= 0. Both sessions must have a frame at this timestamp
   * for a delta to be produced.
   */
  timestamp_ms: number;

  /**
   * Current delta in amps (session_a - session_b).
   * `null` if either session lacks an amps reading at this timestamp.
   */
  amps_delta: number | null;

  /**
   * Voltage delta in volts (session_a - session_b).
   * `null` if either session lacks a volts reading at this timestamp.
   */
  volts_delta: number | null;

  /**
   * Angle delta in degrees (session_a - session_b).
   * `null` if either session lacks an angle reading at this timestamp.
   */
  angle_degrees_delta: number | null;

  /**
   * Heat dissipation rate delta in °C/sec (session_a - session_b).
   * `null` if either session lacks a dissipation value at this timestamp.
   */
  heat_dissipation_rate_celsius_per_sec_delta: number | null;

  /**
   * Thermal deltas for this frame (one per aligned distance).
   * Empty array if neither session has thermal data at this timestamp.
   */
  thermal_deltas: ThermalDelta[];
}

// ---------------------------------------------------------------------------
// Runtime validation
// ---------------------------------------------------------------------------

/**
 * Validate that a `FrameDelta` satisfies the canonical contract at runtime.
 *
 * Checks performed:
 *   1. `timestamp_ms` is a non-negative integer.
 *   2. Optional numeric delta fields are either `null` or a finite number.
 *   3. `thermal_deltas` distances are positive numbers.
 *
 * @param delta - The frame delta to validate.
 * @returns An array of error messages (empty if valid).
 */
export function validateFrameDelta(delta: FrameDelta): string[] {
  const errors: string[] = [];

  // 1. timestamp_ms: non-negative integer
  if (
    typeof delta.timestamp_ms !== "number" ||
    !Number.isInteger(delta.timestamp_ms) ||
    delta.timestamp_ms < 0
  ) {
    errors.push(
      `timestamp_ms must be a non-negative integer, got ${delta.timestamp_ms}`
    );
  }

  // 2. Optional numeric fields: null or finite number
  const optionalFields: Array<{ name: string; value: number | null }> = [
    { name: "amps_delta", value: delta.amps_delta },
    { name: "volts_delta", value: delta.volts_delta },
    { name: "angle_degrees_delta", value: delta.angle_degrees_delta },
    {
      name: "heat_dissipation_rate_celsius_per_sec_delta",
      value: delta.heat_dissipation_rate_celsius_per_sec_delta,
    },
  ];

  for (const { name, value } of optionalFields) {
    if (
      value !== null &&
      (typeof value !== "number" || !Number.isFinite(value))
    ) {
      errors.push(`${name} must be null or a finite number, got ${value}`);
    }
  }

  // 3. Thermal delta distances must be positive
  for (let i = 0; i < delta.thermal_deltas.length; i++) {
    const td = delta.thermal_deltas[i];
    if (typeof td.distance_mm !== "number" || td.distance_mm <= 0) {
      errors.push(
        `thermal_deltas[${i}].distance_mm must be positive, got ${td.distance_mm}`
      );
    }
  }

  return errors;
}
