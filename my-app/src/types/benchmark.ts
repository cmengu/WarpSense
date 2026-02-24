/**
 * Benchmark types — per-metric percentile rankings for welders.
 * Matches backend schemas.benchmark exactly.
 */
import type { WelderID, WeldMetric } from "./shared";

export interface MetricBenchmark {
  metric: WeldMetric;
  label: string;
  welder_value: number;
  population_mean: number;
  population_min: number;
  population_max: number;
  population_std: number;
  percentile: number;
  tier: "top" | "mid" | "bottom";
}

export interface WelderBenchmarks {
  welder_id: WelderID;
  population_size: number;
  metrics: MetricBenchmark[];
  overall_percentile: number;
}
