/**
 * NarrativePanel — displays AI-generated narrative for a session.
 * Fetches on mount; shows loading/error states.
 * "Regenerate" triggers POST with force_regenerate=true.
 */
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import type { SessionID } from "@/types/shared";
import type { NarrativeResponse } from "@/types/narrative";
import { fetchNarrative, generateNarrative } from "@/lib/narrative-api";
import { logError } from "@/lib/logger";

interface NarrativePanelProps {
  sessionId: SessionID;
}

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "generating" }
  | { status: "ready"; data: NarrativeResponse }
  | { status: "error"; message: string };

export function NarrativePanel({ sessionId }: NarrativePanelProps) {
  const [state, setState] = useState<State>({ status: "loading" });
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const load = useCallback(
    (forceRegenerate = false) => {
      setState({ status: forceRegenerate ? "generating" : "loading" });
      const action = forceRegenerate
        ? generateNarrative(sessionId, true)
        : fetchNarrative(sessionId).catch(() =>
            generateNarrative(sessionId, false)
          );

      action
        .then((data) => {
          if (mountedRef.current) setState({ status: "ready", data });
        })
        .catch((err) => {
          logError("NarrativePanel", err);
          if (mountedRef.current)
            setState({ status: "error", message: "Failed to generate narrative." });
        });
    },
    [sessionId]
  );

  useEffect(() => {
    load();
  }, [load]);

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString(undefined, {
      dateStyle: "short",
      timeStyle: "short",
    });

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
          AI Coach Report
        </h2>
        {state.status === "ready" && (
          <div className="flex items-center gap-4">
            <span className="text-xs text-neutral-600">
              {state.data.cached ? "Cached" : "Generated"} ·{" "}
              {formatDate(state.data.generated_at)}
            </span>
            <button
              onClick={() => load(true)}
              className="text-xs text-cyan-400 hover:text-cyan-300 underline"
            >
              Regenerate
            </button>
          </div>
        )}
      </div>

      {(state.status === "loading" || state.status === "generating") && (
        <div className="space-y-3 animate-pulse">
          <div className="h-4 bg-neutral-800 rounded w-full" />
          <div className="h-4 bg-neutral-800 rounded w-5/6" />
          <div className="h-4 bg-neutral-800 rounded w-4/6" />
        </div>
      )}

      {state.status === "error" && (
        <p className="text-sm text-red-400">{state.message}</p>
      )}

      {state.status === "ready" && (
        <p className="text-sm text-neutral-300 leading-relaxed whitespace-pre-line">
          {state.data.narrative_text}
        </p>
      )}
    </div>
  );
}

export default NarrativePanel;
