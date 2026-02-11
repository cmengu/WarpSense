'use client';

import { Suspense, use, useEffect, useState } from 'react';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import HeatMap from '@/components/welding/HeatMap';
import TorchAngleGraph from '@/components/welding/TorchAngleGraph';
import ScorePanel from '@/components/welding/ScorePanel';
import { fetchSession } from '@/lib/api';
import { extractHeatmapData } from '@/utils/heatmapData';
import { extractAngleData } from '@/utils/angleData';
import { useSessionMetadata } from '@/hooks/useSessionMetadata';
import { useFrameData } from '@/hooks/useFrameData';
import type { Session } from '@/types/session';

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
  return <ReplayPageInner sessionId={sessionId} />;
}

function ReplayPageInner({ sessionId }: { sessionId: string }) {
  const [sessionData, setSessionData] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const metadata = useSessionMetadata(sessionData);
  const frameData = useFrameData(
    sessionData?.frames ?? [],
    null,
    null
  );

  const heatmapData = sessionData?.frames
    ? extractHeatmapData(frameData.thermal_frames)
    : null;
  const angleData = sessionData?.frames
    ? extractAngleData(sessionData.frames)
    : null;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchSession(sessionId)
      .then((session) => {
        if (!cancelled) {
          setSessionData(session);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setSessionData(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
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
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white dark:bg-zinc-900 rounded-lg border border-red-200 dark:border-red-800 p-6">
          <h2 className="text-lg font-semibold text-red-800 dark:text-red-400 mb-2">
            Failed to load session
          </h2>
          <p className="text-sm text-red-600 dark:text-red-500 mb-4">
            {error}
          </p>
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
          <div className="text-sm text-zinc-600 dark:text-zinc-400 mb-4">
            {metadata.weld_type_label} • {metadata.duration_display} •{' '}
            {metadata.frame_count} frames
          </div>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <ErrorBoundary>
            <HeatMap sessionId={sessionId} data={heatmapData} />
          </ErrorBoundary>
          <ErrorBoundary>
            <TorchAngleGraph sessionId={sessionId} data={angleData} />
          </ErrorBoundary>
        </div>

        <div className="mb-6">
          <ErrorBoundary>
            <ScorePanel sessionId={sessionId} />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
