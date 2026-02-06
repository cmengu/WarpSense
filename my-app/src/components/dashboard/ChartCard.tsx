/**
 * ChartCard Component
 * Wrapper component for consistent chart styling and layout
 * Server Component - layout wrapper only
 */

interface ChartCardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export function ChartCard({ title, description, children, className }: ChartCardProps) {
  return (
    <div className={`bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6 ${className || ''}`}>
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-black dark:text-zinc-50 mb-1">
          {title}
        </h3>
        {description && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            {description}
          </p>
        )}
      </div>
      <div className="w-full">
        {children}
      </div>
    </div>
  );
}
