/**
 * panel-mapping.ts — Client-side panel enrichment for WarpSense Analysis.
 *
 * Sessions come from the FastAPI backend (`GET /api/mock-sessions`) and do not
 * carry panel information. This module provides a static mapping from welder_id
 * to panel assignment, allowing the frontend to group sessions into weld panels
 * without requiring backend changes.
 *
 * WHEN TO UPDATE THIS FILE:
 *   - When new welders are added to the backend `WELDER_ARCHETYPES` list
 *     (backend/data/mock_welders.py).
 *   - When the backend starts returning `panel_id` directly on sessions — at
 *     that point this mapping can be replaced with a derived approach.
 *
 * PANEL DESIGN:
 *   Panels represent physical weld panels. Multiple welders can work the same
 *   panel (e.g. a senior welder paired with a trainee). This grouping is what
 *   makes the panel-centric Analysis page meaningful — you can see which welders
 *   touched a given panel and compare their outcomes.
 */

import type { MockSession, WarpDisposition } from "@/types/warp-analysis";

// ---------------------------------------------------------------------------
// WeldPanel — derived (client-side only, never persisted)
// ---------------------------------------------------------------------------

/** A physical weld panel derived by grouping sessions from the same panel_id. */
export interface WeldPanel {
  /** Stable identifier matching WELDER_PANEL_MAP values (e.g. "PANEL-D01"). */
  panel_id: string;
  /** Human-readable name shown in the sidebar (e.g. "Deck Panel D-01"). */
  panel_name: string;
  /** Distinct welder names who have sessions on this panel, for attribution. */
  welder_names: string[];
  /** All sessions belonging to this panel, sorted newest-first. */
  sessions: MockSession[];
  /**
   * Worst-case disposition across all sessions on this panel:
   * REWORK_REQUIRED > CONDITIONAL > PASS > null (any unanalysed session → null).
   */
  panel_disposition: WarpDisposition | null;
}

// ---------------------------------------------------------------------------
// WELDER_PANEL_MAP — static mapping, keyed by welder_id
// ---------------------------------------------------------------------------

/**
 * Maps each `welder_id` (as returned by the backend) to the panel it belongs to.
 * Welders not present here fall back to their own welder_id / welder_name as the
 * panel identifier, so new welders degrade gracefully rather than crashing.
 *
 * Welder IDs sourced from: backend/data/mock_welders.py → WELDER_ARCHETYPES.
 */
