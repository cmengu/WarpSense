import { render, screen } from "@testing-library/react";
import { ReportLayout } from "@/components/layout/ReportLayout";

describe("ReportLayout", () => {
  it("renders thresholdSpec in header when provided", () => {
    render(
      <ReportLayout
        welderName="Test Welder"
        sessionId="sess_1"
        scoreTotal={80}
        thresholdSpec={<>Evaluated against MIG spec — Target 45° ±5°</>}
      />
    );
    const thresholdEl = screen.getByTestId("header-threshold");
    expect(thresholdEl).toBeInTheDocument();
    expect(thresholdEl).toHaveTextContent(/Evaluated against.*MIG spec/);
  });

  it("does not render header-threshold when thresholdSpec absent", () => {
    render(
      <ReportLayout
        welderName="Test Welder"
        sessionId="sess_1"
        scoreTotal={80}
      />
    );
    expect(screen.queryByTestId("header-threshold")).not.toBeInTheDocument();
  });

  it("renders thresholdSpec in header, not in narrative", () => {
    render(
      <ReportLayout
        welderName="Test"
        sessionId="sess_1"
        scoreTotal={80}
        thresholdSpec={<>Evaluated against TIG spec</>}
        narrative={<div>🤖 AI Analysis: Strong.</div>}
      />
    );
    const narrativeEl = screen.getByTestId("report-narrative");
    expect(narrativeEl).not.toHaveTextContent(/Evaluated against/);
  });

  it("renders progress slot with trend-chart data-testid inside progress-slot", () => {
    render(
      <ReportLayout
        welderName="Test"
        sessionId="sess_1"
        scoreTotal={80}
        progress={
          <div data-testid="trend-chart">Chart placeholder</div>
        }
      />
    );
    const progressSlot = screen.getByTestId("progress-slot");
    const trendChart = screen.getByTestId("trend-chart");
    expect(progressSlot).toContainElement(trendChart);
  });
});
