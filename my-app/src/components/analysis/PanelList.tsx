"use client";
/**
 * PanelList — panel-centric sidebar for the Analysis page.
 *
 * Replaces SessionList as the primary navigation in the analysis sidebar.
 * Panels group multiple welder sessions onto a single physical work piece.
 * Each panel entry shows which welder(s) worked on it; expanding the panel
 * reveals its individual weld sessions.
 *
 * Data flow: page.tsx fetches sessions → derives WeldPanel[] via
 * groupSessionsByPanel() → passes panels as a prop here. PanelList does
 * NOT fetch data itself — it is a pure presentation component.
 */
import { useState } from "react";
import type { MockSession } from "@/types/warp-analysis";
import type { WeldPanel } from "@/lib/panel-mapping";
import { StatusBadge } from "./StatusBadge";

export interface PanelListProps {
  panels: WeldPanel[];
  selectedPanelId: string | null;
  selectedSessionId: string | null;
  onPanelSelect: (panel: WeldPanel) => void;
  onSessionSelect: (session: MockSession) => void;
  isAnalysing: boolean;
  onAnalyseAll?: () => void;
  loading: boolean;
}

/** Tailwind left-border colour driven by panel-level worst-case disposition. */
function panelBorderClass(disposition: WeldPanel["panel_disposition"]): string {
  if (disposition === "PASS")            return "border-l-green-500";
  if (disposition === "CONDITIONAL")     return "border-l-amber-400";
  if (disposition === "REWORK_REQUIRED") return "border-l-red-500";
  return "border-l-zinc-700";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit", month: "short",
    hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-3 border-b border-zinc-900 animate-pulse">
          <div className="flex-1 space-y-1.5">
            <div className="h-2 bg-zinc-800 rounded w-3/4" />
            <div className="h-1.5 bg-zinc-800 rounded w-1/2" />
          </div>
          <div className="h-2 bg-zinc-800 rounded w-10" />
        </div>
      ))}
    </>
  );
}

export function PanelList({
  panels,
  selectedPanelId,
  selectedSessionId,
  onPanelSelect,
  onSessionSelect,
  isAnalysing,
  onAnalyseAll,
  loading,
}: PanelListProps) {
  // Track which panels are expanded locally — the selected panel is always expanded.
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const unanalysedCount = panels.reduce(
    (sum, p) => sum + p.sessions.filter((s) => s.disposition === null).length,
    0,
  );

  function togglePanel(panel: WeldPanel) {
    let isExpanding = false;
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(panel.panel_id)) {
        // Keep selected panel always open
        if (panel.panel_id !== selectedPanelId) next.delete(panel.panel_id);
      } else {
        next.add(panel.panel_id);
        isExpanding = true;
      }
      return next;
    });
    // Only fire onPanelSelect when expanding — collapsing an already-selected
    // panel must not restart the analysis stream.
    if (isExpanding || panel.panel_id !== selectedPanelId) {
      onPanelSelect(panel);
    }
  }

  const isExpanded = (panelId: string) =>
    panelId === selectedPanelId || expandedIds.has(panelId);

  return (
    <div className="flex flex-col min-h-[400px] h-full bg-[var(--warp-surface)]">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-900 shrink-0">
        <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--warp-text-muted)]">
          Panels
        </span>
        <button
          type="button"
          onClick={() => onAnalyseAll?.()}
          disabled={isAnalysing || unanalysedCount === 0 || !onAnalyseAll}
          className="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-zinc-800 text-[var(--warp-text-muted)] hover:border-amber-400 hover:text-[var(--warp-amber)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors duration-100"
        >
          {isAnalysing ? "Running…" : `Analyse All (${unanalysedCount})`}
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto border-t border-zinc-900">
        {loading && <SkeletonRows />}

        {!loading && panels.length === 0 && (
          <p className="px-3 py-4 font-mono text-[10px] text-[var(--warp-text-dim)]">
            No sessions available.
          </p>
        )}

        {!loading && panels.map((panel) => {
          const expanded = isExpanded(panel.panel_id);
          const isSelected = panel.panel_id === selectedPanelId;

          return (
            <div key={panel.panel_id}>
              {/* Panel header row */}
              <button
                type="button"
                onClick={() => togglePanel(panel)}
                aria-expanded={expanded}
                className={[
                  "w-full text-left flex items-start gap-2 px-3 py-2.5",
                  "border-l-2 border-b border-b-zinc-900",
                  "transition-colors duration-100",
                  isSelected
                    ? "border-l-amber-400 bg-[var(--warp-surface-2)]"
                    : `${panelBorderClass(panel.panel_disposition)} hover:bg-[var(--warp-surface-2)]`,
                ].join(" ")}
              >
                <div className="flex-1 min-w-0">
                  {/* Panel name */}
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="font-mono text-[10px] font-semibold text-[var(--warp-text)] truncate">
                      {panel.panel_name}
                    </span>
                    {/* Expand/collapse indicator */}
                    <span className="shrink-0 font-mono text-[8px] text-[var(--warp-text-dim)]">
                      {expanded ? "▾" : "▸"}
                    </span>
                  </div>
                  {/* Welder attribution */}
                  <span className="font-mono text-[9px] text-[var(--warp-text-muted)] truncate block">
                    {panel.welder_names.join(", ")}
                  </span>
                  {/* Session count */}
                  <span className="font-mono text-[8px] text-zinc-600">
                    {panel.sessions.length} session{panel.sessions.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="shrink-0 mt-0.5">
                  <StatusBadge disposition={panel.panel_disposition} />
                </div>
              </button>

              {/* Expanded session rows */}
              {expanded && (
                <div className="bg-[var(--warp-bg)]">
                  {panel.sessions.map((session) => {
                    const sessionSelected = session.session_id === selectedSessionId;
                    return (
                      <button
                        key={session.session_id}
                        type="button"
                        onClick={() => onSessionSelect(session)}
                        aria-pressed={sessionSelected}
                        className={[
                          "w-full text-left flex items-center gap-2 pl-6 pr-3 py-2",
                          "border-l-2 border-b border-b-zinc-900/60",
                          "transition-colors duration-100",
                          sessionSelected
                            ? "border-l-amber-400 bg-[var(--warp-surface-2)]"
                            : "border-l-zinc-800 hover:bg-[var(--warp-surface)]",
                        ].join(" ")}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <span className="font-mono text-[9px] text-[var(--warp-text)] truncate">
                              {formatDate(session.started_at)}
                            </span>
                            <span className="shrink-0 font-mono text-[7px] uppercase tracking-widest border border-zinc-800 px-1 text-[var(--warp-text-dim)]">
                              {session.arc_type.replaceAll("_", " ")}
                            </span>
                          </div>
                          <span className="font-mono text-[8px] text-zinc-600">
                            {session.welder_name}
                          </span>
                        </div>
                        <div className="shrink-0">
                          <StatusBadge disposition={session.disposition} />
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
