/**
 * TorchViz3D verification — Step 2.
 *
 * Tests HUD rendering (Orbitron/JetBrains Mono), props display, industrial labels,
 * WebGL context lost overlay. Canvas/WebGL is mocked to avoid jsdom WebGL issues.
 */

import { render, screen, waitFor, act } from '@testing-library/react';
import TorchViz3D from '@/components/welding/TorchViz3D';

// Mock R3F Canvas — avoid WebGL in jsdom; invokes onCreated + dispatches contextlost only when __TORCHVIZ_TEST_CONTEXT_LOSS is set
jest.mock('@react-three/fiber', () => ({
  Canvas: (props: { onCreated?: (state: { gl: { domElement: HTMLCanvasElement } }) => void }) => {
    if (typeof props?.onCreated === 'function') {
      const canvas = document.createElement('canvas');
      props.onCreated({ gl: { domElement: canvas } });
      if ((global as { __TORCHVIZ_TEST_CONTEXT_LOSS?: boolean }).__TORCHVIZ_TEST_CONTEXT_LOSS) {
        queueMicrotask(() => {
          canvas.dispatchEvent(new Event('webglcontextlost', { bubbles: false }));
        });
      }
    }
    return <div data-testid="r3f-canvas-mock" />;
  },
  useFrame: () => {},
}));

jest.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Environment: () => null,
  ContactShadows: () => null,
  PerspectiveCamera: () => null,
}));

// Mock next/font — return simple className
jest.mock('next/font/google', () => ({
  Orbitron: () => ({ className: 'font-orbitron' }),
  JetBrains_Mono: () => ({ className: 'font-jetbrains-mono' }),
}));

describe('TorchViz3D', () => {
  it('renders label in HUD when provided', () => {
    render(<TorchViz3D angle={45} temp={400} label="Current Session" />);
    expect(screen.getByText(/current session/i)).toBeInTheDocument();
  });

  it('displays angle and temp in HUD', () => {
    render(<TorchViz3D angle={52.5} temp={425} label="Test" />);
    expect(screen.getByText('52.5°')).toBeInTheDocument();
    expect(screen.getByText('425°C')).toBeInTheDocument();
  });

  it('shows industrial labels: Torch angle, Weld pool temp', () => {
    render(<TorchViz3D angle={45} temp={400} label="Test" />);
    expect(screen.getByText(/torch angle/i)).toBeInTheDocument();
    expect(screen.getByText(/weld pool temp/i)).toBeInTheDocument();
  });

  it('shows status LED and temp scale indicator', () => {
    render(<TorchViz3D angle={45} temp={400} label="Test" />);
    expect(screen.getByText(/0–700°C/i)).toBeInTheDocument();
  });

  it('shows technical footer SENSOR_ID', () => {
    render(<TorchViz3D angle={45} temp={400} label="Test" />);
    expect(screen.getByText(/SENSOR_ID: TH_001/i)).toBeInTheDocument();
  });

  it('uses blue theme classes', () => {
    const { container } = render(<TorchViz3D angle={45} temp={400} label="Test" />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toMatch(/border-blue|bg-neutral-950|shadow/);
  });

  it('shows WebGL context lost overlay when context is lost', async () => {
    (global as { __TORCHVIZ_TEST_CONTEXT_LOSS?: boolean }).__TORCHVIZ_TEST_CONTEXT_LOSS = true;
    try {
      render(<TorchViz3D angle={45} temp={400} label="Test" />);
      await act(async () => {
        await new Promise<void>((resolve) => queueMicrotask(() => resolve()));
      });
      expect(screen.getByText(/WebGL context lost/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Reload 3D view without refreshing/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Refresh the page to restore/i })).toBeInTheDocument();
    } finally {
      delete (global as { __TORCHVIZ_TEST_CONTEXT_LOSS?: boolean }).__TORCHVIZ_TEST_CONTEXT_LOSS;
    }
  });

  it('context lost overlay has keyboard-accessible refresh button', async () => {
    (global as { __TORCHVIZ_TEST_CONTEXT_LOSS?: boolean }).__TORCHVIZ_TEST_CONTEXT_LOSS = true;
    try {
      render(<TorchViz3D angle={45} temp={400} label="Test" />);
      await act(async () => {
        await new Promise<void>((resolve) => queueMicrotask(() => resolve()));
      });
      const refreshBtn = screen.getByRole('button', {
        name: /Refresh the page to restore 3D view/i,
      });
      expect(refreshBtn).toBeInTheDocument();
      expect(refreshBtn).toHaveAttribute('type', 'button');
    } finally {
      delete (global as { __TORCHVIZ_TEST_CONTEXT_LOSS?: boolean }).__TORCHVIZ_TEST_CONTEXT_LOSS;
    }
  });
});
