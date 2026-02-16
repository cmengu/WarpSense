/**
 * Tests for LineChart (Seagull pilot Step 5 — TrendChart verification).
 *
 * Validates:
 *   - Prop interface: data { date, value }[], color, height
 *   - Renders in isolation with mock data
 *   - MOCK_HISTORICAL format: 3 points, X-axis Week 1/2/3
 *   - No "No data available" when data provided
 *   - Shows "No data available" when empty
 */

import { render, screen } from "@testing-library/react";
import { LineChart } from "@/components/charts/LineChart";

const MOCK_HISTORICAL = [
  { date: "Week 1", value: 68 },
  { date: "Week 2", value: 72 },
  { date: "Week 3", value: 75 },
];

describe("LineChart — Step 5 TrendChart verification", () => {
  it("renders in isolation with single point", () => {
    render(<LineChart data={[{ date: "W1", value: 70 }]} />);
    expect(screen.queryByText(/No data available/)).not.toBeInTheDocument();
  });

  it("renders MOCK_HISTORICAL with 3 points; no No data available; chart container present", () => {
    const { container } = render(
      <LineChart data={MOCK_HISTORICAL} color="#3b82f6" height={200} />
    );
    expect(screen.queryByText(/No data available/)).not.toBeInTheDocument();
    const responsiveContainer = container.querySelector(
      ".recharts-responsive-container"
    );
    expect(responsiveContainer).toBeInTheDocument();
    expect((responsiveContainer as HTMLElement)?.style.height).toBe("200px");
  });

  it("shows No data available when data is empty", () => {
    render(<LineChart data={[]} />);
    expect(screen.getByText(/No data available/)).toBeInTheDocument();
  });

  it("uses default height (300) when not provided", () => {
    const { container } = render(<LineChart data={MOCK_HISTORICAL} />);
    expect(screen.queryByText(/No data available/)).not.toBeInTheDocument();
    const responsiveContainer = container.querySelector(
      ".recharts-responsive-container"
    );
    expect((responsiveContainer as HTMLElement)?.style.height).toBe("300px");
  });

  it("accepts color and height props", () => {
    const { container } = render(
      <LineChart data={MOCK_HISTORICAL} color="#a855f7" height={150} />
    );
    expect(screen.queryByText(/No data available/)).not.toBeInTheDocument();
    const responsiveContainer = container.querySelector(
      ".recharts-responsive-container"
    );
    expect(responsiveContainer).toBeInTheDocument();
    expect((responsiveContainer as HTMLElement)?.style.height).toBe("150px");
  });
});
