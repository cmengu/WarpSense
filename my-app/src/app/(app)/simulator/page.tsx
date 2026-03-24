"use client";

import { useRef, useState } from "react";
import { simulateWeld, getClosestMatch } from "@/lib/warp-api";
import type { SimulatorResult, ClosestMatchResult } from "@/types/warp-analysis";

const COST_COLOR: Record<number, string> = {
  0: "text-green-400",
  1800: "text-amber-400",
  4200: "text-red-400",
};

function costColor(cost: number): string {
  return COST_COLOR[cost] ?? "text-red-400";
}

export default function SimulatorPage() {
  const [heatInput, setHeatInput] = useState(5500);
  const [angleDeviation, setAngleDeviation] = useState(3);
  const [arcStability, setArcStability] = useState(0.92);
  const [result, setResult] = useState<SimulatorResult | null>(null);
  const [matchResult, setMatchResult] = useState<ClosestMatchResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function runSimulation(hi: number, ad: number, ar: number) {
    setIsLoading(true);
    setError(null);
    setMatchResult(null);
    try {
      const res = await simulateWeld({
        heat_input_level: hi,
        torch_angle_deviation: ad,
        arc_stability: ar,
      });
      setResult(res);
      try {
        const match = await getClosestMatch(hi, ad, ar);
        setMatchResult(match);
      } catch {
        /* match card optional */
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setIsLoading(false);
    }
  }

  function scheduleDebounce(hi: number, ad: number, ar: number) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulation(hi, ad, ar), 300);
  }

  function handleHeatInput(v: number) {
    setHeatInput(v);
    scheduleDebounce(v, angleDeviation, arcStability);
  }
  function handleAngle(v: number) {
    setAngleDeviation(v);
    scheduleDebounce(heatInput, v, arcStability);
  }
  function handleArc(v: number) {
    setArcStability(v);
    scheduleDebounce(heatInput, angleDeviation, v);
  }

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-1 font-mono tracking-tight">
        Weld Simulator
      </h1>
      <p className="text-zinc-400 text-sm mb-8">
        Adjust welding parameters to see real-time defect prediction.
      </p>

      <div className="space-y-6 mb-8">
        <div>
          <div className="flex justify-between text-xs font-mono text-zinc-400 mb-1">
            <span>Heat Input (J/frame)</span>
            <span className="text-zinc-200">{heatInput.toLocaleString()}</span>
          </div>
          <input
            type="range"
            min={2000}
            max={8000}
            step={100}
            value={heatInput}
            onChange={(e) => handleHeatInput(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-[10px] text-zinc-600 mt-0.5">
            <span>2,000 (cold — LOF risk)</span>
            <span>8,000 (hot — good fusion)</span>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs font-mono text-zinc-400 mb-1">
            <span>Torch Angle Deviation (°)</span>
            <span className="text-zinc-200">{angleDeviation.toFixed(1)}°</span>
          </div>
          <input
            type="range"
            min={0}
            max={30}
            step={0.5}
            value={angleDeviation}
            onChange={(e) => handleAngle(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-[10px] text-zinc-600 mt-0.5">
            <span>0° (optimal 55°)</span>
            <span>30° (extreme drift — LOF)</span>
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs font-mono text-zinc-400 mb-1">
            <span>Arc Stability (arc-on ratio)</span>
            <span className="text-zinc-200">{arcStability.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min={0.40}
            max={1.00}
            step={0.01}
            value={arcStability}
            onChange={(e) => handleArc(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-[10px] text-zinc-600 mt-0.5">
            <span>0.40 (many gaps — LOF)</span>
            <span>1.00 (continuous arc)</span>
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={() => runSimulation(heatInput, angleDeviation, arcStability)}
        disabled={isLoading}
        className="w-full py-3 px-6 bg-blue-600 hover:bg-blue-500 disabled:opacity-50
                   text-white font-mono text-sm rounded-lg transition-colors mb-6"
      >
        {isLoading ? "Simulating…" : "Simulate Weld"}
      </button>

      {error && (
        <div className="p-4 bg-red-950 border border-red-800 rounded-lg text-red-300 text-sm mb-6">
          {error}
        </div>
      )}

      {result && !isLoading && (
        <div className="border border-zinc-800 rounded-xl bg-zinc-900 p-6 space-y-4">
          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
              Defect Classification
            </p>
            <p
              className={`text-2xl font-bold font-mono ${
                result.quality_class === "GOOD"
                  ? "text-green-400"
                  : result.quality_class === "MARGINAL"
                    ? "text-amber-400"
                    : "text-red-400"
              }`}
            >
              {result.defect_type}
            </p>
          </div>

          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
              Model Confidence
            </p>
            <div className="w-full bg-zinc-800 rounded-full h-2">
              <div
                className="bg-amber-400 h-2 rounded-full transition-all duration-300"
                style={{ width: `${Math.round(result.confidence * 100)}%` }}
              />
            </div>
            <p className="text-xs text-zinc-400 mt-1 font-mono">
              {Math.round(result.confidence * 100)}%
            </p>
          </div>

          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
              Estimated Rework Cost
            </p>
            <p className={`text-5xl font-bold font-mono tabular-nums ${costColor(result.rework_cost_usd)}`}>
              ${result.rework_cost_usd.toLocaleString("en-US")}
            </p>
            {result.rework_cost_usd === 0 && (
              <p className="text-xs text-green-600 mt-1 font-mono">No rework required</p>
            )}
          </div>

          <div>
            <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-1">
              Top Risk Factor
            </p>
            <p className="text-sm font-mono text-zinc-300">
              {result.top_driver.replace(/_/g, " ")}
            </p>
          </div>
        </div>
      )}

      {matchResult && !isLoading && (
        <div className="mt-4 border border-zinc-700 rounded-xl bg-zinc-900/60 p-5">
          <p className="font-mono text-[9px] uppercase tracking-widest text-zinc-500 mb-3">
            Closest Real Weld — from library of 100 aluminium sessions
          </p>

          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="font-mono text-xs text-zinc-400">Session ID</p>
              <p className="font-mono text-sm text-zinc-200 mt-0.5">{matchResult.session_id}</p>
            </div>
            <span
              className={`px-2 py-1 rounded text-xs font-mono font-semibold ${
                matchResult.quality_class === "GOOD"
                  ? "bg-green-900/60 text-green-300"
                  : matchResult.quality_class === "MARGINAL"
                    ? "bg-amber-900/60 text-amber-300"
                    : "bg-red-900/60 text-red-300"
              }`}
            >
              {matchResult.quality_class}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4 text-center">
            <div className="bg-zinc-800/60 rounded-lg p-2">
              <p className="font-mono text-[9px] text-zinc-500 uppercase mb-1">Heat Input</p>
              <p className="font-mono text-xs text-zinc-200">{Math.round(matchResult.matched_heat_input).toLocaleString()}</p>
              <p className="font-mono text-[9px] text-zinc-600">vs {heatInput.toLocaleString()}</p>
            </div>
            <div className="bg-zinc-800/60 rounded-lg p-2">
              <p className="font-mono text-[9px] text-zinc-500 uppercase mb-1">Angle Dev</p>
              <p className="font-mono text-xs text-zinc-200">{matchResult.matched_angle_deviation.toFixed(1)}°</p>
              <p className="font-mono text-[9px] text-zinc-600">vs {angleDeviation.toFixed(1)}°</p>
            </div>
            <div className="bg-zinc-800/60 rounded-lg p-2">
              <p className="font-mono text-[9px] text-zinc-500 uppercase mb-1">Arc Ratio</p>
              <p className="font-mono text-xs text-zinc-200">{matchResult.matched_arc_ratio.toFixed(2)}</p>
              <p className="font-mono text-[9px] text-zinc-600">vs {arcStability.toFixed(2)}</p>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-mono text-[9px] text-zinc-500 uppercase mb-0.5">Matched Rework Cost</p>
              <p
                className={`font-mono text-2xl font-bold tabular-nums ${
                  matchResult.rework_cost_usd === 0
                    ? "text-green-400"
                    : matchResult.rework_cost_usd <= 1800
                      ? "text-amber-400"
                      : "text-red-400"
                }`}
              >
                ${matchResult.rework_cost_usd.toLocaleString("en-US")}
              </p>
            </div>
            <a
              href={`/compare/${matchResult.session_id}/sess_expert_aluminium_001_001`}
              className="px-3 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-xs font-mono rounded-lg transition-colors"
            >
              View 3D comparison →
            </a>
          </div>
        </div>
      )}
    </main>
  );
}