const WELDER_PANEL_MAP: Record<string, { panel_id: string; panel_name: string }> = {
  // ── Deck Panel D-01 ── senior expert + fast learner ──────────────────────
  "sara-okafor":  { panel_id: "PANEL-D01", panel_name: "Deck Panel D-01" },
  "mike-chen":    { panel_id: "PANEL-D01", panel_name: "Deck Panel D-01" },

  // ── Deck Panel D-02 ── consistent expert + fast learner ──────────────────
  "priya-nair":   { panel_id: "PANEL-D02", panel_name: "Deck Panel D-02" },
  "derek-kwon":   { panel_id: "PANEL-D02", panel_name: "Deck Panel D-02" },

  // ── Hull Panel H-01 ── plateaued senior + new hire ────────────────────────
  "james-park":   { panel_id: "PANEL-H01", panel_name: "Hull Panel H-01" },
  "tom-bradley":  { panel_id: "PANEL-H01", panel_name: "Hull Panel H-01" },

  // ── Hull Panel H-02 ── declining + volatile ────────────────────────────────
  "lucia-reyes":  { panel_id: "PANEL-H02", panel_name: "Hull Panel H-02" },
  "ana-silva":    { panel_id: "PANEL-H02", panel_name: "Hull Panel H-02" },

  // ── Bulkhead B-01 ── declining + benchmark expert ─────────────────────────
  "marcus-bell":      { panel_id: "PANEL-B01", panel_name: "Bulkhead B-01" },
  "expert-benchmark": { panel_id: "PANEL-B01", panel_name: "Bulkhead B-01" },

  // ── Aft Panel A-01 ── aluminium stitch expert + novice ────────────────────
  "expert_aluminium_001": { panel_id: "PANEL-A01", panel_name: "Aft Panel A-01" },
  "novice_aluminium_001": { panel_id: "PANEL-A01", panel_name: "Aft Panel A-01" },

  // ── Simulator Corpus (parametric) ─────────────────────────────────────────
  // All 100 parametric sessions share one panel — they are corpus data, not
  // production weld sessions, so collapsing them avoids 100 sidebar entries.
  "al_hot_clean_001":  { panel_id: "PANEL-SIM", panel_name: "Simulator Corpus" },
  "al_nominal_001":    { panel_id: "PANEL-SIM", panel_name: "Simulator Corpus" },
  "al_cold_001":       { panel_id: "PANEL-SIM", panel_name: "Simulator Corpus" },
  "al_angled_001":     { panel_id: "PANEL-SIM", panel_name: "Simulator Corpus" },
  "al_defective_001":  { panel_id: "PANEL-SIM", panel_name: "Simulator Corpus" },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** ISO string comparison — newest first. */
function newestFirst(a: MockSession, b: MockSession): number {
  return new Date(b.started_at).getTime() - new Date(a.started_at).getTime();
}

/**
 * Compute the worst-case disposition across a set of sessions.
 * Returns null if any session is still unanalysed (disposition === null),
 * or if the sessions array is empty.
 */
function worstCaseDisposition(sessions: MockSession[]): WarpDisposition | null {
  if (sessions.length === 0) return null;
  if (sessions.some((s) => s.disposition === null)) return null;
  if (sessions.some((s) => s.disposition === "REWORK_REQUIRED")) return "REWORK_REQUIRED";
  if (sessions.some((s) => s.disposition === "CONDITIONAL")) return "CONDITIONAL";
  return "PASS";
}

// ---------------------------------------------------------------------------
// groupSessionsByPanel — main export
// ---------------------------------------------------------------------------

/**
 * Groups a flat list of MockSessions into WeldPanels using WELDER_PANEL_MAP.
 *
 * - Sessions with an unmapped welder_id get a single-session panel keyed by
 *   their own welder_id, so new welders never crash the sidebar.
 * - Panels are sorted alphabetically by panel_id for stable ordering.
 * - Sessions within each panel are sorted newest-first.
 *
 * @param sessions — raw sessions from fetchMockSessions()
 * @returns sorted array of WeldPanel objects
 */
export function groupSessionsByPanel(sessions: MockSession[]): WeldPanel[] {
  // Build a map of panel_id → accumulator
  const map = new Map<
    string,
    { panel_id: string; panel_name: string; sessions: MockSession[]; welderNames: Set<string> }
  >();

  for (const session of sessions) {
    const assignment = WELDER_PANEL_MAP[session.welder_id] ?? {
      panel_id:   session.welder_id,
      panel_name: session.welder_name,
    };

    let entry = map.get(assignment.panel_id);
    if (!entry) {
      entry = {
        panel_id:    assignment.panel_id,
        panel_name:  assignment.panel_name,
        sessions:    [],
        welderNames: new Set(),
      };
      map.set(assignment.panel_id, entry);
    }

    entry.sessions.push(session);
    entry.welderNames.add(session.welder_name);
  }

  // Convert accumulator map → WeldPanel[], sort panels + sessions
  return Array.from(map.values())
    .map((entry) => ({
      panel_id:          entry.panel_id,
      panel_name:        entry.panel_name,
      welder_names:      Array.from(entry.welderNames),
      sessions:          entry.sessions.slice().sort(newestFirst),
      panel_disposition: worstCaseDisposition(entry.sessions),
    }))
    .sort((a, b) => a.panel_id.localeCompare(b.panel_id));
}
