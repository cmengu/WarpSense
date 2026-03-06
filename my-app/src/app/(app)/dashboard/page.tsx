"use client";

/**
 * Panel Readiness — 6 panels with latest scores.
 *
 * Fetches latest score per panel. Uses Promise.allSettled with 5s timeout
 * so one failure doesn't block others. Cards sorted by score ascending (worst first).
 * Expert Benchmark fetched in same batch; stored in separate state.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchScore } from "@/lib/api";
import type { SessionScore } from "@/lib/api";
import { logWarn } from "@/lib/logger";
import { PANELS, getSessionIdForPanel } from "@/data/panels";
import type { Panel, PanelScoreResult, PanelRiskLevel } from "@/types/panel";
import { ArrowRight, CheckCircle } from "lucide-react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const EXPERT_SESSION_ID = "sess_expert-benchmark_005";
const FETCH_TIMEOUT_MS = 5000;

const PANEL_MOCK_SCORES: Record<string, number> = {
  "PANEL-4C": 45,  // red   — X-ray inspection required
  "PANEL-7A": 72,  // amber — Dye penetrant inspection required
  "PANEL-2B": 63,  // amber — Dye penetrant inspection required
  "PANEL-1A": 91,  // green — Surveyor-ready
  "PANEL-9D": 88,  // green — Surveyor-ready
  "PANEL-3F": 94,  // green — Surveyor-ready
};

/** Risk level from score for panel cards. Do not confuse with RiskLevel in @/types/shared. */
function getRiskLevel(score: number | null): PanelRiskLevel {
  if (score === null) return "amber";
  if (score >= 85) return "green";
  if (score >= 60) return "amber";
  return "red";
}

/** Color for risk level — green/amber/red. */
function getRiskLevelColor(risk: PanelRiskLevel): string {
  if (risk === "green") return "#22c55e";
  if (risk === "amber") return "#f59e0b";
  return "#ef4444";
}

/** Score-based color using design tokens (used by Expert block). */
function getScoreColor(score: number): string {
  if (score >= 85) return "#3dd68c";
  if (score >= 60) return "#e8a030";
  return "#f06060";
}

/** Score tier for data-score-tier attribute (test compatibility). */
function getScoreTier(score: number | null): string {
  if (score === null) return "unknown";
  if (score >= 85) return "high";
  if (score >= 60) return "mid";
  return "low";
}

/**
 * Fetch score with timeout; clears timer on settle to avoid leaks.
 * Logs on failure when context.panelId provided (avoids log noise for expert benchmark).
 */
