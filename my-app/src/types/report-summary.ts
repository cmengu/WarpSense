/**
 * Report summary types — matches backend scoring.report_summary.
 * Used by compliance UI and PDF export.
 */

/** Single excursion (alert or frame-derived, run-length collapsed). */
export interface ExcursionEntry {
  timestamp_ms: number;
  defect_type: string;
  parameter_value?: number | null;
  threshold_value?: number | null;
  duration_ms?: number | null;
  source: "alert" | "frame_derived";
  notes?: string | null;
}

/** Session-level compliance summary for report UI and PDF. */
export interface ReportSummary {
  session_id: string;
  generated_at: string;

  heat_input_min_kj_per_mm?: number | null;
  heat_input_max_kj_per_mm?: number | null;
  heat_input_mean_kj_per_mm?: number | null;
  heat_input_wps_min: number;
  heat_input_wps_max: number;
  heat_input_compliant: boolean;

  travel_angle_excursion_count: number;
  travel_angle_worst_case_deg?: number | null;
  travel_angle_threshold_deg: number;

  total_arc_terminations: number;
  no_crater_fill_count: number;
  crater_fill_rate_pct: number;

  defect_counts_by_type: Record<string, number>;
  total_defect_alerts: number;

  excursions: ExcursionEntry[];
}
