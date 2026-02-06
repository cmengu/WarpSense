/**
 * MetricCard Component
 * Displays a single metric with optional change percentage and trend indicator
 * Server Component - no interactivity needed
 */

interface MetricCardProps {
  title: string;
  value: number | string;
  change?: number;
  trend?: 'up' | 'down' | 'neutral';
}

export function MetricCard({ title, value, change, trend }: MetricCardProps) {
  // Determine trend color and icon
  const getTrendStyles = () => {
    if (trend === 'up') {
      return {
        color: 'text-green-600 dark:text-green-400',
        icon: '↑',
        bgColor: 'bg-green-50 dark:bg-green-900/20'
      };
    }
    if (trend === 'down') {
      return {
        color: 'text-red-600 dark:text-red-400',
        icon: '↓',
        bgColor: 'bg-red-50 dark:bg-red-900/20'
      };
    }
    return {
      color: 'text-zinc-600 dark:text-zinc-400',
      icon: '→',
      bgColor: 'bg-zinc-50 dark:bg-zinc-900/20'
    };
  };

  const trendStyles = getTrendStyles();
  const hasChange = change !== undefined && trend !== undefined;

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 hover:shadow-lg transition-shadow duration-200">
      <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400 mb-2">
        {title}
      </h3>
      <div className="flex items-baseline justify-between">
        <p className="text-3xl font-semibold text-black dark:text-zinc-50">
          {value}
        </p>
        {hasChange && (
          <div className={`flex items-center gap-1 px-2 py-1 rounded ${trendStyles.bgColor}`}>
            <span className={`text-sm font-medium ${trendStyles.color}`}>
              {trendStyles.icon} {Math.abs(change)}%
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
