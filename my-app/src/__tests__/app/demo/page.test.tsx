import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { DemoPageInner } from '@/app/demo/[sessionIdA]/[sessionIdB]/page';
import * as api from '@/lib/api';

// BeadDiffPlaceholder uses canvas.getContext('2d'); jsdom does not implement it. Return null to skip drawing.
const originalGetContext = HTMLCanvasElement.prototype.getContext;
beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = jest.fn(() => null);
});
afterAll(() => {
  HTMLCanvasElement.prototype.getContext = originalGetContext;
});

jest.mock('@/lib/api');

const mockUseSessionComparison = jest.fn();
jest.mock('@/hooks/useSessionComparison', () => ({
  useSessionComparison: (...args: unknown[]) => mockUseSessionComparison(...args),
}));

jest.mock('@/components/welding/TorchWithHeatmap3D', () => ({
  __esModule: true,
  default: () => <div data-testid="torch-with-heatmap-3d" />,
}));

// Reconcile with Session type: every non-optional field must be present.
const baseSession = {
  session_id: 'sess_a',
  operator_id: 'op_1',
  start_time: '2026-01-01T00:00:00Z',
  weld_type: 'butt_joint',
  thermal_sample_interval_ms: 100,
  thermal_directions: ['center'],
  thermal_distance_interval_mm: 10,
  sensor_sample_rate_hz: 100,
  status: 'complete' as const,
  frame_count: 2,
  expected_frame_count: 2,
  last_successful_frame_index: 1,
  validation_errors: [] as string[],
  completed_at: '2026-01-01T00:00:15Z',
  score_total: 72,
  frames: [
    {
      timestamp_ms: 0,
      amps: 180,
      volts: 22,
      angle_degrees: 68,
      heat_input_kj_per_mm: 0.65,
      thermal_snapshots: [],
      has_thermal_data: false,
    },
    {
      timestamp_ms: 1000,
      amps: 182,
      volts: 22,
      angle_degrees: 69,
      heat_input_kj_per_mm: 0.67,
      thermal_snapshots: [],
      has_thermal_data: false,
    },
  ],
};

beforeEach(() => {
  mockUseSessionComparison.mockReturnValue({
    deltas: [{ timestamp_ms: 0 }, { timestamp_ms: 1000 }],
    shared_count: 2,
    total_a: 2,
    total_b: 2,
  });
  (api.fetchSession as jest.Mock).mockImplementation((id: string) =>
    Promise.resolve({ ...baseSession, session_id: id })
  );
  (api.fetchSessionAlerts as jest.Mock).mockResolvedValue({ alerts: [] });
});

afterEach(() => jest.clearAllMocks());

test('renders loaded state after fetch resolves', async () => {
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  expect(screen.getByTestId('demo-skeleton')).toBeInTheDocument();
  await waitFor(() => expect(screen.getByTestId('demo-loaded')).toBeInTheDocument());
  expect(screen.queryByTestId('demo-skeleton')).not.toBeInTheDocument();
});

test('WQI shows score_total when present', async () => {
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByTestId('demo-loaded'));
  expect(screen.getAllByText('72').length).toBeGreaterThanOrEqual(1);
});

test('WQI shows "--" when score_total is null', async () => {
  (api.fetchSession as jest.Mock).mockImplementation((id: string) =>
    Promise.resolve({ ...baseSession, session_id: id, score_total: null })
  );
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByTestId('demo-loaded'));
  expect(screen.getAllByText('--').length).toBeGreaterThanOrEqual(1);
});

test('shows "Alerts unavailable" when fetchSessionAlerts rejects for session A', async () => {
  (api.fetchSessionAlerts as jest.Mock).mockImplementation((id: string) =>
    id === 'sess_a' ? Promise.reject(new Error('network')) : Promise.resolve({ alerts: [] })
  );
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByTestId('demo-loaded'));
  expect(screen.getByText(/Alerts unavailable/i)).toBeInTheDocument();
});

test('shows error page on 404', async () => {
  (api.fetchSession as jest.Mock).mockRejectedValue(new Error('404 not found'));
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByText(/Demo sessions not found/i));
});

test('no overlapping frames shows message', async () => {
  // Use mockReturnValue so every call (including after data load) returns empty deltas.
  mockUseSessionComparison.mockReturnValue({
    deltas: [],
    shared_count: 0,
    total_a: 2,
    total_b: 2,
  });
  render(<DemoPageInner sessionIdA="sess_a" sessionIdB="sess_b" />);
  await waitFor(() => screen.getByTestId('demo-loaded'));
  expect(screen.getByText(/No overlapping frames/i)).toBeInTheDocument();
});
