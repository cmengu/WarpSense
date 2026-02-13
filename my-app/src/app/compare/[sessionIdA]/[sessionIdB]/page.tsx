'use client';

import { Suspense, use, useEffect, useState } from 'react';
import Link from 'next/link';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import HeatMap from '@/components/welding/HeatMap';
import { fetchSession } from '@/lib/api';
import { FRAME_INTERVAL_MS } from '@/constants/validation';
import { extractHeatmapData, tempToColorRange } from '@/utils/heatmapData';
import { extractDeltaHeatmapData, deltaTempToColor } from '@/utils/deltaHeatmapData';
import { useSessionComparison } from '@/hooks/useSessionComparison';
import { useFrameData } from '@/hooks/useFrameData';
import type { Session } from '@/types/session';

type CompareParams =
  | { sessionIdA: string; sessionIdB: string }
  | Promise<{ sessionIdA: string; sessionIdB: string }>;

function isPromise(
  p: CompareParams
): p is Promise<{ sessionIdA: string; sessionIdB: string }> {
  return p != null && typeof (p as Promise<unknown>).then === 'function';
}

/**
 * Compare Page
 * Side-by-side comparison of two welding sessions with delta heatmap.
 * Fetches both sessions in parallel, computes deltas via useSessionComparison,
 * single timeline slider drives all three columns.
 */
export default function ComparePage({ params }: { params: CompareParams }) {
  if (isPromise(params)) {
    return (
      <Suspense
        fallback={
          <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
            <div className="text-sm text-zinc-500">Loading...</div>
          </div>
        }
      >
        <ComparePageWithAsyncParams params={params} />
      </Suspense>
    );
  }
  return (
    <ComparePageInner
      sessionIdA={params.sessionIdA}
      sessionIdB={params.sessionIdB}
    />
  );
}

function ComparePageWithAsyncParams({
  params,
}: {
  params: Promise<{ sessionIdA: string; sessionIdB: string }>;
}) {
  const { sessionIdA, sessionIdB } = use(params);
  return (
    <ComparePageInner sessionIdA={sessionIdA} sessionIdB={sessionIdB} />
  );
}

