You are implementing the Comparative Benchmarking Engine for a welding
analytics platform in Cursor. Complete ALL steps in order.

━━━ STRICT SCOPE RULES ━━━
✅ Create or modify ONLY the files listed under "Files you own"
🚫 Do NOT touch: welders.py, api.ts, welder report page, sessions.py
🚫 Do NOT touch: any coaching or certification files
🚫 Do NOT import from coaching_service anywhere in this agent's files

━━━ FILES YOU OWN (create from scratch) ━━━
- backend/schemas/benchmark.py
- backend/services/benchmark_service.py
- my-app/src/types/benchmark.ts
- my-app/src/components/welding/BenchmarkPanel.tsx
- my-app/src/components/dashboard/RankingsTable.tsx

━━━ STEP 1 — Create backend/schemas/benchmark.py ━━━

from pydantic import BaseModel
from typing import List
from .shared import MetricScore, WeldMetric

class MetricBenchmark(BaseModel):
    metric: WeldMetric
    label: str
    welder_value: float
    population_mean: float
    population_min: float
    population_max: float
    population_std: float
    percentile: float            # 0–100
    tier: str                    # "top" | "mid" | "bottom"

class WelderBenchmarks(BaseModel):
    welder_id: str
    population_size: int
    metrics: List[MetricBenchmark]
    overall_percentile: float

━━━ STEP 2 — Create backend/services/benchmark_service.py ━━━

"""
Benchmark service — computes per-metric percentile rankings.
Population: all welders' MOST RECENT complete session with a score.

IMPORT RULE: This file must NEVER import coaching_service.
Other services may import this one, never the reverse.
"""
import logging
import statistics
from sqlalchemy.orm import Session as DBSession
from ..models.session import SessionModel
from ..models.shared_enums import WeldMetric
from ..schemas.benchmark import MetricBenchmark, WelderBenchmarks
from ..schemas.shared import METRIC_LABELS
from ..services.scoring_service import get_session_score
from ..services.trajectory_service import _extract_metric_scores

logger = logging.getLogger(__name__)
TOP_PERCENTILE    = 75.0
BOTTOM_PERCENTILE = 25.0


def get_welder_benchmarks(welder_id: str, db: DBSession) -> WelderBenchmarks:
    operator_ids = [
        row.operator_id for row in
        db.query(SessionModel.operator_id)
        .filter(SessionModel.status == "COMPLETE",
                SessionModel.operator_id.isnot(None))
        .distinct().all()
    ]

    population: dict[str, dict[WeldMetric, float]] = {}
    for op_id in operator_ids:
        latest = (
            db.query(SessionModel)
            .filter(SessionModel.operator_id == op_id,
                    SessionModel.status == "COMPLETE")
            .order_by(SessionModel.start_time.desc())
            .first()
        )
        if not latest:
            continue
        score = get_session_score(latest.session_id, db)
        if not score:
            continue
        metric_scores = _extract_metric_scores(score)
        population[op_id] = {ms.metric: ms.value for ms in metric_scores}

    if welder_id not in population:
        logger.warning("Welder %s not in benchmark population", welder_id)
        return WelderBenchmarks(
            welder_id=welder_id, population_size=0,
            metrics=[], overall_percentile=0.0
        )

    welder_metrics = population[welder_id]
    metrics_result = []

    for metric in WeldMetric:
        values = [v[metric] for v in population.values() if metric in v]
        if len(values) < 2:
            continue
        welder_val = welder_metrics.get(metric, 0.0)
        mean      = statistics.mean(values)
        std       = statistics.stdev(values)
        pop_min   = min(values)
        pop_max   = max(values)
        percentile = _compute_percentile(welder_val, values)
        if percentile >= TOP_PERCENTILE:
            tier = "top"
        elif percentile <= BOTTOM_PERCENTILE:
            tier = "bottom"
        else:
            tier = "mid"
        metrics_result.append(MetricBenchmark(
            metric=metric,
            label=METRIC_LABELS[metric],
            welder_value=round(welder_val, 2),
            population_mean=round(mean, 2),
            population_min=round(pop_min, 2),
            population_max=round(pop_max, 2),
            population_std=round(std, 2),
            percentile=round(percentile, 1),
            tier=tier,
        ))

    welder_session = (
        db.query(SessionModel)
        .filter(SessionModel.operator_id == welder_id,
                SessionModel.status == "COMPLETE")
        .order_by(SessionModel.start_time.desc())
        .first()
    )
    all_scores = [
        s.score_total for s in
        db.query(SessionModel.score_total)
        .filter(SessionModel.status == "COMPLETE",
                SessionModel.score_total.isnot(None))
        .all()
        if s.score_total is not None
    ]
    overall_pct = 0.0
    if welder_session and welder_session.score_total and all_scores:
        overall_pct = _compute_percentile(welder_session.score_total, all_scores)

    return WelderBenchmarks(
        welder_id=welder_id,
        population_size=len(population),
        metrics=metrics_result,
        overall_percentile=round(overall_pct, 1),
    )


