import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from '@/app/(app)/dashboard/page';

// Mock the API call to avoid actual fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ metrics: [], charts: [] }),
  })
) as jest.Mock;

describe('Dashboard Page Session List', () => {
  it('renders Live Demo link for zero-setup demo', async () => {
    render(<DashboardPage />);
    await waitFor(() => {
      const links = screen.getAllByRole('link');
      const demoLink = links.find((l) => l.getAttribute('href') === '/demo');
      expect(demoLink).toBeDefined();
      expect(demoLink).toBeInTheDocument();
    });
  });

  it('renders session list links with correct hrefs', async () => {
    render(<DashboardPage />);

    // Wait for component to render and session links to appear
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /expert \(sess_expert_001\)/i })).toBeInTheDocument();
    });

    const link1 = screen.getByRole('link', { name: /expert \(sess_expert_001\)/i });
    expect(link1).toHaveAttribute('href', '/replay/sess_expert_001');

    const link2 = screen.getByRole('link', { name: /novice \(sess_novice_001\)/i });
    expect(link2).toHaveAttribute('href', '/replay/sess_novice_001');
  });

  it('displays mock label for sessions', async () => {
    render(<DashboardPage />);
    
    // Wait for mock labels to appear
    await waitFor(() => {
      expect(screen.getAllByText(/\(mock\)/i).length).toBeGreaterThan(0);
    });
    
    const mockLabels = screen.getAllByText(/\(mock\)/i);
    expect(mockLabels.length).toBeGreaterThan(0);
  });
});
