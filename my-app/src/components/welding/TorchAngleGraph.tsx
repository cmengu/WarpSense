'use client';

/**
 * TorchAngleGraph Component
 * Graphs torch angle over time for a welding session.
 *
 * Accepts pre-extracted angle data from `extractAngleData()`.
 * The component does NOT fetch or transform raw frame data itself —
 * data transformation is the caller's responsibility.
 *
 * @param sessionId - Session ID for labelling.
 * @param data - Optional pre-extracted angle data. Null = loading/empty state.
 */

import type { AngleData } from '@/utils/angleData';

interface TorchAngleGraphProps {
  sessionId: string;
  data?: AngleData | null;
}

export default function TorchAngleGraph({ sessionId, data }: TorchAngleGraphProps) {
  if (!data || data.point_count === 0) {
    return (
      <div className="torch-angle-graph-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
          Torch Angle Over Time
        </h3>
        <div className="placeholder-visualization text-zinc-500 dark:text-zinc-400 min-h-[300px] flex items-center justify-center border border-dashed border-zinc-300 dark:border-zinc-700 rounded">
          <div className="text-center">
            <p className="text-sm">Torch angle graph for session {sessionId}</p>
            <p className="text-xs mt-2">No angle data available</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="torch-angle-graph-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
        Torch Angle Over Time
      </h3>
      <div className="placeholder-visualization text-zinc-500 dark:text-zinc-400 min-h-[300px] flex items-center justify-center border border-dashed border-zinc-300 dark:border-zinc-700 rounded">
        <div className="text-center">
          <p className="text-sm">Torch angle graph for session {sessionId}</p>
          <p className="text-xs mt-2">
            {data.point_count} data points |
            Range: {data.min_angle_degrees?.toFixed(1)}° – {data.max_angle_degrees?.toFixed(1)}° |
            Avg: {data.avg_angle_degrees?.toFixed(1)}°
          </p>
          <p className="text-xs mt-1 text-zinc-400 dark:text-zinc-500">
            Visualization rendering coming soon
          </p>
        </div>
      </div>
    </div>
  );
}