async function fetchScoreWithTimeout(
  sessionId: string,
  signal?: AbortSignal,
  context?: { panelId: string }
): Promise<SessionScore | null> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(
      () => reject(new Error("fetchScore timeout")),
      FETCH_TIMEOUT_MS
    );
  });
  try {
    return await Promise.race([fetchScore(sessionId, signal), timeout]);
  } catch (err) {
    if (context?.panelId) {
      logWarn("DashboardPage", "Score unavailable", {
        panelId: context.panelId,
        sessionId,
        error: err instanceof Error ? err.message : String(err),
      });
    }
    return null;
  } finally {
    if (timeoutId !== undefined) clearTimeout(timeoutId);
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [panelScores, setPanelScores] = useState<PanelScoreResult[] | null>(
    null
  );
  const [expertScore, setExpertScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "risk" | "top">("all");

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();
    setLoading(true);

    const panelFetches = PANELS.map((p) => ({
      panel: p,
      sessionId: getSessionIdForPanel(p),
    }));
    const allFetches = [
      ...panelFetches,
      { panel: null, sessionId: EXPERT_SESSION_ID },
    ];

    Promise.allSettled(
      allFetches.map((f) =>
        fetchScoreWithTimeout(
          f.sessionId,
          controller.signal,
          f.panel ? { panelId: f.panel.id } : undefined
        )
      )
    ).then((results) => {
      if (!mounted) return;
      const panelResults = panelFetches.map((f, i) => {
        const r = results[i];
        const score =
          r.status === "fulfilled" && r.value != null
            ? (r.value as SessionScore).total           // real seeded score wins
            : (PANEL_MOCK_SCORES[f.panel.id] ?? null); // fallback only when API returns null
        return { panel: f.panel, score, riskLevel: getRiskLevel(score) };
      });
      setPanelScores(panelResults);

      const expertR = results[results.length - 1];
      const expertVal =
        expertR.status === "fulfilled" && expertR.value != null
          ? (expertR.value as SessionScore).total
          : null;
      setExpertScore(expertVal);

      setLoading(false);
    });

    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  if (loading || panelScores === null) {
    return (
      <div className="min-h-screen bg-black text-gray-100 relative overflow-hidden">
        <div className="fixed inset-0 bg-gradient-to-br from-cyan-900/5 via-transparent to-emerald-900/5 pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 py-12">
          <h2 className="text-4xl font-bold mb-6">Panel Readiness</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {PANELS.map((p) => (
              <div
                key={p.id}
                className="rounded-xl p-6 bg-gray-900/80 animate-pulse"
              >
                <div className="h-5 w-32 bg-gray-700 rounded mb-2" />
                <div className="h-4 w-24 bg-gray-700 rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const panelResults = panelScores ?? [];
  const sorted = [...panelResults].sort((a, b) => {
    const sa = a.score ?? Infinity;
    const sb = b.score ?? Infinity;
    return sa - sb;
  });
  const filtered = sorted.filter(({ panel, score }) => {
    if (filter === "risk")
      return (score !== null && score < 70) ||
        panel.inspectionDecision !== "clear";
    if (filter === "top") return panel.inspectionDecision === "clear";
    return true;
  });

  const scores = panelResults
    .map((r) => r.score)
    .filter((s): s is number => s !== null);
  const totalNonNull = scores.length;
  const avgScore =
    totalNonNull === 0
      ? "—"
      : String(Math.round(scores.reduce((a, b) => a + b, 0) / totalNonNull));
  const totalJointsComplete = PANELS.reduce(
    (s, p) => s + p.jointsComplete,
    0
  );
  const surveyorReadyCount = PANELS.filter(
    (p) => p.inspectionDecision === "clear"
  ).length;
  const surveyorReadyPct =
    PANELS.length === 0
      ? "—"
      : `${Math.round((surveyorReadyCount / PANELS.length) * 100)}%`;

  return (
    <div className="min-h-screen bg-black text-gray-100 relative overflow-hidden">
      <div className="fixed inset-0 bg-gradient-to-br from-cyan-900/5 via-transparent to-emerald-900/5 pointer-events-none" />
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-[120px]" />
      </div>
      <main className="relative max-w-7xl mx-auto px-6 py-12">
        <div
          className="flex mb-8 rounded-xl overflow-hidden border"
          style={{
            borderColor: "var(--color-border)",
            background: "var(--color-surface)",
          }}
        >
          {[
            {
              label: "ACTIVE PANELS",
              value: PANELS.length,
              accent: false,
            },
            { label: "AVG READINESS", value: avgScore, accent: true },
            {
              label: "JOINTS INSPECTED",
              value: totalJointsComplete,
              accent: false,
            },
            {
              label: "SURVEYOR-READY",
              value: surveyorReadyPct,
              accent: true,
            },
          ].map((stat, i) => (
            <div key={stat.label} className="flex-1 px-6 py-5 relative">
              {i > 0 && (
                <div
                  className="absolute left-0 top-[20%] bottom-[20%] w-px"
                  style={{ background: "var(--color-border)" }}
                />
              )}
              <div
                className="text-3xl font-semibold tracking-tight mb-1.5"
                style={{
                  color: stat.accent ? "var(--color-green)" : "#f0f2f4",
                  letterSpacing: "-0.03em",
                }}
              >
                {stat.value}
              </div>
              <div
                className="text-[10px] font-medium tracking-[0.1em] uppercase"
                style={{
                  color: "var(--color-text-muted)",
                  fontFamily: "var(--font-geist-mono)",
                }}
              >
                {stat.label}
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between mb-4">
          <span
            className="text-[11px] font-medium uppercase tracking-[0.1em]"
            style={{
              color: "#404750",
              fontFamily: "var(--font-geist-mono)",
            }}
          >
            PANELS — {PANELS.length} ACTIVE
          </span>
          <div className="flex gap-1">
            {(["all", "risk", "top"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                aria-pressed={filter === f}
                className="px-3.5 py-1.5 rounded-lg text-[12.5px] font-medium transition-all duration-150 border"
                style={{
                  fontFamily: "inherit",
                  background: filter === f ? "#111316" : "transparent",
                  borderColor:
                    filter === f ? "rgba(255,255,255,0.07)" : "transparent",
                  color: filter === f ? "#f0f2f4" : "#8a9099",
                }}
              >
                {f === "all"
                  ? "All Panels"
                  : f === "risk"
                    ? "Needs Inspection"
                    : "Surveyor-Ready"}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filtered.map(({ panel, score, riskLevel }) => {
            const sessionId = getSessionIdForPanel(panel);
            const tierFromRisk =
              score !== null
                ? riskLevel === "green"
                  ? "high"
                  : riskLevel === "amber"
                    ? "mid"
                    : "low"
                : "unknown";
            return (
              <div
                key={panel.id}
                className="rounded-[14px] p-[22px] pb-0 transition-all duration-200 hover:-translate-y-0.5"
                style={{
                  background:
                    "linear-gradient(160deg, #181c21 0%, #111316 60%)",
                  border: "1px solid rgba(255,255,255,0.09)",
                  borderTopColor: "rgba(255,255,255,0.14)",
                  boxShadow:
                    "0 1px 0 0 rgba(255,255,255,0.06) inset, 0 -1px 0 0 rgba(0,0,0,0.4) inset, 0 4px 8px rgba(0,0,0,0.35), 0 12px 28px rgba(0,0,0,0.3)",
                }}
              >
                {/* Top row */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3
                      className="text-[15px] font-semibold tracking-tight font-mono uppercase"
                      style={{ color: "#f0f2f4", fontSize: "13px" }}
                    >
                      {panel.id}
                    </h3>
                    <div
                      className="text-[12px] mt-0.5"
                      style={{ color: "#8a9099" }}
                    >
                      {panel.label}
                    </div>
                  </div>
                  <div className="text-right">
                    {score !== null ? (
                      <span
                        data-score-tier={tierFromRisk}
                        className="text-[22px] font-medium leading-none"
                        style={{
                          color: getRiskLevelColor(riskLevel),
                          fontFamily: "var(--font-geist-mono)",
                          letterSpacing: "-0.02em",
                        }}
                      >
                        {score}/100
                      </span>
                    ) : (
                      <span className="text-violet-400">Score unavailable</span>
                    )}
                  </div>
                </div>

                {/* Score bar */}
                <div
                  className="relative h-[2px] rounded-full mb-4 overflow-hidden"
                  style={{ background: "rgba(255,255,255,0.05)" }}
                >
                  {score !== null && (
                    <div
                      className="absolute inset-y-0 left-0 rounded-full"
                      style={{
                        width: `${score}%`,
                        background: getRiskLevelColor(riskLevel),
                      }}
                    />
                  )}
                </div>

                {/* Meta row */}
                <div className="flex items-center justify-between gap-2.5 mb-4">
                  <div>
                    <span
                      className="text-[11.5px] font-medium px-2.5 py-0.5 rounded-full inline-block"
                      style={{
                        fontFamily: "var(--font-geist-mono)",
                        color: "#8a9099",
                        background: "rgba(255,255,255,0.05)",
                      }}
                    >
                      {panel.stage.charAt(0).toUpperCase() +
                        panel.stage.slice(1)}
                    </span>
                    <span
                      className="text-[12px] ml-2"
                      style={{ color: "#404750" }}
                    >
                      {panel.blockLabel}
                    </span>
                  </div>
                  <span
                    className="text-[12px] font-mono"
                    style={{ color: "#8a9099" }}
                  >
                    {panel.jointsComplete}/{panel.jointsTotal} joints
                  </span>
                </div>

                {/* Inspection decision row */}
                <div className="flex items-center gap-2 mb-4">
                  <div
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{
                      background:
                        panel.inspectionDecision === "clear"
                          ? "#22c55e"
                          : panel.inspectionDecision === "needs-dpi"
                            ? "#f59e0b"
                            : "#ef4444",
                    }}
                  />
                  <span
                    className="text-[12px]"
                    style={{ color: "#8a9099" }}
                  >
                    {panel.inspectionDecision === "clear"
                      ? "Surveyor-ready — no inspection needed"
                      : panel.inspectionDecision === "needs-dpi"
                        ? "Dye penetrant inspection required"
                        : panel.inspectionDecision === "needs-xray"
                          ? "X-ray inspection required"
                          : "Immediate surveyor visit required"}
                  </span>
                </div>

                {/* Actions */}
                <div
                  style={{
                    borderTop: "1px solid rgba(255,255,255,0.04)",
                  }}
                >
                  <Link
                    href={`/replay/${sessionId}`}
                    className="flex items-center justify-between py-[11px] text-[12.5px] transition-colors duration-100 group"
                    style={{
                      color: "#8a9099",
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                    }}
                  >
                    <span className="group-hover:text-[#f0f2f4] transition-colors">
                      View weld passes
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                  </Link>
                  <Link
                    href={`/compare/${sessionId}/${EXPERT_SESSION_ID}`}
                    className="flex items-center justify-between py-[11px] text-[12.5px] transition-colors duration-100 group"
                    style={{
                      color: "#8a9099",
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                    }}
                  >
                    <span className="group-hover:text-[#f0f2f4] transition-colors">
                      Inspection decision
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                  </Link>
                  <Link
                    href={`/seagull/welder/${panel.id}`}
                    className="flex items-center justify-between py-[11px] text-[12.5px] transition-colors duration-100 group"
                    style={{ color: "#8a9099" }}
                  >
                    <span className="group-hover:text-[#f0f2f4] transition-colors">
                      Surveyor report
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
        <div
          className="mt-8 relative rounded-xl p-6 overflow-hidden"
          style={{
            background:
              "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
            boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <CheckCircle className="w-5 h-5 text-cyan-400" />
            <h3 className="text-lg font-bold text-gray-100">
              Expert Benchmark
            </h3>
          </div>
          {expertScore !== null && (
            <span
              data-score-tier={getScoreTier(expertScore)}
              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
              style={{
                color: getScoreColor(expertScore),
                backgroundColor: `${getScoreColor(expertScore)}20`,
              }}
            >
              {expertScore}/100
            </span>
          )}
          <p className="text-sm text-gray-400 mb-4 mt-2">
            Reference standard for optimal weld quality parameters and
            technique
          </p>
          <Link
            href={`/replay/${EXPERT_SESSION_ID}`}
            className="text-sm text-cyan-400 hover:text-cyan-300"
          >
            View benchmark details
          </Link>
          <span className="mx-2 text-gray-600">|</span>
          <Link
            href={`/seagull/welder/expert-benchmark`}
            className="text-sm text-cyan-400 hover:text-cyan-300"
          >
            Full report
          </Link>
        </div>
      </main>
    </div>
  );
}