def _compute_percentile(value: float, population: list[float]) -> float:
    below = sum(1 for v in population if v < value)
    return (below / len(population)) * 100

━━━ STEP 3 — Create my-app/src/types/benchmark.ts ━━━

import { WelderID, WeldMetric } from "./shared";

export interface MetricBenchmark {
  metric: WeldMetric;
  label: string;
  welder_value: number;
  population_mean: number;
  population_min: number;
  population_max: number;
  population_std: number;
  percentile: number;
  tier: "top" | "mid" | "bottom";
}

export interface WelderBenchmarks {
  welder_id: WelderID;
  population_size: number;
  metrics: MetricBenchmark[];
  overall_percentile: number;
}

━━━ STEP 4 — Create my-app/src/components/welding/BenchmarkPanel.tsx ━━━

"use client";
import React from "react";
import { WelderBenchmarks, MetricBenchmark } from "@/types/benchmark";

interface BenchmarkPanelProps {
  benchmarks: WelderBenchmarks;
}

const TIER_COLORS = {
  top:    { bar: "bg-green-500", text: "text-green-400",
            badge: "bg-green-500/10 text-green-400 border-green-500/30" },
  mid:    { bar: "bg-amber-500", text: "text-amber-400",
            badge: "bg-amber-500/10 text-amber-400 border-amber-500/30" },
  bottom: { bar: "bg-red-500",   text: "text-red-400",
            badge: "bg-red-500/10 text-red-400 border-red-500/30" },
};

