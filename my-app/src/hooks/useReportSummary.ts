/**
 * Hook to fetch report summary for a session.
 *
 * Uses AbortController to cancel fetch on unmount — no state updates after unmount.
 * Returns { data, loading, error } for compliance UI.
 */

import { useEffect, useState } from "react";

import { fetchReportSummary } from "@/lib/api";
import type { ReportSummary } from "@/types/report-summary";

export interface UseReportSummaryResult {
  data: ReportSummary | null;
  loading: boolean;
  error: string | null;
}

/**
 * Fetch report summary for the given session.
 *
 * When sessionId is null, loading is false and data/error are null.
 * On unmount, in-flight fetch is aborted.
 *
 * @param sessionId - Session ID to fetch, or null to skip.
 * @returns { data, loading, error }
 */
export function useReportSummary(
  sessionId: string | null
): UseReportSummaryResult {
  const [data, setData] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId || sessionId.trim() === "") {
      setLoading(false);
      setData(null);
      setError(null);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    fetchReportSummary(sessionId, controller.signal)
      .then((summary) => {
        if (!controller.signal.aborted) {
          setData(summary);
          setError(null);
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : String(err));
          setData(null);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [sessionId]);

  return { data, loading, error };
}
