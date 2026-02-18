"use client";

/**
 * Seagull Team Dashboard — 10 welders with skill arcs.
 *
 * Fetches latest and second-latest score per welder for badge (On track / Needs attention).
 * Uses Promise.allSettled with 5s timeout so one failure doesn't block others.
 * setWelderScores called once after all fetches resolve (single setState).
 *
 * Pre-flight: Verify WELDERS matches WELDER_ARCHETYPES (IDs and sessionCount).
 * Prerequisite: Run seed before opening dashboard.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchScore } from "@/lib/api";
import type { SessionScore } from "@/lib/api";

// ---------------------------------------------------------------------------
// Constants — Must match WELDER_ARCHETYPES (backend/data/mock_welders.py)
// ---------------------------------------------------------------------------

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

function getSecondLatestSessionId(w: Welder): string | null {
  if (w.sessionCount < 2) return null;
  return `sess_${w.id}_${String(w.sessionCount - 1).padStart(3, "0")}`;
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

function getBadge(
  score: number | null,
  secondScore: number | null
): "on_track" | "needs_attention" | "neutral" | null {
  if (score === null || secondScore === null) return null;
  const diff = score - secondScore;
  if (Math.abs(diff) <= 2) return "neutral";
  if (diff > 0) return "on_track";
  return "needs_attention";
}

interface WelderScoreResult {
  welder: Welder;
  score: number | null;
  secondScore: number | null;
  error: unknown;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function SeagullDashboardPage() {
  const [welderScores, setWelderScores] = useState<WelderScoreResult[] | null>(
    null
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);

    const fetches: { welder: Welder; sessionId: string; isLatest: boolean }[] = [];
    WELDERS.forEach((w) => {
      fetches.push({ welder: w, sessionId: getLatestSessionId(w), isLatest: true });
      const second = getSecondLatestSessionId(w);
      if (second) fetches.push({ welder: w, sessionId: second, isLatest: false });
    });

    Promise.allSettled(
      fetches.map((f) => fetchScoreWithTimeout(f.sessionId).catch(() => null))
    ).then((results) => {
      if (!mounted) return;
      const byWelder = new Map<
        string,
        { latest: number | null; second: number | null }
      >();
      WELDERS.forEach((w) => byWelder.set(w.id, { latest: null, second: null }));
      fetches.forEach((f, i) => {
        const r = results[i];
        const val =
          r.status === "fulfilled" && r.value != null
            ? (r.value as SessionScore).total
            : null;
        const entry = byWelder.get(f.welder.id)!;
        if (f.isLatest) entry.latest = val;
        else entry.second = val;
      });
      setWelderScores(
        WELDERS.map((w) => {
          const { latest, second } = byWelder.get(w.id)!;
          return {
            welder: w,
            score: latest,
            secondScore: second,
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
            Team Dashboard — Seagull Pilot
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

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="max-w-4xl">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100 mb-6">
          Team Dashboard — Seagull Pilot
        </h1>

        <div className="grid gap-4 sm:grid-cols-2">
          {welderScores.map(({ welder, score, secondScore }) => {
            const badge = getBadge(score, secondScore);
            return (
              <Link
                key={welder.id}
                href={`/seagull/welder/${welder.id}`}
                className="block p-6 bg-white dark:bg-zinc-900 rounded-lg shadow border border-zinc-200 dark:border-zinc-800 hover:border-blue-500 dark:hover:border-blue-500 transition-colors"
              >
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                  {welder.name}
                </h2>
                <p className="mt-2 text-sm flex items-center gap-2">
                  {score !== null ? (
                    <span className="font-bold text-blue-600 dark:text-blue-400">
                      {score}/100
                    </span>
                  ) : (
                    <span className="text-violet-600 dark:text-violet-400">
                      Score unavailable
                    </span>
                  )}
                  {badge === "on_track" && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                      On track
                    </span>
                  )}
                  {badge === "needs_attention" && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
                      Needs attention
                    </span>
                  )}
                  {badge === "neutral" && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                      Neutral
                    </span>
                  )}
                </p>
                <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                  View report →
                </p>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
