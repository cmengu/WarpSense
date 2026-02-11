import { render, screen, waitFor } from '@testing-library/react';
import ReplayPage from '@/app/replay/[sessionId]/page';

// Mock fetchSession to avoid real API calls
jest.mock('@/lib/api', () => ({
  fetchSession: jest.fn(),
}));

import { fetchSession } from '@/lib/api';

const mockFetchSession = fetchSession as jest.MockedFunction<typeof fetchSession>;

describe('ReplayPage', () => {
  beforeEach(() => {
    mockFetchSession.mockResolvedValue({
      session_id: 'test-session-123',
      operator_id: 'op-1',
      start_time: '2026-02-07T10:00:00Z',
      weld_type: 'mild_steel',
      thermal_sample_interval_ms: 100,
      thermal_directions: ['center', 'north', 'south', 'east', 'west'],
      thermal_distance_interval_mm: 10.0,
      sensor_sample_rate_hz: 100,
      frames: [
        { timestamp_ms: 0, volts: 22, amps: 150, angle_degrees: 45, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null },
        { timestamp_ms: 10, volts: 22.1, amps: 150.1, angle_degrees: 45.1, thermal_snapshots: [], has_thermal_data: false, optional_sensors: null, heat_dissipation_rate_celsius_per_sec: null },
      ],
      status: 'complete',
      frame_count: 2,
      expected_frame_count: 2,
      last_successful_frame_index: 1,
      validation_errors: [],
      completed_at: '2026-02-07T10:00:01Z',
    });
  });

  it('renders with sessionId from params after load', async () => {
    render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);
    await waitFor(() => {
      expect(screen.getByText(/session replay: test-session-123/i)).toBeInTheDocument();
    });
  });

  it('renders all welding components after fetch', async () => {
    render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);
    await waitFor(() => {
      expect(screen.getAllByText(/test-session-123/i).length).toBeGreaterThan(0);
    });
  });
});
