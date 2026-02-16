/**
 * PieChart Component
 * Client Component for interactive pie charts using recharts
 * Requires 'use client' directive for interactivity
 */

'use client';

import { PieChart as RechartsPieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface PieChartProps {
  data: Array<{
    name: string;
    value: number;
    color?: string;
  }>;
  height?: number;
  showLegend?: boolean;
}

// Default color palette: WarpSense blue/purple only
const DEFAULT_COLORS = ['#2563eb', '#4f46e5', '#7c3aed', '#8b5cf6', '#6366f1', '#9333ea'];

export function PieChart({ data, height = 300, showLegend = true }: PieChartProps) {
  // Handle empty data state
  if (!data || data.length === 0) {
    return (
      <div 
        className="flex items-center justify-center text-zinc-500 dark:text-zinc-400"
        style={{ height: `${height}px` }}
      >
        No data available
      </div>
    );
  }

  // Assign colors to data points
  const chartData = data.map((item, index) => ({
    ...item,
    color: item.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length]
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsPieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
          outerRadius={80}
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip 
          contentStyle={{
            backgroundColor: 'var(--background)',
            border: '1px solid var(--foreground)',
            borderRadius: '8px'
          }}
        />
        {showLegend && (
          <Legend 
            wrapperStyle={{ color: 'var(--foreground)' }}
          />
        )}
      </RechartsPieChart>
    </ResponsiveContainer>
  );
}
