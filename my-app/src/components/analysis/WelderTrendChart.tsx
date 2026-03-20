"use client";
/**
 * WelderTrendChart — quality score trajectory for a given welder.
 *
 * Recharts SSR safety: wrapped in a `mounted` guard (useEffect sets it to true).
 * Phase UI-7 MUST also wrap the import with dynamic({ssr:false}) per LEARNING_LOG.
 *
 * X axis: session number 1–N (oldest left, newest right).
 * Y axis: 0 = REWORK_REQUIRED, 0.5 = CONDITIONAL, 1.0 = PASS.
 * Dot colour: green (#22C55E) = PASS, amber (#F59E0B) = CONDITIONAL, red (#EF4444) = REWORK.
 */
import { useEffect, useState } from "react";
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { WelderTrendPoint } from "@/types/warp-analysis";
import { fetchWelderTrend } from "@/lib/warp-api";

export interface WelderTrendChartProps {
  welderId: string;
}

const DOT_COLOR: Record<string, string> = {
  PASS:             "#22C55E",
  CONDITIONAL:      "#F59E0B",
  REWORK_REQUIRED:  "#EF4444",
};

interface ChartRow extends WelderTrendPoint {
  session_number: number;
}

function CustomDot(props: {
  cx?: number; cy?: number; payload?: ChartRow;
}) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return null;
  const fill = DOT_COLOR[payload.disposition] ?? "#6B7280";
  return <circle cx={cx} cy={cy} r={5} fill={fill} stroke="none" />;
}

function yTickFormatter(value: number): string {
  if (value === 1.0) return "PASS";
  if (value === 0.5) return "COND";
  if (value === 0.0) return "REWORK";
  return String(value);
}

export function WelderTrendChart({ welderId }: WelderTrendChartProps) {
  const [mounted, setMounted]     = useState(false);
  const [rows, setRows]           = useState<ChartRow[]>([]);
  const [loading, setLoading]     = useState(false);
  const [errorMsg, setErrorMsg]   = useState<string | null>(null);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    if (!welderId) return;
    let cancelled = false;
    setLoading(true);
    setErrorMsg(null);

    fetchWelderTrend(welderId)
      .then((points) => {
        if (cancelled) return;
        setRows(
          points.map((p, i) => ({ ...p, session_number: i + 1 })),
        );
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setErrorMsg(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [welderId]);

  const containerClass =
    "w-full h-[180px] bg-[var(--warp-surface)] border border-zinc-900 p-2";

  if (!mounted) {
    return <div className={containerClass} />;
  }

  if (loading) {
    return (
      <div className={`${containerClass} flex items-center justify-center`}>
        <p className="font-mono text-[9px] text-[var(--warp-text-muted)] uppercase tracking-widest">
          Loading trend…
        </p>
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div className={`${containerClass} flex items-center justify-center`}>
        <p className="font-mono text-[9px] text-red-400 uppercase tracking-widest">
          Trend unavailable
        </p>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className={`${containerClass} flex items-center justify-center`}>
        <p className="font-mono text-[9px] text-[var(--warp-text-muted)] uppercase tracking-widest">
          No analysed sessions
        </p>
      </div>
    );
  }

  return (
    <div className={containerClass}>
      <p className="font-mono text-[8px] uppercase tracking-widest text-[var(--warp-text-muted)] mb-1">
        Quality Trend
      </p>
      <ResponsiveContainer width="100%" height={148}>
        <ComposedChart
          data={rows}
          margin={{ top: 4, right: 8, bottom: 4, left: 4 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.05)"
            vertical={false}
          />
          <XAxis
            dataKey="session_number"
            tick={{ fontSize: 8, fill: "var(--warp-text-muted)", fontFamily: "var(--font-warp-mono)" }}
            tickLine={false}
            axisLine={false}
            label={undefined}
          />
          <YAxis
            ticks={[0, 0.5, 1]}
            tickFormatter={yTickFormatter}
            domain={[-0.1, 1.1]}
            tick={{ fontSize: 8, fill: "var(--warp-text-muted)", fontFamily: "var(--font-warp-mono)" }}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip
            contentStyle={{
              background: "var(--warp-surface)",
              border: "1px solid var(--warp-border)",
              borderRadius: 0,
              fontSize: 9,
              fontFamily: "var(--font-warp-mono)",
              color: "var(--warp-text)",
            }}
            formatter={(value: number, _name, entry: any) => {
              // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
              const row = entry.payload as ChartRow | undefined;
              const disposition = row?.disposition ?? "";
              return [`${disposition} (${value})`, "Quality"];
            }}
            labelFormatter={(label) => `Session ${String(label)}`}
          />
          <ReferenceLine
            y={0.5}
            stroke="#F59E0B"
            strokeDasharray="4 4"
            strokeOpacity={0.5}
            label={{ value: "", position: "insideRight" }}
          />
          <ReferenceLine
            y={0.0}
            stroke="#EF4444"
            strokeDasharray="4 4"
            strokeOpacity={0.5}
            label={{ value: "", position: "insideRight" }}
          />
          <Line
            type="monotone"
            dataKey="quality_score"
            stroke="#6B7280"
            strokeWidth={1}
            strokeOpacity={0.5}
            dot={CustomDot}
            activeDot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
