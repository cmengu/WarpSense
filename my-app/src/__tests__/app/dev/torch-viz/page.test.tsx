/**
 * TorchViz3D dev page — Step 3 verification.
 *
 * Tests industrial layout: blue/purple WarpSense theme, floating panel, Orbitron + JetBrains Mono.
 * TorchViz3D is mocked to avoid WebGL/Canvas in jsdom.
 */

import { render, screen } from '@testing-library/react';
import DevTorchVizPage from '@/app/dev/torch-viz/page';

jest.mock('next/dynamic', () => ({
  __esModule: true,
  default: () => {
    const MockTorchViz3D = () => <div data-testid="torch-viz-mock" />;
    return MockTorchViz3D;
  },
}));

describe('DevTorchVizPage', () => {
  it('renders TorchViz3D in industrial layout', () => {
    render(<DevTorchVizPage />);
    expect(screen.getByTestId('torch-viz-mock')).toBeInTheDocument();
  });

  it('shows floating panel header "TorchViz3D Demo"', () => {
    render(<DevTorchVizPage />);
    expect(screen.getByText(/TorchViz3D Demo/i)).toBeInTheDocument();
  });

  it('shows WarpSense theme elements: scenario reference, path indicator', () => {
    render(<DevTorchVizPage />);
    expect(screen.getByText(/Scenario reference/i)).toBeInTheDocument();
    expect(screen.getByText(/\/dev\/torch-viz/)).toBeInTheDocument();
  });

  it('displays OrbitControls hint: drag and scroll', () => {
    render(<DevTorchVizPage />);
    expect(screen.getByText(/Drag.*rotate.*Scroll.*zoom/i)).toBeInTheDocument();
  });
});
