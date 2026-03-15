"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useSessionList } from "@/hooks/useSessionList";
import type { SessionSummary } from "@/lib/api";

interface QuickPick {
  label: string;
  sessA: string;
  sessB: string;
}

/** Quick picks — IDs must exist in seeded DB (WELDER_ARCHETYPES). */
const QUICK_PICKS: QuickPick[] = [
  {
    label: "Expert vs Novice",
    sessA: "sess_expert_aluminium_001_001",
    sessB: "sess_novice_aluminium_001_001",
  },
  {
    label: "Mike vs Sara",
    sessA: "sess_mike-chen_005",
    sessB: "sess_sara-okafor_005",
  },
];

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "2-digit",
  });
}

function formatScore(s: number | null): string {
  return s == null ? "—" : s.toFixed(1);
}

function scoreColor(s: number | null): string {
  if (s == null) return "text-zinc-500";
  if (s >= 80) return "text-emerald-400";
  if (s >= 60) return "text-amber-400";
  return "text-red-400";
}

function shortLabel(id: string): string {
  const parts = id.replace(/^sess_/, "").split("_");
  if (parts.length >= 2) {
    const last = parts[parts.length - 1];
    const num = parseInt(last, 10);
    const body = parts.slice(0, -1).join("-");
    return isNaN(num) ? id : `${body} #${num}`;
  }
  return id;
}

interface SessionCardProps {
  session: SessionSummary;
  selected: boolean;
  onSelect: (id: string) => void;
  otherSelected: string | null;
}

