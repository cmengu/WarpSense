/**
 * BarChart Component
 * Client Component for interactive bar charts using recharts
 * Requires 'use client' directive for interactivity
 */

'use client';

import { BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface BarChartProps {
  data: Array<{
    category: string;
    value: number;
  }>;
  color?: string;
  height?: number;
  horizontal?: boolean;
}

export function BarChart({ data, color = '#3b82f6', height = 300, horizontal = false }: BarChartProps) {
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
      <RechartsBarChart data={data} layout={horizontal ? 'horizontal' : 'vertical'}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-zinc-200 dark:stroke-zinc-800" />
        {horizontal ? (
          <>
            <XAxis type="number" className="text-zinc-600 dark:text-zinc-400" stroke="currentColor" />
            <YAxis dataKey="category" type="category" className="text-zinc-600 dark:text-zinc-400" stroke="currentColor" />
          </>
        ) : (
          <>
            <XAxis dataKey="category" className="text-zinc-600 dark:text-zinc-400" stroke="currentColor" />
            <YAxis className="text-zinc-600 dark:text-zinc-400" stroke="currentColor" />
          </>
        )}
        <Tooltip 
          contentStyle={{
            backgroundColor: 'var(--background)',
            border: '1px solid var(--foreground)',
            borderRadius: '8px'
          }}
        />
        <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} />
      </RechartsBarChart>
    </ResponsiveContainer>
  );
}
