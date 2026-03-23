"use client";
/**
 * /analysis — WarpSense post-weld analysis surface.
 *
 * State machine (simplified in Phase UI-8.5):
 *   empty  → no session selected; right panel shows prompt
 *   active → AnalysisTimeline owns both SSE streaming and inline report display
 *
 * Height: fills the `(app)` layout content area via `h-full min-h-0` beside AppSidebar.
 * WelderTrendChart is loaded via next/dynamic (ssr:false) — Recharts uses DOM APIs
 * unavailable in Node. See LEARNING_LOG.md 2026-03-02.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type {
  MockSession,
  WarpReport,
  WarpHealthResponse,
} from "@/types/warp-analysis";
import {
  fetchWarpHealth,
  fetchWarpReport,
  fetchMockSessions,
} from "@/lib/warp-api";
import { SessionList } from "@/components/analysis/SessionList";
import { AnalysisTimeline } from "@/components/analysis/AnalysisTimeline";

const WelderTrendChart = dynamic(
  () =>
    import("@/components/analysis/WelderTrendChart").then(
      (m) => m.WelderTrendChart,
    ),
  { ssr: false },
);

type ViewState =
  | { mode: "empty" }
  | { mode: "active"; sessionId: string };

const HEALTH_POLL_MS = 30_000;

export default function AnalysisPage() {
  const [selectedSession, setSelectedSession] = useState<MockSession | null>(null);
  const [viewState, setViewState]             = useState<ViewState>({ mode: "empty" });
  // Increment to re-trigger AnalysisTimeline's stream effect without unmounting.
  const [streamTrigger, setStreamTrigger]     = useState(0);
  const [streamError, setStreamError]         = useState<string | null>(null);
  const [health, setHealth]                   = useState<WarpHealthResponse | null>(null);
  const [isAnalysing, setIsAnalysing]         = useState(false);
  const [allSessions, setAllSessions]         = useState<MockSession[]>([]);

  const analyseQueueRef  = useRef<MockSession[]>([]);
  const selectCounterRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const h = await fetchWarpHealth();
      if (!cancelled) setHealth(h);
    };
    void poll();
    const id = setInterval(() => void poll(), HEALTH_POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  useEffect(() => {
    fetchMockSessions()
      .then(setAllSessions)
      .catch(() => {});
  }, []);

  const startStream = useCallback((sessionId: string) => {
    setStreamError(null);
    setViewState({ mode: "active", sessionId });
    setStreamTrigger((n) => n + 1);
  }, []);

  const handleSessionSelect = useCallback(
    async (session: MockSession) => {
      setSelectedSession(session);
      setIsAnalysing(false);
      analyseQueueRef.current = [];
      setViewState({ mode: "empty" });

      const callId = ++selectCounterRef.current;

      try {
        await fetchWarpReport(session.session_id);
      } catch (err) {
        if (callId !== selectCounterRef.current) return;
        setStreamError(
          `Could not load report for ${session.session_id}: ${String(err)}`,
        );
        return;
      }

      if (callId !== selectCounterRef.current) return;

      // Whether or not a cached report exists, we stream — backend may short-circuit to cached result.
      startStream(session.session_id);
    },
    [startStream],
  );

  const handleStreamComplete = useCallback(
    (_report: WarpReport) => {
      // AnalysisTimeline displays the report internally.
      // This callback advances the Analyse All queue.
      const queue = analyseQueueRef.current;
      if (queue.length > 0) {
        const nextSession = queue[0];
        analyseQueueRef.current = queue.slice(1);
        setSelectedSession(nextSession);
        startStream(nextSession.session_id);
      } else {
        setIsAnalysing(false);
      }
    },
    [startStream],
  );

  const handleStreamError = useCallback((message: string) => {
    setStreamError(message);
    setIsAnalysing(false);
    analyseQueueRef.current = [];
    setViewState({ mode: "empty" });
  }, []);

  const handleReanalyse = useCallback(() => {
    if (!selectedSession) return;
    // Restores active mode after error (view was cleared) and bumps streamTrigger to re-run.
    startStream(selectedSession.session_id);
  }, [selectedSession, startStream]);

  const handleAnalyseAll = useCallback(async () => {
    let sessions: MockSession[];
    try {
      sessions = await fetchMockSessions();
    } catch (err) {
      setStreamError(`Could not load sessions: ${String(err)}`);
      return;
    }
    if (sessions.length === 0) return;
    const first = sessions[0];
    analyseQueueRef.current = sessions.slice(1);
    setSelectedSession(first);
    setIsAnalysing(true);
    startStream(first.session_id);
  }, [startStream]);

  const healthOk =
    health !== null &&
    health.graph_initialised &&
    health.classifier_initialised;

  const analysedSessions = allSessions.filter((s) => s.disposition !== null);
  const kpiPassRate       = analysedSessions.length > 0
    ? Math.round(
        (analysedSessions.filter((s) => s.disposition === "PASS").length / analysedSessions.length) * 100,
      )
    : 0;
  const kpiReworkCount = analysedSessions.filter((s) => s.disposition === "REWORK_REQUIRED").length;

  return (
    <div
      className="flex h-full min-h-0 w-full flex-col bg-[var(--warp-bg)]"
      style={{ fontFamily: "var(--font-warp-mono), monospace" }}
    >
      <div className="flex shrink-0 items-center justify-between border-b border-[var(--warp-border)] bg-[var(--warp-surface)] px-4 py-2">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)]">
            WarpSense
          </span>
          <span className="font-mono text-[8px] text-[var(--warp-text-dim)]">
            AI Analysis Engine
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              health === null
                ? "bg-gray-600"
                : healthOk
                  ? "bg-green-500"
                  : "bg-red-500"
            }`}
          />
          <span className="font-mono text-[9px] text-[var(--warp-text-dim)]">
            {health === null
              ? "system: checking"
              : healthOk
                ? "system: OK"
                : "system: unavailable"}
          </span>
        </div>
      </div>

      {streamError && (
        <div className="flex shrink-0 items-center justify-between border-b border-red-800 bg-red-950/50 px-4 py-2 font-mono text-[10px] text-red-300">
          <span>Analysis failed: {streamError}</span>
          <div className="ml-4 flex items-center gap-3">
            {selectedSession && (
              <button
                type="button"
                onClick={handleReanalyse}
                className="text-red-400 transition-colors hover:text-red-200"
                aria-label="Retry analysis"
              >
                Retry
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                setStreamError(null);
              }}
              className="text-red-400 transition-colors hover:text-red-200"
              aria-label="Dismiss error"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {health !== null && !healthOk && (
        <div className="shrink-0 border-b border-amber-900 bg-amber-950/40 px-4 py-2 font-mono text-[10px] text-amber-400">
          AI pipeline unavailable — analysis may not complete
        </div>
      )}

      {analysedSessions.length > 0 && (
        <div className="flex shrink-0 gap-6 border-b border-[var(--warp-border)] bg-[var(--warp-surface)] px-4 py-2">
          <div>
            <p className="font-mono text-[8px] uppercase tracking-widest text-[var(--warp-text-muted)]">Sessions Analysed</p>
            <p className="font-mono text-[16px] text-[var(--warp-text)]">{analysedSessions.length}</p>
          </div>
          <div>
            <p className="font-mono text-[8px] uppercase tracking-widest text-[var(--warp-text-muted)]">Pass Rate</p>
            <p className="font-mono text-[16px] text-green-400">{kpiPassRate}%</p>
          </div>
          <div>
            <p className="font-mono text-[8px] uppercase tracking-widest text-[var(--warp-text-muted)]">Rework Caught</p>
            <p className="font-mono text-[16px] text-red-400">{kpiReworkCount}</p>
          </div>
        </div>
      )}

      <div
        className="flex min-h-0 min-w-[1200px] flex-1 overflow-hidden"
      >
        <div className="flex w-[320px] shrink-0 flex-col overflow-hidden border-r border-[var(--warp-border)]">
          <div className="min-h-0 flex-1 overflow-hidden">
            <SessionList
              onSessionSelect={handleSessionSelect}
              selectedSessionId={selectedSession?.session_id ?? null}
              onAnalyseAll={handleAnalyseAll}
              isAnalysing={isAnalysing}
            />
          </div>
          {selectedSession && (
            <div id="welder-trend-chart">
              <WelderTrendChart welderId={selectedSession.welder_id} />
            </div>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-hidden">
          {viewState.mode === "empty" && (
            <div className="flex h-full items-center justify-center">
              <div className="space-y-1 text-center">
                <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-dim)]">
                  Select a session to begin analysis
                </p>
                <p className="font-mono text-[9px] text-zinc-700">
                  Or use Analyse All to run the full pipeline
                </p>
              </div>
            </div>
          )}

          {viewState.mode === "active" && (
            <AnalysisTimeline
              key={viewState.sessionId}
              sessionId={viewState.sessionId}
              streamTrigger={streamTrigger}
              onError={handleStreamError}
              onComplete={handleStreamComplete}
              onReanalyse={handleReanalyse}
              welderDisplayName={selectedSession?.welder_name ?? null}
            />
          )}
        </div>
      </div>
    </div>
  );
}
