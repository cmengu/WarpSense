/**
 * Tests for TrajectoryChart — multi-line skill trajectory chart.
 */
import { render, screen } from "@testing-library/react";
import { TrajectoryChart } from "@/components/welding/TrajectoryChart";

const mockTrajectoryEmpty = {
  welder_id: "mike-chen",
  points: [],
  trend_slope: null,
  projected_next_score: null,
};

const mockTrajectorySingle = {
  welder_id: "mike-chen",
  points: [
    {
      session_id: "sess_001",
      session_date: "2025-01-01T00:00:00Z",
      score_total: 72,
      metrics: [],
      session_index: 1,
    },
  ],
  trend_slope: null,
  projected_next_score: null,
};

const mockTrajectoryImproving = {
  welder_id: "mike-chen",
  points: [
    { session_id: "s1", session_date: "2025-01-01", score_total: 70, metrics: [], session_index: 1 },
    { session_id: "s2", session_date: "2025-01-02", score_total: 75, metrics: [], session_index: 2 },
  ],
  trend_slope: 5.0,
  projected_next_score: 80,
};

const mockTrajectoryDeclining = {
  welder_id: "mike-chen",
  points: [
    { session_id: "s1", session_date: "2025-01-01", score_total: 85, metrics: [], session_index: 1 },
    { session_id: "s2", session_date: "2025-01-02", score_total: 80, metrics: [], session_index: 2 },
  ],
  trend_slope: -5.0,
  projected_next_score: 75,
};

const mockTrajectoryStable = {
  welder_id: "mike-chen",
  points: [
    { session_id: "s1", session_date: "2025-01-01", score_total: 75, metrics: [], session_index: 1 },
    { session_id: "s2", session_date: "2025-01-02", score_total: 75, metrics: [], session_index: 2 },
  ],
  trend_slope: 0.0,
  projected_next_score: 75,
};

describe("TrajectoryChart", () => {
  it("shows empty state when no points", () => {
    render(<TrajectoryChart trajectory={mockTrajectoryEmpty} />);
    expect(screen.getByTestId("trajectory-empty")).toBeInTheDocument();
    expect(screen.getByText(/No session history available yet/)).toBeInTheDocument();
  });

  it("shows Skill Trajectory heading with points", () => {
    render(<TrajectoryChart trajectory={mockTrajectorySingle} />);
    expect(screen.getByText(/Skill Trajectory/)).toBeInTheDocument();
    expect(screen.getByTestId("trajectory-chart")).toBeInTheDocument();
  });

  it("shows Improving trend when trend_slope > 0.5", () => {
    render(<TrajectoryChart trajectory={mockTrajectoryImproving} />);
    expect(screen.getByTestId("trajectory-chart-trend")).toHaveTextContent("↑ Improving");
  });

  it("shows Declining trend when trend_slope < -0.5", () => {
    render(<TrajectoryChart trajectory={mockTrajectoryDeclining} />);
    expect(screen.getByTestId("trajectory-chart-trend")).toHaveTextContent("↓ Declining");
  });

  it("shows Stable trend when trend_slope in [-0.5, 0.5]", () => {
    render(<TrajectoryChart trajectory={mockTrajectoryStable} />);
    expect(screen.getByTestId("trajectory-chart-trend")).toHaveTextContent("→ Stable");
  });

  it("renders Line chart with data paths (Recharts path elements)", () => {
    render(<TrajectoryChart trajectory={mockTrajectoryImproving} />);
    const chart = screen.getByTestId("trajectory-chart");
    const paths = chart.querySelectorAll("path");
    const pathsWithD = Array.from(paths).filter((p) => {
      const d = p.getAttribute("d");
      return d && d.length > 50;
    });
    expect(pathsWithD.length).toBeGreaterThan(0);
  });

  it("shows projected next session when projected_next_score is set", () => {
    render(<TrajectoryChart trajectory={mockTrajectoryImproving} />);
    expect(screen.getByText(/Projected next session/)).toBeInTheDocument();
    expect(screen.getByText(/80\/100/)).toBeInTheDocument();
  });
});
