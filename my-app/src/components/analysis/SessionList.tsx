"use client";
import type { MockSession } from "@/types/warp-analysis";
export interface SessionListProps {
  onSessionSelect: (session: MockSession) => void;
  selectedSessionId: string | null;
}
export function SessionList(_props: SessionListProps) { return null; } // Phase UI-3
