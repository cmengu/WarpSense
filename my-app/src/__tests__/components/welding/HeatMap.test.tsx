import { render, screen } from '@testing-library/react';
import HeatMap from '@/components/welding/HeatMap';
import type { HeatmapData } from '@/utils/heatmapData';

describe('HeatMap', () => {
  it('renders with sessionId prop', () => {
    render(<HeatMap sessionId="test-session-123" />);
    expect(screen.getByText(/test-session-123/i)).toBeInTheDocument();
  });

  it('displays no-data message when data is not provided', () => {
    render(<HeatMap sessionId="test-session-123" />);
    expect(screen.getByText(/no thermal data available/i)).toBeInTheDocument();
  });

  it('displays no-data message when data is null', () => {
    render(<HeatMap sessionId="test-session-123" data={null} />);
    expect(screen.getByText(/no thermal data available/i)).toBeInTheDocument();
  });

  it('displays no-data message when data has zero points', () => {
    const emptyData: HeatmapData = {
      points: [],
      timestamps_ms: [],
      distances_mm: [],
      point_count: 0,
    };
    render(<HeatMap sessionId="test-session-123" data={emptyData} />);
    expect(screen.getByText(/no thermal data available/i)).toBeInTheDocument();
  });

  it('displays data summary and heatmap grid when data is provided', () => {
    const data: HeatmapData = {
      points: [
        { timestamp_ms: 100, distance_mm: 10.0, temp_celsius: 425.3, direction: "center" },
        { timestamp_ms: 100, distance_mm: 20.0, temp_celsius: 430.1, direction: "center" },
        { timestamp_ms: 200, distance_mm: 10.0, temp_celsius: 420.0, direction: "center" },
        { timestamp_ms: 200, distance_mm: 20.0, temp_celsius: 425.0, direction: "center" },
      ],
      timestamps_ms: [100, 200],
      distances_mm: [10.0, 20.0],
      point_count: 4,
    };
    render(<HeatMap sessionId="test-session-123" data={data} />);
    expect(screen.getByText(/4 points/i)).toBeInTheDocument();
    expect(screen.getByText(/2 timestamps/i)).toBeInTheDocument();
    expect(screen.getByText(/2 distances/i)).toBeInTheDocument();
    // Heatmap grid renders divs with temperature tooltips
    expect(screen.getByTitle(/425\.3°C/)).toBeInTheDocument();
  });

  it('displays heat map title', () => {
    render(<HeatMap sessionId="test-session-123" />);
    expect(screen.getByText(/heat map visualization/i)).toBeInTheDocument();
  });

  it('accepts activeTimestamp prop for column highlight', () => {
    const data: HeatmapData = {
      points: [
        { timestamp_ms: 100, distance_mm: 10.0, temp_celsius: 425.3, direction: "center" },
        { timestamp_ms: 200, distance_mm: 10.0, temp_celsius: 420.0, direction: "center" },
      ],
      timestamps_ms: [100, 200],
      distances_mm: [10.0],
      point_count: 2,
    };
    render(<HeatMap sessionId="test-session-123" data={data} activeTimestamp={100} />);
    expect(screen.getByTitle(/425\.3°C/)).toBeInTheDocument();
  });

  it('Step 2 verification: renders div grid with blue-yellow-red gradient, no placeholder', () => {
    const data: HeatmapData = {
      points: [
        { timestamp_ms: 0, distance_mm: 10.0, temp_celsius: 20, direction: "center" },
        { timestamp_ms: 100, distance_mm: 10.0, temp_celsius: 310, direction: "center" },
        { timestamp_ms: 200, distance_mm: 10.0, temp_celsius: 600, direction: "center" },
        { timestamp_ms: 0, distance_mm: 20.0, temp_celsius: 490, direction: "center" },
      ],
      timestamps_ms: [0, 100, 200],
      distances_mm: [10.0, 20.0],
      point_count: 4,
    };
    const { container } = render(<HeatMap sessionId="verify" data={data} />);
    expect(screen.queryByText(/visualization rendering coming soon/i)).not.toBeInTheDocument();
    const grid = container.querySelector('.overflow-x-auto .grid');
    expect(grid).toBeInTheDocument();
    expect(screen.getByTitle(/20\.0°C/)).toHaveStyle({ backgroundColor: '#3b82f6' });
    expect(screen.getByTitle(/310\.0°C/)).toHaveStyle({ backgroundColor: '#eab308' });
    expect(screen.getByTitle(/600\.0°C/)).toHaveStyle({ backgroundColor: '#ef4444' });
  });
});
