import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from '@/app/(app)/dashboard/page';

const mockFetchScore = jest.fn();
jest.mock('@/lib/api', () => ({
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
}));

describe('Dashboard Page (Welder Roster)', () => {
  beforeEach(() => {
    mockFetchScore.mockResolvedValue({ total: 75, rules: [] });
  });

  it('renders welder roster with cards', async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Welder Roster/)).toBeInTheDocument();
    expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
  });

  it('links cards to replay and full report', async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });
    const links = screen.getAllByRole('link');
    const replayLink = links.find((l) => l.getAttribute('href') === '/replay/sess_mike-chen_005');
    const fullReportLink = links.find((l) => l.getAttribute('href') === '/seagull/welder/mike-chen');
    expect(replayLink).toBeDefined();
    expect(fullReportLink).toBeDefined();
  });
});
