/**
 * WarpRiskGauge — semicircle probability gauge for warp prediction.
 * ok → cyan-400, warning → amber-400, critical → red-500
 */
"use client";

import React from "react";
import type { RiskLevel } from "@/types/shared";

interface WarpRiskGaugeProps {
  probability: number;
  riskLevel: RiskLevel;
  modelAvailable: boolean;
  className?: string;
}

const RISK_COLORS: Record<RiskLevel, { stroke: string; text: string; bg: string }> =
  {
    ok: { stroke: "#22d3ee", text: "text-cyan-400", bg: "bg-cyan-400/10" },
    warning: {
      stroke: "#fbbf24",
      text: "text-amber-400",
      bg: "bg-amber-400/10",
    },
    critical: {
      stroke: "#ef4444",
      text: "text-red-500",
      bg: "bg-red-500/10",
    },
  };

const RISK_LABELS: Record<RiskLevel, string> = {
  ok: "LOW RISK",
  warning: "WARP WARNING",
  critical: "WARP CRITICAL",
};

export function WarpRiskGauge({
  probability,
  riskLevel,
  modelAvailable,
  className = "",
}: WarpRiskGaugeProps) {
  const colors = RISK_COLORS[riskLevel];
  const pct = Math.min(1, Math.max(0, probability));

  const r = 50;
  const cx = 60;
  const cy = 60;
  const startAngle = Math.PI;
  const endAngle = startAngle - pct * Math.PI;
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArc = pct > 0.5 ? 1 : 0;

  if (!modelAvailable) {
    return (
      <div
        className={`flex flex-col items-center ${className}`}
        data-testid="warp-risk-gauge-unavailable"
      >
        <div className="text-xs text-neutral-500 uppercase tracking-widest">
          Warp Risk
        </div>
        <div className="text-xs text-neutral-600 mt-1">Model unavailable</div>
      </div>
    );
  }

  return (
    <div
      className={`flex flex-col items-center ${colors.bg} rounded-lg p-4 ${className}`}
      data-testid="warp-risk-gauge"
    >
      <div className="text-xs text-neutral-400 uppercase tracking-widest mb-2">
        Warp Risk
      </div>
      <svg
        width="120"
        height="70"
        viewBox="0 0 120 70"
        aria-label={`Warp risk: ${Math.round(pct * 100)}%`}
      >
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="#262626"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {pct > 0 && (
          <path
            d={`M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`}
            fill="none"
            stroke={colors.stroke}
            strokeWidth="10"
            strokeLinecap="round"
          />
        )}
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          fill={colors.stroke}
          fontSize="18"
          fontWeight="bold"
          fontFamily="monospace"
        >
          {Math.round(pct * 100)}%
        </text>
      </svg>
      <div
        className={`text-xs font-semibold tracking-widest ${colors.text} mt-1`}
      >
        {RISK_LABELS[riskLevel]}
      </div>
    </div>
  );
}
