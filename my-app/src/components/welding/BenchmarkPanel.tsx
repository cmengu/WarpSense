"use client";

import React from "react";
import type { WelderBenchmarks, MetricBenchmark } from "@/types/benchmark";

interface BenchmarkPanelProps {
  benchmarks: WelderBenchmarks;
}

const TIER_COLORS = {
  top: {
    bar: "bg-green-500",
    text: "text-green-400",
    badge: "bg-green-500/10 text-green-400 border-green-500/30",
  },
  mid: {
    bar: "bg-amber-500",
    text: "text-amber-400",
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
  bottom: {
    bar: "bg-red-500",
    text: "text-red-400",
    badge: "bg-red-500/10 text-red-400 border-red-500/30",
  },
};

function GaugeRow({ m }: { m: MetricBenchmark }) {
  const colors = TIER_COLORS[m.tier];
  const range = m.population_max - m.population_min;
  const pct = range > 0 ? ((m.welder_value - m.population_min) / range) * 100 : 50;
  const meanPct =
    range > 0 ? ((m.population_mean - m.population_min) / range) * 100 : 50;

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-neutral-400">{m.label}</span>
        <div className="flex items-center gap-2">
          <span className={`text-lg font-bold tabular-nums ${colors.text}`}>
            {Math.round(m.welder_value)}
          </span>
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded border ${colors.badge}`}
          >
            {Math.round(m.percentile)}th%
          </span>
        </div>
      </div>
      <div className="relative h-2 bg-neutral-800 rounded-full">
        <div
          className="absolute top-1/2 -translate-y-1/2 w-0.5 h-4 bg-neutral-600"
          style={{ left: `${meanPct}%` }}
          title={`Population mean: ${Math.round(m.population_mean)}`}
        />
        <div
          className={`absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full
                      border-2 border-neutral-950 ${colors.bar}`}
          style={{ left: `${pct}%`, transform: "translate(-50%, -50%)" }}
        />
      </div>
      <div className="flex justify-between text-xs text-neutral-600 mt-1">
        <span>{Math.round(m.population_min)}</span>
        <span className="text-neutral-500">
          avg {Math.round(m.population_mean)}
        </span>
        <span>{Math.round(m.population_max)}</span>
      </div>
    </div>
  );
}

/**
 * BenchmarkPanel — displays per-metric percentile gauges for a welder vs population.
 * Requires at least 2 welders in the system.
 */
export function BenchmarkPanel({ benchmarks }: BenchmarkPanelProps) {
  if (benchmarks.population_size < 2) {
    return (
      <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6
                      text-sm text-neutral-500 text-center">
        Benchmarking requires at least 2 welders in the system.
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 p-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
          Benchmark Comparison
        </h2>
        <span className="text-xs text-neutral-600">
          vs {benchmarks.population_size} welders ·{" "}
          {Math.round(benchmarks.overall_percentile)}th percentile overall
        </span>
      </div>
      {benchmarks.metrics.map((m) => (
        <GaugeRow key={m.metric} m={m} />
      ))}
    </div>
  );
}

export default BenchmarkPanel;
