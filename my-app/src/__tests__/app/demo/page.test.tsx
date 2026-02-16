/**
 * Demo page — smoke test for browser-only demo mode.
 *
 * Verifies that the demo page renders expert/novice columns, scores,
 * playback controls, and demo-mode footer.
 *
 * Mocks used to avoid jsdom incompatibilities:
 *   - TorchViz3D: WebGL/three.js not available in jsdom
 *   - HeatMap: avoid SVG/CSS grid layout edge cases
 *   - TorchAngleGraph: Recharts ResponsiveContainer needs real dimensions
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import DemoPage from '@/app/demo/page';

// Mock WebGL/3D component to avoid three.js in jsdom
// next/dynamic(importFn, options?) returns a component
jest.mock('next/dynamic', () => ({
  __esModule: true,
  default: (
    _importFn: () => Promise<{ default: React.ComponentType }>,
    _options?: { ssr?: boolean; loading?: React.ComponentType }
  ) => {
    const DynamicComponent = () => <div data-testid="torch-with-heatmap-3d-mock" />;
    return DynamicComponent;
  },
}));

// Mock HeatMap and TorchAngleGraph to avoid Recharts/SVG issues in jsdom
jest.mock('@/components/welding/HeatMap', () => ({
  __esModule: true,
  default: () => <div data-testid="heatmap-mock" />,
}));
jest.mock('@/components/welding/TorchAngleGraph', () => ({
  __esModule: true,
  default: () => <div data-testid="torch-angle-graph-mock" />,
}));

/** Wait for session generation (useEffect) to complete; content replaces loading state. */
async function waitForDemoContent() {
  await waitFor(() => {
    expect(screen.queryByText(/Loading demo…/i)).not.toBeInTheDocument();
    expect(screen.getByText(/WarpSense/i)).toBeInTheDocument();
  });
}

describe('DemoPage', () => {
  it('shows loading state initially', () => {
    render(<DemoPage />);
    expect(screen.getByText(/Loading demo…/i)).toBeInTheDocument();
  });

  it('renders header with WarpSense', async () => {
    render(<DemoPage />);
    await waitForDemoContent();
    expect(screen.getByText(/WarpSense/i)).toBeInTheDocument();
    expect(screen.getByText(/Live Quality Analysis/i)).toBeInTheDocument();
  });

  it('renders expert and novice columns with scores', async () => {
    render(<DemoPage />);
    await waitForDemoContent();
    expect(screen.getByText(/EXPERT WELDER/i)).toBeInTheDocument();
    expect(screen.getByText(/94\/100/)).toBeInTheDocument();
    expect(screen.getByText(/NOVICE WELDER/i)).toBeInTheDocument();
    expect(screen.getByText(/42\/100/)).toBeInTheDocument();
  });

  it('renders playback controls with play button', async () => {
    render(<DemoPage />);
    await waitForDemoContent();
    expect(screen.getByRole('button', { name: /play demo/i })).toBeInTheDocument();
    expect(screen.getByText(/Time/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/scrub playback position/i)).toBeInTheDocument();
  });

  it('shows demo mode footer', async () => {
    render(<DemoPage />);
    await waitForDemoContent();
    expect(screen.getByText(/DEMO MODE — No backend required/i)).toBeInTheDocument();
  });

  it('renders TorchWithHeatmap3D placeholders (mocked)', async () => {
    render(<DemoPage />);
    await waitForDemoContent();
    const mocks = screen.getAllByTestId('torch-with-heatmap-3d-mock');
    expect(mocks.length).toBe(2); // expert + novice
  });

  /**
   * WebGL context loss prevention: demo page uses at most 2 TorchWithHeatmap3D instances.
   * Per .cursor/issues/webgl-context-lost-consistent-project-wide.md and constants/webgl.ts.
   */
  it('uses at most 2 TorchWithHeatmap3D instances', async () => {
    render(<DemoPage />);
    await waitForDemoContent();
    const torchMocks = screen.getAllByTestId('torch-with-heatmap-3d-mock');
    expect(torchMocks.length).toBeLessThanOrEqual(2);
  });

  it('renders TorchAngleGraph placeholders (mocked)', async () => {
    render(<DemoPage />);
    await waitForDemoContent();
    const angleGraphs = screen.getAllByTestId('torch-angle-graph-mock');
    expect(angleGraphs.length).toBe(2); // expert + novice
  });

  it('renders feedback bullets for expert and novice', async () => {
    render(<DemoPage />);
    await waitForDemoContent();
    expect(screen.getByText(/Consistent temperature/i)).toBeInTheDocument();
    expect(screen.getByText(/Steady torch angle/i)).toBeInTheDocument();
    expect(screen.getByText(/Temperature spike at 2.3s/i)).toBeInTheDocument();
    expect(screen.getByText(/Torch angle drift/i)).toBeInTheDocument();
  });

  it('toggles playback when play/pause button is clicked', async () => {
    render(<DemoPage />);
    await waitForDemoContent();
    const playButton = screen.getByRole('button', { name: /play demo/i });
    expect(playButton).toBeInTheDocument();

    fireEvent.click(playButton);
    expect(screen.getByRole('button', { name: /pause demo/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /pause demo/i }));
    expect(screen.getByRole('button', { name: /play demo/i })).toBeInTheDocument();
  });
});
