"use client";

import { Suspense, use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchSession,
  fetchScore,
  fetchNarrative,
  fetchBenchmarks,
  type SessionScore,
} from "@/lib/api";
import { fetchTrajectory } from "@/lib/api.merge_agent1";
import {
  computeHistoricalScores,
  getTrajectoryFromResults,
  assertTrajectoryAtIdx,
} from "@/lib/welder-report-utils";
import { generateAIFeedback } from "@/lib/ai-feedback";
import { logError } from "@/lib/logger";
import { captureChartToBase64 } from "@/lib/pdf-chart-capture";
import { getApiBase } from "@/lib/api-base";
import { useFrameData } from "@/hooks/useFrameData";
import { useReportSummary } from "@/hooks/useReportSummary";
import { extractHeatmapData, tempToColorRange } from "@/utils/heatmapData";
import HeatMap from "@/components/welding/HeatMap";
import FeedbackPanel from "@/components/welding/FeedbackPanel";
import { NarrativePanel } from "@/components/welding/NarrativePanel";
import { LineChart } from "@/components/charts/LineChart";
import { ReportLayout } from "@/components/layout/ReportLayout";
import { TrajectoryChart } from "@/components/welding/TrajectoryChart";
import { BenchmarkPanel } from "@/components/welding/BenchmarkPanel";
import { CoachingPlanPanel } from "@/components/welding/CoachingPlanPanel";
import { CertificationCard } from "@/components/welding/CertificationCard";
import { ComplianceSummaryPanel } from "@/components/welding/ComplianceSummaryPanel";
import { ExcursionLogTable } from "@/components/welding/ExcursionLogTable";
import type { Session } from "@/types/session";
import type { WelderTrajectory } from "@/types/trajectory";
import type { WelderBenchmarks } from "@/types/benchmark";

// ---------------------------------------------------------------------------
// Constants — Must match WELDER_ARCHETYPES (backend/data/mock_welders.py)
// ---------------------------------------------------------------------------

const WELDER_SESSION_COUNT: Record<string, number> = {
  "mike-chen": 5,
  "sara-okafor": 5,
  "james-park": 5,
  "lucia-reyes": 5,
  "tom-bradley": 3,
  "ana-silva": 5,
  "derek-kwon": 5,
  "priya-nair": 5,
  "marcus-bell": 5,
  "expert-benchmark": 5,
};

const WELDER_DISPLAY_NAMES: Record<string, string> = {
  "mike-chen": "Mike Chen",
  "sara-okafor": "Sara Okafor",
  "james-park": "James Park",
  "lucia-reyes": "Lucia Reyes",
  "tom-bradley": "Tom Bradley",
  "ana-silva": "Ana Silva",
  "derek-kwon": "Derek Kwon",
  "priya-nair": "Priya Nair",
  "marcus-bell": "Marcus Bell",
  "expert-benchmark": "Expert Benchmark",
};

const EXPERT_SESSION_ID = "sess_expert-benchmark_005";

/** Coerce welder name to string; always returns string. Matches API route. */
function toWelderName(v: unknown): string {
  if (typeof v === "string" && v.trim().length > 0) return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return "Unknown";
}

function sanitizeDownloadFilename(name: string): string {
  const s = String(name).replace(/[^a-zA-Z0-9_-]/g, "-").slice(0, 64) || "welder";
  return `${s}-warp-report.pdf`;
}

function getLatestSessionId(welderId: string): string {
  const n = WELDER_SESSION_COUNT[welderId] ?? 1;
  return `sess_${welderId}_${String(n).padStart(3, "0")}`;
}


// ---------------------------------------------------------------------------
// Local subcomponents (page-specific; not extracted to separate files)
// ---------------------------------------------------------------------------

function SideBySideHeatmaps({
  heatmapData,
  expertHeatmapData,
  colorFn,
  sessionId,
  displayName,
  expertSession,
}: {
  heatmapData: ReturnType<typeof extractHeatmapData>;
  expertHeatmapData: ReturnType<typeof extractHeatmapData>;
  colorFn: (temp: number) => string;
  sessionId: string;
  displayName: string;
  expertSession: Session | null;
}) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
      <h2 className="text-xl font-bold mb-4">Thermal Comparison</h2>
      {expertSession ? (
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
      ) : (
        <div>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
            Expert comparison unavailable — run seed to add sess_expert-benchmark_005.
          </p>
          <HeatMap
            sessionId={sessionId}
            data={heatmapData}
            colorFn={colorFn}
            label={displayName}
          />
        </div>
      )}
    </div>
  );
}

