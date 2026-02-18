/**
 * Types for weld quality thresholds.
 * Matches backend WeldTypeThresholds and ActiveThresholdSpec.
 */

export interface WeldTypeThresholds {
  weld_type: string;
  angle_target_degrees: number;
  angle_warning_margin: number;
  angle_critical_margin: number;
  thermal_symmetry_warning_celsius: number;
  thermal_symmetry_critical_celsius: number;
  amps_stability_warning: number;
  volts_stability_warning: number;
  heat_diss_consistency: number;
}

/**
 * Optional thermal/amps/volts/heat_diss for legacy API callers that return old 4-field spec.
 */
export interface ActiveThresholdSpec {
  weld_type: string;
  angle_target: number;
  angle_warning: number;
  angle_critical: number;
  thermal_symmetry_warning_celsius?: number;
  thermal_symmetry_critical_celsius?: number;
  amps_stability_warning?: number;
  volts_stability_warning?: number;
  heat_diss_consistency?: number;
}
