
/**
 * This file is the frontend’s strict mirror of the backend thermal gate — it makes invalid thermal data impossible to use, not just impossible to store.
 * Thermal sensor type definitions for the canonical time-series contract.
 *
 * These types mirror the backend Pydantic models in `backend/models/thermal.py`
 * exactly. Field names use snake_case to match the backend — no conversion layer.
 *
 * Data flow:
 *   Sensor hardware → Backend Pydantic validation → JSON API → These types
 *
 * Assumptions:
 *   - Every thermal snapshot has exactly 5 readings (center + 4 cardinal).
 *   - Distances are in millimeters along the weld seam.
 *   - Temperatures are in degrees Celsius.
 *   - Snapshots appear every `thermal_sample_interval_ms` (typically 100ms / 5Hz).
 */

// ---------------------------------------------------------------------------
// ThermalDirection
// ---------------------------------------------------------------------------

/**
 * Canonical thermal measurement directions.
 *
 * The sensor grid captures temperature at the weld center plus
 * four cardinal directions around it. Every `ThermalSnapshot`
 * must contain exactly one reading per direction.
 *
 * Layout (top-down view of weld):
 * ```
 *        north
 *          |
 *  west -- center -- east
 *          |
 *        south
 * ```
 */
export type ThermalDirection = "center" | "north" | "south" | "east" | "west";

/**
 * All valid thermal directions as a readonly array.
 * Useful for iteration and runtime validation.
 */
export const THERMAL_DIRECTIONS: readonly ThermalDirection[] = [
  "center",
  "north",
  "south",
  "east",
  "west",
] as const;

/**
 * Number of readings required per thermal snapshot.
 * Matches backend: `min_length=5, max_length=5`.
 */
export const READINGS_PER_SNAPSHOT = 5;

// ---------------------------------------------------------------------------
// TemperaturePoint
// ---------------------------------------------------------------------------

/**
 * Single temperature reading at a named direction.
 *
 * Mirrors `backend/models/thermal.py → TemperaturePoint`.
 *
 * @example
 * ```typescript
 * const center: TemperaturePoint = {
 *   direction: "center",
 *   temp_celsius: 425.3,
 * };
 * ```
 */
export interface TemperaturePoint {
  /** Direction of the temperature reading (center + 4 cardinal). */
  direction: ThermalDirection;

  /** Temperature in degrees Celsius at the specified direction. */
  temp_celsius: number;
}

// ---------------------------------------------------------------------------
// ThermalSnapshot
// ---------------------------------------------------------------------------

/**
 * Thermal readings at a fixed distance along the weld for one frame.
 *
 * Mirrors `backend/models/thermal.py → ThermalSnapshot`.
 *
 * Invariants enforced by the backend (and checked at runtime via guards):
 *   - `readings` has exactly 5 elements.
 *   - Each of the 5 canonical directions appears exactly once.
 *   - `distance_mm` > 0.
 *
 * @example
 * ```typescript
 * const snapshot: ThermalSnapshot = {
 *   distance_mm: 10.0,
 *   readings: [
 *     { direction: "center", temp_celsius: 425.3 },
 *     { direction: "north",  temp_celsius: 380.1 },
 *     { direction: "south",  temp_celsius: 390.7 },
 *     { direction: "east",   temp_celsius: 370.2 },
 *     { direction: "west",   temp_celsius: 375.0 },
 *   ],
 * };
 * ```
 *
 * Future expansion:
 *   - Additional directions (e.g., "northeast") would require updating
 *     `ThermalDirection`, `THERMAL_DIRECTIONS`, and `READINGS_PER_SNAPSHOT`.
 *   - A `sensor_id` field could be added if multiple sensors are used.
 */
export interface ThermalSnapshot {
  /** Distance along weld seam in millimeters for this snapshot. */
  distance_mm: number;

  /**
   * Exactly 5 temperature readings: center + 4 cardinal directions.
   *
   * WARNING: Always validate length before accessing by index.
   * Use the runtime guards below for safe access.
   */
  readings: TemperaturePoint[];
}

// ---------------------------------------------------------------------------
// Runtime validation guards
// ---------------------------------------------------------------------------

/**
 * Check whether a string is a valid `ThermalDirection`.
 *
 * @param value - The string to check.
 * @returns `true` if the value is one of the 5 canonical directions.
 */
export function isThermalDirection(value: string): value is ThermalDirection {
  return (THERMAL_DIRECTIONS as readonly string[]).includes(value);
}

/**
 * Validate that a `ThermalSnapshot` satisfies the canonical contract.
 *
 * Checks performed:
 *   1. `readings` has exactly `READINGS_PER_SNAPSHOT` (5) elements.
 *   2. Every canonical direction appears exactly once.
 *   3. `distance_mm` is a positive number.
 *
 * @param snapshot - The snapshot to validate.
 * @returns An array of error messages (empty if valid).
 */
export function validateThermalSnapshot(
  snapshot: ThermalSnapshot
): string[] {
  const errors: string[] = [];

  // Check distance
  if (typeof snapshot.distance_mm !== "number" || snapshot.distance_mm <= 0) {
    errors.push(
      `distance_mm must be a positive number, got ${snapshot.distance_mm}`
    );
  }

  // Check readings count
  if (!Array.isArray(snapshot.readings)) {
    errors.push("readings must be an array");
    return errors;
  }

  if (snapshot.readings.length !== READINGS_PER_SNAPSHOT) {
    errors.push(
      `readings must have exactly ${READINGS_PER_SNAPSHOT} elements, got ${snapshot.readings.length}`
    );
  }

  // Check each canonical direction appears exactly once
  const directionCounts = new Map<string, number>();
  for (const reading of snapshot.readings) {
    if (!isThermalDirection(reading.direction)) {
      errors.push(`Invalid direction: "${reading.direction}"`);
      continue;
    }
    const count = directionCounts.get(reading.direction) ?? 0;
    directionCounts.set(reading.direction, count + 1);
  }

  for (const dir of THERMAL_DIRECTIONS) {
    const count = directionCounts.get(dir) ?? 0;
    if (count === 0) {
      errors.push(`Missing direction: "${dir}"`);
    } else if (count > 1) {
      errors.push(`Duplicate direction: "${dir}" (appeared ${count} times)`);
    }
  }

  return errors;
}
