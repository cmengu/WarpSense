/**
 * GitHub-style calendar heatmap for sessions per day.
 * Uses UTC consistently to avoid timezone off-by-one across DST/month boundaries.
 */

'use client';

interface DayValue {
  date: string;
  value: number;
}

interface CalendarHeatmapProps {
  data: DayValue[];
  title?: string;
  emptyMessage?: string;
  weeksToShow?: number;
}

export function CalendarHeatmap({
  data,
  title = 'Activity',
  emptyMessage = 'No activity',
  weeksToShow = 12,
}: CalendarHeatmapProps) {
  if (!data || data.length === 0) {
    return (
      <div className="p-6 text-center text-zinc-500 dark:text-zinc-400 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
        {emptyMessage}
      </div>
    );
  }

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const byDate = new Map(data.map((d) => [d.date, d.value]));

  // Build grid: last N weeks, Sun–Sat. Use UTC to avoid timezone off-by-one.
  const now = new Date();
  const todayUtc = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
  );
  const cells: { date: string; value: number }[] = [];

  for (let w = weeksToShow - 1; w >= 0; w--) {
    for (let d = 0; d < 7; d++) {
      const daysBack = w * 7 + (6 - d);
      const dte = new Date(todayUtc);
      dte.setUTCDate(dte.getUTCDate() - daysBack);
      const key = dte.toISOString().slice(0, 10);
      cells.push({ date: key, value: byDate.get(key) ?? 0 });
    }
  }

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-4">
      {title && (
        <h3 className="text-sm font-medium mb-2 text-zinc-700 dark:text-zinc-300">
          {title}
        </h3>
      )}
      <div
        className="grid grid-cols-7 gap-0.5"
        style={{ width: 'fit-content' }}
      >
        {cells.map((c, i) => {
          const intensity = maxVal > 0 ? c.value / maxVal : 0;
          return (
            <div
              key={i}
              title={`${c.date}: ${c.value} sessions`}
              role="img"
              aria-label={`${c.date}: ${c.value} session${c.value === 1 ? '' : 's'}`}
              className="w-3 h-3 rounded-sm"
              style={{
                backgroundColor:
                  intensity === 0
                    ? 'var(--zinc-200, #e4e4e7)'
                    : `rgba(59, 130, 246, ${0.2 + 0.8 * intensity})`,
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
