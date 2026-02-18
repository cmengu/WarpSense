/**
 * Canonical shared types for WarpSense.
 * Import from here. Never redefine these elsewhere.
 * WELD_METRICS must match backend models.shared_enums.WeldMetric values.
 */

// ─── ID Types ───────────────────────────────────────────────────────────────
export type WelderID = string;
export type SessionID = string;
export type SiteID = string;
export type TeamID = string;

// ─── Metric Names ───────────────────────────────────────────────────────────
export type WeldMetric =
  | "angle_consistency"
  | "thermal_symmetry"
  | "amps_stability"
  | "volts_stability"
  | "heat_diss_consistency";

export const WELD_METRICS: WeldMetric[] = [
  "angle_consistency",
  "thermal_symmetry",
  "amps_stability",
  "volts_stability",
  "heat_diss_consistency",
];

export const METRIC_LABELS: Record<WeldMetric, string> = {
  angle_consistency: "Angle Consistency",
  thermal_symmetry: "Thermal Symmetry",
  amps_stability: "Amps Stability",
  volts_stability: "Volts Stability",
  heat_diss_consistency: "Heat Dissipation Consistency",
};

// ─── Severity / Risk ─────────────────────────────────────────────────────────
export type RiskLevel = "ok" | "warning" | "critical";
/** info | warning for session-level; critical reserved in ai-feedback for micro-feedback */
export type FeedbackSeverity = "info" | "warning";

// ─── Metric Score ───────────────────────────────────────────────────────────
export interface MetricScore {
  metric: WeldMetric;
  value: number; // 0–100
  label: string;
}

// ─── Pagination (Batch 2+ list endpoints) ─────────────────────────────────────
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Status Enums ───────────────────────────────────────────────────────────
export type AnnotationType =
  | "defect_confirmed"
  | "near_miss"
  | "technique_error"
  | "equipment_issue";

export type CoachingStatus = "active" | "complete" | "overdue";

export type CertificationStatus =
  | "not_started"
  | "on_track"
  | "at_risk"
  | "certified";
