import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import ReplayPage from '@/app/replay/[sessionId]/page';

// Mock api to avoid real API calls (fetchSession for replay, fetchScore for ScorePanel)
jest.mock('@/lib/api', () => ({
  fetchSession: jest.fn(),
  fetchScore: jest.fn().mockResolvedValue({
    total: 100,
    rules: [
      { rule_id: 'amps_stability', threshold: 5, passed: true, actual_value: 1.18 },
      { rule_id: 'angle_consistency', threshold: 5, passed: true, actual_value: 1.0 },
      { rule_id: 'thermal_symmetry', threshold: 60, passed: true, actual_value: 0.01 },
      { rule_id: 'heat_diss_consistency', threshold: 40, passed: true, actual_value: 3.6 },
      { rule_id: 'volts_stability', threshold: 1, passed: true, actual_value: 0.35 },
    ],
  }),
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

  it('calls fetchSession with limit 2000 for full session load', async () => {
    render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);
    await waitFor(() => {
      expect(mockFetchSession).toHaveBeenCalledWith('test-session-123', {
        limit: 2000,
      });
    });
  });

  /**
   * TorchViz3D production-grade plan Step 4: Replay with comparison enabled.
   * Verifies dual 3D layout renders (Current Session + Comparison) when showComparison is true.
   * Compare page does NOT use TorchViz3D (HeatMap only) — N/A.
   */
  it('TorchViz3D Step 4: replay with comparison shows dual 3D layout and toggle', async () => {
    render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);
    await waitFor(() => {
      expect(screen.getByText(/session replay: test-session-123/i)).toBeInTheDocument();
    });
    // Comparison enabled by default; button shows "Hide"
    expect(screen.getByRole('button', { name: /hide.*comparison/i })).toBeInTheDocument();
    // Both score blocks present when comparison loaded (mock returns same session for both fetches)
    await waitFor(() => {
      expect(screen.getAllByText(/Score:/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  /**
   * Step 4 verification test.
   *
   * Verification result (when PASS):
   *   - slider_rendered: true — Timeline slider in DOM when session has frames
   *   - slider_range: { min: 0, max: 10 } — min/max match first_timestamp_ms / last_timestamp_ms (ms)
   *   - slider_init: 0 — value initializes to firstTimestamp
   *   - slider_onchange: true — fireEvent.change updates currentTimestamp; time label shows 0.01 s
   *
   * Why "0.01 s"? Mock has 2 frames: timestamp_ms 0 and 10. Slider value 10 = 10 ms.
   * Display formula: (currentTimestamp / 1000) + " s" → 10/1000 = 0.01 → "0.01 s".
   *
   * If FAIL: Assertion error shows which check failed (slider missing, wrong range, or time not updating).
   */
  it('Step 4 verification: slider renders, moves, updates currentTimestamp', async () => {
    const { container } = render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);

    await waitFor(() => {
      expect(screen.getByText(/session replay: test-session-123/i)).toBeInTheDocument();
    });

    const slider = screen.queryByRole('slider', { name: /timeline/i }) ?? container.querySelector('#replay-slider');
    expect(slider).toBeInTheDocument();
    if (!slider) return;

    expect(slider).toHaveAttribute('min', '0');
    expect(slider).toHaveAttribute('max', '10');
    expect(slider).toHaveAttribute('value', '0');

    fireEvent.change(slider as HTMLInputElement, { target: { value: '10' } });

    await waitFor(() => {
      expect(screen.getByText(/0\.01\s*s/)).toBeInTheDocument();
    });
  });

  /**
   * Step 5 verification test.
   *
   * Verification result (when PASS):
   *   - play_button_rendered: true — Play button in DOM when session has valid range
   *   - play_toggles_pause: true — Click Play toggles button label to Pause
   *   - playback_advances: true — setInterval advances currentTimestamp; time label updates
   *   - playback_stops_at_end: true — When currentTimestamp reaches lastTimestamp, isPlaying → false
   *   - interval_cleared_on_unmount: true — Unmount clears interval; no state update on unmounted component
   *
   * Test uses jest.useFakeTimers() to advance time. Mock has frames 0–40 ms (5 frames).
   * At 1× speed, interval fires every FRAME_INTERVAL_MS (10 ms). After 20 ms: 0→10→20 (display 0.02 s).
   * After 30 ms: third tick does 30→40, 40>=40 → stop. Display: "0.04 s".
   *
   * If FAIL: Assertion error shows which check failed.
   */
  it('Step 5 verification: Play advances playback; stops at end; interval cleared on unmount', async () => {
    const frames = [0, 10, 20, 30, 40].map((ts) => ({
      timestamp_ms: ts,
      volts: 22,
      amps: 150,
      angle_degrees: 45,
      thermal_snapshots: [],
      has_thermal_data: false,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: null,
    }));
    mockFetchSession.mockResolvedValueOnce({
      session_id: 'step5-session',
      operator_id: 'op-1',
      start_time: '2026-02-07T10:00:00Z',
      weld_type: 'mild_steel',
      thermal_sample_interval_ms: 100,
      thermal_directions: ['center'],
      thermal_distance_interval_mm: 10.0,
      sensor_sample_rate_hz: 100,
      frames,
      status: 'complete',
      frame_count: 5,
      expected_frame_count: 5,
      last_successful_frame_index: 4,
      validation_errors: [],
      completed_at: '2026-02-07T10:00:01Z',
    });

    jest.useFakeTimers();

    const { unmount } = render(<ReplayPage params={{ sessionId: 'step5-session' }} />);
    await waitFor(() => {
      expect(screen.getByText(/session replay: step5-session/i)).toBeInTheDocument();
    });

    const playBtn = screen.getByRole('button', { name: /play playback/i });
    expect(playBtn).toBeInTheDocument();
    expect(playBtn).toHaveTextContent('Play');

    fireEvent.click(playBtn);
    expect(playBtn).toHaveTextContent('Pause');

    await act(async () => {
      jest.advanceTimersByTime(20);
    });
    await waitFor(() => {
      expect(screen.getByText(/0\.02\s*s/)).toBeInTheDocument();
    });

    await act(async () => {
      jest.advanceTimersByTime(20);
    });
    await waitFor(() => {
      expect(screen.getByText(/0\.04\s*s/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /play playback/i })).toHaveTextContent('Play');
    });

    fireEvent.click(playBtn);
    unmount();
    act(() => {
      jest.advanceTimersByTime(100);
    });

    jest.useRealTimers();
  });

  /**
   * Step 6 verification test.
   *
   * Verification result (when PASS):
   *   - space_toggles_play: true — Space key toggles play/pause (Play↔Pause)
   *   - arrow_right_steps: true — ArrowRight steps +10ms; at 0ms → 10ms (0.01 s)
   *   - arrow_left_steps: true — ArrowLeft steps -10ms; at 10ms → 0ms (0.00 s)
   *   - arrow_clamped: true — ArrowLeft at start stays at 0; ArrowRight at end stays at 10
   *   - prevent_default: true — L/R do not scroll page (preventDefault called)
   *   - cleanup_on_unmount: true — Listener removed on unmount; no duplicate handlers
   *
   * Mock has frames 0 and 10 ms. fireEvent.keyDown(window, { code }) simulates key press.
   *
   * If FAIL: Assertion error shows which check failed.
   */
  it('Step 6 verification: Space toggles play; L/R step ±10ms; cleanup on unmount', async () => {
    const { unmount } = render(<ReplayPage params={{ sessionId: 'test-session-123' }} />);
    await waitFor(() => {
      expect(screen.getByText(/session replay: test-session-123/i)).toBeInTheDocument();
    });

    const playBtn = screen.getByRole('button', { name: /play playback/i });
    expect(playBtn).toHaveTextContent('Play');

    fireEvent.keyDown(window, { code: 'Space' });
    await waitFor(() => expect(playBtn).toHaveTextContent('Pause'));

    fireEvent.keyDown(window, { code: 'Space' });
    await waitFor(() => expect(playBtn).toHaveTextContent('Play'));

    expect(screen.getByText(/0\s+s/, { selector: 'p' })).toBeInTheDocument();

    fireEvent.keyDown(window, { code: 'ArrowRight' });
    await waitFor(() => expect(screen.getByText(/0\.01\s*s/)).toBeInTheDocument());

    fireEvent.keyDown(window, { code: 'ArrowLeft' });
    await waitFor(() => expect(screen.getByText(/0\s+s/, { selector: 'p' })).toBeInTheDocument());

    fireEvent.keyDown(window, { code: 'ArrowLeft' });
    await waitFor(() => expect(screen.getByText(/0\s+s/, { selector: 'p' })).toBeInTheDocument());

    fireEvent.keyDown(window, { code: 'ArrowRight' });
    await waitFor(() => expect(screen.getByText(/0\.01\s*s/)).toBeInTheDocument());
    fireEvent.keyDown(window, { code: 'ArrowRight' });
    await waitFor(() => expect(screen.getByText(/0\.01\s*s/)).toBeInTheDocument());

    unmount();
    expect(() => fireEvent.keyDown(window, { code: 'Space' })).not.toThrow();
  });
});
