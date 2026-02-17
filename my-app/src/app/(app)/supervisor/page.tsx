'use client';

import { useEffect, useState, useRef } from 'react';
import { DashboardLayout } from '@/components/dashboard/DashboardLayout';
import { CalendarHeatmap } from '@/components/dashboard/CalendarHeatmap';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { fetchAggregateKPIs } from '@/lib/api';
import { logError, logWarn } from '@/lib/logger';
import { aggregateToDashboardData } from '@/lib/aggregate-transform';
import { generateCSV, downloadCSV } from '@/lib/export';
import type { AggregateKPIResponse } from '@/types/aggregate';
import type { DashboardData } from '@/types/dashboard';
import type { SessionSummary } from '@/types/aggregate';

function getDateRange(days: number): { start: string; end: string } {
  const end = new Date();
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - days);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

export default function SupervisorPage() {
  const initialRange = getDateRange(7);
  const [dateStart, setDateStart] = useState(initialRange.start);
  const [dateEnd, setDateEnd] = useState(initialRange.end);
  const [fetchDateStart, setFetchDateStart] = useState(initialRange.start);
  const [fetchDateEnd, setFetchDateEnd] = useState(initialRange.end);
  const isFirstDateSync = useRef(true);

  const [data, setData] = useState<DashboardData | null>(null);
  const [calendar, setCalendar] = useState<{ date: string; value: number }[]>(
    []
  );
  const [sessionsTruncated, setSessionsTruncated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  // Debounce date changes (0ms on mount, 300ms thereafter)
  useEffect(() => {
    const delay = isFirstDateSync.current ? 0 : 300;
    isFirstDateSync.current = false;
    const t = setTimeout(() => {
      setFetchDateStart(dateStart);
      setFetchDateEnd(dateEnd);
    }, delay);
    return () => clearTimeout(t);
  }, [dateStart, dateEnd]);

  useEffect(() => {
    let cancelled = false;
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    fetchAggregateKPIs(
      { date_start: fetchDateStart, date_end: fetchDateEnd },
      ac.signal
    )
      .then((res: AggregateKPIResponse) => {
        if (!cancelled) {
          setData(aggregateToDashboardData(res));
          setCalendar(res.calendar ?? []);
          setSessionsTruncated(res.sessions_truncated ?? false);
        }
      })
      .catch((err) => {
        if (!cancelled && err?.name !== 'AbortError') {
          logError('SupervisorPage', err, { context: 'fetchAggregateKPIs' });
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
      ac.abort();
    };
  }, [fetchDateStart, fetchDateEnd]);

  const applyPreset = (days: number) => {
    const { start, end } = getDateRange(days);
    setDateStart(start);
    setDateEnd(end);
  };

  const handleExportCSV = async () => {
    setExportError(null);
    setExporting(true);
    try {
      const res = await fetchAggregateKPIs({
        date_start: dateStart,
        date_end: dateEnd,
        include_sessions: true,
      });
      const sessions = res.sessions ?? [];
      if (res.sessions_truncated) {
        setSessionsTruncated(true);
        logWarn(
          'SupervisorPage',
          'Export truncated: sessions_truncated=true, limited to 1000 sessions'
        );
      }
      if (sessions.length === 0) {
        setExportError('No sessions in date range to export.');
        return;
      }
      const rows: Record<string, string | number>[] = sessions.map(
        (s: SessionSummary) => ({
          session_id: s.session_id,
          operator_id: s.operator_id,
          weld_type: s.weld_type,
          start_time: s.start_time,
          score_total: s.score_total ?? '',
          frame_count: s.frame_count,
        })
      );
      const csv = generateCSV(rows);
      const filename = `supervisor-export-${new Date().toISOString().slice(0, 10)}.csv`;
      downloadCSV(filename, csv);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      logError('SupervisorPage', err, { context: 'export' });
      setExportError(`Export failed: ${msg}`);
    } finally {
      setExporting(false);
    }
  };

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-lg text-zinc-600 dark:text-zinc-400">
          Loading...
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center p-6">
        <div className="text-red-500 dark:text-red-400">Error: {error}</div>
      </div>
    );
  }

  const sessionCount = data?.metrics?.find((m) => m.id === 'session-count')
    ?.value as string | undefined;
  const isEmpty = sessionCount === '0' || !sessionCount;

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-zinc-50 dark:bg-black p-6">
        {/* Date filter and Export */}
        <div className="max-w-7xl mx-auto mb-6 flex flex-wrap items-center gap-4">
          <div className="flex gap-2" role="group" aria-label="Date range presets">
            <button
              type="button"
              onClick={() => applyPreset(7)}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-zinc-200 dark:bg-zinc-700 rounded hover:bg-zinc-300 dark:hover:bg-zinc-600 disabled:opacity-50"
            >
              Last 7 days
            </button>
            <button
              type="button"
              onClick={() => applyPreset(30)}
              disabled={loading}
              className="px-3 py-1.5 text-sm bg-zinc-200 dark:bg-zinc-700 rounded hover:bg-zinc-300 dark:hover:bg-zinc-600 disabled:opacity-50"
            >
              Last 30 days
            </button>
          </div>
          <button
            type="button"
            onClick={handleExportCSV}
            disabled={loading || exporting}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            aria-label="Export CSV"
          >
            {exporting ? 'Exporting...' : 'Export CSV'}
          </button>
          {exportError && (
            <span className="text-sm text-red-500 dark:text-red-400" role="alert">
              {exportError}
            </span>
          )}
        </div>

        {/* Mandatory truncation alert */}
        {sessionsTruncated && (
          <div
            className="max-w-7xl mx-auto mb-6 p-4 bg-amber-100 dark:bg-amber-900/30 border border-amber-300 dark:border-amber-700 rounded-lg"
            role="alert"
          >
            <strong>Export limited to 1000 sessions.</strong> Data may be
            truncated. Consider narrowing the date range.
          </div>
        )}

        {isEmpty ? (
          <div className="max-w-7xl mx-auto p-8 text-center text-zinc-500 dark:text-zinc-400 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
            No sessions in date range. Try a wider range (e.g. Last 30 days).
          </div>
        ) : (
          <>
            <DashboardLayout data={data!} title="Supervisor Dashboard" />
            <div className="mt-8 max-w-7xl mx-auto">
              <CalendarHeatmap data={calendar} title="Sessions by day" />
            </div>
          </>
        )}
      </div>
    </ErrorBoundary>
  );
}
