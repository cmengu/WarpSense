/**
 * LiveStatusLED — full-width traffic light for iPad mount view.
 */
"use client";
import React from "react";
import { RiskLevel } from "@/types/shared";

interface LiveStatusLEDProps {
  riskLevel: RiskLevel;
  message?: string;
  height?: number;
}

const LED_CONFIG: Record<RiskLevel, { bg: string; text: string; label: string }> = {
  ok:       { bg: "bg-green-600",  text: "text-green-100",  label: "NOMINAL" },
  warning:  { bg: "bg-amber-500",  text: "text-amber-100",  label: "WARP WARNING" },
  critical: { bg: "bg-red-600",    text: "text-red-100",    label: "WARP CRITICAL" },
};

export function LiveStatusLED({ riskLevel, message, height = 120 }: LiveStatusLEDProps) {
  const config = LED_CONFIG[riskLevel];
  return (
    <div
      className={`w-full flex flex-col items-center justify-center rounded-xl transition-colors duration-300 ${config.bg}`}
      style={{ height }}
    >
      <span className={`text-4xl font-black tracking-widest uppercase ${config.text}`}>
        {config.label}
      </span>
      {message && (
        <span className={`text-sm mt-1 opacity-80 ${config.text}`}>{message}</span>
      )}
    </div>
  );
}

export default LiveStatusLED;
