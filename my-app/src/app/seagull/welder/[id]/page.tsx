"use client";

import { Suspense, use, useEffect, useState } from "react";
import Link from "next/link";
import { fetchSession, fetchScore, type SessionScore } from "@/lib/api";
import { generateAIFeedback } from "@/lib/ai-feedback";
import { logError } from "@/lib/logger";
import { useFrameData } from "@/hooks/useFrameData";
import { extractHeatmapData, tempToColorRange } from "@/utils/heatmapData";
import HeatMap from "@/components/welding/HeatMap";
import FeedbackPanel from "@/components/welding/FeedbackPanel";
import { LineChart } from "@/components/charts/LineChart";
import type { Session } from "@/types/session";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const WELDER_MAP: Record<string, string> = {
  "mike-chen": "sess_novice_001",
  "expert-benchmark": "sess_expert_001",
};

const WELDER_DISPLAY_NAMES: Record<string, string> = {
  "mike-chen": "Mike Chen",
  "expert-benchmark": "Expert Benchmark",
};

const MOCK_HISTORICAL = [
  { date: "Week 1", value: 68 },
  { date: "Week 2", value: 72 },
  { date: "Week 3", value: 75 },
];

type WelderParams = { id: string } | Promise<{ id: string }>;

function isPromise(p: WelderParams): p is Promise<{ id: string }> {
  return p != null && typeof (p as Promise<unknown>).then === "function";
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function WelderReportPage({
  params,
}: {
  params: WelderParams;
}) {
  if (isPromise(params)) {
    return (
      <Suspense
        fallback={
          <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
            <div className="text-sm text-zinc-500">Loading...</div>
          </div>
        }
      >
        <WelderReportWithAsyncParams params={params} />
      </Suspense>
    );
  }
  return <WelderReportInner welderId={params.id} />;
}

function WelderReportWithAsyncParams({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <WelderReportInner welderId={id} />;
}

function WelderReportInner({ welderId }: { welderId: string }) {
  const sessionId = WELDER_MAP[welderId] ?? welderId;
  const displayName = WELDER_DISPLAY_NAMES[welderId] ?? welderId;

  const [session, setSession] = useState<Session | null>(null);
  const [expertSession, setExpertSession] = useState<Session | null>(null);
  const [score, setScore] = useState<SessionScore | null>(null);
  const [report, setReport] = useState<
    ReturnType<typeof generateAIFeedback> | null
  >(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    Promise.all([
      fetchSession(sessionId, { limit: 2000 }),
      fetchSession("sess_expert_001", { limit: 2000 }),
      fetchScore(sessionId),
    ])
      .then(([s, e, sc]) => {
        if (!mounted) return;
        setSession(s);
        setExpertSession(e);
        setScore(sc);
        setReport(generateAIFeedback(s, sc, [68, 72, 75]));
      })
      .catch((err) => {
        logError("WelderReport", err);
        if (!mounted) return;
        const message =
          process.env.NODE_ENV === "development"
            ? err instanceof Error ? err.message : String(err)
            : "Session not found. Make sure mock data is seeded. See STARTME.md.";
        setError(message);
        setSession(null);
        setExpertSession(null);
        setScore(null);
        setReport(null);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [sessionId]);

  // Hooks must run unconditionally — call before any early returns
  const frameData = useFrameData(session?.frames ?? [], null, null);
  const expertFrameData = useFrameData(expertSession?.frames ?? [], null, null);

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <div className="bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:border-violet-800 rounded-lg p-6 max-w-md">
          <h2 className="text-lg font-bold text-violet-900 dark:text-violet-200">
            ⚠️ Error
          </h2>
          <p className="text-violet-800 dark:text-violet-300 mt-2 text-sm">{error}</p>
          <Link
            href="/seagull"
            className="text-blue-600 dark:text-blue-400 underline mt-4 block"
          >
            ← Back to Team Dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (loading || !report || !session || !expertSession) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        Loading AI analysis...
      </div>
    );
  }

  const heatmapData = extractHeatmapData(frameData.thermal_frames);
  const expertHeatmapData = extractHeatmapData(expertFrameData.thermal_frames);

  const allTemps = [
    ...heatmapData.points.map((p) => p.temp_celsius),
    ...expertHeatmapData.points.map((p) => p.temp_celsius),
  ];
  const minT = allTemps.length > 0 ? Math.min(...allTemps) : 0;
  const maxT = allTemps.length > 0 ? Math.max(...allTemps) : 600;
  const colorFn = tempToColorRange(minT, maxT);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="mb-4">
        <Link
          href="/seagull"
          className="text-blue-600 dark:text-blue-400 hover:underline text-sm"
        >
          ← Back to Team Dashboard
        </Link>
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">
            {displayName} — Weekly Report
          </h1>
          <div className="text-right">
            <div className="text-5xl font-bold text-blue-600">
              {report.score}/100
            </div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400">
              {report.skill_level} • {report.trend}
            </div>
          </div>
        </div>
        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/30 border-l-4 border-blue-500 rounded">
          <p className="text-sm font-medium">
            🤖 AI Analysis: {report.summary}
          </p>
        </div>
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold mb-4">Thermal Comparison</h2>
        <div className="grid grid-cols-2 gap-8">
          <div>
            <h3 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-2">
              Expert Benchmark
            </h3>
            <HeatMap
              sessionId="expert"
              data={expertHeatmapData}
              colorFn={colorFn}
              label="Expert"
            />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-2">
              Your Weld
            </h3>
            <HeatMap
              sessionId={sessionId}
              data={heatmapData}
              colorFn={colorFn}
              label={displayName}
            />
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold mb-4">Detailed Feedback</h2>
        <FeedbackPanel items={report.feedback_items} />
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold mb-4">Progress Over Time</h2>
        <LineChart data={MOCK_HISTORICAL} color="#3b82f6" height={200} />
      </div>

      <div className="flex gap-4">
        <button
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700"
          onClick={() => alert("Email report — coming soon")}
        >
          📧 Email Report
        </button>
        <button
          className="bg-zinc-200 text-zinc-800 px-6 py-3 rounded-lg font-semibold hover:bg-zinc-300 dark:bg-zinc-700 dark:text-zinc-200"
          onClick={() => alert("Download PDF — coming soon")}
        >
          📄 Download PDF
        </button>
      </div>
    </div>
  );
}
