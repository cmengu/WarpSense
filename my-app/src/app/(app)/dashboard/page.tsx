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
import { ArrowRight, TrendingUp, AlertTriangle, CheckCircle } from "lucide-react";

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

/** Score-based color for badge styling (emerald/lime/amber/orange/red). */
function getScoreColor(score: number | null): string {
  if (score === null) return "#6b7280";
  if (score >= 90) return "#00ff9f";
  if (score >= 75) return "#7fff00";
  if (score >= 60) return "#ffb800";
  if (score >= 40) return "#ff6b00";
  return "#ff3838";
}

/** Score tier for data-score-tier attribute (test compatibility). */
function getScoreTier(score: number | null): string {
  if (score === null) return "unknown";
  if (score >= 90) return "excellent";
  if (score >= 75) return "good";
  if (score >= 60) return "fair";
  if (score >= 40) return "poor";
  return "critical";
}

/** Fetch score with timeout; clears timer on settle to avoid leaks. */
async function fetchScoreWithTimeout(
  sessionId: string,
  signal?: AbortSignal
): Promise<SessionScore | null> {
  let timeoutId: ReturnType<typeof setTimeout>;
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
    clearTimeout(timeoutId!);
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
        <h2 className="text-4xl font-bold tracking-tight mb-2">
          Welder Roster
        </h2>
        <p className="text-gray-500 text-sm mb-6">
          Last updated: {new Date().toLocaleTimeString()}
        </p>
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div
            className="rounded-lg p-4"
            style={{
              background:
                "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
            }}
          >
            <div className="text-2xl font-bold text-gray-100">
              {rosterWelders.length}
            </div>
            <div className="text-xs text-gray-500 uppercase tracking-wider">
              Active Welders
            </div>
          </div>
          <div
            className="rounded-lg p-4"
            style={{
              background:
                "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
            }}
          >
            <div className="text-2xl font-bold text-gray-100">{avgScore}</div>
            <div className="text-xs text-gray-500 uppercase tracking-wider">
              Avg Score
            </div>
          </div>
          <div
            className="rounded-lg p-4"
            style={{
              background:
                "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
            }}
          >
            <div className="text-2xl font-bold text-gray-100">
              {totalSessions}
            </div>
            <div className="text-xs text-gray-500 uppercase tracking-wider">
              Total Sessions
            </div>
          </div>
          <div
            className="rounded-lg p-4"
            style={{
              background:
                "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
            }}
          >
            <div className="text-2xl font-bold text-gray-100">
              {qualityIndex}
            </div>
            <div className="text-xs text-gray-500 uppercase tracking-wider">
              Quality Index
            </div>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {sorted.map(({ welder, score }) => {
            const sessionId = getLatestSessionId(welder);
            const isExpert = welder.id === "expert-benchmark";
            const trend =
              score !== null
                ? Math.min(15, Math.max(-15, Math.round((score - 75) / 2)))
                : 0;
            return (
              <div
                key={welder.id}
                className="relative rounded-xl overflow-hidden p-6 transition-colors duration-200"
                style={{
                  background:
                    "linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
                  boxShadow:
                    "0 8px 32px -8px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05)",
                }}
              >
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-xl font-bold text-gray-100">
                    {welder.name}
                  </h3>
                  <div
                    className="flex items-center gap-2"
                    style={{
                      color:
                        score !== null ? getScoreColor(score) : undefined,
                    }}
                  >
                    {score !== null &&
                      (score >= 90 ? (
                        <CheckCircle className="w-4 h-4" />
                      ) : score >= 60 ? (
                        <TrendingUp className="w-4 h-4" />
                      ) : (
                        <AlertTriangle className="w-4 h-4" />
                      ))}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-4">
                  <span>{welder.sessionCount} sessions</span>
                  <span>•</span>
                  <span
                    className={
                      trend > 0
                        ? "text-emerald-400"
                        : trend < 0
                          ? "text-red-400"
                          : "text-gray-500"
                    }
                  >
                    {trend > 0 ? "+" : ""}
                    {trend}%
                    <TrendingUp
                      className={`inline w-3 h-3 ml-0.5 ${trend < 0 ? "rotate-180" : ""}`}
                    />
                  </span>
                </div>
                <div className="mb-6">
                  {score !== null ? (
                    <span
                      data-score-tier={getScoreTier(score)}
                      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                      style={{
                        color: getScoreColor(score),
                        backgroundColor: `${getScoreColor(score)}20`,
                      }}
                    >
                      {score}/100
                    </span>
                  ) : (
                    <span className="text-violet-400">Score unavailable</span>
                  )}
                </div>
                <div className="space-y-2">
                  <Link
                    href={`/replay/${sessionId}`}
                    className="flex items-center justify-between text-sm text-gray-400 hover:text-cyan-400 py-2"
                  >
                    <span>View report</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                  {!isExpert && (
                    <Link
                      href={`/compare/${sessionId}/${EXPERT_SESSION_ID}`}
                      className="flex items-center justify-between text-sm text-gray-400 hover:text-cyan-400 py-2"
                    >
                      <span>Compare to expert</span>
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  )}
                  <Link
                    href={`/seagull/welder/${welder.id}`}
                    className="flex items-center justify-between text-sm text-gray-400 hover:text-cyan-400 py-2"
                  >
                    <span>Full report</span>
                    <ArrowRight className="w-4 h-4" />
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
