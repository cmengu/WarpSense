import { render, screen } from '@testing-library/react';
import TorchAngleGraph from '@/components/welding/TorchAngleGraph';

describe('TorchAngleGraph', () => {
  it('renders with sessionId prop', () => {
    render(<TorchAngleGraph sessionId="test-session-123" />);
    expect(screen.getByText(/test-session-123/i)).toBeInTheDocument();
  });

  it('displays placeholder content', () => {
    render(<TorchAngleGraph sessionId="test-session-123" />);
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });

  it('displays torch angle title', () => {
    render(<TorchAngleGraph sessionId="test-session-123" />);
    expect(screen.getByText(/torch angle over time/i)).toBeInTheDocument();
  });
});
