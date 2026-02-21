'use client';

import { Suspense, use, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import HeatMap from '@/components/welding/HeatMap';
import TorchAngleGraph from '@/components/welding/TorchAngleGraph';
import ScorePanel from '@/components/welding/ScorePanel';
import FeedbackPanel from '@/components/welding/FeedbackPanel';
import TimelineMarkers from '@/components/welding/TimelineMarkers';
import AnnotationMarker from '@/components/welding/AnnotationMarker';
import AddAnnotationPanel from '@/components/welding/AddAnnotationPanel';
import { generateMicroFeedback } from '@/lib/micro-feedback';
import type { WeldTypeThresholds } from '@/types/thresholds';
import {
  fetchSession,
  fetchScore,
  fetchWarpRisk,
  fetchAnnotations,
  type SessionScore,
} from '@/lib/api';
import type { WarpRiskResponse } from '@/types/prediction';
import { alertOnReplayFailure, logWarn } from '@/lib/logger';
import { FRAME_INTERVAL_MS } from '@/constants/validation';
import {
  THERMAL_MAX_TEMP,
  THERMAL_MIN_TEMP,
  THERMAL_COLOR_SENSITIVITY,
} from '@/constants/thermal';
import { extractHeatmapData } from '@/utils/heatmapData';
import { extractAngleData } from '@/utils/angleData';
import { useSessionMetadata } from '@/hooks/useSessionMetadata';
import { useFrameData } from '@/hooks/useFrameData';
import { getFrameAtTimestamp, extractCenterTemperatureWithCarryForward } from '@/utils/frameUtils';
import type { Session } from '@/types/session';
import type { Annotation } from '@/types/annotation';

// Dynamic import for TorchWithHeatmap3D — unified torch + thermal metal (replaces TorchViz3D + HeatmapPlate3D)
// Per WEBGL_CONTEXT_LOSS.md: max 2 instances (see constants/webgl.ts)
const WarpRiskGauge = dynamic(
  () =>
    import('@/components/welding/WarpRiskGauge').then((m) => m.WarpRiskGauge),
  { ssr: false }
);

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

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Safe getter for comparison session ID — avoids process undefined in edge runtimes.
 * Returns undefined when env is empty or unset; falls back to default for demo.
 *
 * @see .cursor/plans/side-by-side_3d_comparison_f15447b8.plan.md — Step 4
 */
function getComparisonSessionId(): string | undefined {
  try {
    const val =
      typeof process !== 'undefined'
        ? process.env?.NEXT_PUBLIC_DEMO_COMPARISON_SESSION_ID
        : undefined;
    if (val === undefined) return 'sess_novice_001';
    return val === '' ? undefined : val;
  } catch {
    return 'sess_novice_001';
  }
}

const COMPARISON_SESSION_ID = getComparisonSessionId();

type ReplayParams = { sessionId: string } | Promise<{ sessionId: string }>;

function isPromise(
  p: ReplayParams
): p is Promise<{ sessionId: string }> {
  return p != null && typeof (p as Promise<unknown>).then === "function";
}

/**
 * Replay Page
 * Displays replay visualization for a specific welding session.
 * Fetches session from API, extracts heatmap/angle data via hooks and utils.
 *
 * @param params - Route parameters (Promise in Next.js 15+, plain object in tests)
 */
export default function ReplayPage({ params }: { params: ReplayParams }) {
  if (isPromise(params)) {
    return (
      <Suspense
        fallback={
          <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
            <div className="text-sm text-zinc-500">Loading...</div>
          </div>
        }
      >
        <ReplayPageWithAsyncParams params={params} />
      </Suspense>
    );
  }
  return <ReplayPageInner sessionId={params.sessionId} />;
}

function ReplayPageWithAsyncParams({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = use(params);
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
          <div className="text-sm text-zinc-500">Loading...</div>
        </div>
      }
    >
      <ReplayPageInner sessionId={sessionId} />
    </Suspense>
  );
}

