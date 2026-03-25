'use client';

import { Suspense, use, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { fetchSession, fetchSessionAlerts, type AlertPayload } from '@/lib/api';
import { getRuleLabel } from '@/lib/alert-labels';
import { logWarn } from '@/lib/logger';
import { FRAME_INTERVAL_MS } from '@/constants/validation';
import { useSessionComparison } from '@/hooks/useSessionComparison';
import { useFrameData } from '@/hooks/useFrameData';
import type { Session } from '@/types/session';
import dynamic from 'next/dynamic';
import { getFrameAtTimestamp, extractCenterTemperatureWithCarryForward } from '@/utils/frameUtils';
import { THERMAL_MAX_TEMP, THERMAL_MIN_TEMP, THERMAL_COLOR_SENSITIVITY } from '@/constants/thermal';

const TorchWithHeatmap3D = dynamic(
  () => import('@/components/welding/TorchWithHeatmap3D').then((m) => m.default),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-64 w-full items-center justify-center rounded-xl border-2 border-blue-400/40 bg-neutral-900">
        <span className="text-blue-400/80 animate-pulse">Loading 3D…</span>
      </div>
    ),
  }
);

/**
 * Compare Page
 * Side-by-side comparison of two welding sessions via 3D torch visualizations.
 * Fetches both sessions in parallel, single timeline slider drives both views.
 * Alert feed shows session-specific alerts with seek-to-timestamp.
 *
 * Next.js 16: params is always a Promise. Tests may pass a resolved Promise.
 */
