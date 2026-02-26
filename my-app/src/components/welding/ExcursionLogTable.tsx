/**
 * ExcursionLogTable — Renders excursion log for compliance report.
 *
 * Columns: Time (m:ss), Type, Value, Threshold, Duration, Notes.
 * Client-side sort by timestamp (default asc) or type.
 * Empty state: "No excursions — session within compliance".
 */

import { useMemo, useState } from "react";
import type { ExcursionEntry } from "@/types/report-summary";

export interface ExcursionLogTableProps {
  excursions: ExcursionEntry[];
}

type SortKey = "timestamp" | "type";
type SortDir = "asc" | "desc";

function formatTime(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function ExcursionLogTable({ excursions }: ExcursionLogTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("timestamp");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const sorted = useMemo(() => {
    const arr = [...excursions];
    arr.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "timestamp") {
        cmp = a.timestamp_ms - b.timestamp_ms;
      } else {
        cmp = a.defect_type.localeCompare(b.defect_type);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [excursions, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  if (excursions.length === 0) {
    return (
      <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mt-6">
        <h2 className="text-xl font-bold mb-4">Excursion Log</h2>
        <p className="text-zinc-500 dark:text-zinc-400 text-sm">
          No excursions — session within compliance
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg shadow p-6 mt-6">
      <h2 className="text-xl font-bold mb-4">Excursion Log</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-200 dark:border-zinc-700">
              <th
                className="text-left py-2 px-2 cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800"
                onClick={() => toggleSort("timestamp")}
              >
                Time {sortKey === "timestamp" && (sortDir === "asc" ? "↑" : "↓")}
              </th>
              <th
                className="text-left py-2 px-2 cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800"
                onClick={() => toggleSort("type")}
              >
                Type {sortKey === "type" && (sortDir === "asc" ? "↑" : "↓")}
              </th>
              <th className="text-left py-2 px-2">Value</th>
              <th className="text-left py-2 px-2">Threshold</th>
              <th className="text-left py-2 px-2">Duration</th>
              <th className="text-left py-2 px-2">Notes</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((e, i) => (
              <tr
                key={`${e.timestamp_ms}-${e.defect_type}-${i}`}
                className="border-b border-zinc-100 dark:border-zinc-800 last:border-0"
              >
                <td className="py-2 px-2">{formatTime(e.timestamp_ms)}</td>
                <td className="py-2 px-2">{e.defect_type}</td>
                <td className="py-2 px-2">
                  {e.parameter_value != null ? String(e.parameter_value) : "—"}
                </td>
                <td className="py-2 px-2">
                  {e.threshold_value != null ? String(e.threshold_value) : "—"}
                </td>
                <td className="py-2 px-2">
                  {e.duration_ms != null ? `${e.duration_ms}ms` : "—"}
                </td>
                <td className="py-2 px-2 text-zinc-600 dark:text-zinc-400 max-w-xs truncate">
                  {e.notes ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ExcursionLogTable;
