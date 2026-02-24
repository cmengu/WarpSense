"use client";

import React, { useEffect, useState } from "react";
import type { CoachingPlan, CoachingAssignment } from "@/types/coaching";
import { METRIC_LABELS, type WelderID } from "@/types/shared";
import {
  fetchCoachingPlan,
  triggerCoachingAssignment,
} from "@/lib/api";
import { logError } from "@/lib/logger";

interface CoachingPlanPanelProps {
  welderId: WelderID;
}

function AssignmentCard({ a }: { a: CoachingAssignment }) {
  const pct =
    a.current_metric_value !== null
      ? Math.min(
          100,
          (a.current_metric_value / a.drill.success_threshold) * 100
        )
      : null;

  const statusColor = {
    active: "text-cyan-400 border-cyan-500/30 bg-cyan-500/5",
    complete: "text-green-400 border-green-500/30 bg-green-500/5",
    overdue: "text-red-400 border-red-500/30 bg-red-500/5",
  }[a.status];

  return (
    <div className={`rounded-lg border p-4 ${statusColor}`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-sm font-semibold text-white">{a.drill.title}</p>
          <p className="text-xs text-neutral-500 mt-0.5">
            {METRIC_LABELS[a.drill.target_metric]} ·{" "}
            {a.sessions_completed}/{a.drill.sessions_required} sessions
          </p>
        </div>
        <span
          className={`text-xs font-semibold uppercase px-2 py-0.5 rounded ${statusColor}`}
        >
          {a.status}
        </span>
      </div>
      <p className="text-xs text-neutral-400 leading-relaxed mb-3">
        {a.drill.description}
      </p>
      {pct !== null && (
        <div>
          <div className="flex justify-between text-xs text-neutral-500 mb-1">
            <span>
              Progress to target ({Math.round(a.drill.success_threshold)})
            </span>
            <span>{Math.round(pct)}%</span>
          </div>
          <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-cyan-500 rounded-full transition-all"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}
      {a.status === "complete" && (
        <p className="text-xs text-green-400 mt-2">
          ✓ Drill complete ·{" "}
          {a.completed_at
            ? new Date(a.completed_at).toLocaleDateString()
            : ""}
        </p>
      )}
    </div>
  );
}

export function CoachingPlanPanel({ welderId }: CoachingPlanPanelProps) {
  const [plan, setPlan] = useState<CoachingPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [assigning, setAssigning] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchCoachingPlan(welderId)
      .then((p) => {
        if (mounted) {
          setPlan(p);
          setAssignError(null);
          setLoading(false);
        }
      })
      .catch((err) => {
        logError("CoachingPlanPanel", err);
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [welderId]);

  const handleAssign = async () => {
    setAssignError(null);
    setAssigning(true);
    try {
      setPlan(await triggerCoachingAssignment(welderId));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      logError("CoachingPlanPanel.handleAssign", err);
      setAssignError(msg);
    } finally {
      setAssigning(false);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
          Coaching Plan
        </h2>
        {!loading && (
          <button
            onClick={handleAssign}
            disabled={assigning}
            className="text-xs text-cyan-400 hover:text-cyan-300 underline disabled:text-neutral-600"
          >
            {assigning ? "Assigning…" : "Assign Drills"}
          </button>
        )}
      </div>
      {loading && (
        <div className="h-24 bg-neutral-800 rounded animate-pulse" />
      )}
      {!loading && plan && (
        <>
          {assignError && (
            <p className="text-sm text-red-400 mb-3" role="alert">
              {assignError}
            </p>
          )}
          {plan.auto_assigned && (
            <div className="text-xs text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 rounded px-3 py-2 mb-3">
              New drills assigned based on your latest benchmarks.
            </div>
          )}
          {plan.active_assignments.length === 0 ? (
            <p className="text-sm text-neutral-500 text-center py-4">
              No active drills. Click &quot;Assign Drills&quot; to get
              recommendations.
            </p>
          ) : (
            <div className="space-y-3">
              {plan.active_assignments.map((a) => (
                <AssignmentCard key={a.id} a={a} />
              ))}
            </div>
          )}
          {plan.completed_assignments.length > 0 && (
            <details className="mt-4">
              <summary className="text-xs text-neutral-600 cursor-pointer hover:text-neutral-400">
                {plan.completed_assignments.length} completed drill(s)
              </summary>
              <div className="space-y-2 mt-2">
                {plan.completed_assignments.map((a) => (
                  <AssignmentCard key={a.id} a={a} />
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  );
}

export default CoachingPlanPanel;