function ReplayPageInner({ sessionId }: { sessionId: string }) {
  const searchParams = useSearchParams();
  const [sessionData, setSessionData] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Annotations (Batch 2 Agent 2)
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [annotateMode, setAnnotateMode] = useState(false);
  const [selectedTimestampForAnnotation, setSelectedTimestampForAnnotation] =
    useState<number | null>(null);
  const [annotationRefreshFailed, setAnnotationRefreshFailed] =
    useState<string | null>(null);
  const refreshFailedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );

  // Comparison session state (for side-by-side 3D visualization)
  const [comparisonSession, setComparisonSession] = useState<Session | null>(null);
  const [showComparison, setShowComparison] = useState(true); // Default: show comparison

  // Score state for both sessions (for 3D block score comparison)
  const [primaryScore, setPrimaryScore] = useState<SessionScore | null>(null);
  const [comparisonScore, setComparisonScore] = useState<SessionScore | null>(null);
  const [scoreFetchError, setScoreFetchError] = useState<string | null>(null);

  const [currentTimestamp, setCurrentTimestamp] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  /** Brief "Copied!" feedback for Copy Session ID button. Resets after 2s. */
  const [copyFeedback, setCopyFeedback] = useState(false);
  const copyFeedbackTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [warpRisk, setWarpRisk] = useState<WarpRiskResponse | null>(null);

  // Clear copy-feedback timer on unmount to avoid state update on unmounted component.
  useEffect(() => {
    return () => {
      if (copyFeedbackTimeoutRef.current != null) {
        clearTimeout(copyFeedbackTimeoutRef.current);
        copyFeedbackTimeoutRef.current = null;
      }
    };
  }, []);

  // Clear annotation refresh-failed timeout on unmount.
  useEffect(() => {
    return () => {
      if (refreshFailedTimeoutRef.current != null) {
        clearTimeout(refreshFailedTimeoutRef.current);
        refreshFailedTimeoutRef.current = null;
      }
    };
  }, []);

  // ?t= deep-link: set currentTimestamp from URL when session is loaded.
  const tParam = searchParams.get('t');
  const initialTimestampMs =
    tParam != null ? parseInt(tParam, 10) : undefined;

  const metadata = useSessionMetadata(sessionData);
  const frameData = useFrameData(
    sessionData?.frames ?? [],
    null,
    null
  );

  // Frame data for comparison session (used by 3D visualization in Step 5)
  const comparisonFrameData = useFrameData(
    comparisonSession?.frames ?? [],
    null,
    null
  );

  const heatmapData = sessionData?.frames
    ? extractHeatmapData(frameData.thermal_frames)
    : null;
  const angleData = sessionData?.frames
    ? extractAngleData(sessionData.frames)
    : null;

  const thresholdsForMicroFeedback = useMemo((): WeldTypeThresholds | undefined => {
    const spec = primaryScore?.active_threshold_spec;
    if (!spec) return undefined;
    return {
      weld_type: spec.weld_type,
      angle_target_degrees: spec.angle_target,
      angle_warning_margin: spec.angle_warning,
      angle_critical_margin: spec.angle_critical,
      thermal_symmetry_warning_celsius: spec.thermal_symmetry_warning_celsius ?? 60,
      thermal_symmetry_critical_celsius: spec.thermal_symmetry_critical_celsius ?? 80,
      amps_stability_warning: spec.amps_stability_warning ?? 5,
      volts_stability_warning: spec.volts_stability_warning ?? 1,
      heat_diss_consistency: spec.heat_diss_consistency ?? 40,
    };
  }, [primaryScore?.active_threshold_spec]);

  const microFeedback = useMemo(() => {
    if (!sessionData?.frames) return [];
    if (!primaryScore && !scoreFetchError) return [];
    return generateMicroFeedback(
      sessionData.frames,
      thresholdsForMicroFeedback
    );
  }, [
    sessionData?.frames,
    primaryScore,
    scoreFetchError,
    thresholdsForMicroFeedback,
  ]);

  const handleFrameSelect = (timestamp_ms: number) => {
    setIsPlaying(false);
    setCurrentTimestamp(timestamp_ms);
  };

  const firstTimestamp = frameData.first_timestamp_ms;
  const lastTimestamp = frameData.last_timestamp_ms;

  // Sync currentTimestamp with valid range; prefer ?t= deep-link when in range.
  useEffect(() => {
    if (firstTimestamp != null && lastTimestamp != null) {
      setCurrentTimestamp((prev) => {
        const tFromUrl =
          initialTimestampMs != null &&
          Number.isFinite(initialTimestampMs) &&
          initialTimestampMs >= firstTimestamp &&
          initialTimestampMs <= lastTimestamp;
        const target = tFromUrl
          ? initialTimestampMs
          : prev != null && prev >= firstTimestamp && prev <= lastTimestamp
            ? prev
            : firstTimestamp;
        return target;
      });
    } else {
      setCurrentTimestamp(null);
    }
  }, [firstTimestamp, lastTimestamp, initialTimestampMs]);

  // Playback loop: advance currentTimestamp every FRAME_INTERVAL_MS at 1× speed.
  // Uses setInterval (not RAF) for 100 updates/sec to match 100Hz frame rate.
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

  // Keyboard shortcuts: Space = toggle play; ArrowLeft/Right = step ±FRAME_INTERVAL_MS
  useEffect(() => {
    if (firstTimestamp == null || lastTimestamp == null || lastTimestamp <= firstTimestamp) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;

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

  // Fetch primary session
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const load = async () => {
      try {
        // CRITICAL: Pass limit to get full session (expert has ~1500 frames; default 1000 truncates)
        const data = await fetchSession(sessionId, { limit: 2000 });
        if (!cancelled) setSessionData(data);
      } catch (err) {
        if (!cancelled) {
          alertOnReplayFailure(sessionId, err, { source: "primary_session" });
          setError(err instanceof Error ? err.message : String(err));
          setSessionData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  // Fetch comparison session (for side-by-side 3D visualization)
  // Handles 404 gracefully: comparison is optional; page still works if missing.
  // Explicit: COMPARISON_SESSION_ID is undefined when env is empty (disables comparison).
  useEffect(() => {
    if (!showComparison || COMPARISON_SESSION_ID === '' || COMPARISON_SESSION_ID == null) {
      setComparisonSession(null);
      return;
    }

    let cancelled = false;

    const loadComparison = async () => {
      const sid = COMPARISON_SESSION_ID;
      if (sid === '' || sid == null) return;
      try {
        const data = await fetchSession(sid, { limit: 2000 });
        if (!cancelled) setComparisonSession(data);
      } catch (err) {
        // 404 or other error: comparison is optional, don't break the page
        if (!cancelled) {
          logWarn(
            "ReplayPage",
            `Comparison session ${COMPARISON_SESSION_ID} not found or failed to load`,
            { error: err instanceof Error ? err.message : String(err) }
          );
          setComparisonSession(null);
        }
      }
    };

    loadComparison();

    return () => {
      cancelled = true;
    };
  }, [showComparison, COMPARISON_SESSION_ID]);

  // Fetch scores for both sessions (for 3D block score comparison)
  useEffect(() => {
    let cancelled = false;

    // Fetch primary session score
    fetchScore(sessionId)
      .then((data) => {
        if (!cancelled) {
          setPrimaryScore(data);
          setScoreFetchError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          logWarn("ReplayPage", `Failed to fetch score for ${sessionId}`, {
            error: err instanceof Error ? err.message : String(err),
          });
          setPrimaryScore(null);
          setScoreFetchError(
            err instanceof Error ? err.message : 'Score unavailable'
          );
        }
      });

    // Fetch comparison session score (if comparison is enabled and loaded)
    if (
      showComparison &&
      COMPARISON_SESSION_ID !== '' &&
      COMPARISON_SESSION_ID != null &&
      comparisonSession
    ) {
      fetchScore(COMPARISON_SESSION_ID)
        .then((data) => {
          if (!cancelled) setComparisonScore(data);
        })
        .catch((err) => {
          if (!cancelled) {
            logWarn(
              "ReplayPage",
              `Failed to fetch score for ${COMPARISON_SESSION_ID}`,
              { error: err instanceof Error ? err.message : String(err) }
            );
            setComparisonScore(null);
          }
        });
    } else {
      setComparisonScore(null);
    }

    return () => {
      cancelled = true;
    };
  }, [sessionId, showComparison, comparisonSession, COMPARISON_SESSION_ID]);

  const FETCH_TIMEOUT_MS = 10_000;
  useEffect(() => {
    let mounted = true;
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('fetchWarpRisk timeout')), FETCH_TIMEOUT_MS)
    );
    Promise.race([fetchWarpRisk(sessionId), timeoutPromise])
      .then((r) => {
        if (mounted) setWarpRisk(r);
      })
      .catch((err) => {
        if (mounted) {
          logWarn('ReplayPage', 'Failed to fetch warp risk', {
            sessionId,
            error: err instanceof Error ? err.message : String(err),
          });
          setWarpRisk({
            session_id: sessionId,
            probability: 0,
            risk_level: 'ok',
            model_available: false,
            window_frames_used: 0,
          });
        }
      });
    return () => {
      mounted = false;
    };
  }, [sessionId]);

  // Fetch annotations for this session (Batch 2 Agent 2).
  const handleAnnotationSaved = useCallback(() => {
    setAnnotationRefreshFailed(null);
    fetchAnnotations(sessionId)
      .then((data) => setAnnotations(data))
      .catch((err) => {
        logWarn('ReplayPage', 'Failed to refresh annotations after save', {
          sessionId,
          error: err instanceof Error ? err.message : String(err),
        });
        setAnnotationRefreshFailed('Annotation saved but list failed to refresh.');
        if (refreshFailedTimeoutRef.current != null) {
          clearTimeout(refreshFailedTimeoutRef.current);
        }
        refreshFailedTimeoutRef.current = setTimeout(() => {
          setAnnotationRefreshFailed(null);
          refreshFailedTimeoutRef.current = null;
        }, 6000);
      });
  }, [sessionId]);

  useEffect(() => {
    let mounted = true;
    fetchAnnotations(sessionId)
      .then((data) => {
        if (mounted) setAnnotations(data);
      })
      .catch((err) => {
        if (mounted) {
          logWarn('ReplayPage', 'Failed to fetch annotations', {
            sessionId,
            error: err instanceof Error ? err.message : String(err),
          });
        }
      });
    return () => {
      mounted = false;
    };
  }, [sessionId]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg text-zinc-600 dark:text-zinc-400 mb-2">
            Loading session...
          </div>
          <div className="text-sm text-zinc-500 dark:text-zinc-500">
            Fetching session data
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    const isNetworkError = /failed to fetch|network error|load failed/i.test(error);
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white dark:bg-zinc-900 rounded-lg border border-violet-200 dark:border-violet-800 p-6">
          <h2 className="text-lg font-semibold text-violet-800 dark:text-violet-400 mb-2">
            Failed to load session
          </h2>
          <p className="text-sm text-violet-600 dark:text-violet-500 mb-4">
            {error}
          </p>
          {isNetworkError && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Ensure the backend is running (e.g. <code className="bg-zinc-100 dark:bg-zinc-800 px-1 rounded">./start-all.sh</code>) and mock data is seeded.
            </p>
          )}
        </div>
      </div>
    );
  }

  // Success state - render replay components
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-semibold mb-6 text-black dark:text-zinc-50">
          Session Replay: {sessionId}
        </h1>

        {metadata && (
          <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-4 flex flex-wrap items-center gap-3">
            <span>
              {metadata.weld_type_label} • {metadata.duration_display} •{' '}
              {metadata.frame_count} frames
            </span>
            <Link
              href={`/compare?sessionA=${encodeURIComponent(sessionId)}`}
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Compare with another session
            </Link>
            <button
              type="button"
              onClick={() => setShowComparison((prev) => !prev)}
              className="px-3 py-1 text-xs rounded-md bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-700"
            >
              {showComparison ? 'Hide' : 'Show'} Comparison
            </button>
            <button
              type="button"
              onClick={async () => {
                try {
                  if (typeof navigator?.clipboard?.writeText === 'function') {
                    await navigator.clipboard.writeText(sessionId);
                    if (copyFeedbackTimeoutRef.current != null) {
                      clearTimeout(copyFeedbackTimeoutRef.current);
                    }
                    setCopyFeedback(true);
                    copyFeedbackTimeoutRef.current = setTimeout(
                      () => {
                        setCopyFeedback(false);
                        copyFeedbackTimeoutRef.current = null;
                      },
                      2000
                    );
                  }
                } catch (err) {
                  logWarn('ReplayPage', 'Clipboard copy failed', {
                    sessionId,
                    error: err instanceof Error ? err.message : String(err),
                  });
                }
              }}
              className="px-3 py-1 text-xs rounded-md bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-700"
              aria-label="Copy session ID to clipboard"
            >
              {copyFeedback ? 'Copied!' : 'Copy Session ID'}
            </button>
            <button
              type="button"
              onClick={() => setAnnotateMode((prev) => !prev)}
              className={`px-3 py-1 text-xs rounded-md ${
                annotateMode
                  ? 'bg-cyan-500 text-black'
                  : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-700'
              }`}
            >
              {annotateMode ? 'Annotate Mode ON' : 'Annotate Mode'}
            </button>
            <Link
              href="/defects"
              className="text-blue-600 dark:text-blue-400 hover:underline text-xs"
            >
              Defect Library
            </Link>
          </div>
        )}

        {firstTimestamp != null && lastTimestamp != null && lastTimestamp > firstTimestamp && (
          <div className="mb-4 space-y-2 relative">
            <div className="flex items-center gap-3 flex-wrap">
              <button
                type="button"
                onClick={() => setIsPlaying((p) => !p)}
                className="px-4 py-2 rounded-md bg-blue-500 text-white text-sm font-medium hover:bg-blue-600 disabled:opacity-50"
                aria-label={isPlaying ? 'Pause playback' : 'Play playback'}
              >
                {isPlaying ? 'Pause' : 'Play'}
              </button>
              <label htmlFor="replay-slider" className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                Timeline
              </label>
              {annotateMode && (
                <button
                  type="button"
                  onClick={() =>
                    setSelectedTimestampForAnnotation(
                      currentTimestamp ?? firstTimestamp ?? 0
                    )
                  }
                  className="px-3 py-1 text-xs rounded-md bg-cyan-600 text-white hover:bg-cyan-500"
                >
                  Add annotation at current position
                </button>
            )}
            </div>
            {annotationRefreshFailed && (
              <p className="text-amber-600 dark:text-amber-400 text-xs">
                {annotationRefreshFailed}
              </p>
            )}
            <div className="relative max-w-2xl">
              {sessionData?.frames && (
                <TimelineMarkers
                  items={microFeedback}
                  frames={sessionData.frames}
                  firstTimestamp={firstTimestamp}
                  lastTimestamp={lastTimestamp}
                  onFrameSelect={handleFrameSelect}
                />
              )}
              {annotations.length > 0 && (
                <AnnotationMarker
                  annotations={annotations}
                  firstTimestamp={firstTimestamp}
                  lastTimestamp={lastTimestamp}
                  onAnnotationClick={handleFrameSelect}
                />
              )}
              <input
                id="replay-slider"
                type="range"
                min={firstTimestamp}
                max={lastTimestamp}
                step={10}
                value={currentTimestamp ?? firstTimestamp}
                onChange={(e) => {
                  setIsPlaying(false);
                  const raw = e.target.value;
                  const val = raw === '' ? currentTimestamp ?? firstTimestamp ?? 0 : Number(raw);
                  setCurrentTimestamp(
                    Number.isFinite(val)
                      ? Math.max(
                          firstTimestamp ?? 0,
                          Math.min(lastTimestamp ?? 0, val)
                        )
                      : currentTimestamp ?? firstTimestamp ?? 0
                  );
                }}
                className="w-full h-2 bg-zinc-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-2"
              />
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {(currentTimestamp ?? firstTimestamp) / 1000} s
            </p>
            {annotateMode && selectedTimestampForAnnotation != null && (
              <div className="absolute left-0 top-0 mt-2 z-10">
                <AddAnnotationPanel
                  sessionId={sessionId}
                  selectedTimestampMs={selectedTimestampForAnnotation}
                  onAnnotationSaved={handleAnnotationSaved}
                  onClose={() => setSelectedTimestampForAnnotation(null)}
                />
              </div>
            )}
          </div>
        )}

        {/* 3D Torch Visualization Block — Side-by-side comparison (Expert | Novice) */}
        {currentTimestamp != null && sessionData?.frames && (
          <ErrorBoundary>
            <div className="mb-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Left: Current Session (Expert) */}
                <div>
                  {(() => {
                    const frame = getFrameAtTimestamp(sessionData.frames, currentTimestamp);
                    const angle = frame?.angle_degrees ?? 45;
                    const temp = extractCenterTemperatureWithCarryForward(
                      sessionData.frames,
                      currentTimestamp
                    );
                    return (
                      <>
                        <TorchWithHeatmap3D
                          angle={angle}
                          temp={temp}
                          label={`Current Session (${sessionId})`}
                          frames={frameData.thermal_frames}
                          activeTimestamp={currentTimestamp}
                          maxTemp={THERMAL_MAX_TEMP}
                          minTemp={THERMAL_MIN_TEMP}
                          colorSensitivity={THERMAL_COLOR_SENSITIVITY}
                        />
                        {/* Warp risk gauge */}
                        {warpRisk && (
                          <div className="mt-2">
                            <WarpRiskGauge
                              probability={warpRisk.probability}
                              riskLevel={warpRisk.risk_level}
                              modelAvailable={warpRisk.model_available}
                            />
                          </div>
                        )}
                        {/* Inline score display */}
                        {primaryScore ? (
                          <div className="mt-2 p-3 bg-white dark:bg-zinc-900 rounded border border-zinc-200 dark:border-zinc-800">
                            <div className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                              Score: {primaryScore.total} / 100
                            </div>
                            <div className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
                              {primaryScore.rules.filter((r) => r.passed).length} / 5 rules passed
                            </div>
                          </div>
                        ) : (
                          <div className="mt-2 p-3 bg-zinc-50 dark:bg-zinc-900/50 rounded border border-zinc-200 dark:border-zinc-800">
                            <div className="text-xs text-zinc-500 dark:text-zinc-400">
                              Loading score...
                            </div>
                          </div>
                        )}
                      </>
                    );
                  })()}
                </div>

                {/* Right: Comparison Session (Novice) */}
                {showComparison && comparisonSession?.frames ? (
                  <div>
                    {(() => {
                      const frame = getFrameAtTimestamp(
                        comparisonSession.frames,
                        currentTimestamp
                      );
                      const angle = frame?.angle_degrees ?? 45;
                      const temp = extractCenterTemperatureWithCarryForward(
                        comparisonSession.frames,
                        currentTimestamp
                      );
                      return (
                        <>
                          <TorchWithHeatmap3D
                            angle={angle}
                            temp={temp}
                            label={`Comparison (${COMPARISON_SESSION_ID ?? 'unknown'})`}
                            frames={comparisonFrameData.thermal_frames}
                            activeTimestamp={currentTimestamp}
                            maxTemp={THERMAL_MAX_TEMP}
                            minTemp={THERMAL_MIN_TEMP}
                            colorSensitivity={THERMAL_COLOR_SENSITIVITY}
                          />
                          {/* Inline score display */}
                          {comparisonScore ? (
                            <div className="mt-2 p-3 bg-white dark:bg-zinc-900 rounded border border-zinc-200 dark:border-zinc-800">
                              <div className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                                Score: {comparisonScore.total} / 100
                              </div>
                              <div className="text-xs text-zinc-600 dark:text-zinc-400 mt-1">
                                {comparisonScore.rules.filter((r) => r.passed).length} / 5 rules
                                passed
                              </div>
                            </div>
                          ) : (
                            <div className="mt-2 p-3 bg-zinc-50 dark:bg-zinc-900/50 rounded border border-zinc-200 dark:border-zinc-800">
                              <div className="text-xs text-zinc-500 dark:text-zinc-400">
                                Loading score...
                              </div>
                            </div>
                          )}
                        </>
                      );
                    })()}
                  </div>
                ) : showComparison ? (
                  <div className="flex items-center justify-center h-64 bg-zinc-50 dark:bg-zinc-900/50 rounded-lg border border-zinc-200 dark:border-zinc-800">
                    <div className="text-sm text-zinc-500 dark:text-zinc-400">
                      Comparison session not available
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </ErrorBoundary>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <ErrorBoundary
            fallback={
              <div className="min-h-[200px] flex items-center justify-center rounded-xl border-2 border-violet-400/40 bg-neutral-900 text-violet-400">
                Heat map unavailable
              </div>
            }
          >
            {frameData.thermal_frames.length > 0 ? (
              <div className="min-h-[200px] flex items-center justify-center rounded-xl border-2 border-blue-400/40 bg-neutral-900/50 text-blue-400/80 text-sm">
                Thermal data shown in 3D view above
              </div>
            ) : (
              <HeatMap
                sessionId={sessionId}
                data={heatmapData}
                activeTimestamp={currentTimestamp}
              />
            )}
          </ErrorBoundary>
          <ErrorBoundary>
            <TorchAngleGraph sessionId={sessionId} data={angleData} activeTimestamp={currentTimestamp} />
          </ErrorBoundary>
        </div>

        {scoreFetchError && (
          <p
            className="text-amber-600 dark:text-amber-400 text-sm mb-2"
            data-testid="score-fetch-error"
          >
            Score unavailable: {scoreFetchError}. Micro-feedback may use default
            thresholds.
          </p>
        )}
        <div className="mb-6">
          <ErrorBoundary>
            <ScorePanel sessionId={sessionId} />
          </ErrorBoundary>
        </div>

        {sessionData != null && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-zinc-800 dark:text-zinc-200 mb-3">
              Frame-level feedback
            </h2>
            {microFeedback.length > 0 ? (
              <FeedbackPanel
                items={microFeedback}
                frames={sessionData.frames ?? []}
                onFrameSelect={handleFrameSelect}
              />
            ) : (
              <p className="text-sm text-zinc-500 dark:text-zinc-400" data-testid="no-micro-feedback">
                No frame-level feedback for this session
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
