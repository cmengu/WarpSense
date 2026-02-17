/**
 * Integration tests for Demo Welder Report page.
 *
 * Validates:
 *   - mike-chen and expert-benchmark render with correct scores
 *   - Empty frames → PlaceholderHeatMap renders; no white screen
 */

import { render, screen, waitFor } from "@testing-library/react";
import DemoTeamWelderPage from "@/app/demo/team/[welderId]/page";
import * as seagullDemoData from "@/lib/seagull-demo-data";

const mockGetDemoTeamData = jest.spyOn(
  seagullDemoData,
  "getDemoTeamData"
);

const minimalSession = {
  session_id: "demo_empty",
  operator_id: "op_1",
  start_time: "2026-02-07T10:00:00Z",
  weld_type: "butt_joint",
  thermal_sample_interval_ms: 100,
  thermal_directions: ["center", "north", "south", "east", "west"],
  thermal_distance_interval_mm: 10.0,
  sensor_sample_rate_hz: 100,
  status: "complete" as const,
  frame_count: 0,
  expected_frame_count: 0,
  last_successful_frame_index: null,
  validation_errors: [],
  completed_at: "2026-02-07T10:00:01Z",
};

describe("DemoTeamWelderPage", () => {
  beforeEach(() => {
    mockGetDemoTeamData.mockImplementation((welderId: string) => {
      const report =
        welderId === "expert-benchmark"
          ? {
              score: 94,
              skill_level: "Advanced",
              trend: "improving" as const,
              summary: "Strong performance.",
              feedback_items: [],
            }
          : {
              score: 42,
              skill_level: "Beginner",
              trend: "stable" as const,
              summary: "Focus on: amps stability.",
              feedback_items: [],
            };
      return {
        session: { ...minimalSession, frames: [] },
        expertSession: { ...minimalSession, frames: [] },
        score: { total: report.score, rules: [] },
        report,
      };
    });
  });

  afterEach(() => {
    mockGetDemoTeamData.mockRestore();
  });

  it("mike-chen renders with score 42", async () => {
    render(
      <DemoTeamWelderPage params={Promise.resolve({ welderId: "mike-chen" })} />
    );

    await waitFor(() => {
      expect(screen.getByText(/42\/100/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen — Weekly Report/)).toBeInTheDocument();
  });

  it("expert-benchmark renders with score 94", async () => {
    render(
      <DemoTeamWelderPage
        params={Promise.resolve({ welderId: "expert-benchmark" })}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/94\/100/)).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Expert Benchmark — Weekly Report/)
    ).toBeInTheDocument();
  });

  it("empty frames → PlaceholderHeatMap renders; no white screen", async () => {
    render(
      <DemoTeamWelderPage params={Promise.resolve({ welderId: "mike-chen" })} />
    );

    await waitFor(() => {
      expect(screen.getByText(/42\/100/)).toBeInTheDocument();
    });

    const placeholders = screen.getAllByText(/No thermal data — demo placeholder/);
    expect(placeholders.length).toBeGreaterThanOrEqual(1);
  });

  it("shows Back to Team Dashboard link", async () => {
    render(
      <DemoTeamWelderPage params={Promise.resolve({ welderId: "mike-chen" })} />
    );

    await waitFor(() => {
      expect(screen.getByText(/42\/100/)).toBeInTheDocument();
    });

    const backLink = screen.getByRole("link", {
      name: /← Back to Team Dashboard/i,
    });
    expect(backLink).toHaveAttribute("href", "/demo/team");
  });

  it("shows Welder not found for unknown welderId", async () => {
    render(
      <DemoTeamWelderPage params={Promise.resolve({ welderId: "unknown-x" })} />
    );

    await waitFor(() => {
      expect(screen.getByText(/Welder not found/)).toBeInTheDocument();
    });
  });
});
