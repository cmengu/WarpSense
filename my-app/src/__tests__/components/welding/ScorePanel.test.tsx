/**
 * Step 10 verification test for ScorePanel.
 *
 * Verification result (when PASS):
 *   - displays_score_panel_title: ScorePanel shows "Scoring Feedback"
 *   - shows_loading_initially: Initial render shows "Loading score..."
 *   - shows_score_on_success: When fetchScore resolves, shows total (e.g. 100/100) and rules
 *   - shows_error_on_fetch_failure: When fetchScore rejects, shows error message
 *   - no_coming_soon_when_loaded: After load, "Coming soon" is NOT displayed
 *
 * Uses jest.mock to mock fetchScore.
 */
import { render, screen, waitFor } from '@testing-library/react';
import ScorePanel from '@/components/welding/ScorePanel';

jest.mock('@/lib/api', () => ({
  fetchScore: jest.fn(),
}));

import { fetchScore } from '@/lib/api';

const mockFetchScore = fetchScore as jest.MockedFunction<typeof fetchScore>;

const mockScoreSuccess = {
  total: 100,
  rules: [
    { rule_id: 'amps_stability', threshold: 5, passed: true, actual_value: 1.18 },
    { rule_id: 'angle_consistency', threshold: 5, passed: true, actual_value: 1.0 },
    { rule_id: 'thermal_symmetry', threshold: 60, passed: true, actual_value: 0.01 },
    { rule_id: 'heat_diss_consistency', threshold: 40, passed: true, actual_value: 3.6 },
    { rule_id: 'volts_stability', threshold: 1, passed: true, actual_value: 0.35 },
  ],
};

describe('ScorePanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchScore.mockResolvedValue(mockScoreSuccess);
  });

  it('displays score panel title', () => {
    render(<ScorePanel sessionId="test-session-123" />);
    expect(screen.getByText(/scoring feedback/i)).toBeInTheDocument();
  });

  it('shows loading initially', () => {
    render(<ScorePanel sessionId="test-session-123" />);
    expect(screen.getByText(/loading score/i)).toBeInTheDocument();
  });

  it('calls fetchScore with sessionId', async () => {
    render(<ScorePanel sessionId="test-session-123" />);
    await waitFor(() => {
      expect(mockFetchScore).toHaveBeenCalledWith('test-session-123');
    });
  });

  it('Step 10 verification: shows score on success (100/100, 5 rules)', async () => {
    render(<ScorePanel sessionId="test-session-123" />);

    await waitFor(() => {
      expect(screen.getByText(/100\/100/)).toBeInTheDocument();
    });

    expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();

    // All 5 rules should be listed
    expect(screen.getByText(/amps stability/i)).toBeInTheDocument();
    expect(screen.getByText(/angle consistency/i)).toBeInTheDocument();
    expect(screen.getByText(/thermal symmetry/i)).toBeInTheDocument();
    expect(screen.getByText(/heat diss consistency/i)).toBeInTheDocument();
    expect(screen.getByText(/volts stability/i)).toBeInTheDocument();
  });

  it('Step 10 verification: shows error on fetch failure', async () => {
    mockFetchScore.mockRejectedValue(new Error('Session not found'));

    render(<ScorePanel sessionId="missing-session" />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load score/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/session not found/i)).toBeInTheDocument();
  });

  it('displays threshold callout when active_threshold_spec present', async () => {
    mockFetchScore.mockResolvedValue({
      total: 100,
      rules: [],
      active_threshold_spec: {
        weld_type: 'mig',
        angle_target: 45,
        angle_warning: 5,
        angle_critical: 15,
      },
    });

    render(<ScorePanel sessionId="sess_1" />);

    await waitFor(() => {
      expect(screen.getByText(/evaluated against mig spec/i)).toBeInTheDocument();
    });
  });
});
