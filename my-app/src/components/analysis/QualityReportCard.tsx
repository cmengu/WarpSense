"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ThresholdViolation, WarpReport } from "@/types/warp-analysis";
import { logWarn } from "@/lib/logger";
import { StatusBadge } from "./StatusBadge";

/** Maps agent code-names → operational display labels. */
const AGENT_DISPLAY: Record<string, string> = {
  ThermalAgent:           "Heat Profile",
  GeometryAgent:          "Torch Angle",
  ProcessStabilityAgent:  "Arc Stability",
};

/**
 * Deterministic consequence prose for each agent's rejection — Part 3 of the
 * three-part humanised narrative in the PDF report.
 * Keys match the PascalCase agent_name values from backend/agent/specialists.py.
 */
const CONSEQUENCE_BY_AGENT: Record<string, string> = {
  ThermalAgent:
    "Excessive or deficient heat input can cause grain coarsening in the heat-affected zone, " +
    "reducing toughness and increasing the risk of HAZ cracking or underbead cracking under service loads.",
  GeometryAgent:
    "Geometric deviations such as undercut, overlap, or incorrect weld profile reduce the " +
    "effective throat thickness, which can lead to premature fatigue failure or brittle fracture at the joint.",
  ProcessStabilityAgent:
    "Process instability — including arc interruptions, voltage fluctuations, or incorrect wire feed — " +
    "can introduce porosity, lack of fusion, or incomplete penetration, compromising joint structural integrity.",
};

/**
 * Deterministic rationale templates — Part 2 of the PDF narrative.
 * Used because per-agent disposition_rationale is not available from the backend;
 * WarpReport.disposition_rationale is report-level only.
 */
const RATIONALE_BY_AGENT: Record<string, string> = {
  ThermalAgent:
    "This heat excursion places the heat-affected zone outside WPS-specified bounds, " +
    "indicating insufficient travel speed or pre-heat temperature control.",
  GeometryAgent:
    "The geometric deviation suggests torch angle drift or inconsistent standoff distance, " +
    "resulting in a weld profile that does not meet dimensional acceptance criteria.",
  ProcessStabilityAgent:
    "The process anomaly reflects inconsistent arc behaviour, typically from parameter drift, " +
    "contact tip wear, or shielding gas fluctuation.",
};

/** Short rejection labels for the visual badge in the PDF per-agent section. */
const REJECT_LABEL_BY_AGENT: Record<string, string> = {
  ThermalAgent:          "HEAT EXCEEDANCE",
  GeometryAgent:         "GEOMETRY DEVIATION",
  ProcessStabilityAgent: "PROCESS INSTABILITY",
};

export interface QualityReportCardProps {
  report: WarpReport;
  /** Wired in Phase UI-7 from selectedSession.welder_name. */
  welderDisplayName?: string | null;
  /** Panel ID passed from AnalysisTimeline → page.tsx for PDF export. */
  panelId?: string | null;
  /** Panel name passed from AnalysisTimeline → page.tsx for PDF export. */
  panelName?: string | null;
  /** Wired in Phase UI-7 to start analysis again for the same session. */
  onReanalyse?: () => void;
  /** Navigate to /compare pre-filled with this session as sessionA. */
  onCompare?: () => void;
}

interface ParsedSpecialistRow {
  agent_name: string;
  disposition?: string;
  root_cause?: string;
  corrective_actions?: string[];
  standards_references?: string[];
  retrieved_chunk_ids?: string[];
}

interface DriverBar {
  label: string;
  percent: number;
  detail: string;
}

function formatReportTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  })} UTC`;
}

function dispositionStrip(disposition: WarpReport["disposition"]): string {
  if (disposition === "PASS") return "bg-green-950/80 border-b border-green-700";
  if (disposition === "CONDITIONAL") return "bg-amber-950/80 border-b border-amber-700";
  return "bg-red-950/80 border-b border-red-700";
}

/**
 * Parse persisted specialist JSON when the backend eventually exposes it.
 * Returns null if the field is absent, invalid, or has no valid rows.
 */
function toStringArray(val: unknown): string[] {
  if (!Array.isArray(val)) return [];
  return val.filter((v): v is string => typeof v === "string");
}

function parseSpecialistRows(raw: string | null | undefined): ParsedSpecialistRow[] | null {
  if (raw == null || raw.trim() === "") return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return null;
    const rows: ParsedSpecialistRow[] = [];
    for (const item of parsed) {
      if (typeof item !== "object" || item === null) continue;
      const obj = item as Record<string, unknown>;
      if (typeof obj.agent_name !== "string") continue;
      // Normalize every optional array field so downstream JSX map/join are always safe.
      rows.push({
        agent_name:           obj.agent_name,
        disposition:          typeof obj.disposition === "string" ? obj.disposition : undefined,
        root_cause:           typeof obj.root_cause === "string" ? obj.root_cause : undefined,
        corrective_actions:   toStringArray(obj.corrective_actions),
        standards_references: toStringArray(obj.standards_references),
        retrieved_chunk_ids:  toStringArray(obj.retrieved_chunk_ids),
      });
    }
    return rows.length > 0 ? rows : null;
  } catch {
    return null;
  }
}

/**
 * Deterministic driver bars:
 * - prefer threshold_violations ranked by absolute distance from threshold
 * - fallback to equal-weight primary defect categories
 *
 * Percentages are rounded to 1 decimal place, so some sets may total 99.9 or
 * 100.1. That is acceptable in UI-5; exact-total normalization is polish work.
 */
function buildDriverBars(report: WarpReport): DriverBar[] {
  const violations = report.threshold_violations ?? [];
  if (violations.length > 0) {
    const scored = violations
      .map((item: ThresholdViolation) => {
        const baseline = Math.max(Math.abs(item.threshold), 1e-9);
        const distance = Math.abs(item.value - item.threshold);
        return {
          label: item.feature,
          score: distance / baseline,
          detail: `${item.value} vs ${item.threshold} (${item.severity})`,
        };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, 5);

    const total = scored.reduce((sum, item) => sum + item.score, 0);
    if (total <= 0) {
      const even = Math.round(1000 / scored.length) / 10;
      return scored.map((item) => ({
        label: item.label,
        percent: even,
        detail: item.detail,
      }));
    }

    return scored.map((item) => ({
      label: item.label,
      percent: Math.round((item.score / total) * 1000) / 10,
      detail: item.detail,
    }));
  }

  const categories = (report.primary_defect_categories ?? []).slice(0, 5);
  if (categories.length === 0) return [];
  const even = Math.round(1000 / categories.length) / 10;
  return categories.map((label) => ({
    label,
    percent: even,
    detail: "Primary defect category",
  }));
}

export function QualityReportCard({
  report,
  welderDisplayName,
  panelId,
  panelName,
  onReanalyse,
  onCompare,
}: QualityReportCardProps) {
  const [copyFeedback, setCopyFeedback] = useState(false);
  const [isPdfLoading, setIsPdfLoading]   = useState(false);
  const [acknowledged, setAcknowledged]   = useState<Set<number>>(new Set());
  const copyFeedbackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const driverBars = useMemo(() => buildDriverBars(report), [report]);
  const specialistRows = useMemo(
    () => parseSpecialistRows(report.llm_raw_response),
    [report.llm_raw_response],
  );

  useEffect(() => {
    return () => {
      if (copyFeedbackTimeoutRef.current != null) {
        clearTimeout(copyFeedbackTimeoutRef.current);
        copyFeedbackTimeoutRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    setAcknowledged(new Set());
  }, [report.session_id]);

  const handleCopySessionId = useCallback(async () => {
    try {
      if (typeof navigator?.clipboard?.writeText === "function") {
        await navigator.clipboard.writeText(report.session_id);
        if (copyFeedbackTimeoutRef.current != null) {
          clearTimeout(copyFeedbackTimeoutRef.current);
        }
        setCopyFeedback(true);
        copyFeedbackTimeoutRef.current = setTimeout(() => {
          setCopyFeedback(false);
          copyFeedbackTimeoutRef.current = null;
        }, 2000);
        return;
      }
    } catch {
      // Fallback below.
    }

    // This may still be blocked in sandboxed/mobile contexts, but is adequate
    // as a last-resort manual copy path for the current desktop workflow.
    window.prompt("Copy session ID:", report.session_id);
  }, [report.session_id]);

  const handleExportPdf = useCallback(async () => {
    if (isPdfLoading) return;
    // Guard: panelId/panelName should always be present at export time.
    // If null, it means the prop threading from page.tsx → AnalysisTimeline → here
    // is broken. Log a warning so the bug is visible in the console.
    if (!panelId || !panelName) {
      logWarn("[QualityReportCard]", "PDF export called without panel context — prop threading bug", {
        sessionId: report.session_id,
      });
    }
    setIsPdfLoading(true);
    try {
      const scoreTotal =
        report.disposition === "PASS"         ? 85
        : report.disposition === "CONDITIONAL" ? 55
        : 30;
      const payload = {
        panel: { id: panelId ?? report.session_id, name: panelName ?? "Panel" },
        welder_attribution: welderDisplayName ?? null,
        score:  { total: scoreTotal },
        feedback: {
          summary: report.root_cause,
          feedback_items: report.corrective_actions.map((action, i) => ({
            message:  action,
            severity: i === 0 ? "high" : "medium",
          })),
        },
        narrative:       report.disposition_rationale.slice(0, 400),
        rework_cost_usd:   report.rework_cost_usd ?? null,
        disposition:       report.disposition,
        agentInsights: (specialistRows ?? []).map((row) => ({
          agent_name:   row.agent_name,
          disposition:  row.disposition,
          root_cause:   row.root_cause,
          corrective_actions: row.corrective_actions,
          // Three-part humanised narrative fields (Part 2 & 3) — deterministic
          // templates keyed by agent name. Null for passing agents.
          disposition_rationale:
            row.disposition && row.disposition !== "PASS"
              ? (RATIONALE_BY_AGENT[row.agent_name] ?? null)
              : null,
          consequence:
            row.disposition && row.disposition !== "PASS"
              ? (CONSEQUENCE_BY_AGENT[row.agent_name] ?? null)
              : null,
          reject_label:
            row.disposition && row.disposition !== "PASS"
              ? (REJECT_LABEL_BY_AGENT[row.agent_name] ?? null)
              : null,
        })),
        sessionDate:       new Date(report.report_timestamp).toLocaleDateString("en-GB"),
      };
      const res = await fetch("/api/welder-report-pdf", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });
      if (!res.ok) {
        logWarn("[QualityReportCard]", "PDF export failed", { status: res.status, sessionId: report.session_id });
        return;
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `${panelId ?? report.session_id}-report.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      logWarn("[QualityReportCard]", "PDF export error", { error: String(err), sessionId: report.session_id });
    } finally {
      setIsPdfLoading(false);
    }
  }, [isPdfLoading, report, welderDisplayName, panelId, panelName, specialistRows]);

  return (
    <div className="flex flex-col min-h-[400px] h-full bg-[var(--warp-surface)] border border-zinc-900">
      <div className={`px-4 py-3 shrink-0 ${dispositionStrip(report.disposition)}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <p className="font-mono text-[10px] uppercase tracking-widest text-white/60">
              WarpSense Report
            </p>
            <StatusBadge disposition={report.disposition} />
            {welderDisplayName ? (
              <p className="font-mono text-[10px] text-white/80">
                Welder: {welderDisplayName}
              </p>
            ) : null}
          </div>
          <div className="text-right">
            <p className="font-mono text-[9px] text-white/70">{report.session_id}</p>
            <p className="font-mono text-[9px] text-white/50">
              {formatReportTimestamp(report.report_timestamp)}
            </p>
          </div>
        </div>
        <p className="font-mono text-[10px] text-white/60 mt-2">
          {(report.confidence * 100).toFixed(0)}% confidence · ISO 5817 Grade {report.iso_5817_level}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {report.rework_cost_usd != null && (
          <div className="px-4 pt-3 pb-1 border-b border-zinc-900">
            <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
              Estimated Rework Cost
            </p>
            <p
              className={`font-mono text-3xl font-bold tabular-nums ${
                report.rework_cost_usd === 0
                  ? "text-green-400"
                  : report.rework_cost_usd <= 1800
                    ? "text-amber-400"
                    : "text-red-400"
              }`}
            >
              ${report.rework_cost_usd.toLocaleString("en-US")}
            </p>
            {report.rework_cost_usd === 0 && (
              <p className="font-mono text-[10px] text-green-600 mt-0.5">
                No rework required — cost avoided
              </p>
            )}
          </div>
        )}
        <section>
          <p className="font-mono text-[9px] uppercase tracking-widest text-[var(--warp-text-muted)] mb-2">
            Root Cause
          </p>
          <p className="font-mono text-[11px] leading-relaxed text-[var(--warp-text)] whitespace-pre-wrap">
            {report.root_cause}
          </p>
          <p className="font-mono text-[10px] leading-relaxed text-zinc-500 mt-2 whitespace-pre-wrap">
            {report.disposition_rationale}
          </p>
        </section>

        <section>
          <p className="font-mono text-[9px] uppercase tracking-widest text-[var(--warp-text-muted)] mb-2">
            Corrective Actions
          </p>
          {report.corrective_actions.length > 0 &&
            acknowledged.size === report.corrective_actions.length && (
              <div className="mb-2 flex items-center gap-1.5 font-mono text-[9px] text-green-400">
                <span>●</span>
                <span>All actions reviewed</span>
              </div>
            )}
          <ol className="space-y-1.5 font-mono text-[11px] text-[var(--warp-text)]">
            {report.corrective_actions.map((action, index) => (
              <li key={index} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={acknowledged.has(index)}
                  onChange={() =>
                    setAcknowledged((prev) => {
                      const next = new Set(prev);
                      if (next.has(index)) next.delete(index);
                      else next.add(index);
                      return next;
                    })
                  }
                  className="mt-0.5 shrink-0 accent-amber-400"
                />
                <span className={acknowledged.has(index) ? "line-through text-zinc-600" : ""}>
                  {action}
                </span>
              </li>
            ))}
          </ol>
        </section>

        <section>
          <p className="font-mono text-[9px] uppercase tracking-widest text-[var(--warp-text-muted)] mb-2">
            Standards References
          </p>
          <div className="flex flex-wrap gap-1.5">
            {report.standards_references.map((ref, index) => (
              <button
                key={index}
                type="button"
                onClick={() => void navigator?.clipboard?.writeText?.(ref).catch(() => {})}
                className="font-mono text-[8px] uppercase tracking-widest border border-zinc-800 px-2 py-1 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100"
              >
                {ref}
              </button>
            ))}
          </div>
        </section>

        <section>
          <p className="font-mono text-[9px] uppercase tracking-widest text-[var(--warp-text-muted)] mb-2">
            Top Drivers
          </p>
          {driverBars.length === 0 ? (
            <p className="font-mono text-[10px] text-zinc-600">No threshold violation data available.</p>
          ) : (
            <div className="space-y-2">
              {driverBars.map((bar) => (
                <div key={bar.label} className="space-y-1">
                  <div className="flex items-center justify-between gap-2 font-mono text-[10px]">
                    <span className="truncate text-[var(--warp-text)]">{bar.label}</span>
                    <span className="shrink-0 text-zinc-500">{bar.percent}%</span>
                  </div>
                  <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[var(--warp-amber)]"
                      style={{ width: `${Math.min(bar.percent, 100)}%` }}
                    />
                  </div>
                  <p className="font-mono text-[9px] text-zinc-600">{bar.detail}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <p className="font-mono text-[9px] uppercase tracking-widest text-[var(--warp-text-muted)] mb-2">
            Assessment Details
          </p>

          {specialistRows ? (
            <div className="space-y-2">
              {specialistRows.map((row) => (
                <details key={row.agent_name} className="border border-zinc-800 rounded">
                  <summary className="cursor-pointer px-3 py-2 font-mono text-[10px] text-[var(--warp-text)] hover:bg-[var(--warp-surface-2)]">
                    {AGENT_DISPLAY[row.agent_name] ?? row.agent_name}
                    {row.disposition ? ` · ${row.disposition.replace("_", " ")}` : ""}
                  </summary>
                  <div className="px-3 pb-3 pt-1 space-y-2">
                    {row.root_cause ? (
                      <p className="font-mono text-[10px] text-[var(--warp-text)] whitespace-pre-wrap">
                        {row.root_cause}
                      </p>
                    ) : null}
                    {row.corrective_actions && row.corrective_actions.length > 0 ? (
                      <ul className="list-disc list-inside font-mono text-[10px] text-[var(--warp-text)] space-y-1">
                        {row.corrective_actions.map((action, actionIndex) => (
                          <li key={actionIndex}>{action}</li>
                        ))}
                      </ul>
                    ) : null}
                    {row.standards_references && row.standards_references.length > 0 ? (
                      <p className="font-mono text-[9px] text-zinc-500">
                        Refs: {row.standards_references.join(" · ")}
                      </p>
                    ) : null}
                    {row.retrieved_chunk_ids && row.retrieved_chunk_ids.length > 0 ? (
                      <p className="font-mono text-[9px] text-zinc-600 break-all">
                        Chunks: {row.retrieved_chunk_ids.join(", ")}
                      </p>
                    ) : null}
                  </div>
                </details>
              ))}
            </div>
          ) : (
            <details className="border border-zinc-800 rounded">
              <summary className="cursor-pointer px-3 py-2 font-mono text-[10px] text-[var(--warp-text)] hover:bg-[var(--warp-surface-2)]">
                Summary and Evidence
              </summary>
              <div className="px-3 pb-3 pt-1 space-y-2">
                <p className="font-mono text-[10px] text-[var(--warp-text)] whitespace-pre-wrap">
                  {report.disposition_rationale}
                </p>
                <p className="font-mono text-[9px] text-zinc-500 whitespace-pre-wrap">
                  Self-check: {report.self_check_passed ? "passed" : "attention required"} ·{" "}
                  {report.self_check_notes}
                </p>
                {report.primary_defect_categories.length > 0 ? (
                  <p className="font-mono text-[9px] text-zinc-500">
                    Categories: {report.primary_defect_categories.join(", ")}
                  </p>
                ) : null}
                {report.retrieved_chunks_used && report.retrieved_chunks_used.length > 0 ? (
                  <p className="font-mono text-[9px] text-zinc-600 break-all">
                    Retrieved chunks: {report.retrieved_chunks_used.join(", ")}
                  </p>
                ) : null}
                {report.report_id != null || report.agent_type ? (
                  <p className="font-mono text-[9px] text-zinc-600">
                    {report.report_id != null ? `Report ID ${report.report_id}` : ""}
                    {report.report_id != null && report.agent_type ? " · " : ""}
                    {report.agent_type ?? ""}
                  </p>
                ) : null}
              </div>
            </details>
          )}
        </section>
      </div>

      <div className="flex flex-wrap gap-2 px-4 py-3 border-t border-zinc-900 shrink-0">
        <button
          type="button"
          onClick={() => { void handleExportPdf(); }}
          disabled={isPdfLoading}
          className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {isPdfLoading ? "Generating…" : "Export PDF"}
        </button>

        <button
          type="button"
          onClick={handleCopySessionId}
          className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100"
          aria-label="Copy session ID to clipboard"
        >
          {copyFeedback ? "Copied!" : "Copy Session ID"}
        </button>

        <button
          type="button"
          onClick={() => onReanalyse?.()}
          disabled={!onReanalyse}
          className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Re-analyse
        </button>

        <button
          type="button"
          onClick={() => onCompare?.()}
          disabled={!onCompare}
          className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] transition-colors duration-100 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          Compare
        </button>
      </div>
    </div>
  );
}
