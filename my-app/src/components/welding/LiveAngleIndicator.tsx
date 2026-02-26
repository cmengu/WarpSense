/**
 * LiveAngleIndicator — 2D SVG semicircle angle display.
 * No WebGL. No Canvas. Touch-optimised.
 * Target: 45°. Warning: ±5°. Critical: ±15°.
 */
"use client";
import React from "react";
import { RiskLevel } from "@/types/shared";

interface LiveAngleIndicatorProps {
  currentAngle: number;
  targetAngle?: number;
  riskLevel: RiskLevel;
  size?: number;
}

const RISK_COLOR: Record<RiskLevel, string> = {
  ok:       "#22d3ee",
  warning:  "#fbbf24",
  critical: "#ef4444",
};

function polarToXY(angleDeg: number, radius: number, cx: number, cy: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
}

export function LiveAngleIndicator({
  currentAngle,
  targetAngle = 45,
  riskLevel,
  size = 200,
}: LiveAngleIndicatorProps) {
  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.38;
  const color = RISK_COLOR[riskLevel];
  const currentPos = polarToXY(currentAngle, r, cx, cy);
  const targetPos = polarToXY(targetAngle, r, cx, cy);

  return (
    <svg
      width={size} height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-label={`Torch angle: ${Math.round(currentAngle)} degrees`}
    >
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#262626" strokeWidth={12} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#92400e" strokeWidth={12}
        strokeDasharray={`${(10 / 360) * 2 * Math.PI * r} ${2 * Math.PI * r}`}
        strokeDashoffset={-((targetAngle - 5 - 90) / 360) * 2 * Math.PI * r}
      />
      <line x1={cx} y1={cy} x2={targetPos.x} y2={targetPos.y}
        stroke="#525252" strokeWidth={2} strokeDasharray="4 4" />
      <line x1={cx} y1={cy} x2={currentPos.x} y2={currentPos.y}
        stroke={color} strokeWidth={4} strokeLinecap="round" />
      <circle cx={currentPos.x} cy={currentPos.y} r={6} fill={color} />
      <circle cx={cx} cy={cy} r={8} fill={color} />
      <text x={cx} y={cy + r * 0.5}
        textAnchor="middle" fill={color}
        fontSize={size * 0.12} fontWeight="bold" fontFamily="monospace">
        {Math.round(currentAngle)}°
      </text>
      <text x={cx} y={cy + r * 0.7}
        textAnchor="middle" fill="#525252"
        fontSize={size * 0.07} fontFamily="monospace">
        target {targetAngle}°
      </text>
    </svg>
  );
}

export default LiveAngleIndicator;
