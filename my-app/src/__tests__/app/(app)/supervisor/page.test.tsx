/**
 * Supervisor page component tests.
 */

import { render, screen } from '@testing-library/react';
import SupervisorPage from '@/app/(app)/supervisor/page';

jest.mock('@/lib/api', () => ({
  fetchAggregateKPIs: jest.fn(() =>
    Promise.resolve({
      kpis: {
        avg_score: 78,
        session_count: 12,
        top_performer: 'operator_01',
        rework_count: 2,
      },
      trend: [{ date: '2025-02-17', value: 80 }],
      calendar: [{ date: '2025-02-17', value: 5 }],
    })
  ),
}));

describe('SupervisorPage', () => {
  it('renders KPI tiles when data loads', async () => {
    render(<SupervisorPage />);
    await screen.findByText(/Supervisor Dashboard/i);
    expect(screen.getByText('78')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('operator_01')).toBeInTheDocument();
    expect(screen.getByText(/Avg Score/i)).toBeInTheDocument();
    expect(screen.getByText(/Sessions/i)).toBeInTheDocument();
    expect(screen.getByText(/Top Performer/i)).toBeInTheDocument();
    expect(screen.getByText(/Rework/i)).toBeInTheDocument();
  });

  it('renders CalendarHeatmap when calendar data exists', async () => {
    render(<SupervisorPage />);
    await screen.findByText(/Sessions by day|Activity/i);
    const heatmapRegion = document.querySelector('[class*="grid-cols-7"]');
    expect(heatmapRegion).toBeInTheDocument();
  });
});
