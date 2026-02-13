import { render, screen } from '@testing-library/react';
import TorchAngleGraph from '@/components/welding/TorchAngleGraph';
import type { AngleData } from '@/utils/angleData';

describe('TorchAngleGraph', () => {
  it('renders with sessionId prop', () => {
    render(<TorchAngleGraph sessionId="test-session-123" />);
    expect(screen.getByText(/test-session-123/i)).toBeInTheDocument();
  });

  it('displays no-data message when data is not provided', () => {
    render(<TorchAngleGraph sessionId="test-session-123" />);
    expect(screen.getByText(/no angle data available/i)).toBeInTheDocument();
  });

  it('displays no-data message when data is null', () => {
    render(<TorchAngleGraph sessionId="test-session-123" data={null} />);
    expect(screen.getByText(/no angle data available/i)).toBeInTheDocument();
  });

  it('displays no-data message when data has zero points', () => {
    const emptyData: AngleData = {
      points: [],
      point_count: 0,
      min_angle_degrees: null,
      max_angle_degrees: null,
      avg_angle_degrees: null,
    };
    render(<TorchAngleGraph sessionId="test-session-123" data={emptyData} />);
    expect(screen.getByText(/no angle data available/i)).toBeInTheDocument();
  });

  it('displays data summary and LineChart when data is provided', () => {
    const data: AngleData = {
      points: [
        { timestamp_ms: 0, angle_degrees: 40.0 },
        { timestamp_ms: 10, angle_degrees: 45.0 },
        { timestamp_ms: 20, angle_degrees: 50.0 },
      ],
      point_count: 3,
      min_angle_degrees: 40.0,
      max_angle_degrees: 50.0,
      avg_angle_degrees: 45.0,
    };
    render(<TorchAngleGraph sessionId="test-session-123" data={data} />);
    expect(screen.getByText(/3 points/i)).toBeInTheDocument();
    expect(screen.getByText(/40\.0°/)).toBeInTheDocument();
    expect(screen.getByText(/50\.0°/)).toBeInTheDocument();
    expect(screen.getByText(/45\.0°/)).toBeInTheDocument();
    expect(screen.queryByText(/visualization rendering coming soon/i)).not.toBeInTheDocument();
  });

  it('displays torch angle title', () => {
    render(<TorchAngleGraph sessionId="test-session-123" />);
    expect(screen.getByText(/torch angle over time/i)).toBeInTheDocument();
  });

  it('Step 3 verification: renders LineChart (no placeholder), accepts activeTimestamp', () => {
    const expertLikeData: AngleData = {
      points: [
        { timestamp_ms: 0, angle_degrees: 44.0 },
        { timestamp_ms: 5000, angle_degrees: 45.0 },
        { timestamp_ms: 10000, angle_degrees: 46.0 },
      ],
      point_count: 3,
      min_angle_degrees: 44.0,
      max_angle_degrees: 46.0,
      avg_angle_degrees: 45.0,
    };
    render(
      <TorchAngleGraph sessionId="verify" data={expertLikeData} activeTimestamp={5000} />
    );
    expect(screen.queryByText(/visualization rendering coming soon/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Range: 44\.0° – 46\.0°/)).toBeInTheDocument();
  });
});
