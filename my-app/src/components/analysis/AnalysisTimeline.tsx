"use client";
/**
 * AnalysisTimeline — unified SSE stream + inline report display.
 *
 * Replaces the AnalysisStream → QualityReportCard context-switch pattern.
 * Agent cards persist above the report (Perplexity "sources before answer" pattern).
 *
 * Props:
 *   sessionId      — session to analyse
 *   streamTrigger  — increment this number to re-run analysis on the same session
 *   onError        — called on SSE pipeline error; parent shows error banner
 *   onComplete     — optional; when the stream finishes with a report (e.g. Analyse All queue)
 *   onReanalyse    — optional; passed to QualityReportCard for in-report retry
 *   welderDisplayName — passed through to QualityReportCard
 */
import { useState, useEffect, useRef } from "react";
import type {
  WarpReport,
  WarpSSEEvent,
  AgentStage,
  AgentCardState,
} from "@/types/warp-analysis";
import { streamAnalysis } from "@/lib/warp-api";
import { SpecialistCard } from "./SpecialistCard";
import { QualityReportCard } from "./QualityReportCard";

export interface AnalysisTimelineProps {
  sessionId: string;
  streamTrigger: number;
  onError: (message: string) => void;
  /** Fired when the pipeline emits a final report — used by /analysis for Analyse All queue. */
  onComplete?: (report: WarpReport) => void;
  /** Wired to QualityReportCard so users can re-run analysis from the report panel. */
  onReanalyse?: () => void;
  welderDisplayName: string | null;
}

const AGENT_STAGES: AgentStage[] = ["thermal_agent", "geometry_agent", "process_agent"];

const BLANK_STATE: AgentCardState = {
  status:      "queued",
  disposition: null,
  message:     null,
  startedAt:   undefined,
  finishedAt:  undefined,
};

const INITIAL_STATES: Record<AgentStage, AgentCardState> = {
  thermal_agent:  { ...BLANK_STATE },
  geometry_agent: { ...BLANK_STATE },
  process_agent:  { ...BLANK_STATE },
};

/** Must match analyse_session_stream event count in warp_service.py (currently 9). */
const TOTAL_EVENTS = 9;

type Phase = "streaming" | "done";

