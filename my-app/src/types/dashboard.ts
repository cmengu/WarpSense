/**
 * Type definitions for dashboard data structures
 * Ensures type safety across all dashboard components
 */

export interface MetricData {
  id: string;
  title: string;
  value: number | string;
  change?: number;
  trend?: 'up' | 'down' | 'neutral';
}

// Discriminated union types for better type safety
export interface LineChartDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface BarChartDataPoint {
  category: string;
  value: number;
}

export interface PieChartDataPoint {
  name: string;
  value: number;
  color?: string;
}

// Union type for backward compatibility
export type ChartDataPoint = LineChartDataPoint | BarChartDataPoint | PieChartDataPoint;

// Discriminated union for chart data
export type ChartData = 
  | {
      id: string;
      type: 'line';
      title: string;
      data: LineChartDataPoint[];
      color?: string;
    }
  | {
      id: string;
      type: 'bar';
      title: string;
      data: BarChartDataPoint[];
      color?: string;
    }
  | {
      id: string;
      type: 'pie';
      title: string;
      data: PieChartDataPoint[];
      color?: string;
    };

export interface DashboardData {
  metrics: MetricData[];
  charts: ChartData[];
}
