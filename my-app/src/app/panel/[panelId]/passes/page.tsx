"use client";

/**
 * Panel Passes Page — loads all weld-pass sessions for a panel.
 *
 * Fetches sess_PANEL-X_001 through sess_PANEL-X_00N in parallel via Promise.allSettled.
 * Individual 404s are logged and skipped; alertOnReplayFailure only when ALL sessions fail.
 * Layout: top bar, 70% canvas placeholder, 30% defect panel placeholder.
 */

import { Suspense, use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { fetchSession } from "@/lib/api";
import { alertOnReplayFailure, logWarn } from "@/lib/logger";
import { PANELS, getSessionIdsForPanel } from "@/data/panels";
import type { Panel } from "@/types/panel";
import type { Session } from "@/types/session";

// ---------------------------------------------------------------------------
// Structure: PanelPassesPage → PanelPassesPageWithParams → PanelPassesPageInner
// Same pattern as replay page (ReplayPage → ReplayPageWithAsyncParams → ReplayPageInner).
// PanelPassesPage = Suspense boundary; PanelPassesPageWithParams = use(params); PanelPassesPageInner = state + layout.
// ---------------------------------------------------------------------------

export default function PanelPassesPage({
  params,
}: {
  params: Promise<{ panelId: string }>;
}) {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
          <div className="text-sm text-zinc-500">Loading...</div>
        </div>
      }
    >
      <PanelPassesPageWithParams params={params} />
    </Suspense>
  );
}

function PanelPassesPageWithParams({
  params,
}: {
  params: Promise<{ panelId: string }>;
}) {
  const { panelId } = use(params);
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
          <div className="text-sm text-zinc-500">Loading...</div>
        </div>
      }
    >
      <PanelPassesPageInner panelId={panelId} />
    </Suspense>
  );
}

function PanelPassesPageInner({ panelId }: { panelId: string }) {
  const [panel, setPanel] = useState<Panel | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const found = PANELS.find((p) => p.id === panelId);
    if (!found) {
      setError(`Panel ${panelId} not found`);
      setLoading(false);
      return;
    }
    setPanel(found);

    const sessionIds = getSessionIdsForPanel(found);

    Promise.allSettled(
      sessionIds.map((id) =>
        fetchSession(id, {
          limit: 2000,
          include_thermal: true,
        })
      )
    ).then((results) => {
      if (!mounted) return;

      const sessionsList: Session[] = [];
      let firstError: unknown = null;

      results.forEach((result, i) => {
        if (result.status === "fulfilled") {
          sessionsList.push(result.value);
        } else {
          if (!firstError) firstError = result.reason;
          logWarn("panel_passes", `Session ${sessionIds[i]} failed`, {
            panelId,
            sessionId: sessionIds[i],
            error: String(result.reason),
          });
        }
      });

      if (sessionsList.length === 0) {
        alertOnReplayFailure(
          `panel_passes_${panelId}`,
          firstError ?? new Error("No sessions to load"),
          { source: "panel_passes", panelId }
        );
        setError("No sessions could be loaded");
        setLoading(false);
        return;
      }

      setSessions(sessionsList);
      setLoading(false);
    });

    return () => {
      mounted = false;
    };
  }, [panelId]);

  // Loading state — use replay page pattern (centered text)
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center">
        <div className="text-center">
          <div className="text-lg text-zinc-600 dark:text-zinc-400 mb-2">
            Loading sessions...
          </div>
          <div className="text-sm text-zinc-500 dark:text-zinc-500">
            Fetching weld pass data
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-black flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white dark:bg-zinc-900 rounded-lg border border-violet-200 dark:border-violet-800 p-6">
          <h2 className="text-lg font-semibold text-violet-800 dark:text-violet-400 mb-2">
            {panelId} — Check that session data is seeded for this panel
          </h2>
          <p className="text-sm text-violet-600 dark:text-violet-500 mb-4">
            {error}
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm text-violet-600 dark:text-violet-400 hover:underline"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  // Success — layout shell
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black">
      {/* Top bar */}
      <div
        className="border-b px-6 py-4 flex items-center justify-between gap-4"
        style={{ borderColor: "rgba(255,255,255,0.08)" }}
      >
        <Link
          href="/dashboard"
          className="flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Dashboard
        </Link>
        <div className="flex-1 text-center">
          <h1 className="text-lg font-semibold text-zinc-100">
            {panel?.id ?? panelId} — {panel?.label ?? "…"}
          </h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            {sessions.length} weld pass{sessions.length !== 1 ? "es" : ""} loaded
          </p>
        </div>
        <div className="w-20" aria-hidden />
      </div>

      {/* 70/30 grid */}
      <div className="grid grid-cols-[70%_30%] min-h-[calc(100vh-73px)]">
        {/* Left — canvas placeholder */}
        <div
          className="flex flex-col items-center justify-center p-8 border-r"
          style={{
            background: "rgba(0,0,0,0.3)",
            borderColor: "rgba(255,255,255,0.08)",
          }}
        >
          <p className="text-zinc-500 text-sm font-mono">
            3D Panel View — {sessions.length} weld pass
            {sessions.length !== 1 ? "es" : ""} loaded
          </p>
        </div>

        {/* Right — defect panel placeholder */}
        <div
          className="flex flex-col items-center justify-center p-8"
          style={{ background: "rgba(0,0,0,0.2)" }}
        >
          <p className="text-zinc-500 text-sm font-mono">Defect Detail Panel</p>
        </div>
      </div>
    </div>
  );
}