export function AnalysisTimeline({
  sessionId,
  streamTrigger,
  onError,
  onComplete,
  onReanalyse,
  welderDisplayName,
}: AnalysisTimelineProps) {
  const [phase, setPhase]           = useState<Phase>("streaming");
  const [progress, setProgress]     = useState(0);
  const [logLines, setLogLines]     = useState<string[]>([]);
  const [stageStates, setStageStates] =
    useState<Record<AgentStage, AgentCardState>>(INITIAL_STATES);
  const [report, setReport]         = useState<WarpReport | null>(null);

  const readerRef          = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const onErrorRef         = useRef(onError);
  const onCompleteRef      = useRef(onComplete);
  const onCompleteFiredRef = useRef(false);

  useEffect(() => { onErrorRef.current = onError; }, [onError]);
  useEffect(() => { onCompleteRef.current = onComplete; }, [onComplete]);

  // Fire onComplete AFTER the report has rendered (not inline in the stream loop).
  // Without this, React 18 batches setPhase("done") + startStream(next) into one
  // render, the key changes, and AnalysisTimeline unmounts before the report displays.
  // 800 ms gives the user a moment to see the result before Analyse All advances.
  useEffect(() => {
    if (phase !== "done" || !report || onCompleteFiredRef.current) return;
    onCompleteFiredRef.current = true;
    const t = setTimeout(() => { onCompleteRef.current?.(report); }, 800);
    return () => clearTimeout(t);
  }, [phase, report]);

  // Re-run stream whenever sessionId or streamTrigger changes.
  useEffect(() => {
    let cancelled = false;
    onCompleteFiredRef.current = false;

    // Reset all state for the new run.
    setPhase("streaming");
    setProgress(0);
    setLogLines([]);
    setStageStates(INITIAL_STATES);
    setReport(null);

    const runStream = async () => {
      let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
      try {
        const stream = await streamAnalysis(sessionId);
        if (cancelled) { stream.cancel().catch(() => {}); return; }

        reader = stream.getReader();
        readerRef.current = reader;

        const decoder = new TextDecoder();
        let buffer = "";
        let eventCount = 0;

        while (true) {
          const { done, value } = await reader.read();
          if (cancelled || done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const line = part.trim();
            // Ignore SSE comment lines (keepalive: ": keepalive")
            if (!line.startsWith("data: ")) continue;

            let event: WarpSSEEvent;
            try {
              event = JSON.parse(line.slice(6)) as WarpSSEEvent;
            } catch {
              continue;
            }

            if (cancelled) return;

            eventCount += 1;
            setProgress(Math.min(Math.round((eventCount / TOTAL_EVENTS) * 100), 100));

            if (event.message) {
              const ts = new Date().toLocaleTimeString("en-GB", {
                hour: "2-digit", minute: "2-digit", second: "2-digit",
              });
              setLogLines((prev) => [...prev, `[${ts}] ${event.message}`]);
            }

            if (
              event.stage === "thermal_agent" ||
              event.stage === "geometry_agent" ||
              event.stage === "process_agent"
            ) {
              const stage = event.stage as AgentStage;
              const isDone = event.status === "done";
              const now = Date.now();
              setStageStates((prev) => ({
                ...prev,
                [stage]: {
                  status:      isDone ? "done" : "running",
                  disposition: event.disposition ?? null,
                  message:     event.message ?? null,
                  startedAt:   isDone ? prev[stage].startedAt : (prev[stage].startedAt ?? now),
                  finishedAt:  isDone ? now : undefined,
                },
              }));
            }

            if (event.stage === "complete" && event.report) {
              if (cancelled) return;
              setProgress(100);
              setReport(event.report);
              setPhase("done");
              // onComplete is fired by useEffect after the report renders — see above.
              return;
            }

            if (event.stage === "error") {
              if (cancelled) return;
              onErrorRef.current(event.message ?? "Pipeline error");
              return;
            }

            // Yield to browser event loop — breaks React 18 automatic batching.
            // Without this, multiple events from one reader.read() buffer are processed
            // synchronously and React collapses all setStageStates calls into one render.
            await new Promise<void>((resolve) => setTimeout(resolve, 0));
          }
        }
      } catch (err) {
        if (!cancelled) onErrorRef.current(String(err));
      } finally {
        try { reader?.releaseLock(); } catch { /* already released */ }
      }
    };

    void runStream();

    return () => {
      cancelled = true;
      readerRef.current?.cancel();
      readerRef.current = null;
    };
  }, [sessionId, streamTrigger]);

  return (
    <div className="flex flex-col h-full min-h-0 bg-[var(--warp-surface)]">
      {/* Header + progress bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-900 shrink-0">
        <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)]">
          {phase === "streaming" ? "Analysis in Progress" : "Analysis Complete"}
        </span>
        <span className="font-mono text-[9px] text-[var(--warp-text-dim)]">{sessionId}</span>
      </div>

      <div className="h-0.5 bg-zinc-900 shrink-0">
        <div
          className="h-full bg-amber-400 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Scrollable content — agent cards persist above report */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* Agent card row — always visible */}
        <div className="flex shrink-0 gap-px p-4">
          {AGENT_STAGES.map((stage, index) => (
            <div
              key={stage}
              className="flex-1"
              style={{ animation: `warp-card-enter 200ms ease-out ${index * 150}ms both` }}
            >
              <SpecialistCard stage={stage} state={stageStates[stage]} />
            </div>
          ))}
        </div>

        {/* Log lines — visible during streaming */}
        {phase === "streaming" && (
          <div className="px-4 pb-4">
            <div className="font-mono text-[9px] text-[var(--warp-text-dim)] space-y-0.5">
              {logLines.map((line, i) => (
                <p key={i}>{line}</p>
              ))}
              {logLines.length === 0 && (
                <p className="text-zinc-700">Waiting for pipeline…</p>
              )}
            </div>
          </div>
        )}

        {/* Report — fades in when phase === "done"; agent cards remain visible above */}
        {phase === "done" && report && (
          <div className="animate-warp-fade-in px-0">
            <div className="border-t border-zinc-800 mx-4 mb-2" />
            <QualityReportCard
              report={report}
              welderDisplayName={welderDisplayName}
              onReanalyse={onReanalyse}
            />
          </div>
        )}
      </div>
    </div>
  );
}
