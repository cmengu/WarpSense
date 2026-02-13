import { render, screen, waitFor } from '@testing-library/react';
import Home from '@/app/page';

// Mock the API call to avoid actual fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ metrics: [], charts: [] }),
  })
) as jest.Mock;

describe('Home Page Session List', () => {
  it('renders session list links with correct hrefs', async () => {
    render(<Home />);

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
    render(<Home />);
    
    // Wait for mock labels to appear
    await waitFor(() => {
      expect(screen.getAllByText(/\(mock\)/i).length).toBeGreaterThan(0);
    });
    
    const mockLabels = screen.getAllByText(/\(mock\)/i);
    expect(mockLabels.length).toBeGreaterThan(0);
  });
});
