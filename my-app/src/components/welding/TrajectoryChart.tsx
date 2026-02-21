/**
 * TrajectoryChart — multi-line Recharts chart for welder skill trajectory.
 */
"use client";

import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { WelderTrajectory, TrajectoryPoint } from "@/types/trajectory";
import type { WeldMetric } from "@/types/shared";
import { METRIC_LABELS } from "@/types/shared";

const TREND_IMPROVING_THRESHOLD = 0.5;
const TREND_DECLINING_THRESHOLD = -0.5;

interface TrajectoryChartProps {
  trajectory: WelderTrajectory;
  height?: number;
}

const METRIC_COLORS: Partial<Record<WeldMetric, string>> = {
  angle_consistency: "#22d3ee",
  thermal_symmetry: "#fbbf24",
  amps_stability: "#a78bfa",
  volts_stability: "#34d399",
  heat_diss_consistency: "#f87171",
};

/** Format ISO date string for chart X-axis (e.g. "Jan 15"). */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function buildChartData(
  points: TrajectoryPoint[],
  projectedNext: number | null
): Record<string, string | number>[] {
  const rows = points.map((p) => {
    const row: Record<string, string | number> = {
      date: formatDate(p.session_date),
      score_total: p.score_total,
    };
    for (const m of p.metrics) {
      row[m.metric] = m.value;
    }
    return row;
  });

  if (projectedNext !== null && rows.length > 0) {
    rows.push({
      date: "Projected",
      score_total: projectedNext,
      _projected: 1,
    });
  }

  return rows;
}

export function TrajectoryChart({ trajectory, height = 280 }: TrajectoryChartProps) {
  const { points, projected_next_score, trend_slope } = trajectory;

  if (points.length === 0) {
    return (
      <div
        className="rounded-lg border border-neutral-800 bg-neutral-900 p-6 text-center text-sm text-neutral-500"
        data-testid="trajectory-empty"
      >
        No session history available yet.
      </div>
    );
  }

  const data = buildChartData(points, projected_next_score);
  const trendLabel =
    trend_slope === null
      ? null
      : trend_slope > TREND_IMPROVING_THRESHOLD
        ? "↑ Improving"
        : trend_slope < TREND_DECLINING_THRESHOLD
          ? "↓ Declining"
          : "→ Stable";
  const trendColor =
    trend_slope === null
      ? "text-neutral-400"
      : trend_slope > TREND_IMPROVING_THRESHOLD
        ? "text-green-400"
        : trend_slope < TREND_DECLINING_THRESHOLD
          ? "text-red-400"
          : "text-neutral-400";

  return (
    <div
      className="rounded-lg border border-neutral-800 bg-neutral-900 p-6"
      data-testid="trajectory-chart"
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-neutral-400">
          Skill Trajectory
        </h2>
        {trendLabel && (
          <span
            className={`text-sm font-semibold ${trendColor}`}
            data-testid="trajectory-chart-trend"
          >
            {trendLabel}
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis dataKey="date" tick={{ fill: "#737373", fontSize: 11 }} />
          <YAxis domain={[0, 100]} tick={{ fill: "#737373", fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#171717",
              border: "1px solid #404040",
            }}
            labelStyle={{ color: "#a3a3a3" }}
            itemStyle={{ color: "#e5e5e5" }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: "#737373" }} />
          <ReferenceLine
            y={80}
            stroke="#404040"
            strokeDasharray="4 4"
            label={{
              value: "Target 80",
              fill: "#525252",
              fontSize: 10,
            }}
          />

          <Line
            type="monotone"
            dataKey="score_total"
            name="Total Score"
            stroke="#ffffff"
            strokeWidth={2.5}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />

          {Object.entries(METRIC_COLORS).map(([metric, color]) => (
            <Line
              key={metric}
              type="monotone"
              dataKey={metric}
              name={METRIC_LABELS[metric as WeldMetric]}
              stroke={color}
              strokeWidth={1.5}
              dot={false}
              strokeOpacity={0.7}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>

      {projected_next_score !== null && (
        <p className="text-xs text-neutral-500 mt-2 text-right">
          Projected next session:{" "}
          <span className="text-neutral-300">
            {Math.round(projected_next_score)}/100
          </span>
        </p>
      )}
    </div>
  );
}

export default TrajectoryChart;