export default function ComparePage({
  params,
}: {
  params: Promise<{ sessionIdA: string; sessionIdB: string }>;
}) {
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

/** Exported for testing — bypasses use(params) Suspense in Jest. */
export function ComparePageInner({
  sessionIdA,
  sessionIdB,
}: {
  sessionIdA: string;
  sessionIdB: string;
}) {
  const [sessionA, setSessionA] = useState<Session | null>(null);
  const [sessionB, setSessionB] = useState<Session | null>(null);
  const [alertsA, setAlertsA] = useState<AlertPayload[]>([]);
  const [alertsB, setAlertsB] = useState<AlertPayload[]>([]);
  const [alertsErrorA, setAlertsErrorA] = useState<string | null>(null);
  const [alertsErrorB, setAlertsErrorB] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [currentTimestamp, setCurrentTimestamp] = useState<number | null>(null);
  const [columnACriticalFlash, setColumnACriticalFlash] = useState(false);
  const [columnBCriticalFlash, setColumnBCriticalFlash] = useState(false);
  const prevVisibleIdsA = useRef<Set<string>>(new Set());
  const prevVisibleIdsB = useRef<Set<string>>(new Set());
  const isFirstFlashRun = useRef(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  const comparison = useSessionComparison(sessionA, sessionB);
  const frameDataA = useFrameData(sessionA?.frames ?? [], null, null);
  const frameDataB = useFrameData(sessionB?.frames ?? [], null, null);

  const { sharedMinTemp, sharedMaxTemp } = useMemo(() => {
    const framesA = sessionA?.frames ?? [];
    const framesB = sessionB?.frames ?? [];
    const allTemps = [...framesA, ...framesB]
      .flatMap((f) => f.thermal_snapshots ?? [])
      .flatMap((s) => s.readings ?? [])
      .map((r) => r.temp_celsius)
      .filter((t): t is number => t != null && isFinite(t));
    if (allTemps.length === 0) return { sharedMinTemp: THERMAL_MIN_TEMP, sharedMaxTemp: THERMAL_MAX_TEMP };
    const min = Math.max(THERMAL_MIN_TEMP, Math.min(...allTemps) - 20);
    const max = Math.min(THERMAL_MAX_TEMP, Math.max(...allTemps) + 20);
    return { sharedMinTemp: min, sharedMaxTemp: max };
  }, [sessionA?.frames, sessionB?.frames]);

  const firstTimestamp =
    comparison && comparison.deltas.length > 0
      ? comparison.deltas[0].timestamp_ms
      : null;
  const lastTimestamp =
    comparison && comparison.deltas.length > 0
      ? comparison.deltas[comparison.deltas.length - 1].timestamp_ms
      : null;

  /** Plain-English summary: alert ratio and end-of-session temp diff at lastTimestamp. */
  const summaryText = useMemo(() => {
    if (!alertsA.length && !alertsB.length) return null;
    let ratioPart: string | null = null;
    if (alertsA.length > 0 && alertsB.length === 0) {
      ratioPart = 'Session A had all the alerts';
    } else if (alertsA.length === 0 && alertsB.length > 0) {
      ratioPart = 'Session B had all the alerts';
    } else if (alertsA.length > 0 && alertsB.length > 0) {
      const ratio = (alertsA.length / alertsB.length).toFixed(1);
      ratioPart =
        Number(ratio) >= 1
          ? `Session A generated ${ratio}× more alerts`
          : `Session B generated ${(alertsB.length / alertsA.length).toFixed(1)}× more alerts`;
    }
    const tempA = sessionA?.frames
      ? extractCenterTemperatureWithCarryForward(sessionA.frames, lastTimestamp ?? 0)
      : null;
    const tempB = sessionB?.frames
      ? extractCenterTemperatureWithCarryForward(sessionB.frames, lastTimestamp ?? 0)
      : null;
    const tempDiff =
      tempA != null && tempB != null ? Math.abs(tempA - tempB) : null;
    const tempPart =
      tempDiff != null && tempDiff > 0
        ? (tempA as number) > (tempB as number)
          ? `Session A ran ${tempDiff.toFixed(0)}°C hotter than Session B`
          : `Session B ran ${tempDiff.toFixed(0)}°C hotter than Session A`
        : null;
    const parts = [ratioPart, tempPart].filter(Boolean);
    return parts.length > 0 ? parts.join(' and ') + '.' : null;
  }, [alertsA, alertsB, sessionA, sessionB, lastTimestamp]);

  const floorTs = currentTimestamp ?? firstTimestamp ?? 0;
  const firedAlertsA = useMemo(
    () => alertsA.filter((a) => a.timestamp_ms <= floorTs),
    [alertsA, floorTs]
  );
  const firedAlertsB = useMemo(
    () => alertsB.filter((a) => a.timestamp_ms <= floorTs),
    [alertsB, floorTs]
  );

  // Swap so higher score is always on the right column (only when both scores exist)
  const scoreA = sessionA?.score_total ?? null;
  const scoreB = sessionB?.score_total ?? null;
  const swap = scoreA !== null && scoreB !== null && scoreA > scoreB;
  const leftId = swap ? sessionIdB : sessionIdA;
  const rightId = swap ? sessionIdA : sessionIdB;
  const leftSession = swap ? sessionB : sessionA;
  const rightSession = swap ? sessionA : sessionB;
  const leftAlerts = swap ? alertsB : alertsA;
  const rightAlerts = swap ? alertsA : alertsB;
  const leftAlertsError = swap ? alertsErrorB : alertsErrorA;
  const rightAlertsError = swap ? alertsErrorA : alertsErrorB;
  const leftScore = swap ? scoreB : scoreA;
  const rightScore = swap ? scoreA : scoreB;
  const leftFlash = swap ? columnBCriticalFlash : columnACriticalFlash;
  const rightFlash = swap ? columnACriticalFlash : columnBCriticalFlash;

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
    setAlertsErrorA(null);
    setAlertsErrorB(null);
    const load = async () => {
      const [dataA, dataB] = await Promise.all([
        fetchSession(sessionIdA, { limit: 2000, include_thermal: true }),
        fetchSession(sessionIdB, { limit: 2000, include_thermal: true }),
      ]);
      if (cancelled) return;
      setSessionA(dataA);
      setSessionB(dataB);

      const [resA, resB] = await Promise.allSettled([
        fetchSessionAlerts(sessionIdA),
        fetchSessionAlerts(sessionIdB),
      ]);
      if (cancelled) return;
      if (resA.status === 'fulfilled') {
        setAlertsA(resA.value.alerts);
        setAlertsErrorA(null);
      } else {
        logWarn('fetchSessionAlerts', 'A failed', { sessionId: sessionIdA, reason: resA.reason });
        setAlertsErrorA('Alerts unavailable');
        setAlertsA([]);
      }
      if (resB.status === 'fulfilled') {
        setAlertsB(resB.value.alerts);
        setAlertsErrorB(null);
      } else {
        logWarn('fetchSessionAlerts', 'B failed', { sessionId: sessionIdB, reason: resB.reason });
        setAlertsErrorB('Alerts unavailable');
        setAlertsB([]);
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

  useEffect(() => {
    const idsA = new Set(
      firedAlertsA.map((a) => `${a.frame_index}-${a.timestamp_ms}-${a.rule_triggered}`)
    );
    const idsB = new Set(
      firedAlertsB.map((a) => `${a.frame_index}-${a.timestamp_ms}-${a.rule_triggered}`)
    );
    const newInA = [...idsA].filter((id) => !prevVisibleIdsA.current.has(id));
    const newInB = [...idsB].filter((id) => !prevVisibleIdsB.current.has(id));
    prevVisibleIdsA.current = idsA;
    prevVisibleIdsB.current = idsB;

    if (isFirstFlashRun.current) {
      isFirstFlashRun.current = false;
      return;
    }

    const hasNewCriticalA = newInA.some((id) => {
      const a = firedAlertsA.find(
        (x) => `${x.frame_index}-${x.timestamp_ms}-${x.rule_triggered}` === id
      );
      return a?.severity === 'critical';
    });
    const hasNewCriticalB = newInB.some((id) => {
      const a = firedAlertsB.find(
        (x) => `${x.frame_index}-${x.timestamp_ms}-${x.rule_triggered}` === id
      );
      return a?.severity === 'critical';
    });
    const timers: ReturnType<typeof setTimeout>[] = [];
    if (hasNewCriticalA) {
      setColumnACriticalFlash(true);
      timers.push(setTimeout(() => setColumnACriticalFlash(false), 800));
    }
    if (hasNewCriticalB) {
      setColumnBCriticalFlash(true);
      timers.push(setTimeout(() => setColumnBCriticalFlash(false), 800));
    }
    return () => timers.forEach(clearTimeout);
  }, [firedAlertsA, firedAlertsB]);

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
        <div className="max-w-md w-full bg-white dark:bg-zinc-900 rounded-lg border border-violet-200 dark:border-violet-800 p-6">
          <h2 className="text-lg font-semibold text-violet-800 dark:text-violet-400 mb-2">
            Failed to load comparison
          </h2>
          <p className="text-sm text-violet-600 dark:text-violet-500 mb-4">
            {error}
          </p>
          <Link
            href="/dashboard"
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
            href="/dashboard"
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
        {summaryText && (
          <p className="text-base text-zinc-400 mb-2 font-medium">
            {summaryText}
          </p>
        )}
        {comparison && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-6">
            {comparison.shared_count} overlapping frames • A: {comparison.total_a} • B: {comparison.total_b}
          </p>
        )}

        {noOverlap && (
          <div className="mb-6 p-4 bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-800 rounded-lg text-violet-800 dark:text-violet-200 text-sm">
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
                  const val = Number(e.target.value);
                  setCurrentTimestamp(
                    Number.isFinite(val) && firstTimestamp != null && lastTimestamp != null
                      ? Math.max(firstTimestamp, Math.min(lastTimestamp, val))
                      : currentTimestamp ?? firstTimestamp ?? 0
                  );
                }}
                className="w-full max-w-2xl h-2 bg-zinc-200 dark:bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
              />
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                {(currentTimestamp ?? firstTimestamp) / 1000} s
              </p>
            </div>
          )}

        {/* 3D Torch Visualization — side-by-side */}
        {currentTimestamp != null && sessionA?.frames && sessionB?.frames && (
          <ErrorBoundary>
            <div className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div>
                <div className="flex items-center justify-between mb-2 px-1">
                  <span className="font-mono text-xs text-zinc-400 truncate">{leftId}</span>
                  {leftScore != null && (
                    <span className="font-mono text-sm font-bold text-zinc-200 ml-2 shrink-0">
                      {Math.round(leftScore)}
                    </span>
                  )}
                </div>
                <TorchWithHeatmap3D
                  angle={
                    getFrameAtTimestamp(leftSession?.frames ?? [], currentTimestamp)?.angle_degrees ??
                    45
                  }
                  temp={extractCenterTemperatureWithCarryForward(
                    leftSession?.frames ?? [],
                    currentTimestamp
                  )}
                  label={leftId}
                  labelPosition="outside"
                  frames={swap ? frameDataB.thermal_frames : frameDataA.thermal_frames}
                  activeTimestamp={currentTimestamp}
                  maxTemp={sharedMaxTemp}
                  minTemp={sharedMinTemp}
                  colorSensitivity={THERMAL_COLOR_SENSITIVITY}
                />
              </div>
              <div>
                <div className="flex items-center justify-between mb-2 px-1">
                  <span className="font-mono text-xs text-zinc-400 truncate">{rightId}</span>
                  {rightScore != null && (
                    <span className="font-mono text-sm font-bold text-zinc-200 ml-2 shrink-0">
                      {Math.round(rightScore)}
                    </span>
                  )}
                </div>
                <TorchWithHeatmap3D
                  angle={
                    getFrameAtTimestamp(rightSession?.frames ?? [], currentTimestamp)?.angle_degrees ??
                    45
                  }
                  temp={extractCenterTemperatureWithCarryForward(
                    rightSession?.frames ?? [],
                    currentTimestamp
                  )}
                  label={rightId}
                  labelPosition="outside"
                  frames={swap ? frameDataA.thermal_frames : frameDataB.thermal_frames}
                  activeTimestamp={currentTimestamp}
                  maxTemp={sharedMaxTemp}
                  minTemp={sharedMinTemp}
                  colorSensitivity={THERMAL_COLOR_SENSITIVITY}
                />
              </div>
            </div>
          </ErrorBoundary>
        )}

        <div className="mt-8">
          <h2 className="text-lg font-semibold mb-3 text-black dark:text-zinc-50">
            Alert feed
          </h2>
          <div className="grid grid-cols-2 gap-4 mb-2">
            <div className="text-sm text-zinc-600 dark:text-zinc-400">
              {leftId}: {leftAlertsError != null ? (
                <span className="text-amber-600 dark:text-amber-500">Alerts unavailable</span>
              ) : (
                `${(swap ? firedAlertsB : firedAlertsA).length} alerts`
              )}
            </div>
            <div className="text-sm text-zinc-600 dark:text-zinc-400">
              {rightId}: {rightAlertsError != null ? (
                <span className="text-amber-600 dark:text-amber-500">Alerts unavailable</span>
              ) : (
                `${(swap ? firedAlertsA : firedAlertsB).length} alerts`
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div
              className={`rounded-lg border p-4 transition-all ${
                leftFlash
                  ? 'ring-4 ring-red-500 bg-red-50 dark:bg-red-950/30 animate-pulse'
                  : 'border-zinc-200 dark:border-zinc-700'
              }`}
            >
              <AlertFeedColumn
                alerts={leftAlerts}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={leftAlertsError}
                label={leftId}
              />
            </div>
            <div
              className={`rounded-lg border p-4 transition-all ${
                rightFlash
                  ? 'ring-4 ring-red-500 bg-red-50 dark:bg-red-950/30 animate-pulse'
                  : 'border-zinc-200 dark:border-zinc-700'
              }`}
            >
              <AlertFeedColumn
                alerts={rightAlerts}
                currentTimestamp={floorTs}
                onSeek={(ts) => {
                  setCurrentTimestamp(ts);
                  setIsPlaying(false);
                }}
                error={rightAlertsError}
                label={rightId}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Pop-in pattern: only fired alerts shown. Three states: active, corrected, uncorrected. */
function AlertFeedColumn({
  alerts,
  currentTimestamp,
  onSeek,
  error,
  label,
}: {
  alerts: AlertPayload[];
  currentTimestamp: number | null;
  onSeek: (ts: number) => void;
  error: string | null;
  label: string;
}) {
  const firedAlerts = useMemo(
    () =>
      alerts
        .filter((a) => currentTimestamp != null && a.timestamp_ms <= currentTimestamp)
        .sort((a, b) => b.timestamp_ms - a.timestamp_ms),
    [alerts, currentTimestamp]
  );

  if (error) return <div className="p-2 text-xs text-amber-500">{error}</div>;

  return (
    <div className="flex flex-col">
      <div className="text-[7px] font-semibold tracking-[0.28em] uppercase text-zinc-500 mb-2">
        {label}
      </div>

      {firedAlerts.length === 0 ? (
        <div className="text-[9px] text-zinc-500">No alerts yet</div>
      ) : (
        firedAlerts.map((alert) => {
          const elapsed =
            currentTimestamp != null
              ? (currentTimestamp - alert.timestamp_ms) / 1000
              : 0;

          const correctedNow =
            alert.corrected === true &&
            alert.corrected_in_seconds != null &&
            elapsed >= alert.corrected_in_seconds;

          const uncorrected = !correctedNow && elapsed >= 2;

          const dotClass = correctedNow
            ? 'bg-green-500'
            : uncorrected
              ? 'bg-red-500 opacity-50'
              : 'bg-amber-500';

          return (
            <button
              key={alert.frame_index}
              type="button"
              onClick={() => onSeek(alert.timestamp_ms)}
              className={`w-full text-left bg-transparent border-0 border-b border-zinc-800 py-2 cursor-pointer flex gap-2.5 transition-opacity duration-500 ${uncorrected ? 'opacity-50' : 'opacity-100'}`}
            >
              {/* Dot */}
              <div className="shrink-0 pt-0.5">
                <div className={`w-[7px] h-[7px] rounded-full transition-colors duration-300 ${dotClass}`} />
              </div>

              <div className="flex-1">
                {/* Rule + counter */}
                <div className="flex justify-between items-baseline">
                  <span className={`text-[9px] font-semibold tracking-[0.16em] uppercase ${correctedNow ? 'text-green-500' : uncorrected ? 'text-red-500' : 'text-amber-500'}`}>
                    {getRuleLabel(alert.rule_triggered)}
                  </span>
                  {!uncorrected && (
                    <span className={`text-[8px] ${correctedNow ? 'text-green-500' : 'text-zinc-500'}`}>
                      {correctedNow
                        ? `+${(alert.corrected_in_seconds ?? 0).toFixed(1)}s`
                        : `+${elapsed.toFixed(1)}s`}
                    </span>
                  )}
                </div>

                {/* Message */}
                <div className="text-[7.5px] text-zinc-500 mt-0.5">{alert.message}</div>

                {/* Footer */}
                <div className="mt-0.5">
                  {correctedNow && (
                    <span className="text-[7.5px] tracking-[0.14em] uppercase text-green-500">
                      ✓ corrected in {(alert.corrected_in_seconds ?? 0).toFixed(1)}s
                    </span>
                  )}
                  {uncorrected && (
                    <span className="text-[7.5px] text-red-500">✗ not corrected</span>
                  )}
                </div>
              </div>
            </button>
          );
        })
      )}
    </div>
  );
}
