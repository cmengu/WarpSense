'use client';

/**
 * HeatMap Component
 * Visualizes heat distribution over time for a welding session.
 *
 * Accepts pre-extracted heatmap data from `extractHeatmapData()`.
 * The component does NOT fetch or transform raw frame data itself —
 * data transformation is the caller's responsibility.
 *
 * @param sessionId - Session ID for labelling.
 * @param data - Optional pre-extracted heatmap data. Null = loading/empty state.
 */

import type { HeatmapData } from '@/utils/heatmapData';

interface HeatMapProps {
  sessionId: string;
  data?: HeatmapData | null;
}

export default function HeatMap({ sessionId, data }: HeatMapProps) {
  if (!data || data.point_count === 0) {
    return (
      <div className="heat-map-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
          Heat Map Visualization
        </h3>
        <div className="placeholder-visualization text-zinc-500 dark:text-zinc-400 min-h-[300px] flex items-center justify-center border border-dashed border-zinc-300 dark:border-zinc-700 rounded">
          <div className="text-center">
            <p className="text-sm">Heat map for session {sessionId}</p>
            <p className="text-xs mt-2">No thermal data available</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="heat-map-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
        Heat Map Visualization
      </h3>
      <div className="placeholder-visualization text-zinc-500 dark:text-zinc-400 min-h-[300px] flex items-center justify-center border border-dashed border-zinc-300 dark:border-zinc-700 rounded">
        <div className="text-center">
          <p className="text-sm">Heat map for session {sessionId}</p>
          <p className="text-xs mt-2">
            {data.point_count} data points across{' '}
            {data.timestamps_ms.length} timestamps and{' '}
            {data.distances_mm.length} distances
          </p>
          <p className="text-xs mt-1 text-zinc-400 dark:text-zinc-500">
            Visualization rendering coming soon
          </p>
        </div>
      </div>
    </div>
  );
}
