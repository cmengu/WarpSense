/**
 * LineChart Component
 * Client Component for interactive line charts using recharts
 * Requires 'use client' directive for interactivity (tooltips, hover)
 */

'use client';

import { LineChart as RechartsLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface LineChartProps {
  data: Array<{
    date: string;
    value: number;
    label?: string;
  }>;
  color?: string;
  height?: number;
}

export function LineChart({ data, color = '#3b82f6', height = 300 }: LineChartProps) {
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

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-zinc-200 dark:stroke-zinc-800" />
        <XAxis 
          dataKey="date" 
          className="text-zinc-600 dark:text-zinc-400"
          stroke="currentColor"
        />
        <YAxis 
          className="text-zinc-600 dark:text-zinc-400"
          stroke="currentColor"
        />
        <Tooltip 
          contentStyle={{
            backgroundColor: 'var(--background)',
            border: '1px solid var(--foreground)',
            borderRadius: '8px'
          }}
        />
        <Line 
          type="monotone" 
          dataKey="value" 
          stroke={color}
          strokeWidth={2}
          dot={{ fill: color }}
        />
      </RechartsLineChart>
    </ResponsiveContainer>
  );
}
