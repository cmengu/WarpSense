'use client';

/**
 * Demo Page — Browser-only welding replay demo.
 *
 * PURPOSE: Self-contained demo at /demo with zero backend/DB/seed.
 * All data synthesized in-browser via lib/demo-data.ts. Enables sending
 * one URL to prospects, demoing on any device, no setup.
 *
 * Reuses HeatMap, TorchViz3D, TorchAngleGraph with same prop contracts.
 * No fetchSession/fetchScore; no useFrameData (fixed 0–15000ms).
 *
 * @see .cursor/issues/browser-only-demo-mode.md
 * @see .cursor/plans/browser-only-demo-mode-plan.md
 */

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import {
  generateExpertSession,
  generateNoviceSession,
  DURATION_MS,
  FRAME_INTERVAL_MS,
} from '@/lib/demo-data';
import {
  MOCK_EXPERT_SCORE_VALUE,
  MOCK_NOVICE_SCORE_VALUE,
} from '@/lib/demo-config';
import { DemoTour } from '@/components/demo/DemoTour';
import { DEMO_TOUR_STEPS } from '@/lib/demo-tour-config';
import type { TourStep } from '@/lib/demo-tour-config';
import type { Session } from '@/types/session';
import { extractHeatmapData } from '@/utils/heatmapData';
import { extractAngleData } from '@/utils/angleData';
import {
  getFrameAtTimestamp,
  extractCenterTemperatureWithCarryForward,
  filterThermalFrames,
} from '@/utils/frameUtils';
import {
  THERMAL_MAX_TEMP,
  THERMAL_MIN_TEMP,
  THERMAL_COLOR_SENSITIVITY,
} from '@/constants/thermal';
import { logError } from '@/lib/logger';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import HeatMap from '@/components/welding/HeatMap';
import TorchAngleGraph from '@/components/welding/TorchAngleGraph';

// Dynamic import for TorchWithHeatmap3D — unified torch + thermal metal
// Per WEBGL_CONTEXT_LOSS.md: max 2 instances (expert, novice)
const TorchWithHeatmap3D = dynamic(
  () => import('@/components/welding/TorchWithHeatmap3D').then((m) => m.default),
  {
    ssr: false,
    loading: () => (
      <div
        className="flex h-64 w-full items-center justify-center rounded-xl border-2 border-blue-400/40 bg-neutral-900"
        role="status"
        aria-live="polite"
      >
        <span className="text-blue-400/80 animate-pulse">Loading 3D…</span>
      </div>
    ),
  }
);

export default function DemoPage() {
  // Defer session generation to useEffect to avoid blocking main thread on mount.
  // ~3000 frames built synchronously would cause 50-200ms+ jank on low-end devices.
  const [sessions, setSessions] = useState<{
    expert: Session;
    novice: Session;
  } | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    try {
      setSessions({
        expert: generateExpertSession(),
        novice: generateNoviceSession(),
      });
    } catch (err) {
      logError('DemoPage', err, { context: 'session-generation' });
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-950 p-8">
        <div className="p-8 bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-800 rounded-lg max-w-md">
          <h2 className="text-lg font-semibold text-violet-800 dark:text-violet-400 mb-2">
            Demo failed to load
          </h2>
          <p className="text-sm text-violet-600 dark:text-violet-500 mb-4">
            {error.message}
          </p>
          <button
            type="button"
            onClick={() =>
              typeof window !== 'undefined' && window.location.reload()
            }
            className="px-4 py-2 bg-violet-600 text-white rounded hover:bg-violet-700 transition-colors"
          >
            Refresh page
          </button>
        </div>
      </div>
    );
  }

  if (!sessions) {
    return (
      <div
        className="min-h-screen flex items-center justify-center bg-neutral-950"
        role="status"
        aria-live="polite"
      >
        <span className="text-blue-400/80 animate-pulse">Loading demo…</span>
      </div>
    );
  }

  return <DemoPageContent sessions={sessions} />;
}

