/**
 * Seagull pilot end-to-end smoke tests.
 *
 * Verifies full user paths with mocked APIs:
 *   - Dashboard loads → 10 cards with scores or "Score unavailable"
 *   - WelderReport loads → score, AI summary, heatmaps, feedback, chart
 *   - Back link navigates to /seagull
 *   - Error state when fetch fails → error card with back link
 */

import { render, screen, waitFor } from "@testing-library/react";
import SeagullDashboardPage from "@/app/seagull/page";
import WelderReportPage from "@/app/seagull/welder/[id]/page";

const mockFetchSession = jest.fn();
const mockFetchScore = jest.fn();

jest.mock("@/lib/api", () => ({
  fetchSession: (...args: unknown[]) => mockFetchSession(...args),
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
}));

const mockSession = {
  session_id: "sess_mike-chen_005",
  operator_id: "mike-chen",
  start_time: "2026-02-07T10:00:00Z",
  weld_type: "butt_joint",
  thermal_sample_interval_ms: 100,
  thermal_directions: ["center", "north", "south", "east", "west"],
  thermal_distance_interval_mm: 10.0,
  sensor_sample_rate_hz: 100,
  frames: [
    {
      timestamp_ms: 0,
      volts: 22,
      amps: 150,
      angle_degrees: 45,
      thermal_snapshots: [
        {
          distance_mm: 10,
          readings: [{ direction: "center" as const, temp_celsius: 400 }],
        },
      ],
      has_thermal_data: true,
      optional_sensors: null,
      heat_dissipation_rate_celsius_per_sec: null,
    },
  ],
  status: "complete" as const,
  frame_count: 1,
  expected_frame_count: 1,
  last_successful_frame_index: 0,
  validation_errors: [],
  completed_at: "2026-02-07T10:00:01Z",
};

const mockScore = { total: 75, rules: [{ rule_id: "amps", passed: true, threshold: 3, actual_value: 1 }] };
const mockScoreExpert = { total: 95, rules: [{ rule_id: "amps", passed: true, threshold: 3, actual_value: 1 }] };

describe("Seagull flow smoke tests", () => {
  beforeEach(() => {
    mockFetchSession.mockResolvedValue(mockSession);
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId === "sess_expert-benchmark_005") return Promise.resolve(mockScoreExpert);
      return Promise.resolve(mockScore);
    });
  });

  it("dashboard loads with 10 cards; no crash", async () => {
    render(<SeagullDashboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
    expect(screen.getByText(/Sara Okafor/)).toBeInTheDocument();
  });

  it("welder report loads with score, AI summary, heatmaps, feedback, chart; no crash", async () => {
    render(<WelderReportPage params={{ id: "mike-chen" }} />);
    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Mike Chen — Weekly Report/)).toBeInTheDocument();
    expect(screen.getByText(/🤖 AI Analysis:/)).toBeInTheDocument();
    expect(screen.getByText(/Thermal Comparison/)).toBeInTheDocument();
    expect(screen.getByText(/Detailed Feedback/)).toBeInTheDocument();
    expect(screen.getByText(/Progress Over Time/)).toBeInTheDocument();
  });

  it("welder report has Back link to /seagull", async () => {
    render(<WelderReportPage params={{ id: "mike-chen" }} />);
    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });
    const backLink = screen.getByRole("link", {
      name: /← Back to Team Dashboard/i,
    });
    expect(backLink).toHaveAttribute("href", "/seagull");
  });

  it("welder report shows error card with back link when fetch fails", async () => {
    mockFetchSession.mockRejectedValueOnce(new Error("404"));

    render(<WelderReportPage params={{ id: "mike-chen" }} />);
    await waitFor(() => {
      expect(screen.getByText(/⚠️ Error/)).toBeInTheDocument();
    });
    const backLink = screen.getByRole("link", {
      name: /← Back to Team Dashboard/i,
    });
    expect(backLink).toHaveAttribute("href", "/seagull");
  });
});
