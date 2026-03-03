"use client";

/**
 * Welder Roster — 10 welders with latest scores.
 *
 * Fetches latest score per welder. Uses Promise.allSettled with 5s timeout
 * so one failure doesn't block others. Cards sorted by score ascending (worst first).
 *
 * Pre-flight: Verify WELDERS matches WELDER_ARCHETYPES (backend/data/mock_welders.py).
 * Prerequisite: Run seed before opening dashboard.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchScore } from "@/lib/api";
import type { SessionScore } from "@/lib/api";
import { ArrowRight, CheckCircle } from "lucide-react";

// ---------------------------------------------------------------------------
// Constants — Must match WELDER_ARCHETYPES (backend/data/mock_welders.py)
// ---------------------------------------------------------------------------

const EXPERT_SESSION_ID = "sess_expert-benchmark_005";
const FETCH_TIMEOUT_MS = 5000;

interface Welder {
  id: string;
  name: string;
  sessionCount: number;
}

interface WelderScoreResult {
  welder: Welder;
  score: number | null;
}

const WELDERS: Welder[] = [
  { id: "mike-chen", name: "Mike Chen", sessionCount: 5 },
  { id: "sara-okafor", name: "Sara Okafor", sessionCount: 5 },
  { id: "james-park", name: "James Park", sessionCount: 5 },
  { id: "lucia-reyes", name: "Lucia Reyes", sessionCount: 5 },
  { id: "tom-bradley", name: "Tom Bradley", sessionCount: 3 },
  { id: "ana-silva", name: "Ana Silva", sessionCount: 5 },
  { id: "derek-kwon", name: "Derek Kwon", sessionCount: 5 },
  { id: "priya-nair", name: "Priya Nair", sessionCount: 5 },
  { id: "marcus-bell", name: "Marcus Bell", sessionCount: 5 },
  { id: "expert-benchmark", name: "Expert Benchmark", sessionCount: 5 },
];

function getLatestSessionId(w: Welder): string {
  return `sess_${w.id}_${String(w.sessionCount).padStart(3, "0")}`;
}

/** Score-based color using design tokens. */
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