/** Main demo content — receives pre-generated sessions; all hooks run unconditionally within. */
function DemoPageContent({
  sessions: { expert: expertSession, novice: noviceSession },
}: {
  sessions: { expert: Session; novice: Session };
}) {
  const [showTour, setShowTour] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [currentTimestamp, setCurrentTimestamp] = useState(0);
  const prevTimestampRef = useRef(0);
  const scrubTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const onStepEnter = useCallback((step: TourStep) => {
    if (scrubTimeoutRef.current) clearTimeout(scrubTimeoutRef.current);
    const ts = step.timestamp_ms;
    if (ts != null) {
      scrubTimeoutRef.current = setTimeout(() => {
        setCurrentTimestamp(ts);
        setPlaying(false);
        scrubTimeoutRef.current = null;
      }, 150);
    }
  }, []);

  useEffect(
    () => () => {
      if (scrubTimeoutRef.current) clearTimeout(scrubTimeoutRef.current);
    },
    []
  );

  // Extract heatmap and angle data (memoized; sessions are stable)
  const expertHeatmap = useMemo(
    () => extractHeatmapData(expertSession.frames),
    [expertSession.frames]
  );
  const noviceHeatmap = useMemo(
    () => extractHeatmapData(noviceSession.frames),
    [noviceSession.frames]
  );
  const expertAngle = useMemo(
    () => extractAngleData(expertSession.frames),
    [expertSession.frames]
  );
  const noviceAngle = useMemo(
    () => extractAngleData(noviceSession.frames),
    [noviceSession.frames]
  );
  const expertThermalFrames = useMemo(
    () => filterThermalFrames(expertSession.frames),
    [expertSession.frames]
  );
  const noviceThermalFrames = useMemo(
    () => filterThermalFrames(noviceSession.frames),
    [noviceSession.frames]
  );

  // Playback loop: advance every FRAME_INTERVAL_MS. At end: stop and reset to 0.
  // Per plan Critical Decision 5: no auto-loop; user clicks Play to restart.
  // Per code review: setState updater must be pure — no side effects. Use ref + useEffect
  // to detect wrap-around (timestamp 14990→0) and stop playback.
  useEffect(() => {
    if (!playing) return;

    const id = setInterval(() => {
      setCurrentTimestamp((prev) => {
        const next = prev + FRAME_INTERVAL_MS;
        if (next >= DURATION_MS) return 0;
        return next;
      });
    }, FRAME_INTERVAL_MS);

    return () => clearInterval(id);
  }, [playing]);

  // Stop playback when we wrap from end (≥14990ms) to 0 — avoid side effect in updater
  useEffect(() => {
    const prev = prevTimestampRef.current;
    prevTimestampRef.current = currentTimestamp;
    if (
      playing &&
      currentTimestamp === 0 &&
      prev >= DURATION_MS - FRAME_INTERVAL_MS
    ) {
      setPlaying(false);
    }
  }, [playing, currentTimestamp]);

  // Frame and temp at current timestamp (getFrameAtTimestamp matches replay pattern)
  const expertFrame = getFrameAtTimestamp(expertSession.frames, currentTimestamp);
  const noviceFrame = getFrameAtTimestamp(noviceSession.frames, currentTimestamp);

  const expertAngleDeg = expertFrame?.angle_degrees ?? 45;
  const noviceAngleDeg = noviceFrame?.angle_degrees ?? 45;

  const expertTemp = extractCenterTemperatureWithCarryForward(
    expertSession.frames,
    currentTimestamp
  );
  const noviceTemp = extractCenterTemperatureWithCarryForward(
    noviceSession.frames,
    currentTimestamp
  );

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      {showTour && (
        <DemoTour
          steps={DEMO_TOUR_STEPS}
          onStepEnter={onStepEnter}
          onComplete={() => setShowTour(false)}
          onSkip={() => setShowTour(false)}
        />
      )}

      {/* Header */}
      <div className="border-b-2 border-blue-400 bg-neutral-900 p-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold text-blue-400 uppercase tracking-wider">
            WarpSense — Live Quality Analysis
          </h1>
          <p className="text-gray-400 mt-2">
            Real-time weld quality feedback system for industrial training
          </p>
        </div>
        <Link
          href="/demo/team"
          onClick={() => setShowTour(false)}
          className="px-6 py-3 bg-blue-400 text-black font-bold rounded hover:bg-blue-300 transition shrink-0"
        >
          See Team Management →
        </Link>
      </div>

      {/* Main content: side-by-side expert vs novice */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 p-8 pb-32">
        {/* Expert column */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <div
              className="w-4 h-4 bg-blue-400 rounded-full animate-pulse"
              aria-hidden
            />
            <h2 className="text-2xl font-bold text-blue-400">
              EXPERT WELDER
            </h2>
            <span className="ml-auto text-3xl font-bold text-blue-400">
              {MOCK_EXPERT_SCORE_VALUE}/100
            </span>
          </div>

          <ErrorBoundary>
            <div className="h-64">
              <TorchWithHeatmap3D
                angle={expertAngleDeg}
                temp={expertTemp}
                label="Expert Technique"
                frames={expertThermalFrames}
                activeTimestamp={currentTimestamp}
                maxTemp={THERMAL_MAX_TEMP}
                minTemp={THERMAL_MIN_TEMP}
                colorSensitivity={THERMAL_COLOR_SENSITIVITY}
              />
            </div>
          </ErrorBoundary>

          {/* 2D HeatMap fallback: shown only when no thermal data (3D thermal uses TorchWithHeatmap3D). */}
          {expertThermalFrames.length === 0 && (
            <ErrorBoundary
              fallback={
                <div className="min-h-[200px] flex items-center justify-center rounded-xl border-2 border-violet-400/40 bg-neutral-900 text-violet-400">
                  Heat map unavailable
                </div>
              }
            >
              <HeatMap
                sessionId="demo_expert"
                data={expertHeatmap}
                activeTimestamp={currentTimestamp}
                label="Temperature Profile"
              />
            </ErrorBoundary>
          )}

          <ErrorBoundary>
            <TorchAngleGraph
              sessionId="demo_expert"
              data={expertAngle}
              activeTimestamp={currentTimestamp}
            />
          </ErrorBoundary>

          <div className="bg-blue-900/20 border border-blue-400/50 rounded-lg p-4 space-y-2">
            <p className="text-blue-400 flex items-center gap-2">
              <span aria-hidden>✓</span>
              <span>Consistent temperature (±5°C)</span>
            </p>
            <p className="text-blue-400 flex items-center gap-2">
              <span aria-hidden>✓</span>
              <span>Steady torch angle (45° ±0.5°)</span>
            </p>
            <p className="text-blue-400 flex items-center gap-2">
              <span aria-hidden>✓</span>
              <span>Smooth heat dissipation (30°C/s)</span>
            </p>
          </div>
        </div>

        {/* Novice column */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <div
              className="w-4 h-4 bg-violet-400 rounded-full animate-pulse"
              aria-hidden
            />
            <h2 className="text-2xl font-bold text-violet-400">NOVICE WELDER</h2>
            <span className="ml-auto text-3xl font-bold text-violet-400">
              {MOCK_NOVICE_SCORE_VALUE}/100
            </span>
          </div>

          <ErrorBoundary>
            <div className="h-64">
              <TorchWithHeatmap3D
                angle={noviceAngleDeg}
                temp={noviceTemp}
                label="Novice Technique"
                frames={noviceThermalFrames}
                activeTimestamp={currentTimestamp}
                maxTemp={THERMAL_MAX_TEMP}
                minTemp={THERMAL_MIN_TEMP}
                colorSensitivity={THERMAL_COLOR_SENSITIVITY}
              />
            </div>
          </ErrorBoundary>

          {/* 2D HeatMap fallback when no thermal data (see expert column). */}
          {noviceThermalFrames.length === 0 && (
            <ErrorBoundary>
              <HeatMap
                sessionId="demo_novice"
                data={noviceHeatmap}
                activeTimestamp={currentTimestamp}
                label="Temperature Profile"
              />
            </ErrorBoundary>
          )}

          <ErrorBoundary>
            <TorchAngleGraph
              sessionId="demo_novice"
              data={noviceAngle}
              activeTimestamp={currentTimestamp}
            />
          </ErrorBoundary>

          <div className="bg-violet-900/20 border border-violet-400/50 rounded-lg p-4 space-y-2">
            <p className="text-violet-400 flex items-center gap-2">
              <span aria-hidden>✗</span>
              <span>Temperature spike at 2.3s (+65°C)</span>
            </p>
            <p className="text-violet-400 flex items-center gap-2">
              <span aria-hidden>✗</span>
              <span>Torch angle drift (45° → 62°)</span>
            </p>
            <p className="text-violet-400 flex items-center gap-2">
              <span aria-hidden>✗</span>
              <span>Erratic heat dissipation (10-120°C/s)</span>
            </p>
          </div>
        </div>
      </div>

      {/* Playback controls — fixed at bottom */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-blue-950/90 backdrop-blur border-2 border-blue-400 rounded-lg p-4 flex items-center gap-4">
        <button
          type="button"
          onClick={() => setPlaying(!playing)}
          className="px-8 py-3 bg-blue-400 text-black font-bold rounded hover:bg-blue-300 transition"
          aria-label={playing ? 'Pause demo' : 'Play demo'}
        >
          {playing ? '⏸ PAUSE' : '▶ PLAY'} DEMO
        </button>

        <div className="flex flex-col">
          <span className="text-blue-400 text-sm">Time</span>
          <span className="text-white font-mono">
            {(currentTimestamp / 1000).toFixed(1)}s / 15.0s
          </span>
        </div>

        <input
          type="range"
          min={0}
          max={DURATION_MS}
          step={FRAME_INTERVAL_MS}
          value={currentTimestamp}
          onChange={(e) => {
            const raw = e.target.value;
            const val = raw === '' ? currentTimestamp : Number(raw);
            setCurrentTimestamp(
              Number.isFinite(val)
                ? Math.max(0, Math.min(DURATION_MS, val))
                : currentTimestamp
            );
            setPlaying(false);
          }}
          className="w-48 md:w-64 min-w-32 max-w-full focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2 focus:ring-offset-neutral-950"
          aria-label="Scrub playback position"
          aria-valuetext={`${(currentTimestamp / 1000).toFixed(1)} seconds`}
        />
      </div>

      <div
        className="fixed bottom-2 right-4 text-blue-400/60 text-sm font-mono"
        role="status"
      >
        DEMO MODE — No backend required
      </div>
    </div>
  );
}
