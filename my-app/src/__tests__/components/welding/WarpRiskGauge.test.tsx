import React from 'react';
import { render, screen } from '@testing-library/react';
import { WarpRiskGauge } from '@/components/welding/WarpRiskGauge';

describe('WarpRiskGauge', () => {
  it('shows Model unavailable when modelAvailable is false', () => {
    render(
      <WarpRiskGauge probability={0} riskLevel="ok" modelAvailable={false} />
    );
    expect(screen.getByTestId('warp-risk-gauge-unavailable')).toHaveTextContent(
      'Model unavailable'
    );
  });

  it('shows probability when modelAvailable is true', () => {
    render(
      <WarpRiskGauge probability={0.3} riskLevel="ok" modelAvailable={true} />
    );
    expect(screen.getByTestId('warp-risk-gauge')).toHaveTextContent('30%');
  });

  it('riskLevel warning applies bg-amber-400/10 class', () => {
    render(
      <WarpRiskGauge
        probability={0.6}
        riskLevel="warning"
        modelAvailable={true}
      />
    );
    const gauge = screen.getByTestId('warp-risk-gauge');
    expect(gauge).toHaveClass('bg-amber-400/10');
  });

  it('riskLevel critical applies bg-red-500/10 class', () => {
    render(
      <WarpRiskGauge
        probability={0.85}
        riskLevel="critical"
        modelAvailable={true}
      />
    );
    const gauge = screen.getByTestId('warp-risk-gauge');
    expect(gauge).toHaveClass('bg-red-500/10');
  });
});