function ActionsBar({
  onDownloadPDF,
  loading,
  pdfLoading,
  pdfError,
}: {
  onDownloadPDF: () => void;
  loading: boolean;
  pdfLoading: boolean;
  pdfError: string | null;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-4">
        <button
          className="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
          disabled
          title="Email report — coming soon"
        >
          📧 Email Report (coming soon)
        </button>
        <button
          className="bg-zinc-200 text-zinc-800 px-6 py-3 rounded-lg font-semibold hover:bg-zinc-300 dark:bg-zinc-700 dark:text-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={onDownloadPDF}
          disabled={loading || pdfLoading}
        >
          {pdfLoading ? "⏳ Generating..." : "📄 Download PDF"}
        </button>
      </div>
      {pdfError && (
        <p className="text-red-600 dark:text-red-400 text-sm">{pdfError}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

/**
 * Welder Report Page
 * Next.js 16: params is always a Promise. Tests pass Promise.resolve({ id }).
 */
export default function WelderReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
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

function WelderReportWithAsyncParams({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <WelderReportInner welderId={id} />;
}

function WelderReportInner({ welderId }: { welderId: string }) {
  const sessionId = getLatestSessionId(welderId);
  const displayName = WELDER_DISPLAY_NAMES[welderId] ?? welderId;
  const sessionCount = WELDER_SESSION_COUNT[welderId] ?? 1;

  const historicalSessionIds = Array.from(
    { length: sessionCount },
    (_, i) => `sess_${welderId}_${String(i + 1).padStart(3, "0")}`
  );

  const [session, setSession] = useState<Session | null>(null);
  const [expertSession, setExpertSession] = useState<Session | null>(null);
  const [score, setScore] = useState<SessionScore | null>(null);
  const [report, setReport] = useState<
    ReturnType<typeof generateAIFeedback> | null
  >(null);
  const [chartData, setChartData] = useState<
    { date: string; value: number }[] | null
  >(null);
  const [trajectory, setTrajectory] = useState<WelderTrajectory | null>(null);
  const [benchmarks, setBenchmarks] = useState<WelderBenchmarks | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    const fetchPrimary = fetchSession(sessionId, { limit: 2000 });
    const fetchExpert = fetchSession(EXPERT_SESSION_ID, { limit: 2000 });
    const fetchScorePrimary = fetchScore(sessionId);
    const histPromises = historicalSessionIds.map((sid) => fetchScore(sid));
    const benchmarksPromise = fetchBenchmarks(welderId).catch(() => null);
    const trajectoryPromise = fetchTrajectory(welderId);

    const allPromises = [
      fetchPrimary,
      fetchExpert,
      fetchScorePrimary,
      ...histPromises,
      benchmarksPromise,
      trajectoryPromise,
    ];
    const trajectoryIdx = allPromises.length - 1;

    Promise.allSettled(allPromises).then((results) => {
      if (!mounted) return;

      assertTrajectoryAtIdx(results, trajectoryIdx);

      const primaryResult = results[0];
      const expertResult = results[1];
      const scoreResult = results[2];

      const s =
        primaryResult?.status === "fulfilled"
          ? (primaryResult.value as Session)
          : null;
      const e =
        expertResult?.status === "fulfilled"
          ? (expertResult.value as Session)
          : null;
      const sc =
        scoreResult?.status === "fulfilled"
          ? (scoreResult.value as SessionScore)
          : null;

      if (s === null || sc === null) {
        const err =
          primaryResult.status === "rejected"
            ? primaryResult.reason
            : scoreResult.status === "rejected"
              ? scoreResult.reason
              : new Error("Primary session or score failed");
        logError(
          "WelderReport",
          err instanceof Error ? err : new Error(String(err))
        );
        const message =
          process.env.NODE_ENV === "development"
            ? primaryResult.status === "rejected"
              ? String(primaryResult.reason)
              : scoreResult.status === "rejected"
                ? String(scoreResult.reason)
                : "Session not found. Make sure mock data is seeded. See STARTME.md."
            : "Session not found. Make sure mock data is seeded. See STARTME.md.";
        setError(message);
        setSession(null);
        setExpertSession(null);
        setScore(null);
        setReport(null);
        setChartData(null);
        setTrajectory(null);
        setBenchmarks(null);
        setLoading(false);
        return;
      }

      const historicalScores = computeHistoricalScores(results, trajectoryIdx);
      const chartDataResult = historicalSessionIds.map((sid, i) => ({
        date: `Session ${i + 1}`,
        value: historicalScores[i] ?? 0,
      }));
      const traj = getTrajectoryFromResults<WelderTrajectory>(results, trajectoryIdx);
      const benchRes = results[trajectoryIdx - 1];
      const bench =
        benchRes?.status === "fulfilled"
          ? (benchRes.value as WelderBenchmarks | null)
          : null;

      setSession(s);
      setExpertSession(e);
      setScore(sc);
      setReport(generateAIFeedback(s, sc, historicalScores));
      setChartData(chartDataResult);
      setTrajectory(traj);
      setBenchmarks(bench);
      setLoading(false);
    });

    return () => {
      mounted = false;
    };
  }, [welderId, sessionId]);

  // Hooks must run unconditionally — call before any early returns
  const frameData = useFrameData(session?.frames ?? [], null, null);
  const expertFrameData = useFrameData(expertSession?.frames ?? [], null, null);
  const {
    data: reportSummary,
    loading: reportSummaryLoading,
    error: reportSummaryError,
  } = useReportSummary(sessionId);

  const handleDownloadPDF = useCallback(async () => {
    if (!report || !score) return;
    setPdfError(null);
    setPdfLoading(true);
    try {
      let narrativeText: string | null = null;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10_000);
      try {
        const n = await fetchNarrative(sessionId, controller.signal);
        narrativeText = n.narrative_text;
      } catch {
        // Non-blocking — PDF still generates without narrative (404, timeout, network error)
        narrativeText = null;
      } finally {
        clearTimeout(timeoutId);
      }

      const chartDataUrl = await captureChartToBase64("trend-chart");

      const welderName = toWelderName(displayName);
      const payload = {
        welder: { name: welderName },
        score: { total: score.total, rules: score.rules },
        feedback: {
          summary: report.summary,
          feedback_items: report.feedback_items,
        },
        chartDataUrl,
        narrative: narrativeText,
      };

      const apiUrl = `${getApiBase()}/api/welder-report-pdf`;
      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(
          (err as { error?: string }).error ??
            `Failed to generate PDF (${res.status})`
        );
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = sanitizeDownloadFilename(welderName);
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setPdfError(err instanceof Error ? err.message : String(err));
      logError("WelderReport", err, { context: "handleDownloadPDF" });
    } finally {
      setPdfLoading(false);
    }
  }, [report, score, displayName, sessionId]);

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <div className="bg-violet-50 dark:bg-violet-950/30 border border-violet-200 dark:bg-violet-800 rounded-lg p-6 max-w-md">
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

  if (loading || !report || !session) {
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
    ...(expertSession ? expertHeatmapData.points.map((p) => p.temp_celsius) : []),
  ];
  const minT = allTemps.length > 0 ? Math.min(...allTemps) : 0;
  const maxT = allTemps.length > 0 ? Math.max(...allTemps) : 600;
  const colorFn = tempToColorRange(minT, maxT);

  return (
    <ReportLayout
      welderName={displayName}
      sessionId={session.session_id}
      scoreTotal={report.score}
      weldType={session.weld_type}
      sessionDate={
        session?.start_time
          ? new Date(session.start_time).toLocaleDateString()
          : undefined
      }
      skillLevel={report.skill_level}
      trend={report.trend}
      thresholdSpec={
        score?.active_threshold_spec ? (
          <>
            Evaluated against{" "}
            {score.active_threshold_spec.weld_type.toUpperCase()} spec —
            Target {score.active_threshold_spec.angle_target}° ±
            {score.active_threshold_spec.angle_warning}°
          </>
        ) : undefined
      }
      backLink={
        <Link
          href="/seagull"
          className="text-blue-600 dark:text-blue-400 hover:underline text-sm"
        >
          ← Back to Team Dashboard
        </Link>
      }
      compliance={
        <>
          <ComplianceSummaryPanel
            data={reportSummary ?? null}
            error={reportSummaryError ?? undefined}
            isEmpty={
              !reportSummaryLoading && !reportSummary && !reportSummaryError
            }
          />
          <ExcursionLogTable
            excursions={reportSummary?.excursions ?? []}
          />
        </>
      }
      narrative={
        <NarrativePanel sessionId={session.session_id} />
      }
      heatmaps={
        <SideBySideHeatmaps
          heatmapData={heatmapData}
          expertHeatmapData={expertHeatmapData}
          colorFn={colorFn}
          sessionId={sessionId}
          displayName={displayName}
          expertSession={expertSession}
        />
      }
      feedback={
        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Detailed Feedback</h2>
          <FeedbackPanel items={report.feedback_items} />
        </div>
      }
      progress={
        <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-bold mb-4">Progress Over Time</h2>
          <div
            id="trend-chart"
            style={{ width: 600, height: 200 }}
            data-testid="trend-chart"
          >
            <LineChart
              data={chartData ?? []}
              color="#3b82f6"
              height={200}
            />
          </div>
        </div>
      }
      trajectory={
        trajectory ? <TrajectoryChart trajectory={trajectory} /> : undefined
      }
      benchmarks={
        benchmarks ? (
          <BenchmarkPanel benchmarks={benchmarks} />
        ) : undefined
      }
      coaching={<CoachingPlanPanel welderId={welderId} />}
      certification={<CertificationCard welderId={welderId} />}
      actions={
        <ActionsBar
          onDownloadPDF={handleDownloadPDF}
          loading={loading}
          pdfLoading={pdfLoading}
          pdfError={pdfError}
        />
      }
    />
  );
}
