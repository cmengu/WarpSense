/**
 * ComplianceSummaryPanel — Renders WPS compliance summary for report UI.
 *
 * Four states:
 * - error: Show error message
 * - loading: Skeleton (no data, no error, no isEmpty)
 * - empty: "Compliance data unavailable" (isEmpty=true)
 * - data: Three rows — Heat Input, Torch Angle, Arc Termination (label, actual, threshold, pass/fail)
 */

import type { ReportSummary } from "@/types/report-summary";

export interface ComplianceSummaryPanelProps {
  /** Report summary from API. Null when loading or failed. */
  data: ReportSummary | null;
  /** Error message when fetch failed. */
  error?: string | null;
  /** True when loaded but no data (e.g. 404, empty session). */
  isEmpty?: boolean;
}

function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 py-2 border-b border-zinc-200 dark:border-zinc-700 last:border-0">
      <div className="w-32 h-4 bg-zinc-200 dark:bg-zinc-700 rounded animate-pulse" />
      <div className="flex-1 h-4 bg-zinc-100 dark:bg-zinc-800 rounded animate-pulse" />
    </div>
  );
}

function ComplianceRow({
  label,
  actual,
  threshold,
  passed,
}: {
  label: string;
  actual: string;
  threshold: string;
  passed: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-4 py-2 border-b border-zinc-200 dark:border-zinc-700 last:border-0">
      <span className="w-32 font-medium text-zinc-700 dark:text-zinc-300">
        {label}
      </span>
      <span className="text-zinc-600 dark:text-zinc-400">
        {actual}
        {threshold && ` (WPS: ${threshold})`}
      </span>
      <span
        className={`text-sm font-semibold px-2 py-0.5 rounded ${
          passed
            ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
            : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
        }`}
      >
        {passed ? "PASS" : "FAIL"}
      </span>
    </div>
  );
}

export function ComplianceSummaryPanel({
  data,
  error,
  isEmpty,
}: ComplianceSummaryPanelProps) {
  if (error) {
    return (
      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Compliance</h2>
        <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Compliance</h2>
        <p className="text-zinc-500 dark:text-zinc-400 text-sm">
          Compliance data unavailable
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Compliance</h2>
        <div className="space-y-0">
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </div>
      </div>
    );
  }

  const heatActual =
    data.heat_input_mean_kj_per_mm != null
      ? `${data.heat_input_mean_kj_per_mm.toFixed(2)} kJ/mm`
      : "—";
  const heatThreshold = `${data.heat_input_wps_min}–${data.heat_input_wps_max} kJ/mm`;

  const travelActual =
    data.travel_angle_excursion_count > 0
      ? `${data.travel_angle_excursion_count} excursion(s), worst ${(data.travel_angle_worst_case_deg ?? 0).toFixed(1)}° from nominal`
      : `Within ±${data.travel_angle_threshold_deg}°`;
  const travelThreshold = `±${data.travel_angle_threshold_deg}°`;

  const arcActual =
    data.total_arc_terminations > 0
      ? `${(data.crater_fill_rate_pct ?? 0).toFixed(0)}% crater fill (${data.total_arc_terminations - data.no_crater_fill_count}/${data.total_arc_terminations})`
      : "No terminations";
  const arcThreshold = "100% preferred";

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Compliance</h2>
      <div className="space-y-0">
        <ComplianceRow
          label="Heat Input"
          actual={heatActual}
          threshold={heatThreshold}
          passed={data.heat_input_compliant}
        />
        <ComplianceRow
          label="Torch Angle"
          actual={travelActual}
          threshold={travelThreshold}
          passed={data.travel_angle_excursion_count === 0}
        />
        <ComplianceRow
          label="Arc Termination"
          actual={arcActual}
          threshold={arcThreshold}
          passed={
            data.total_arc_terminations === 0 ||
            data.crater_fill_rate_pct >= 100
          }
        />
      </div>
    </div>
  );
}

export default ComplianceSummaryPanel;
