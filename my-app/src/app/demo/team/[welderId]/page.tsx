"use client";

/**
 * Demo Welder Report — Browser-only welder report.
 *
 * Uses getDemoTeamData; no fetchSession/fetchScore.
 * When session.frames is empty or thermal data absent: PlaceholderHeatMap (neutral gradient).
 * Never white screen.
 * Threshold callout: prefer mock score's active_threshold_spec; else fetch GET /api/thresholds.
 */

import { use, Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { getDemoTeamData, DEMO_WELDERS } from "@/lib/seagull-demo-data";
import { fetchThresholds } from "@/lib/api";
import type { WeldTypeThresholds } from "@/types/thresholds";
import { useFrameData } from "@/hooks/useFrameData";
import {
  extractHeatmapData,
  tempToColorRange,
} from "@/utils/heatmapData";
import { computeMinMaxTemp } from "@/utils/heatmapTempRange";
import HeatMap from "@/components/welding/HeatMap";
import FeedbackPanel from "@/components/welding/FeedbackPanel";
import { LineChart } from "@/components/charts/LineChart";

const MOCK_HISTORICAL_CHART = [
  { date: "Week 1", value: 68 },
  { date: "Week 2", value: 72 },
  { date: "Week 3", value: 75 },
];

/** Placeholder when no thermal data — neutral gradient, no white screen. */
function PlaceholderHeatMap({ label }: { label: string }) {
  return (
    <div className="heat-map-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
        {label}
      </h3>
      <div
        className="min-h-[300px] flex items-center justify-center rounded border border-dashed border-zinc-300 dark:border-zinc-700"
        style={{
          background:
            "linear-gradient(135deg, #e2e8f0 0%, #94a3b8 50%, #64748b 100%)",
        }}
      >
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          No thermal data — demo placeholder
        </p>
      </div>
    </div>
  );
}

function WelderReportContent({ welderId }: { welderId: string }) {
  const data = getDemoTeamData(welderId);
  const { session, expertSession, report } = data;
  const [fetchedThresholds, setFetchedThresholds] = useState<
    WeldTypeThresholds[] | null
  >(null);

  useEffect(() => {
    fetchThresholds()
      .then(setFetchedThresholds)
      .catch(() => setFetchedThresholds(null));
  }, []);

  const sessionFrames = session?.frames ?? [];
  const expertFrames = expertSession?.frames ?? [];

  const frameData = useFrameData(sessionFrames, null, null);
  const expertFrameData = useFrameData(expertFrames, null, null);

  const heatmapData = extractHeatmapData(frameData.thermal_frames);
  const expertHeatmapData = extractHeatmapData(expertFrameData.thermal_frames);

  const hasSessionThermal = heatmapData.point_count > 0;
  const hasExpertThermal = expertHeatmapData.point_count > 0;

  const allPoints = [...heatmapData.points, ...expertHeatmapData.points];
  const { min: minT, max: maxT } = computeMinMaxTemp(allPoints);
  const colorFn = tempToColorRange(minT, maxT);

  const displayName =
    DEMO_WELDERS.find((w) => w.id === welderId)?.name ?? welderId;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="mb-4">
        <Link
          href="/demo/team"
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
            {data.score?.active_threshold_spec ? (
              <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                Evaluated against{' '}
                {data.score.active_threshold_spec.weld_type.toUpperCase()} spec
                — Target {data.score.active_threshold_spec.angle_target}° ±
                {data.score.active_threshold_spec.angle_warning}°
              </div>
            ) : (
              (() => {
                const mig = fetchedThresholds?.find(
                  (t) => t.weld_type === 'mig'
                );
                return mig ? (
                  <div className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                    Evaluated against MIG spec — Target{' '}
                    {mig.angle_target_degrees}° ±{mig.angle_warning_margin}°
                  </div>
                ) : null;
              })()
            )}
          </div>
        </div>
        <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-950/30 border-l-4 border-blue-500 rounded">
          <p className="text-sm font-medium">🤖 AI Analysis: {report.summary}</p>
        </div>
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold mb-4">Thermal Comparison</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
          <div>
            <h3 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-2">
              Expert Benchmark
            </h3>
            {hasExpertThermal ? (
              <HeatMap
                sessionId="expert"
                data={expertHeatmapData}
                colorFn={colorFn}
                label="Expert"
              />
            ) : (
              <PlaceholderHeatMap label="Expert" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 mb-2">
              Your Weld
            </h3>
            {hasSessionThermal && session ? (
              <HeatMap
                sessionId={session.session_id}
                data={heatmapData}
                colorFn={colorFn}
                label={displayName}
              />
            ) : (
              <PlaceholderHeatMap label={displayName} />
            )}
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold mb-4">Detailed Feedback</h2>
        <FeedbackPanel items={report.feedback_items} />
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold mb-4">Progress Over Time</h2>
        <LineChart data={MOCK_HISTORICAL_CHART} color="#3b82f6" height={200} />
      </div>
    </div>
  );
}

function DemoTeamWelderPageInner({
  params,
}: {
  params: Promise<{ welderId: string }>;
}) {
  const { welderId } = use(params);

  if (!DEMO_WELDERS.some((w) => w.id === welderId)) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-8">
        <p className="text-zinc-600 dark:text-zinc-400">Welder not found</p>
        <Link
          href="/demo/team"
          className="text-blue-600 dark:text-blue-400 hover:underline text-sm mt-4 block"
        >
          ← Back to Team Dashboard
        </Link>
      </div>
    );
  }

  return <WelderReportContent welderId={welderId} />;
}

export default function DemoTeamWelderPage({
  params,
}: {
  params: Promise<{ welderId: string }>;
}) {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
          <span className="text-sm text-zinc-500">Loading…</span>
        </div>
      }
    >
      <DemoTeamWelderPageInner params={params} />
    </Suspense>
  );
}
