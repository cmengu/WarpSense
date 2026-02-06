/**
 * DashboardLayout Component
 * Server Component that orchestrates the dashboard layout
 * Receives dashboard data and renders metrics and charts in responsive grid
 */

import { MetricCard } from './MetricCard';
import { ChartCard } from './ChartCard';
import { LineChart } from '../charts/LineChart';
import { BarChart } from '../charts/BarChart';
import { PieChart } from '../charts/PieChart';
import type { DashboardData } from '@/types/dashboard';

interface DashboardLayoutProps {
  data: DashboardData;
}

export function DashboardLayout({ data }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-black p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-semibold mb-6 text-black dark:text-zinc-50">
          Dashboard
        </h1>
        
        {/* Metrics Grid */}
        {data.metrics.length === 0 ? (
          <div className="mb-8 p-8 text-center text-zinc-500 dark:text-zinc-400 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
            No metrics available
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {data.metrics.map((metric) => (
              <MetricCard
                key={metric.id}
                title={metric.title}
                value={metric.value}
                change={metric.change}
                trend={metric.trend}
              />
            ))}
          </div>
        )}

        {/* Charts Grid */}
        {data.charts.length === 0 ? (
          <div className="p-8 text-center text-zinc-500 dark:text-zinc-400 bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
            No charts available
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {data.charts.map((chart) => (
              <ChartCard key={chart.id} title={chart.title}>
                {chart.type === 'line' && (
                  <LineChart data={chart.data} color={chart.color} />
                )}
                {chart.type === 'bar' && (
                  <BarChart data={chart.data} color={chart.color} />
                )}
                {chart.type === 'pie' && (
                  <PieChart data={chart.data} />
                )}
              </ChartCard>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
