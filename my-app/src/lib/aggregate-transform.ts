/**
 * Transform AggregateKPIResponse to DashboardData for reuse of DashboardLayout.
 * Guards against malformed API responses; uses [] fallbacks for trend/calendar.
 */

import type { AggregateKPIResponse } from '@/types/aggregate';
import type { DashboardData } from '@/types/dashboard';

/**
 * Convert aggregate API response to DashboardData shape.
 * Throws if kpis is missing; uses empty arrays for null/undefined trend/calendar.
 */
export function aggregateToDashboardData(res: unknown): DashboardData {
  if (!res || typeof res !== 'object') {
    throw new Error('Invalid aggregate response: not an object');
  }
  const r = res as Record<string, unknown>;
  if (!r.kpis || typeof r.kpis !== 'object') {
    throw new Error('Invalid aggregate response: missing kpis');
  }
  const kpis = r.kpis as Record<string, unknown>;
  if (typeof kpis.session_count !== 'number') {
    throw new Error('Invalid kpis.session_count');
  }

  const trend = Array.isArray(r.trend) ? r.trend : [];
  const calendar = Array.isArray(r.calendar) ? r.calendar : [];

  const toMetricValue = (v: unknown): string | number => {
    if (typeof v === 'number' && Number.isFinite(v)) return v;
    if (typeof v === 'string') return v;
    return v != null ? String(v) : '—';
  };
  const metrics = [
    { id: 'avg-score', title: 'Avg Score', value: toMetricValue(kpis.avg_score) },
    { id: 'session-count', title: 'Sessions', value: String(kpis.session_count) },
    { id: 'top-performer', title: 'Top Performer', value: toMetricValue(kpis.top_performer) },
    { id: 'rework-count', title: 'Rework', value: toMetricValue(kpis.rework_count) },
  ];

  const chartData = trend.map((t: { date?: string; value?: number }) => ({
    date: typeof t?.date === 'string' ? t.date : '',
    value: typeof t?.value === 'number' ? t.value : 0,
  }));

  return {
    metrics,
    charts: [
      {
        id: 'trend-1',
        type: 'line' as const,
        title: 'Score Trend',
        data: chartData,
      },
    ],
  };
}
