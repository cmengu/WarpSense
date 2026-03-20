"use client";
// SSE: fetch() + ReadableStream only. Never EventSource (POST route is not GET).
import { useState, useEffect, useRef } from "react";
import type { WarpReport, WarpSSEEvent, AgentStage, AgentCardState } from "@/types/warp-analysis";
import { streamAnalysis } from "@/lib/warp-api";
import { SpecialistCard } from "./SpecialistCard";

export interface AnalysisStreamProps {
  sessionId: string;
  onComplete: (report: WarpReport) => void;
  onError: (message: string) => void;
}

const AGENT_STAGES: AgentStage[] = ["thermal_agent", "geometry_agent", "process_agent"];

const INITIAL_STATES: Record<AgentStage, AgentCardState> = {
  thermal_agent:  { status: "queued", disposition: null },
  geometry_agent: { status: "queued", disposition: null },
  process_agent:  { status: "queued", disposition: null },
};

/** Must match `analyse_session_stream` event count in warp_service.py (currently 9). */
const TOTAL_EVENTS = 9;

/**
 * Consumes POST /analyse SSE via same-origin proxy. Callbacks are held in refs so the stream
 * effect depends only on sessionId — parent inline handlers must not restart the reader (F1).
 */
export function AnalysisStream({ sessionId, onComplete, onError }: AnalysisStreamProps) {
  const [progress, setProgress] = useState(0);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [stageStates, setStageStates] = useState<Record<AgentStage, AgentCardState>>(INITIAL_STATES);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    let cancelled = false;
    let eventCount = 0;

    const runStream = async () => {
      setProgress(0);
      setLogLines([]);
      setStageStates(INITIAL_STATES);

      let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
      try {
        const stream = await streamAnalysis(sessionId);
        if (cancelled) {
          stream.cancel().catch(() => {});
          return;
        }

        reader = stream.getReader();
        readerRef.current = reader;

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (cancelled || done) break;

          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const line = part.trim();
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
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              });
              setLogLines((prev) => [...prev, `[${ts}] ${event.message}`]);
            }

            if (
              event.stage === "thermal_agent" ||
              event.stage === "geometry_agent" ||
              event.stage === "process_agent"
            ) {
              const stage = event.stage as AgentStage;
              setStageStates((prev) => ({
                ...prev,
                [stage]: {
                  status: event.status === "done" ? "done" : "running",
                  disposition: event.disposition ?? null,
                },
              }));
            }

            // Ignore late terminal events after unmount/session switch.
            if (event.stage === "complete" && event.report) {
              if (cancelled) return;
              setProgress(100);
              onCompleteRef.current(event.report);
              return;
            }

            if (event.stage === "error") {
              if (cancelled) return;
              onErrorRef.current(event.message ?? "Pipeline error");
              return;
            }
          }
        }
      } catch (err) {
        if (!cancelled) onErrorRef.current(String(err));
      } finally {
        try {
          reader?.releaseLock();
        } catch {
          /* releaseLock may throw if reader already cancelled / released */
        }
      }
    };

    void runStream();

    return () => {
      cancelled = true;
      readerRef.current?.cancel();
      readerRef.current = null;
    };
  }, [sessionId]);

  return (
    <div className="flex flex-col bg-[var(--warp-surface)] min-h-[400px]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-900 shrink-0">
        <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)]">
          Analysis in Progress
        </span>
        <span className="font-mono text-[9px] text-[var(--warp-text-dim)]">{sessionId}</span>
      </div>

      <div className="h-0.5 bg-zinc-900 shrink-0">
        <div
          className="h-full bg-amber-400 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex shrink-0 gap-px p-4">
        {AGENT_STAGES.map((stage, index) => (
          <div
            key={stage}
            className="flex-1"
            style={{
              animation: `warp-card-enter 200ms ease-out ${index * 150}ms both`,
            }}
          >
            <SpecialistCard stage={stage} state={stageStates[stage]} />
          </div>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        <div className="font-mono text-[9px] text-[var(--warp-text-dim)] space-y-0.5">
          {logLines.map((line, i) => (
            <p key={i}>{line}</p>
          ))}
          {logLines.length === 0 && <p className="text-zinc-700">Waiting for pipeline…</p>}
        </div>
      </div>
    </div>
  );
}
