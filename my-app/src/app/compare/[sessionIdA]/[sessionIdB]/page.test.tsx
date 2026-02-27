import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { ComparePageInner } from './page';

// ── Mocks ────────────────────────────────────────────────────────────────────

jest.mock('@/components/welding/TorchWithHeatmap3D', () => ({
  __esModule: true,
  default: ({ label }: { label?: string }) => (
    <div data-testid="torch-3d" data-label={label ?? ''} />
  ),
}));

// Synchronous dynamic mock — avoids React.lazy suspense race conditions in tests
jest.mock('next/dynamic', () => ({
  __esModule: true,
  default: (_loader: unknown, _options: unknown) => {
    return function TorchWithHeatmap3DDynamic(props: Record<string, unknown>) {
      const MockTorch = jest.requireMock('@/components/welding/TorchWithHeatmap3D').default;
      return <MockTorch {...props} />;
    };
  },
}));

// useSessionComparison must be mocked — without it firstTimestamp/lastTimestamp
// stay null, currentTimestamp never sets, and the 3D block never renders.
jest.mock('@/hooks/useSessionComparison', () => ({
  useSessionComparison: (a: { frames?: unknown[] } | null, b: { frames?: unknown[] } | null) => {
    if (!a || !b) return null;
    const aHasFrames = Array.isArray(a.frames) && a.frames.length > 0;
    const bHasFrames = Array.isArray(b.frames) && b.frames.length > 0;
    if (!aHasFrames || !bHasFrames) return null;
    return {
      deltas: [{ timestamp_ms: 0 }, { timestamp_ms: 14990 }],
      shared_count: 2,
      total_a: 2,
      total_b: 2,
    };
  },
}));

jest.mock('@/lib/api', () => ({
  fetchSession: jest.fn(),
  fetchSessionAlerts: jest.fn().mockResolvedValue({ alerts: [] }),
}));

jest.mock('@/components/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

const { fetchSession } = jest.requireMock('@/lib/api');

/** Minimal frame matching Frame type — useSessionComparison and useFrameData accept. */
const makeFrame = (ts: number, angle = 45) => ({
  timestamp_ms: ts,
  volts: 22,
  amps: 150,
  angle_degrees: angle,
  thermal_snapshots: [],
  has_thermal_data: false,
  optional_sensors: null,
  heat_dissipation_rate_celsius_per_sec: null,
});

const FRAME_A = makeFrame(0, 45);
const FRAME_B = makeFrame(0, 50);

const SESSION_A = {
  session_id: 'sess_expert_001',
  frames: [FRAME_A],
};
const SESSION_B = {
  session_id: 'sess_novice_001',
  frames: [FRAME_B],
};

/**
 * Renders ComparePageInner directly to bypass use(params) Suspense.
 * In Jest, use(promise) suspends and never resolves; ComparePageInner
 * is exported for testing so we can test the 3D block logic.
 */
function renderComparePage(idA = 'sess_expert_001', idB = 'sess_novice_001') {
  return render(<ComparePageInner sessionIdA={idA} sessionIdB={idB} />);
}

async function waitForLoad() {
  await waitFor(() =>
    expect(screen.queryByText(/loading sessions/i)).not.toBeInTheDocument()
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

beforeEach(() => jest.clearAllMocks());

it('does not render torch block when sessionA frames are empty', async () => {
  fetchSession
    .mockResolvedValueOnce({ session_id: 'sess_expert_001', frames: [] })
    .mockResolvedValueOnce(SESSION_B);
  renderComparePage();
  await waitForLoad();
  expect(screen.queryAllByTestId('torch-3d')).toHaveLength(0);
});

it('does not render torch block when sessionB frames are empty', async () => {
  fetchSession
    .mockResolvedValueOnce(SESSION_A)
    .mockResolvedValueOnce({ session_id: 'sess_novice_001', frames: [] });
  renderComparePage();
  await waitForLoad();
  expect(screen.queryAllByTestId('torch-3d')).toHaveLength(0);
});

it('does not render torch block when both sessions have empty frames', async () => {
  fetchSession
    .mockResolvedValueOnce({ session_id: 'sess_expert_001', frames: [] })
    .mockResolvedValueOnce({ session_id: 'sess_novice_001', frames: [] });
  renderComparePage();
  await waitForLoad();
  expect(screen.queryAllByTestId('torch-3d')).toHaveLength(0);
});

it('renders two torch instances when both sessions have frames', async () => {
  fetchSession
    .mockResolvedValueOnce(SESSION_A)
    .mockResolvedValueOnce(SESSION_B);
  renderComparePage();
  await waitForLoad();
  await waitFor(() => {
    expect(screen.getAllByTestId('torch-3d')).toHaveLength(2);
  });
});

it('session A torch receives correct label', async () => {
  fetchSession
    .mockResolvedValueOnce(SESSION_A)
    .mockResolvedValueOnce(SESSION_B);
  renderComparePage('sess_expert_001', 'sess_novice_001');
  await waitForLoad();
  await waitFor(() => {
    const torches = screen.getAllByTestId('torch-3d');
    const labels = torches.map((el) => el.getAttribute('data-label'));
    expect(labels).toContain('Session A (sess_expert_001)');
  });
});

it('session B torch receives correct label', async () => {
  fetchSession
    .mockResolvedValueOnce(SESSION_A)
    .mockResolvedValueOnce(SESSION_B);
  renderComparePage('sess_expert_001', 'sess_novice_001');
  await waitForLoad();
  await waitFor(() => {
    const torches = screen.getAllByTestId('torch-3d');
    const labels = torches.map((el) => el.getAttribute('data-label'));
    expect(labels).toContain('Session B (sess_novice_001)');
  });
});
