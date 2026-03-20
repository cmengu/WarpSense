"use client";
import type { AgentStage, AgentCardState, WarpDisposition } from "@/types/warp-analysis";

export interface SpecialistCardProps { stage: AgentStage; state: AgentCardState; }

const STAGE_LABEL: Record<AgentStage, string> = {
  thermal_agent:  "Thermal",
  geometry_agent: "Geometry",
  process_agent:  "Process",
};

/** Left border + text colour based on disposition when done. */
function doneStyle(disposition: WarpDisposition | null): string {
  if (disposition === "PASS")             return "border-l-green-500 text-green-400";
  if (disposition === "CONDITIONAL")      return "border-l-amber-400 text-amber-400";
  if (disposition === "REWORK_REQUIRED")  return "border-l-red-500 text-red-400";
  return "border-l-zinc-600 text-zinc-500";
}

export function SpecialistCard({ stage, state }: SpecialistCardProps) {
  const label = STAGE_LABEL[stage];

  if (state.status === "queued") {
    return (
      <div className="border border-zinc-800 border-l-2 border-l-zinc-700 p-3">
        <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-600">{label}</p>
        <p className="font-mono text-[10px] text-zinc-700 mt-1">Queued</p>
      </div>
    );
  }

  if (state.status === "running") {
    return (
      <div className="flex-1 border border-amber-400/30 border-l-2 border-l-amber-400 p-3 [animation:warp-pulse_2s_ease-in-out_infinite]">
        <p className="font-mono text-[9px] uppercase tracking-widest text-amber-400">{label}</p>
        <p className="font-mono text-[10px] text-amber-300 mt-1 animate-pulse">Analysing…</p>
      </div>
    );
  }

  return (
    <div className={`border border-zinc-800 border-l-2 p-3 ${doneStyle(state.disposition)}`}>
      <p className="font-mono text-[9px] uppercase tracking-widest opacity-70">{label}</p>
      <p className="font-mono text-[10px] mt-1">
        {state.disposition?.replaceAll("_", " ") ?? "DONE"}
      </p>
    </div>
  );
}