function GaugeRow({ m }: { m: MetricBenchmark }) {
  const colors  = TIER_COLORS[m.tier];
  const range   = m.population_max - m.population_min;
  const pct     = range > 0 ? ((m.welder_value - m.population_min) / range) * 100 : 50;
  const meanPct = range > 0 ? ((m.population_mean - m.population_min) / range) * 100 : 50;

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-neutral-400">{m.label}</span>
        <div className="flex items-center gap-2">
          <span className={`text-lg font-bold tabular-nums ${colors.text}`}>
            {Math.round(m.welder_value)}
          </span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${colors.badge}`}>
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
        <span className="text-neutral-500">avg {Math.round(m.population_mean)}</span>
        <span>{Math.round(m.population_max)}</span>
      </div>
    </div>
  );
}

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
          vs {benchmarks.population_size} welders
          · {Math.round(benchmarks.overall_percentile)}th percentile overall
        </span>
      </div>
      {benchmarks.metrics.map((m) => (
        <GaugeRow key={m.metric} m={m} />
      ))}
    </div>
  );
}

export default BenchmarkPanel;

━━━ STEP 5 — Create my-app/src/components/dashboard/RankingsTable.tsx ━━━

ORTHOGONALITY RULE: import ONLY from @/types/benchmark, @/types/shared,
@/lib/api. Zero imports from TorchViz3D, HeatMap, FeedbackPanel,
TorchAngleGraph, coaching, or certification files.

"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { WelderBenchmarks } from "@/types/benchmark";
import { WeldMetric, METRIC_LABELS, WELD_METRICS } from "@/types/shared";
import { fetchBenchmarks } from "@/lib/api";

const WELDER_IDS = [
  "mike-chen", "expert-benchmark",
  // Add remaining archetype IDs here to match mock_welders.py
];

export function RankingsTable() {
  const [data, setData]     = useState<WelderBenchmarks[]>([]);
  const [sortBy, setSortBy] = useState<WeldMetric | "overall">("overall");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled(WELDER_IDS.map(id => fetchBenchmarks(id)))
      .then(results => {
        const successful = results
          .filter((r): r is PromiseFulfilledResult<WelderBenchmarks> =>
            r.status === "fulfilled")
          .map(r => r.value);
        setData(successful);
        setLoading(false);
      });
  }, []);

  const sorted = [...data].sort((a, b) => {
    if (sortBy === "overall") return b.overall_percentile - a.overall_percentile;
    const aM = a.metrics.find(m => m.metric === sortBy)?.percentile ?? 0;
    const bM = b.metrics.find(m => m.metric === sortBy)?.percentile ?? 0;
    return bM - aM;
  });

  if (loading) return <div className="h-32 bg-neutral-900 rounded animate-pulse" />;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neutral-800">
              <th className="px-4 py-3 text-left text-xs text-neutral-500 font-medium">
                Rank
              </th>
              <th className="px-4 py-3 text-left text-xs text-neutral-500 font-medium">
                Welder
              </th>
              <th
                className={`px-4 py-3 text-right text-xs font-medium cursor-pointer
                            hover:text-white
                            ${sortBy === "overall" ? "text-cyan-400" : "text-neutral-500"}`}
                onClick={() => setSortBy("overall")}
              >
                Overall %ile
              </th>
              {WELD_METRICS.map(metric => (
                <th
                  key={metric}
                  className={`px-4 py-3 text-right text-xs font-medium cursor-pointer
                              hover:text-white
                              ${sortBy === metric ? "text-cyan-400" : "text-neutral-500"}`}
                  onClick={() => setSortBy(metric)}
                >
                  {METRIC_LABELS[metric].split(" ")[0]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((w, i) => (
              <tr key={w.welder_id}
                  className="border-b border-neutral-800/50 hover:bg-neutral-800/30">
                <td className="px-4 py-3 text-neutral-500 tabular-nums">{i + 1}</td>
                <td className="px-4 py-3">
                  <Link
                    href={`/seagull/welder/${w.welder_id}`}
                    className="text-cyan-400 hover:text-cyan-300"
                  >
                    {w.welder_id}
                  </Link>
                </td>
                <td className="px-4 py-3 text-right font-semibold tabular-nums">
                  {Math.round(w.overall_percentile)}th
                </td>
                {WELD_METRICS.map(metric => {
                  const m = w.metrics.find(x => x.metric === metric);
                  return (
                    <td key={metric} className={`px-4 py-3 text-right tabular-nums ${
                      m?.tier === "top"    ? "text-green-400" :
                      m?.tier === "bottom" ? "text-red-400"   : "text-neutral-300"
                    }`}>
                      {m ? `${Math.round(m.percentile)}th` : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

━━━ VERIFICATION CHECKLIST ━━━
[ ] benchmark.py schema created — MetricBenchmark + WelderBenchmarks
[ ] benchmark_service.py created — no coaching_service import anywhere
[ ] benchmark.ts frontend types created
[ ] BenchmarkPanel.tsx renders gauges with green/amber/red tier colours
[ ] RankingsTable.tsx sorts by any column, links to welder pages
[ ] RankingsTable has zero imports from coaching/cert/TorchViz3D/HeatMap files
[ ] welders.py NOT touched
[ ] api.ts NOT touched
[ ] welder report page NOT touched