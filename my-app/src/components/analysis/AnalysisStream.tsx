"use client";
// Uses fetch() + ReadableStream. Never EventSource (POST route, GET-only).
import type { WarpReport } from "@/types/warp-analysis";
export interface AnalysisStreamProps {
  sessionId: string;
  onComplete: (report: WarpReport) => void;
  onError: (message: string) => void;
}
export function AnalysisStream(_props: AnalysisStreamProps) { return null; } // Phase UI-4
