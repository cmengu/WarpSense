/**
 * Tests for aggregateToDashboardData.
 * Covers: happy path, empty trend, null trend, all-zero trend, malformed.
 */

import { aggregateToDashboardData } from '@/lib/aggregate-transform';

describe('aggregateToDashboardData', () => {
  it('happy path: maps kpis and trend correctly', () => {
    const input = {
      kpis: {
        avg_score: 78,
        session_count: 12,
        top_performer: 'op1',
        rework_count: 2,
      },
      trend: [{ date: '2025-02-17', value: 80 }],
      calendar: [{ date: '2025-02-17', value: 5 }],
    };
    const output = aggregateToDashboardData(input);
    expect(output.metrics).toHaveLength(4);
    expect(output.metrics[0]).toEqual({
      id: 'avg-score',
      title: 'Avg Score',
      value: 78,
    });
    expect(output.metrics[1].id).toBe('session-count');
    expect(output.charts).toHaveLength(1);
    expect(output.charts[0].id).toBe('trend-1');
    expect(output.charts[0].type).toBe('line');
    expect(output.charts[0].data[0].value).toBe(80);
  });

  it('empty trend: no throw; charts[0].data === []', () => {
    const input = {
      kpis: {
        avg_score: null,
        session_count: 0,
        top_performer: null,
        rework_count: 0,
      },
      trend: [],
      calendar: [],
    };
    const output = aggregateToDashboardData(input);
    expect(output.charts[0].data).toEqual([]);
  });

  it('null trend: no throw; uses [] fallback', () => {
    const input = {
      kpis: {
        avg_score: 80,
        session_count: 1,
        top_performer: 'op1',
        rework_count: 0,
      },
      trend: null,
      calendar: [],
    };
    const output = aggregateToDashboardData(input);
    expect(output.charts[0].data).toEqual([]);
  });

  it('all-zero trend: chart renders; no NaN', () => {
    const input = {
      kpis: {
        avg_score: 0,
        session_count: 2,
        top_performer: null,
        rework_count: 2,
      },
      trend: [
        { date: '2025-02-17', value: 0 },
        { date: '2025-02-16', value: 0 },
      ],
      calendar: [],
    };
    const output = aggregateToDashboardData(input);
    expect(output.charts[0].data).toHaveLength(2);
    expect(output.charts[0].data[0].value).toBe(0);
    expect(output.charts[0].data[1].value).toBe(0);
  });

  it('malformed: missing kpis throws', () => {
    expect(() => aggregateToDashboardData({})).toThrow(
      'Invalid aggregate response: missing kpis'
    );
    expect(() => aggregateToDashboardData({ kpis: null })).toThrow(
      'Invalid aggregate response: missing kpis'
    );
  });

  it('malformed: not an object throws', () => {
    expect(() => aggregateToDashboardData(null)).toThrow(
      'Invalid aggregate response: not an object'
    );
  });
});