function ComparePageInner({
  sessionIdA,
  sessionIdB,
}: {
  sessionIdA: string;
  sessionIdB: string;
}) {
  const [sessionA, setSessionA] = useState<Session | null>(null);
  const [sessionB, setSessionB] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [currentTimestamp, setCurrentTimestamp] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  const comparison = useSessionComparison(sessionA, sessionB);
  const frameDataA = useFrameData(sessionA?.frames ?? [], null, null);
  const frameDataB = useFrameData(sessionB?.frames ?? [], null, null);

  const heatmapDataA =
    sessionA?.frames && frameDataA.thermal_frames.length > 0
      ? extractHeatmapData(frameDataA.thermal_frames)
      : null;
  const heatmapDataB =
    sessionB?.frames && frameDataB.thermal_frames.length > 0
      ? extractHeatmapData(frameDataB.thermal_frames)
      : null;
  const deltaHeatmapData =
    comparison && comparison.deltas.length > 0
      ? extractDeltaHeatmapData(comparison.deltas)
      : null;

  const compareColorFn = (() => {
    if (!heatmapDataA?.points.length || !heatmapDataB?.points.length) return undefined;
    let minT = Infinity;
    let maxT = -Infinity;
    for (const p of heatmapDataA.points) {
      if (Number.isFinite(p.temp_celsius)) {
        minT = Math.min(minT, p.temp_celsius);
        maxT = Math.max(maxT, p.temp_celsius);
      }
    }
    for (const p of heatmapDataB.points) {
      if (Number.isFinite(p.temp_celsius)) {
        minT = Math.min(minT, p.temp_celsius);
        maxT = Math.max(maxT, p.temp_celsius);
      }
    }
    if (minT > maxT) return undefined;
    return tempToColorRange(minT, maxT);
  })();

  const firstTimestamp =
    comparison && comparison.deltas.length > 0
      ? comparison.deltas[0].timestamp_ms
      : null;
  const lastTimestamp =
    comparison && comparison.deltas.length > 0
      ? comparison.deltas[comparison.deltas.length - 1].timestamp_ms
      : null;

  useEffect(() => {
    if (firstTimestamp != null && lastTimestamp != null) {
      setCurrentTimestamp((prev) => {
        if (prev == null || prev < firstTimestamp || prev > lastTimestamp) {
          return firstTimestamp;
        }
        return prev;
      });
    } else {
      setCurrentTimestamp(null);
    }
  }, [firstTimestamp, lastTimestamp]);

  useEffect(() => {
    if (!isPlaying || lastTimestamp == null || firstTimestamp == null) return;
    const intervalMs = FRAME_INTERVAL_MS / playbackSpeed;
    const id = setInterval(() => {
      setCurrentTimestamp((prev) => {
        const base = prev ?? firstTimestamp;
        const next = base + FRAME_INTERVAL_MS;
        if (next >= lastTimestamp) {
          setIsPlaying(false);
          return lastTimestamp;
        }
        return next;
      });
    }, intervalMs);
    return () => clearInterval(id);
  }, [isPlaying, playbackSpeed, firstTimestamp, lastTimestamp]);

  useEffect(() => {
    if (
      firstTimestamp == null ||
      lastTimestamp == null ||
      lastTimestamp <= firstTimestamp
    )
      return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLElement &&
        /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)
      )
        return;
      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying((p) => !p);
        return;
      }
      if (e.code === 'ArrowLeft') {
        e.preventDefault();
        setIsPlaying(false);
        setCurrentTimestamp((prev) => {
          const base = prev ?? firstTimestamp;
          return Math.max(firstTimestamp, base - FRAME_INTERVAL_MS);
        });
        return;
      }
      if (e.code === 'ArrowRight') {
        e.preventDefault();
        setIsPlaying(false);
        setCurrentTimestamp((prev) => {
          const base = prev ?? firstTimestamp;
          return Math.min(lastTimestamp, base + FRAME_INTERVAL_MS);
        });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [firstTimestamp, lastTimestamp]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    const load = async () => {
      const [dataA, dataB] = await Promise.all([
        fetchSession(sessionIdA, { limit: 2000 }),
        fetchSession(sessionIdB, { limit: 2000 }),
      ]);
      if (!cancelled) {
        setSessionA(dataA);
        setSessionB(dataB);
      }
    };
    load()
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setSessionA(null);
          setSessionB(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionIdA, sessionIdB]);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg text-zinc-600 dark:text-zinc-400 mb-2">
            Loading sessions...
          </div>
          <div className="text-sm text-zinc-500 dark:text-zinc-500">
            Fetching {sessionIdA} and {sessionIdB}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white dark:bg-zinc-900 rounded-lg border border-red-200 dark:border-red-800 p-6">
          <h2 className="text-lg font-semibold text-red-800 dark:text-red-400 mb-2">
            Failed to load comparison
          </h2>
          <p className="text-sm text-red-600 dark:text-red-500 mb-4">
            {error}
          </p>
          <Link
            href="/"
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  const noOverlap =
    !comparison ||
    comparison.deltas.length === 0 ||
    (comparison.shared_count === 0 && comparison.total_a > 0 && comparison.total_b > 0);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-6">
      <div className="max-w-full mx-auto">
        <div className="flex items-center gap-4 mb-4">
          <Link
            href="/"
            className="text-sm text-zinc-500 dark:text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-300"
          >
            Dashboard
          </Link>
          <span className="text-zinc-400">/</span>
          <Link
            href={`/replay/${sessionIdA}`}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Replay {sessionIdA}
          </Link>
          <span className="text-zinc-400">vs</span>
          <Link
            href={`/replay/${sessionIdB}`}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Replay {sessionIdB}
          </Link>
        </div>

        <h1 className="text-3xl font-semibold mb-2 text-black dark:text-zinc-50">
          Compare: {sessionIdA} vs {sessionIdB}
        </h1>
        {comparison && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-6">
            {comparison.shared_count} overlapping frames • A: {comparison.total_a} • B: {comparison.total_b}
          </p>
        )}

        {noOverlap && (
          <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-amber-800 dark:text-amber-200 text-sm">
            No overlapping frames. Sessions must share timestamps to show deltas. Check that both use the same duration and frame interval (e.g. mock: 15s, 10ms).
          </div>
        )}

        {firstTimestamp != null &&
          lastTimestamp != null &&
          lastTimestamp > firstTimestamp && (
            <div className="mb-4 space-y-2">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setIsPlaying((p) => !p)}
                  className="px-4 py-2 rounded-md bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
                  aria-label={isPlaying ? 'Pause playback' : 'Play playback'}
                >
                  {isPlaying ? 'Pause' : 'Play'}
                </button>
                <label
                  htmlFor="compare-slider"
                  className="text-sm font-medium text-zinc-700 dark:text-zinc-300"
                >
                  Timeline
                </label>
              </div>
              <input
                id="compare-slider"
                type="range"
                min={firstTimestamp}
                max={lastTimestamp}
                step={10}
                value={currentTimestamp ?? firstTimestamp}
                onChange={(e) => {
                  setIsPlaying(false);
                  setCurrentTimestamp(Number(e.target.value));
                }}
                className="w-full max-w-2xl h-2 bg-zinc-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                {(currentTimestamp ?? firstTimestamp) / 1000} s
              </p>
            </div>
          )}

        {heatmapDataA?.point_count && heatmapDataB?.point_count && (
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-2">
            Session A and B use a shared temperature scale (cold→blue, hot→red) so differences are visible. Delta column: red = A hotter, blue = B hotter.
          </p>
        )}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <ErrorBoundary>
            <HeatMap
              sessionId={sessionIdA}
              data={heatmapDataA}
              activeTimestamp={currentTimestamp}
              colorFn={compareColorFn}
              label="Session A"
            />
          </ErrorBoundary>
          <ErrorBoundary>
            <HeatMap
              sessionId={`${sessionIdA}-${sessionIdB}-delta`}
              data={deltaHeatmapData}
              activeTimestamp={currentTimestamp}
              colorFn={deltaTempToColor}
              label="Delta (A − B)"
              valueLabel="delta"
            />
          </ErrorBoundary>
          <ErrorBoundary>
            <HeatMap
              sessionId={sessionIdB}
              data={heatmapDataB}
              activeTimestamp={currentTimestamp}
              colorFn={compareColorFn}
              label="Session B"
            />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