function SessionCard({
  session,
  selected,
  onSelect,
  otherSelected,
}: SessionCardProps) {
  const isDisabled = session.session_id === otherSelected;
  return (
    <button
      type="button"
      onClick={() => !isDisabled && onSelect(session.session_id)}
      disabled={isDisabled}
      aria-pressed={selected}
      className={[
        "w-full text-left px-3 py-2.5 border transition-all duration-100 rounded-sm font-mono text-xs",
        selected
          ? "border-amber-400 bg-amber-400/10 text-amber-300"
          : isDisabled
            ? "border-zinc-800 bg-zinc-900/40 text-zinc-700 cursor-not-allowed"
            : "border-zinc-700 bg-zinc-900 text-zinc-300 hover:border-zinc-500 hover:bg-zinc-800 cursor-pointer",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="truncate font-semibold tracking-tight text-[11px]">
            {shortLabel(session.session_id)}
          </span>
          <span className="text-zinc-500 text-[10px] truncate">
            {session.operator_id ?? "unknown operator"}
          </span>
        </div>
        <div className="flex flex-col items-end gap-0.5 shrink-0">
          <span
            className={`font-bold text-[11px] tabular-nums ${scoreColor(session.score_total)}`}
          >
            {formatScore(session.score_total)}
          </span>
          <span className="text-zinc-600 text-[10px] tabular-nums">
            {formatDate(session.start_time)}
          </span>
        </div>
      </div>
      {session.weld_type && (
        <span className="mt-1 inline-block text-[9px] uppercase tracking-widest text-zinc-600 border border-zinc-800 px-1">
          {session.weld_type}
        </span>
      )}
    </button>
  );
}

interface ColumnPickerProps {
  label: "A" | "B";
  sessions: SessionSummary[];
  selected: string | null;
  otherSelected: string | null;
  onSelect: (id: string) => void;
}

function ColumnPicker({
  label,
  sessions,
  selected,
  otherSelected,
  onSelect,
}: ColumnPickerProps) {
  const [search, setSearch] = useState("");
  const [weldFilter, setWeldFilter] = useState("all");

  const weldTypes = useMemo(() => {
    const types = Array.from(
      new Set(sessions.map((s) => s.weld_type).filter(Boolean))
    );
    return (types as string[]).sort();
  }, [sessions]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return sessions.filter((s) => {
      const matchSearch =
        !q ||
        s.session_id.toLowerCase().includes(q) ||
        (s.operator_id ?? "").toLowerCase().includes(q);
      const matchWeld = weldFilter === "all" || s.weld_type === weldFilter;
      return matchSearch && matchWeld;
    });
  }, [sessions, search, weldFilter]);

  return (
    <div className="flex flex-col min-h-0">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-zinc-500">
          Session
        </span>
        <span
          className={`text-xs font-bold font-mono px-1.5 py-0.5 border ${
            label === "A"
              ? "border-sky-500/60 text-sky-400 bg-sky-500/10"
              : "border-violet-500/60 text-violet-400 bg-violet-500/10"
          }`}
        >
          {label}
        </span>
        {selected && (
          <span className="ml-auto text-[10px] text-zinc-600 font-mono truncate max-w-[120px]">
            {shortLabel(selected)}
          </span>
        )}
      </div>
      <div className="flex gap-1.5 mb-2">
        <input
          type="text"
          placeholder="search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-0 bg-zinc-900 border border-zinc-700 text-zinc-300 placeholder-zinc-600 text-[11px] font-mono px-2 py-1.5 rounded-sm focus:outline-none focus:border-zinc-500"
        />
        {weldTypes.length > 0 && (
          <select
            value={weldFilter}
            onChange={(e) => setWeldFilter(e.target.value)}
            className="bg-zinc-900 border border-zinc-700 text-zinc-400 text-[11px] font-mono px-1.5 py-1.5 rounded-sm focus:outline-none focus:border-zinc-500 shrink-0"
          >
            <option value="all">all types</option>
            {weldTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        )}
      </div>
      <div className="flex flex-col gap-1 overflow-y-auto min-h-0 flex-1 pr-0.5">
        {filtered.length === 0 && (
          <p className="text-zinc-600 text-[11px] font-mono text-center py-6">
            no sessions found
          </p>
        )}
        {filtered.map((s) => (
          <SessionCard
            key={s.session_id}
            session={s}
            selected={selected === s.session_id}
            otherSelected={otherSelected}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}

export interface SessionBrowserPanelProps {
  navigateTo?: "demo" | "compare";
  initialA?: string;
  initialB?: string;
  onCompare?: (sessA: string, sessB: string) => void;
}

export function SessionBrowserPanel({
  navigateTo = "demo",
  initialA,
  initialB,
  onCompare,
}: SessionBrowserPanelProps) {
  const router = useRouter();
  const { sessions, loading, error } = useSessionList();
  const [selectedA, setSelectedA] = useState<string | null>(initialA ?? null);
  const [selectedB, setSelectedB] = useState<string | null>(initialB ?? null);
  const bothSelected = selectedA !== null && selectedB !== null;

  function handleCompare() {
    if (!selectedA || !selectedB) return;
    if (onCompare) {
      onCompare(selectedA, selectedB);
      return;
    }
    router.push(
      navigateTo === "compare"
        ? `/compare/${selectedA}/${selectedB}`
        : `/demo/${selectedA}/${selectedB}`
    );
  }

  return (
    <div
      className="flex flex-col gap-4 bg-zinc-950 border border-zinc-800 rounded-sm p-4"
      style={{ fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace" }}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] uppercase tracking-[0.25em] text-zinc-600">
            WeldView
          </p>
          <h2 className="text-sm font-bold text-zinc-200 tracking-tight">
            Session Comparison
          </h2>
        </div>
        <span className="text-[9px] uppercase tracking-widest text-zinc-700 border border-zinc-800 px-2 py-1">
          {loading ? "loading…" : `${sessions.length} sessions`}
        </span>
      </div>

      <div>
        <p className="text-[9px] uppercase tracking-[0.2em] text-zinc-600 mb-1.5">
          Quick picks
        </p>
        <div className="flex flex-wrap gap-1.5">
          {QUICK_PICKS.map((pick) => (
            <button
              key={pick.label}
              type="button"
              onClick={() => {
                setSelectedA(pick.sessA);
                setSelectedB(pick.sessB);
              }}
              className="text-[10px] font-mono px-2 py-1 border border-zinc-700 text-zinc-400 hover:border-amber-400/50 hover:text-amber-300 hover:bg-amber-400/5 transition-colors rounded-sm"
            >
              {pick.label}
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-zinc-800" />

      {error && (
        <div className="text-red-400 text-xs font-mono border border-red-900/50 bg-red-950/30 px-3 py-2 rounded-sm">
          ⚠ {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12 text-zinc-600 text-xs font-mono tracking-widest">
          <span className="animate-pulse">scanning sessions…</span>
        </div>
      ) : (
        <div
          className="grid grid-cols-2 gap-4"
          style={{ minHeight: "320px", maxHeight: "420px" }}
        >
          <ColumnPicker
            label="A"
            sessions={sessions}
            selected={selectedA}
            otherSelected={selectedB}
            onSelect={setSelectedA}
          />
          <ColumnPicker
            label="B"
            sessions={sessions}
            selected={selectedB}
            otherSelected={selectedA}
            onSelect={setSelectedB}
          />
        </div>
      )}

      <div className="flex items-center gap-3 pt-1">
        <button
          type="button"
          onClick={handleCompare}
          disabled={!bothSelected}
          aria-disabled={!bothSelected}
          className={[
            "flex-1 py-2.5 text-xs font-mono font-bold uppercase tracking-[0.15em] border transition-all duration-150",
            bothSelected
              ? "border-amber-400 text-amber-300 bg-amber-400/10 hover:bg-amber-400/20 cursor-pointer"
              : "border-zinc-800 text-zinc-700 cursor-not-allowed",
          ].join(" ")}
        >
          {bothSelected ? "▶ Compare sessions" : "Select two sessions"}
        </button>
        {bothSelected && (
          <button
            type="button"
            onClick={() => {
              setSelectedA(null);
              setSelectedB(null);
            }}
            className="text-[10px] font-mono text-zinc-600 hover:text-zinc-400 underline underline-offset-2 transition-colors"
          >
            clear
          </button>
        )}
      </div>

      {bothSelected && (
        <p className="text-[10px] text-zinc-600 font-mono mt-1">
          ℹ Delta charts require overlapping timestamps. All seeded sessions
          share a 15 s / 10 ms window.
        </p>
      )}
    </div>
  );
}

export default SessionBrowserPanel;
