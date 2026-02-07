/**
 * Any change here can ripple through components, services, tests, and occasionally the backend.
 * Metal type constants for welding sessions.
 *
 * Centralizes metal type identifiers, display labels, and physical
 * properties. Prevents magic strings scattered across components.
 *
 * NOTE: These are MVP defaults. Update when hardware team provides
 * actual metal-specific parameters.
 */

// ---------------------------------------------------------------------------
// Metal types
// ---------------------------------------------------------------------------

/**
 * Valid metal type identifiers.
 * Must match backend `weld_type` values stored in the database.
 */
export const METAL_TYPES = [
  "mild_steel",
  "stainless_steel",
  "aluminum",
  "cast_iron",
  "copper",
] as const;

/** Union type of valid metal type identifiers. */
export type MetalType = (typeof METAL_TYPES)[number];

/**
 * Human-readable labels for each metal type.
 * Use in dropdowns, table headers, and display text.
 */
export const METAL_TYPE_LABELS: Readonly<Record<MetalType, string>> = {
  mild_steel: "Mild Steel",
  stainless_steel: "Stainless Steel",
  aluminum: "Aluminum",
  cast_iron: "Cast Iron",
  copper: "Copper",
} as const;

// ---------------------------------------------------------------------------
// Physical properties
// ---------------------------------------------------------------------------

/**
 * Physical properties relevant to welding for each metal type.
 *
 * Units are explicit in field names. Values are approximate —
 * consult materials engineering data for production use.
 *
 * Assumption: properties are for common alloys at room temperature.
 */
export interface MetalProperties {
  /** Melting point in degrees Celsius. */
  melting_point_celsius: number;
  /** Thermal conductivity in W/(m·K). */
  thermal_conductivity_w_per_mk: number;
  /** Typical preheat temperature in degrees Celsius (0 = no preheat). */
  preheat_temp_celsius: number;
  /** Typical voltage range for MIG/MAG welding in volts. */
  typical_voltage_range_volts: readonly [number, number];
  /** Typical amperage range for MIG/MAG welding in amps. */
  typical_amperage_range_amps: readonly [number, number];
}

/**
 * Physical properties per metal type.
 *
 * Sources: AWS D1.1 (structural steel), AWS D1.2 (aluminum),
 * general welding reference handbooks.
 */
export const METAL_PROPERTIES: Readonly<Record<MetalType, MetalProperties>> = {
  mild_steel: {
    melting_point_celsius: 1425,
    thermal_conductivity_w_per_mk: 50,
    preheat_temp_celsius: 0,
    typical_voltage_range_volts: [17, 30],
    typical_amperage_range_amps: [50, 300],
  },
  stainless_steel: {
    melting_point_celsius: 1400,
    thermal_conductivity_w_per_mk: 16,
    preheat_temp_celsius: 0,
    typical_voltage_range_volts: [18, 28],
    typical_amperage_range_amps: [40, 250],
  },
  aluminum: {
    melting_point_celsius: 660,
    thermal_conductivity_w_per_mk: 237,
    preheat_temp_celsius: 150,
    typical_voltage_range_volts: [18, 28],
    typical_amperage_range_amps: [60, 350],
  },
  cast_iron: {
    melting_point_celsius: 1200,
    thermal_conductivity_w_per_mk: 52,
    preheat_temp_celsius: 260,
    typical_voltage_range_volts: [17, 25],
    typical_amperage_range_amps: [40, 200],
  },
  copper: {
    melting_point_celsius: 1085,
    thermal_conductivity_w_per_mk: 401,
    preheat_temp_celsius: 200,
    typical_voltage_range_volts: [20, 30],
    typical_amperage_range_amps: [80, 350],
  },
} as const;
