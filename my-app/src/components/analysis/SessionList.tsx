"use client";
import { useState, useEffect } from "react";
import type { MockSession } from "@/types/warp-analysis";
import { fetchMockSessions } from "@/lib/warp-api";
import { StatusBadge } from "./StatusBadge";

export interface SessionListProps {
  /** Called when the user clicks a session row. Always passes the full MockSession. */
  onSessionSelect: (session: MockSession) => void;
  selectedSessionId: string | null;
  /** Wired in Phase UI-7. */
  onAnalyseAll?: () => void;
  /** Disables "Analyse All" while a stream is active. Wired in Phase UI-7. */
  isAnalysing?: boolean;
}

/** First letter of each of the first two words in a name. */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return (parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "");
}

/** Amber for expert archetype, blue for novice, grey fallback. */
function avatarClass(welderId: string): string {
  if (welderId.includes("expert")) return "bg-[var(--warp-amber)] text-black";
  if (welderId.includes("novice")) return "bg-[var(--warp-blue)] text-white";
  return "bg-zinc-700 text-zinc-300";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit", month: "short", year: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

/** Maps disposition to a Tailwind left-border colour class for unselected rows. */
function dispositionBorderClass(disposition: MockSession["disposition"]): string {
  if (disposition === "PASS")             return "border-l-green-500";
  if (disposition === "CONDITIONAL")      return "border-l-amber-400";
  if (disposition === "REWORK_REQUIRED")  return "border-l-red-500";
  return "border-l-zinc-700";
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-2.5 border-b border-zinc-900 animate-pulse">
          <div className="w-7 h-7 rounded-full bg-zinc-800 shrink-0" />
          <div className="flex-1 space-y-1.5">
            <div className="h-2 bg-zinc-800 rounded w-2/3" />
            <div className="h-1.5 bg-zinc-800 rounded w-1/3" />
          </div>
          <div className="h-2 bg-zinc-800 rounded w-16" />
        </div>
      ))}
    </>
  );
}

const PAGE_SIZE = 10;

export function SessionList({
  onSessionSelect,
  selectedSessionId,
  onAnalyseAll,
  isAnalysing = false,
}: SessionListProps) {
  const [sessions, setSessions] = useState<MockSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  useEffect(() => {
    let cancelled = false;
    fetchMockSessions()
      .then((data) => { if (!cancelled) { setSessions(data); setLoading(false); } })
      .catch((err) => { if (!cancelled) { setError(String(err)); setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  const unanalysedCount = sessions.filter((s) => s.disposition === null).length;
  const visibleSessions = sessions.slice(0, visibleCount);
  const hasMore = visibleCount < sessions.length;

  return (
    <div className="flex flex-col min-h-[400px] h-full bg-[var(--warp-surface)]">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-900 shrink-0">
        <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)]">
          Sessions
        </span>
        <button
          type="button"
          onClick={onAnalyseAll}
          disabled={isAnalysing || unanalysedCount === 0 || !onAnalyseAll}
          className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5
            border border-zinc-800 text-[var(--warp-text-muted)]
            hover:border-amber-400 hover:text-[var(--warp-amber)]
            disabled:opacity-30 disabled:cursor-not-allowed
            transition-colors duration-100"
        >
          {isAnalysing ? "Running…" : `Analyse All (${unanalysedCount})`}
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {loading && <SkeletonRows />}
        {error && (
          <p className="px-3 py-4 font-mono text-[10px] text-[var(--warp-danger)]">
            Error: {error}
          </p>
        )}
        {!loading && !error && visibleSessions.map((session) => {
          const selected = session.session_id === selectedSessionId;
          return (
            <button
              key={session.session_id}
              type="button"
              onClick={() => onSessionSelect(session)}
              aria-pressed={selected}
              className={[
                "w-full text-left flex items-center gap-3 px-3 py-2.5",
                "border-l-2 border-b border-b-zinc-900",
                "transition-colors duration-100",
                selected
                  ? "border-l-amber-400 bg-[var(--warp-surface-2)]"
                  : `${dispositionBorderClass(session.disposition)} hover:bg-[var(--warp-surface-2)]`,
              ].join(" ")}
            >
              {/* Welder avatar — colour coded by archetype */}
              <span className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center font-mono text-[9px] font-bold uppercase ${avatarClass(session.welder_id)}`}>
                {initials(session.welder_name)}
              </span>

              {/* Welder name + session ID + arc type tag */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="font-mono text-[10px] text-[var(--warp-text)] truncate">
                    {session.welder_name}
                  </span>
                  <span className="shrink-0 font-mono text-[8px] uppercase tracking-widest border border-zinc-800 px-1 text-[var(--warp-text-dim)]">
                    {session.arc_type.replaceAll("_", " ")}
                  </span>
                </div>
                <span className="font-mono text-[9px] text-[var(--warp-text-muted)]">
                  {session.session_id} · {formatDate(session.started_at)}
                </span>
              </div>

              {/* Disposition status */}
              <div className="shrink-0">
                <StatusBadge disposition={session.disposition} />
              </div>
            </button>
          );
        })}
        {!loading && !error && hasMore && (
          <button
            type="button"
            onClick={() => setVisibleCount((n) => n + PAGE_SIZE)}
            className="w-full px-3 py-2 font-mono text-[9px] uppercase tracking-widest
              text-[var(--warp-text-muted)] hover:text-[var(--warp-amber)]
              border-t border-zinc-900 transition-colors duration-100"
          >
            Load more ({sessions.length - visibleCount} remaining)
          </button>
        )}
      </div>
    </div>
  );
}