/** Fetch score with timeout; clears timer on settle to avoid leaks. */
async function fetchScoreWithTimeout(
  sessionId: string,
  signal?: AbortSignal
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
  } catch {
    return null;
  } finally {
    if (timeoutId !== undefined) clearTimeout(timeoutId);
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const [welderScores, setWelderScores] = useState<WelderScoreResult[] | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "risk" | "top">("all");

  useEffect(() => {
    let mounted = true;
    const controller = new AbortController();
    setLoading(true);

    const fetches = WELDERS.map((w) => ({
      welder: w,
      sessionId: getLatestSessionId(w),
    }));

    Promise.allSettled(
      fetches.map((f) =>
        fetchScoreWithTimeout(f.sessionId, controller.signal).catch(() => null)
      )
    ).then((results) => {
      if (!mounted) return;
      setWelderScores(
        fetches.map((f, i) => {
          const r = results[i];
          const score =
            r.status === "fulfilled" && r.value != null
              ? (r.value as SessionScore).total
              : null;
          return {
            welder: f.welder,
            score,
          };
        })
      );
      setLoading(false);
    });

    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  if (loading || welderScores === null) {
    return (
      <div className="min-h-screen bg-black text-gray-100 relative overflow-hidden">
        <div className="fixed inset-0 bg-gradient-to-br from-cyan-900/5 via-transparent to-emerald-900/5 pointer-events-none" />
        <div className="max-w-7xl mx-auto px-6 py-12">
          <h2 className="text-4xl font-bold mb-6">Welder Roster</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {WELDERS.filter((w) => w.id !== "expert-benchmark").map((w) => (
              <div
                key={w.id}
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

  const rosterResults =
    welderScores?.filter((r) => r.welder.id !== "expert-benchmark") ?? [];
  const sorted = [...rosterResults].sort((a, b) => {
    const sa = a.score ?? Infinity;
    const sb = b.score ?? Infinity;
    return sa - sb;
  });
  const filtered = sorted.filter(({ score }) => {
    if (filter === "risk") return score !== null && score < 60;
    if (filter === "top") return score !== null && score >= 85;
    return true;
  });

  const rosterWelders = WELDERS.filter((w) => w.id !== "expert-benchmark");
  const scores = rosterResults
    .map((r) => r.score)
    .filter((s): s is number => s !== null);
  const totalNonNull = scores.length;
  const avgScore =
    totalNonNull === 0
      ? "—"
      : String(Math.round(scores.reduce((a, b) => a + b, 0) / totalNonNull));
  const totalSessions = rosterWelders.reduce(
    (s, w) => s + w.sessionCount,
    0
  );
  const countAbove80 = scores.filter((s) => s >= 80).length;
  const qualityIndex =
    totalNonNull === 0
      ? "—"
      : `${Math.round((countAbove80 / totalNonNull) * 100)}%`;

  const expertResult = welderScores?.find(
    (r) => r.welder.id === "expert-benchmark"
  );
  const expertScore = expertResult?.score ?? null;

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
              label: "ACTIVE WELDERS",
              value: rosterWelders.length,
              accent: false,
            },
            { label: "AVG SCORE", value: avgScore, accent: true },
            {
              label: "TOTAL SESSIONS",
              value: totalSessions,
              accent: false,
            },
            {
              label: "QUALITY INDEX",
              value: qualityIndex,
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
            Roster — {filtered.length}{" "}
            {filtered.length === 1 ? "welder" : "welders"}
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
                  ? "All"
                  : f === "risk"
                    ? "At Risk"
                    : "Top Performers"}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filtered.map(({ welder, score }) => {
            const sessionId = getLatestSessionId(welder);
            const isExpert = welder.id === "expert-benchmark";
            const trend =
              score !== null
                ? Math.min(15, Math.max(-15, Math.round((score - 75) / 2)))
                : 0;
            return (
              <div
                key={welder.id}
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
                  <h3
                    className="text-[15px] font-semibold tracking-tight"
                    style={{ color: "#f0f2f4" }}
                  >
                    {welder.name}
                  </h3>
                  <div className="text-right">
                    {score !== null ? (
                      <span
                        data-score-tier={getScoreTier(score)}
                        className="text-[22px] font-medium leading-none"
                        style={{
                          color: getScoreColor(score),
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
                        background: getScoreColor(score),
                      }}
                    />
                  )}
                </div>

                {/* Meta */}
                <div className="flex items-center gap-2.5 mb-4">
                  <span
                    className="text-[11.5px] font-medium px-2.5 py-0.5 rounded-full"
                    style={{
                      fontFamily: "var(--font-geist-mono)",
                      color:
                        trend > 0
                          ? "#3dd68c"
                          : trend < 0
                            ? "#f06060"
                            : "#8a9099",
                      background:
                        trend > 0
                          ? "rgba(61,214,140,0.08)"
                          : trend < 0
                            ? "rgba(240,96,96,0.08)"
                            : "rgba(255,255,255,0.05)",
                    }}
                  >
                    {trend > 0 ? "↑" : trend < 0 ? "↓" : "·"}{" "}
                    {trend > 0 ? "+" : ""}
                    {trend}%
                  </span>
                  <span className="text-[12px]" style={{ color: "#404750" }}>
                    {welder.sessionCount} sessions
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
                      View report
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                  </Link>
                  {!isExpert && (
                    <Link
                      href={`/compare/${sessionId}/${EXPERT_SESSION_ID}`}
                      className="flex items-center justify-between py-[11px] text-[12.5px] transition-colors duration-100 group"
                      style={{
                        color: "#8a9099",
                        borderBottom: "1px solid rgba(255,255,255,0.04)",
                      }}
                    >
                      <span className="group-hover:text-[#f0f2f4] transition-colors">
                        Compare to expert
                      </span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                    </Link>
                  )}
                  <Link
                    href={`/seagull/welder/${welder.id}`}
                    className="flex items-center justify-between py-[11px] text-[12.5px] transition-colors duration-100 group"
                    style={{ color: "#8a9099" }}
                  >
                    <span className="group-hover:text-[#f0f2f4] transition-colors">
                      Full report
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
