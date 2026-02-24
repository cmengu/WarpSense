"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import type { WelderBenchmarks } from "@/types/benchmark";
import { WELD_METRICS, METRIC_LABELS, type WeldMetric } from "@/types/shared";
import { fetchBenchmarks } from "@/lib/api";

/**
 * Welder IDs to display in rankings. Matches mock_welders.py archetypes.
 */
const WELDER_IDS = [
  "mike-chen",
  "sara-okafor",
  "james-park",
  "lucia-reyes",
  "tom-bradley",
  "ana-silva",
  "derek-kwon",
  "priya-nair",
  "marcus-bell",
  "expert-benchmark",
  "expert_aluminium_001",
  "novice_aluminium_001",
];

/**
 * RankingsTable — sortable table of welders by overall or per-metric percentile.
 * Orthogonal to coaching/certification; imports only from @/types/benchmark,
 * @/types/shared, @/lib/api.
 */
export function RankingsTable() {
  const [data, setData] = useState<WelderBenchmarks[]>([]);
  const [sortBy, setSortBy] = useState<WeldMetric | "overall">("overall");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled(WELDER_IDS.map((id) => fetchBenchmarks(id))).then(
      (results) => {
        const successful = results
          .filter(
            (r): r is PromiseFulfilledResult<WelderBenchmarks> =>
              r.status === "fulfilled"
          )
          .map((r) => r.value);
        setData(successful);
        setLoading(false);
      }
    );
  }, []);

  const sorted = [...data].sort((a, b) => {
    if (sortBy === "overall")
      return b.overall_percentile - a.overall_percentile;
    const aM = a.metrics.find((m) => m.metric === sortBy)?.percentile ?? 0;
    const bM = b.metrics.find((m) => m.metric === sortBy)?.percentile ?? 0;
    return bM - aM;
  });

  if (loading)
    return <div className="h-32 bg-neutral-900 rounded animate-pulse" />;

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
              {WELD_METRICS.map((metric) => (
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
              <tr
                key={w.welder_id}
                className="border-b border-neutral-800/50 hover:bg-neutral-800/30"
              >
                <td className="px-4 py-3 text-neutral-500 tabular-nums">
                  {i + 1}
                </td>
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
                {WELD_METRICS.map((metric) => {
                  const m = w.metrics.find((x) => x.metric === metric);
                  return (
                    <td
                      key={metric}
                      className={`px-4 py-3 text-right tabular-nums ${
                        m?.tier === "top"
                          ? "text-green-400"
                          : m?.tier === "bottom"
                            ? "text-red-400"
                            : "text-neutral-300"
                      }`}
                    >
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
