'use client';

/**
 * HeatMap Component
 * Visualizes heat distribution over time for a welding session.
 * Uses a CSS grid of divs (columns = time, rows = distance).
 *
 * @param sessionId - Session ID for labelling.
 * @param data - Pre-extracted heatmap data from extractHeatmapData() or extractDeltaHeatmapData().
 * @param activeTimestamp - Optional timestamp to highlight column (±50ms tolerance).
 * @param colorFn - Optional. Default: tempToColor. Use deltaTempToColor for delta heatmaps.
 * @param label - Optional heading (e.g. "Session A", "Delta", "Session B").
 * @param valueLabel - Optional. "temperature" → "425.3°C"; "delta" → "Δ +12.5°C".
 */

import { useMemo } from 'react';
import type { HeatmapData } from '@/utils/heatmapData';
import { tempToColor } from '@/utils/heatmapData';

interface HeatMapProps {
  sessionId: string;
  data?: HeatmapData | null;
  /** Highlight column at this timestamp (±50ms tolerance). */
  activeTimestamp?: number | null;
  /** Color function. Default: tempToColor. Use deltaTempToColor for delta column. */
  colorFn?: (value_celsius: number) => string;
  /** Column heading. Default: "Heat Map Visualization". */
  label?: string;
  /** "temperature" | "delta" — tooltip format. Default: "temperature". */
  valueLabel?: 'temperature' | 'delta';
}

const DEFAULT_LABEL = 'Heat Map Visualization';

const CELL_WIDTH_PX = 8;
const CELL_HEIGHT_PX = 20;
const ACTIVE_TOLERANCE_MS = 50;

export default function HeatMap({
  sessionId,
  data,
  activeTimestamp,
  colorFn = tempToColor,
  label = DEFAULT_LABEL,
  valueLabel = 'temperature',
}: HeatMapProps) {
  const { colByTs, rowByDist, isActiveColumn } = useMemo(() => {
    if (!data || data.point_count === 0) {
      return { colByTs: new Map<number, number>(), rowByDist: new Map<number, number>(), isActiveColumn: () => false };
    }
    const colByTs = new Map(data.timestamps_ms.map((t, i) => [t, i + 1]));
    const rowByDist = new Map(data.distances_mm.map((d, i) => [d, i + 1]));
    const isActiveColumn = (ts: number) =>
      activeTimestamp != null &&
      Math.abs(ts - activeTimestamp) <= ACTIVE_TOLERANCE_MS;
    return { colByTs, rowByDist, isActiveColumn };
  }, [data, activeTimestamp]);

  if (!data || data.point_count === 0) {
    return (
      <div className="heat-map-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
          {label}
        </h3>
        <div className="min-h-[300px] flex items-center justify-center border border-dashed border-zinc-300 dark:border-zinc-700 rounded text-zinc-500 dark:text-zinc-400">
          <div className="text-center">
            <p className="text-sm">Heat map for session {sessionId}</p>
            <p className="text-xs mt-2">No thermal data available</p>
          </div>
        </div>
      </div>
    );
  }

  const formatTitle = (p: { temp_celsius: number; distance_mm: number }) =>
    valueLabel === 'delta'
      ? `Δ ${p.temp_celsius >= 0 ? '+' : ''}${p.temp_celsius.toFixed(1)}°C at ${p.distance_mm}mm`
      : `${p.temp_celsius.toFixed(1)}°C at ${p.distance_mm}mm`;

  return (
    <div className="heat-map-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
        {label}
      </h3>
      <div className="overflow-x-auto">
        <div
          className="grid gap-px"
          style={{
            gridTemplateColumns: `repeat(${data.timestamps_ms.length}, ${CELL_WIDTH_PX}px)`,
            gridTemplateRows: `repeat(${data.distances_mm.length}, ${CELL_HEIGHT_PX}px)`,
            width: 'fit-content',
            minHeight: data.distances_mm.length * (CELL_HEIGHT_PX + 1),
          }}
        >
          {data.points.map((p) => {
            const col = colByTs.get(p.timestamp_ms);
            const row = rowByDist.get(p.distance_mm);
            const active = isActiveColumn(p.timestamp_ms);
            if (col == null || row == null) return null;
            return (
              <div
                key={`${p.timestamp_ms}-${p.distance_mm}`}
                style={{
                  gridColumn: col,
                  gridRow: row,
                  backgroundColor: colorFn(p.temp_celsius),
                  ...(active && {
                    outline: '2px solid #3b82f6',
                    outlineOffset: '-1px',
                    zIndex: 1,
                  }),
                }}
                title={formatTitle(p)}
                role="img"
                aria-label={valueLabel === 'delta' ? `Δ ${p.temp_celsius.toFixed(0)}°C` : `${p.temp_celsius.toFixed(0)}°C`}
              />
            );
          })}
        </div>
      </div>
      <p className="text-xs mt-2 text-zinc-500 dark:text-zinc-400">
        {data.point_count} points • {data.timestamps_ms.length} timestamps × {data.distances_mm.length} distances
      </p>
    </div>
  );
}
