import { render, screen } from '@testing-library/react';
import HeatMap from '@/components/welding/HeatMap';

describe('HeatMap', () => {
  it('renders with sessionId prop', () => {
    render(<HeatMap sessionId="test-session-123" />);
    expect(screen.getByText(/test-session-123/i)).toBeInTheDocument();
  });

  it('displays placeholder content', () => {
    render(<HeatMap sessionId="test-session-123" />);
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });

  it('displays heat map title', () => {
    render(<HeatMap sessionId="test-session-123" />);
    expect(screen.getByText(/heat map visualization/i)).toBeInTheDocument();
  });
});
