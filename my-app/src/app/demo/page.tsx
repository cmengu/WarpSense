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

import { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { generateExpertSession, generateNoviceSession } from '@/lib/demo-data';
import { extractHeatmapData } from '@/utils/heatmapData';
import { extractAngleData } from '@/utils/angleData';
import {
  getFrameAtTimestamp,
  extractCenterTemperatureWithCarryForward,
} from '@/utils/frameUtils';
import { logError } from '@/lib/logger';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import HeatMap from '@/components/welding/HeatMap';
import TorchAngleGraph from '@/components/welding/TorchAngleGraph';

// Dynamic import for WebGL/3D — avoids SSR issues with three.js (same as replay page)
const TorchViz3D = dynamic(
  () => import('@/components/welding/TorchViz3D').then((m) => m.default),
  { ssr: false }
);

const DURATION_MS = 15000;
const FRAME_INTERVAL_MS = 10;

export default function DemoPage() {
  const [playing, setPlaying] = useState(false);
  const [currentTimestamp, setCurrentTimestamp] = useState(0);

  // Sessions generated once on mount (lazy init to avoid recompute)
  const [expertSession] = useState(() => {
    try {
      return generateExpertSession();
    } catch (err) {
      logError('DemoPage', err, { context: 'session-generation', session: 'expert' });
      throw err;
    }
  });
  const [noviceSession] = useState(() => {
    try {
      return generateNoviceSession();
    } catch (err) {
      logError('DemoPage', err, { context: 'session-generation', session: 'novice' });
      throw err;
    }
  });

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

  // Playback loop: advance every FRAME_INTERVAL_MS. At end: stop and reset to 0.
  // Per plan Critical Decision 5: no auto-loop; user clicks Play to restart.
  useEffect(() => {
    if (!playing) return;

    const id = setInterval(() => {
      setCurrentTimestamp((prev) => {
        const next = prev + FRAME_INTERVAL_MS;
        if (next >= DURATION_MS) {
          setPlaying(false);
          return 0;
        }
        return next;
      });
    }, FRAME_INTERVAL_MS);

    return () => clearInterval(id);
  }, [playing]);

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
      {/* Header */}
      <div className="border-b-2 border-cyan-400 bg-neutral-900 p-6">
        <h1 className="text-4xl font-bold text-cyan-400 uppercase tracking-wider">
          Shipyard Welding — Live Quality Analysis
        </h1>
        <p className="text-gray-400 mt-2">
          Real-time weld quality feedback system for industrial training
        </p>
      </div>

      {/* Main content: side-by-side expert vs novice */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 p-8 pb-32">
        {/* Expert column */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <div
              className="w-4 h-4 bg-green-400 rounded-full animate-pulse"
              aria-hidden
            />
            <h2 className="text-2xl font-bold text-green-400">
              EXPERT WELDER
            </h2>
            <span className="ml-auto text-3xl font-bold text-green-400">
              94/100
            </span>
          </div>

          <ErrorBoundary>
            <div className="h-64">
              <TorchViz3D
                angle={expertAngleDeg}
                temp={expertTemp}
                label="Expert Technique"
              />
            </div>
          </ErrorBoundary>

          <ErrorBoundary>
            <HeatMap
              sessionId="demo_expert"
              data={expertHeatmap}
              activeTimestamp={currentTimestamp}
              label="Temperature Profile"
            />
          </ErrorBoundary>

          <ErrorBoundary>
            <TorchAngleGraph
              sessionId="demo_expert"
              data={expertAngle}
              activeTimestamp={currentTimestamp}
            />
          </ErrorBoundary>

          <div className="bg-green-900/20 border border-green-400/50 rounded-lg p-4 space-y-2">
            <p className="text-green-400 flex items-center gap-2">
              <span aria-hidden>✓</span>
              <span>Consistent temperature (±5°C)</span>
            </p>
            <p className="text-green-400 flex items-center gap-2">
              <span aria-hidden>✓</span>
              <span>Steady torch angle (45° ±0.5°)</span>
            </p>
            <p className="text-green-400 flex items-center gap-2">
              <span aria-hidden>✓</span>
              <span>Smooth heat dissipation (30°C/s)</span>
            </p>
          </div>
        </div>

        {/* Novice column */}
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <div
              className="w-4 h-4 bg-red-400 rounded-full animate-pulse"
              aria-hidden
            />
            <h2 className="text-2xl font-bold text-red-400">NOVICE WELDER</h2>
            <span className="ml-auto text-3xl font-bold text-red-400">
              42/100
            </span>
          </div>

          <ErrorBoundary>
            <div className="h-64">
              <TorchViz3D
                angle={noviceAngleDeg}
                temp={noviceTemp}
                label="Novice Technique"
              />
            </div>
          </ErrorBoundary>

          <ErrorBoundary>
            <HeatMap
              sessionId="demo_novice"
              data={noviceHeatmap}
              activeTimestamp={currentTimestamp}
              label="Temperature Profile"
            />
          </ErrorBoundary>

          <ErrorBoundary>
            <TorchAngleGraph
              sessionId="demo_novice"
              data={noviceAngle}
              activeTimestamp={currentTimestamp}
            />
          </ErrorBoundary>

          <div className="bg-red-900/20 border border-red-400/50 rounded-lg p-4 space-y-2">
            <p className="text-red-400 flex items-center gap-2">
              <span aria-hidden>✗</span>
              <span>Temperature spike at 2.3s (+65°C)</span>
            </p>
            <p className="text-red-400 flex items-center gap-2">
              <span aria-hidden>✗</span>
              <span>Torch angle drift (45° → 62°)</span>
            </p>
            <p className="text-red-400 flex items-center gap-2">
              <span aria-hidden>✗</span>
              <span>Erratic heat dissipation (10-120°C/s)</span>
            </p>
          </div>
        </div>
      </div>

      {/* Playback controls — fixed at bottom */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-cyan-950/90 backdrop-blur border-2 border-cyan-400 rounded-lg p-4 flex items-center gap-4">
        <button
          type="button"
          onClick={() => setPlaying(!playing)}
          className="px-8 py-3 bg-cyan-400 text-black font-bold rounded hover:bg-cyan-300 transition"
          aria-label={playing ? 'Pause demo' : 'Play demo'}
        >
          {playing ? '⏸ PAUSE' : '▶ PLAY'} DEMO
        </button>

        <div className="flex flex-col">
          <span className="text-cyan-400 text-sm">Time</span>
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
            const val = Number(e.target.value);
            setCurrentTimestamp(
              Number.isFinite(val)
                ? Math.max(0, Math.min(DURATION_MS, val))
                : currentTimestamp
            );
            setPlaying(false);
          }}
          className="w-64"
          aria-label="Scrub playback position"
        />
      </div>

      <div
        className="fixed bottom-2 right-4 text-cyan-400/60 text-sm font-mono"
        role="status"
      >
        DEMO MODE — No backend required
      </div>
    </div>
  );
}
