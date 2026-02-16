/**
 * HeatmapPlate3D unit test — Step 1.10.
 *
 * Verifies component renders without crash when given thermal frames.
 * R3F/Canvas mocked to avoid WebGL in jsdom.
 *
 * @see .cursor/plans/3d-warped-heatmap-plate-implementation-plan.md Step 1.10
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import HeatmapPlate3D from '@/components/welding/HeatmapPlate3D';
import type { Frame } from '@/types/frame';

// Mock R3F Canvas — avoid WebGL; do not render 3D children (mesh, etc.) in jsdom
jest.mock('@react-three/fiber', () => ({
  Canvas: () => <div data-testid="heatmap-plate-3d-canvas" />,
}));

jest.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
}));

function makeThermalFrame(ts: number, centerTemp: number): Frame {
  return {
    timestamp_ms: ts,
    volts: 22,
    amps: 150,
    angle_degrees: 45,
    thermal_snapshots: [
      {
        distance_mm: 10,
        readings: [
          { direction: 'center', temp_celsius: centerTemp },
          { direction: 'north', temp_celsius: centerTemp - 20 },
          { direction: 'south', temp_celsius: centerTemp - 15 },
          { direction: 'east', temp_celsius: centerTemp - 10 },
          { direction: 'west', temp_celsius: centerTemp - 12 },
        ],
      },
    ],
    has_thermal_data: true,
    optional_sensors: null,
    heat_dissipation_rate_celsius_per_sec: null,
  };
}

describe('HeatmapPlate3D', () => {
  it('renders without crash with thermal frames', () => {
    const frames: Frame[] = [
      makeThermalFrame(0, 400),
      makeThermalFrame(100, 450),
    ];
    expect(() => {
      render(
        <HeatmapPlate3D
          frames={frames}
          activeTimestamp={0}
          maxTemp={600}
          plateSize={10}
        />
      );
    }).not.toThrow();
  });

  it('renders canvas container with role img', () => {
    const frames: Frame[] = [makeThermalFrame(0, 400)];
    render(<HeatmapPlate3D frames={frames} />);
    const container = screen.getByRole('img', {
      name: /3D heatmap plate with thermal warping/i,
    });
    expect(container).toBeInTheDocument();
  });

  it('renders when frames is empty', () => {
    expect(() => {
      render(<HeatmapPlate3D frames={[]} />);
    }).not.toThrow();
  });
});
