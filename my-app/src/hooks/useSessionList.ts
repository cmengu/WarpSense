import { useState, useEffect, useCallback } from "react";
import { fetchSessionList, SessionSummary, SessionListParams } from "@/lib/api";

interface UseSessionListResult {
  sessions: SessionSummary[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

/**
 * Hook to fetch session list for demo/compare picker.
 * Uses GET /api/sessions; optional site/team/date filters.
 */
export function useSessionList(
  params?: SessionListParams
): UseSessionListResult {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const paramsKey = JSON.stringify(params ?? {});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSessionList(params);
      setSessions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    load();
  }, [load]);

  return { sessions, loading, error, refetch: load };
}
