'use client';

import { useEffect, useState } from 'react';
import HeatMap from '@/components/welding/HeatMap';
import TorchAngleGraph from '@/components/welding/TorchAngleGraph';
import ScorePanel from '@/components/welding/ScorePanel';
import type { Session } from '@/types/session';

/**
 * Replay Page
 * Displays replay visualization for a specific welding session
 * 
 * @param params - Route parameters containing sessionId
 */
export default function ReplayPage({ params }: { params: { sessionId: string } }) {
  const [sessionData, setSessionData] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // NOTE: Replay visualization deferred to Phase 2 (after live session validation).
    // Will wire fetchSession() → extractHeatmapData() / extractAngleData() → components in next iteration.
    setLoading(false);
  }, [params.sessionId]);

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
          Session Replay: {params.sessionId}
        </h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <HeatMap sessionId={params.sessionId} />
          <TorchAngleGraph sessionId={params.sessionId} />
        </div>
        
        <div className="mb-6">
          <ScorePanel sessionId={params.sessionId} />
        </div>
      </div>
    </div>
  );
}
