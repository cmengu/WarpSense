/**
 * Any change here can ripple through components, services, tests, and occasionally the backend.
 * Sensor configuration constants for welding sessions.
 *
 * Centralizes valid ranges, display units, and temperature limits.
 * Prevents magic numbers scattered across components and validators.
 *
 * These ranges are for display/warning purposes on the frontend.
 * The backend enforces hard constraints (see backend/models/).
 */

// ---------------------------------------------------------------------------
// Sensor ranges
// ---------------------------------------------------------------------------

/**
 * Valid range for a sensor value.
 * Used for display warnings and soft validation on the frontend.
 */
export interface SensorRange {
  /** Minimum valid value (inclusive). */
  min: number;
  /** Maximum valid value (inclusive). */
  max: number;
  /** Unit string for display. */
  unit: string;
}

/**
 * Valid ranges for each sensor type.
 *
 * Assumption: ranges cover MIG/MAG welding across common metals.
 * Values outside these ranges trigger a frontend warning (not rejection).
 * The backend applies its own constraints.
 */
export const SENSOR_RANGES: Readonly<Record<string, SensorRange>> = {
  volts: { min: 0, max: 50, unit: "V" },
  amps: { min: 0, max: 500, unit: "A" },
  angle_degrees: { min: -90, max: 90, unit: "°" },
  speed_mm_per_sec: { min: 0, max: 50, unit: "mm/s" },
} as const;

// ---------------------------------------------------------------------------
// Sensor units
// ---------------------------------------------------------------------------

/**
 * Display units for each sensor field.
 * Use for axis labels, tooltips, and table headers.
 */
export const SENSOR_UNITS: Readonly<Record<string, string>> = {
  volts: "V",
  amps: "A",
  angle_degrees: "°",
  speed_mm_per_sec: "mm/s",
  temp_celsius: "°C",
  distance_mm: "mm",
  heat_dissipation_rate_celsius_per_sec: "°C/s",
  timestamp_ms: "ms",
} as const;

// ---------------------------------------------------------------------------
// Temperature range
// ---------------------------------------------------------------------------

/**
 * Valid temperature range for thermal sensor readings in degrees Celsius.
 *
 * Assumption: infrared thermal sensor range for welding applications.
 * Temperatures outside this range are likely sensor errors.
 */
export const TEMPERATURE_RANGE_CELSIUS = {
  /** Minimum measurable temperature in °C. */
  min: -20,
  /** Maximum measurable temperature in °C (above this, sensor saturates). */
  max: 2000,
} as const;
