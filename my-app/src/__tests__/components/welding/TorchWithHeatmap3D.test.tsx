/**
 * TorchWithHeatmap3D verification — unified torch + thermal metal.
 *
 * Tests HUD rendering, props display, flat vs thermal (frames empty vs with data),
 * context-loss overlay. Canvas/WebGL mocked; ThermalPlate/Three.js not exercised.
 *
 * Context-loss test uses simulateContextLoss prop instead of global mutation.
 *
 * @see .cursor/plans/unified-torch-heatmap-replay-plan.md Step 4.2
 */

import { render, screen, act } from '@testing-library/react';
import TorchWithHeatmap3D, {
  WORKPIECE_GROUP_Y,
} from '@/components/welding/TorchWithHeatmap3D';
import { WORKPIECE_BASE_Y } from '@/constants/welding3d';
import { THERMAL_MIN_TEMP, THERMAL_MAX_TEMP } from '@/constants/thermal';

// Mock RectAreaLightUniformsLib — TorchSceneContent imports it; ESM module, Jest doesn't transform
jest.mock('three/addons/lights/RectAreaLightUniformsLib.js', () => ({
  RectAreaLightUniformsLib: { init: () => {} },
}));

jest.mock('@react-three/fiber', () => ({
  Canvas: (props: {
    onCreated?: (state: { gl: { domElement: HTMLCanvasElement } }) => void;
  }) => {
    if (typeof props?.onCreated === 'function') {
      const canvas = document.createElement('canvas');
      props.onCreated({ gl: { domElement: canvas } });
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

jest.mock('next/font/google', () => ({
  Orbitron: () => ({ className: 'font-orbitron' }),
  JetBrains_Mono: () => ({ className: 'font-jetbrains-mono' }),
}));

const thermalFrame = {
  timestamp_ms: 100,
  volts: 22,
  amps: 150,
  angle_degrees: 45,
  thermal_snapshots: [
    {
      distance_mm: 10,
      readings: [
        { direction: 'center' as const, temp_celsius: 400 },
        { direction: 'north' as const, temp_celsius: 380 },
        { direction: 'south' as const, temp_celsius: 390 },
        { direction: 'east' as const, temp_celsius: 370 },
        { direction: 'west' as const, temp_celsius: 375 },
      ],
    },
  ],
  has_thermal_data: true,
  optional_sensors: null,
  heat_dissipation_rate_celsius_per_sec: null,
};

describe('TorchWithHeatmap3D', () => {
  it('renders without error with frames=[] (flat metal)', () => {
    expect(() => {
      render(
        <TorchWithHeatmap3D
          angle={45}
          temp={400}
          frames={[]}
          activeTimestamp={0}
        />
      );
    }).not.toThrow();
  });

  it('renders without error with thermal frames', () => {
    expect(() => {
      render(
        <TorchWithHeatmap3D
          angle={45}
          temp={400}
          frames={[thermalFrame]}
          activeTimestamp={100}
        />
      );
    }).not.toThrow();
  });

  it('renders label in HUD when provided', () => {
    render(
      <TorchWithHeatmap3D
        angle={45}
        temp={400}
        label="Expert Technique"
        frames={[]}
      />
    );
    expect(screen.getByText(/expert technique/i)).toBeInTheDocument();
  });

  it('displays angle and temp in HUD', () => {
    render(
      <TorchWithHeatmap3D
        angle={52.5}
        temp={425}
        label="Test"
        frames={[]}
      />
    );
    expect(screen.getByText('52.5°')).toBeInTheDocument();
    expect(screen.getByText('425°C')).toBeInTheDocument();
  });

  it('shows temp scale from minTemp–maxTemp props', () => {
    render(
      <TorchWithHeatmap3D
        angle={45}
        temp={400}
        label="Test"
        frames={[]}
        minTemp={THERMAL_MIN_TEMP}
        maxTemp={THERMAL_MAX_TEMP}
      />
    );
    expect(screen.getByText(/0–500°C/i)).toBeInTheDocument();
  });

  it('shows custom temp scale when minTemp/maxTemp provided', () => {
    render(
      <TorchWithHeatmap3D
        angle={45}
        temp={400}
        minTemp={100}
        maxTemp={600}
        frames={[]}
      />
    );
    expect(screen.getByText(/100–600°C/i)).toBeInTheDocument();
  });

  it('renders HUD above canvas when labelPosition=outside', () => {
    render(
      <TorchWithHeatmap3D
        angle={45}
        temp={400}
        label="Session A"
        labelPosition="outside"
        frames={[]}
      />
    );
    expect(screen.getByTestId('hud-outside')).toBeInTheDocument();
    expect(screen.queryByTestId('hud-inside')).not.toBeInTheDocument();
  });

  describe('TorchWithHeatmap3D constants application', () => {
    it('workpiece group uses WORKPIECE_BASE_Y from welding3d', () => {
      expect(WORKPIECE_GROUP_Y).toBe(WORKPIECE_BASE_Y);
      expect(WORKPIECE_GROUP_Y).toBe(-0.85);
    });
  });

  it('shows WebGL context lost overlay when simulateContextLoss is true', async () => {
    render(
      <TorchWithHeatmap3D
        angle={45}
        temp={400}
        frames={[]}
        simulateContextLoss
      />
    );
    await act(async () => {
      await new Promise<void>((resolve) => queueMicrotask(() => resolve()));
    });
    expect(screen.getByText(/WebGL context lost/i)).toBeInTheDocument();
  });
});
