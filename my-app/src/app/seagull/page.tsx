"use client";

/**
 * Seagull Team Dashboard — Step 6.
 *
 * Fetches fetchScore per welder; displays cards with name, score (or "Score unavailable").
 * Uses Promise.allSettled so one failing score does not block others.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchScore } from "@/lib/api";
import type { SessionScore } from "@/lib/api";

// ---------------------------------------------------------------------------
// Constants — Single source of truth for pilot welders
// ---------------------------------------------------------------------------

interface Welder {
  id: string;
  name: string;
  sessionId: string;
}

const WELDERS: Welder[] = [
  { id: "mike-chen", name: "Mike Chen", sessionId: "sess_novice_001" },
  { id: "expert-benchmark", name: "Expert Benchmark", sessionId: "sess_expert_001" },
];

interface WelderScoreResult {
  welder: Welder;
  score: number | null;
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
    Promise.allSettled(
      WELDERS.map((w) => fetchScore(w.sessionId))
    ).then((results) => {
      if (!mounted) return;
      const scores: WelderScoreResult[] = results.map((r, i) => ({
        welder: WELDERS[i],
        score: r.status === "fulfilled" ? (r.value as SessionScore).total : null,
        error: r.status === "rejected" ? r.reason : null,
      }));
      setWelderScores(scores);
      setLoading(false);
    });
    return () => {
      mounted = false;
    };
  }, []);

  if (loading || welderScores === null) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-sm text-zinc-500 dark:text-zinc-400">
          Loading scores...
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
          {welderScores.map(({ welder, score }) => (
            <Link
              key={welder.id}
              href={`/seagull/welder/${welder.id}`}
              className="block p-6 bg-white dark:bg-zinc-900 rounded-lg shadow border border-zinc-200 dark:border-zinc-800 hover:border-blue-500 dark:hover:border-blue-500 transition-colors"
            >
              <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                {welder.name}
              </h2>
              <p className="mt-2 text-sm">
                {score !== null ? (
                  <span className="font-bold text-blue-600 dark:text-blue-400">
                    {score}/100
                  </span>
                ) : (
                  <span className="text-amber-600 dark:text-amber-400">
                    Score unavailable
                  </span>
                )}
              </p>
              <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                View report →
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
