"use client";
import type { WarpDisposition } from "@/types/warp-analysis";

export interface StatusBadgeProps { disposition: WarpDisposition | null; }

const BADGE: Record<
  NonNullable<WarpDisposition> | "null",
  { label: string; dot: string; text: string }
> = {
  PASS:            { label: "PASS",         dot: "bg-[var(--warp-green)]",  text: "text-[var(--warp-green)]"  },
  CONDITIONAL:     { label: "CONDITIONAL",  dot: "bg-[var(--warp-amber)]",  text: "text-[var(--warp-amber)]"  },
  REWORK_REQUIRED: { label: "REWORK REQ.",  dot: "bg-[var(--warp-danger)]", text: "text-[var(--warp-danger)]" },
  null:            { label: "NOT ANALYSED", dot: "bg-zinc-600",              text: "text-zinc-500"              },
};

export function StatusBadge({ disposition }: StatusBadgeProps) {
  const key = disposition ?? "null";
  const { label, dot, text } = BADGE[key];
  return (
    <span
      className={`inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-widest transition-colors duration-200 ${text}`}
    >
      <span
        className={`h-1.5 w-1.5 shrink-0 rounded-full transition-colors duration-200 ${dot}`}
      />
      {label}
    </span>
  );
}
