import { render, screen } from '@testing-library/react';
import ScorePanel from '@/components/welding/ScorePanel';

describe('ScorePanel', () => {
  it('renders with sessionId prop', () => {
    render(<ScorePanel sessionId="test-session-123" />);
    expect(screen.getByText(/test-session-123/i)).toBeInTheDocument();
  });

  it('displays placeholder content', () => {
    render(<ScorePanel sessionId="test-session-123" />);
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });

  it('displays score panel title', () => {
    render(<ScorePanel sessionId="test-session-123" />);
    expect(screen.getByText(/scoring feedback/i)).toBeInTheDocument();
  });
});
