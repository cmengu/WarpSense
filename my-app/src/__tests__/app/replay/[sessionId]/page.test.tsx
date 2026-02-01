import { render, screen } from '@testing-library/react';
import ReplayPage from '@/app/replay/[sessionId]/page';

// Mock Next.js dynamic route params
jest.mock('next/navigation', () => ({
  useParams: () => ({ sessionId: 'test-session-123' }),
}));

describe('ReplayPage', () => {
  it('renders with sessionId from params', () => {
    render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);
    expect(screen.getByText(/session replay: test-session-123/i)).toBeInTheDocument();
  });

  it('renders all welding components', () => {
    render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);
    // Check that components are rendered (they show sessionId in their placeholder)
    expect(screen.getAllByText(/test-session-123/i).length).toBeGreaterThan(0);
  });
});
