'use client';

/**
 * TorchAngleGraph Component
 * Graphs torch angle over time for a welding session.
 * Uses Recharts LineChart with ReferenceLine at 45° target.
 *
 * @param sessionId - Session ID for labelling.
 * @param data - Pre-extracted angle data from extractAngleData().
 * @param activeTimestamp - Optional timestamp to show vertical cursor line.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import type { AngleData } from '@/utils/angleData';

interface TorchAngleGraphProps {
  sessionId: string;
  data?: AngleData | null;
  /** Vertical cursor line at this timestamp (ms). */
  activeTimestamp?: number | null;
}

const TARGET_ANGLE_DEG = 45;
const CHART_HEIGHT = 300;

export default function TorchAngleGraph({ sessionId, data, activeTimestamp }: TorchAngleGraphProps) {
  if (!data || data.point_count === 0) {
    return (
      <div className="torch-angle-graph-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
          Torch Angle Over Time
        </h3>
        <div className="min-h-[300px] flex items-center justify-center border border-dashed border-zinc-300 dark:border-zinc-700 rounded text-zinc-500 dark:text-zinc-400">
          <div className="text-center">
            <p className="text-sm">Torch angle graph for session {sessionId}</p>
            <p className="text-xs mt-2">No angle data available</p>
          </div>
        </div>
      </div>
    );
  }

  const minAngle = data.min_angle_degrees ?? 0;
  const maxAngle = data.max_angle_degrees ?? 90;
  const yDomain = [minAngle - 5, maxAngle + 5];

  return (
    <div className="torch-angle-graph-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
        Torch Angle Over Time
      </h3>
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <LineChart data={data.points} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <XAxis
            dataKey="timestamp_ms"
            tickFormatter={(t: number) => `${(t / 1000).toFixed(1)}s`}
            stroke="currentColor"
            className="text-zinc-600 dark:text-zinc-400"
          />
          <YAxis
            domain={yDomain}
            tickFormatter={(v: number) => `${v}°`}
            stroke="currentColor"
            className="text-zinc-600 dark:text-zinc-400"
          />
          <ReferenceLine
            y={TARGET_ANGLE_DEG}
            stroke="#a855f7"
            strokeDasharray="3 3"
            label={{ value: 'Target', position: 'top', fill: '#a855f7' }}
          />
          {activeTimestamp != null && (
            <ReferenceLine
              x={activeTimestamp}
              stroke="#94a3b8"
              strokeDasharray="2 2"
              label={{ value: '', position: 'top' }}
            />
          )}
          <Tooltip
            formatter={(value: number | undefined) => [value != null ? `${value}°` : '—', 'Angle']}
            labelFormatter={(label: unknown) =>
              typeof label === 'number' ? `${(label / 1000).toFixed(1)}s` : String(label)
            }
          />
          <Line
            type="monotone"
            dataKey="angle_degrees"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs mt-2 text-zinc-500 dark:text-zinc-400">
        {data.point_count} points | Range: {minAngle.toFixed(1)}° – {maxAngle.toFixed(1)}° | Avg: {data.avg_angle_degrees?.toFixed(1)}°
      </p>
    </div>
  );
}
