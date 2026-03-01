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

// ---------------------------------------------------------------------------
// Constants — Must match WELDER_ARCHETYPES (backend/data/mock_welders.py)
// ---------------------------------------------------------------------------

const EXPERT_SESSION_ID = "sess_expert-benchmark_005";

interface Welder {
  id: string;
  name: string;
  sessionCount: number;
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

const FETCH_TIMEOUT_MS = 5000;

async function fetchScoreWithTimeout(sessionId: string): Promise<SessionScore | null> {
  const timeout = new Promise<null>((_, reject) =>
    setTimeout(() => reject(new Error("fetchScore timeout")), FETCH_TIMEOUT_MS)
  );
  try {
    return await Promise.race([fetchScore(sessionId), timeout]);
  } catch {
    return null;
  }
}

/** Score-based badge colour: red <60, amber 60–80, green ≥80 */
function getScoreBadgeClass(score: number | null): string {
  if (score === null) return "";
  if (score < 60) return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
  if (score < 80) return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300";
  return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300";
}

interface WelderScoreResult {
  welder: Welder;
  score: number | null;
  error: unknown;
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
    setLoading(true);

    const fetches = WELDERS.map((w) => ({
      welder: w,
      sessionId: getLatestSessionId(w),
    }));

    Promise.allSettled(
      fetches.map((f) => fetchScoreWithTimeout(f.sessionId).catch(() => null))
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
            error: null,
          };
        })
      );
      setLoading(false);
    });

    return () => {
      mounted = false;
    };
  }, []);

  if (loading || welderScores === null) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <div className="max-w-4xl">
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mb-6">
            Welder Roster
          </h1>
          <div className="grid gap-4 sm:grid-cols-2">
            {WELDERS.map((w) => (
              <div
                key={w.id}
                className="block p-6 bg-white dark:bg-zinc-900 rounded-lg shadow border border-zinc-200 dark:border-zinc-800 animate-pulse"
              >
                <div className="h-5 w-24 bg-zinc-200 dark:bg-zinc-700 rounded mb-2" />
                <div className="h-4 w-16 bg-zinc-200 dark:bg-zinc-700 rounded" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const sorted = [...welderScores].sort((a, b) => {
    const sa = a.score ?? Infinity;
    const sb = b.score ?? Infinity;
    return sa - sb;
  });

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="max-w-4xl">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mb-6">
          Welder Roster
        </h1>

        <div className="grid gap-4 sm:grid-cols-2">
          {sorted.map(({ welder, score }) => {
            const sessionId = getLatestSessionId(welder);
            const isExpert = welder.id === "expert-benchmark";
            const badgeClass = getScoreBadgeClass(score);

            return (
              <div
                key={welder.id}
                className="block p-6 bg-white dark:bg-zinc-900 rounded-lg shadow border border-zinc-200 dark:border-zinc-800 hover:border-blue-500 dark:hover:border-blue-500 transition-colors"
              >
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                  {welder.name}
                </h2>
                <p className="mt-2 text-sm flex items-center gap-2">
                  {score !== null ? (
                    <span
                      className={
                        badgeClass
                          ? `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${badgeClass}`
                          : "font-bold text-blue-600 dark:text-blue-400"
                      }
                    >
                      {score}/100
                    </span>
                  ) : (
                    <span className="text-violet-600 dark:text-violet-400">
                      Score unavailable
                    </span>
                  )}
                </p>
                <div className="mt-2 flex flex-col gap-1">
                  <Link
                    href={`/replay/${sessionId}`}
                    className="text-xs text-zinc-500 dark:text-zinc-400 hover:underline"
                  >
                    View report →
                  </Link>
                  {!isExpert && (
                    <Link
                      href={`/compare/${sessionId}/${EXPERT_SESSION_ID}`}
                      className="text-xs text-zinc-500 dark:text-zinc-400 hover:underline"
                    >
                      Compare to expert →
                    </Link>
                  )}
                  <Link
                    href={`/seagull/welder/${welder.id}`}
                    className="text-xs text-zinc-500 dark:text-zinc-400 hover:underline"
                  >
                    Full report →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
