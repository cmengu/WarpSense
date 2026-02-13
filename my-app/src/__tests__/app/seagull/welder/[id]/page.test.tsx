/**
 * Tests for WelderReport page (Seagull pilot Step 3).
 *
 * Validates:
 *   - Renders score header, AI summary, heatmaps, feedback, chart when data loads
 *   - Error state with back link when fetch fails
 *   - Back nav link to /seagull
 *   - Promise.all fetches session, expert session, score
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import WelderReportPage from "@/app/seagull/welder/[id]/page";

const mockFetchSession = jest.fn();
const mockFetchScore = jest.fn();

jest.mock("@/lib/api", () => ({
  fetchSession: (...args: unknown[]) => mockFetchSession(...args),
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
}));

const mockSession = {
  session_id: "sess_novice_001",
  operator_id: "op_1",
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

const mockScore = {
  total: 75,
  rules: [
    {
      rule_id: "amps_stability",
      threshold: 3,
      passed: false,
      actual_value: 5.2,
    },
    {
      rule_id: "angle_consistency",
      threshold: 5,
      passed: true,
      actual_value: 3.1,
    },
  ],
};

describe("WelderReportPage", () => {
  beforeEach(() => {
    mockFetchSession.mockResolvedValue(mockSession);
    mockFetchScore.mockResolvedValue(mockScore);
  });

  it("renders report with score, AI summary, heatmaps, feedback when data loads", async () => {
    render(<WelderReportPage params={{ id: "mike-chen" }} />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen — Weekly Report/)).toBeInTheDocument();
    expect(screen.getByText(/🤖 AI Analysis:/)).toBeInTheDocument();
    expect(screen.getByText(/Thermal Comparison/)).toBeInTheDocument();
    expect(screen.getByText(/Detailed Feedback/)).toBeInTheDocument();
    expect(screen.getByText(/Progress Over Time/)).toBeInTheDocument();
    // Step 5: LineChart receives MOCK_HISTORICAL; no "No data available"
    expect(screen.queryByText(/No data available/)).not.toBeInTheDocument();
  });

  it("shows error state with back link when fetch fails", async () => {
    mockFetchSession.mockRejectedValueOnce(new Error("Network error"));

    render(<WelderReportPage params={{ id: "mike-chen" }} />);

    await waitFor(() => {
      expect(screen.getByText(/⚠️ Error/)).toBeInTheDocument();
    });

    const backLink = screen.getByRole("link", {
      name: /← Back to Team Dashboard/i,
    });
    expect(backLink).toBeInTheDocument();
    expect(backLink).toHaveAttribute("href", "/seagull");
  });

  it("fetches session (×2), expert session, and score via Promise.all", async () => {
    render(<WelderReportPage params={{ id: "mike-chen" }} />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    expect(mockFetchSession).toHaveBeenCalledWith("sess_novice_001", {
      limit: 2000,
    });
    expect(mockFetchSession).toHaveBeenCalledWith("sess_expert_001", {
      limit: 2000,
    });
    expect(mockFetchScore).toHaveBeenCalledWith("sess_novice_001");
  });

  it("maps expert-benchmark id to sess_expert_001", async () => {
    render(<WelderReportPage params={{ id: "expert-benchmark" }} />);

    await waitFor(() => {
      expect(screen.getByText(/Expert Benchmark — Weekly Report/)).toBeInTheDocument();
    });

    expect(mockFetchSession).toHaveBeenCalledWith("sess_expert_001", {
      limit: 2000,
    });
  });

  it("shows Back to Team Dashboard link when report loads", async () => {
    render(<WelderReportPage params={{ id: "mike-chen" }} />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    const backLink = screen.getByRole("link", {
      name: /← Back to Team Dashboard/i,
    });
    expect(backLink).toHaveAttribute("href", "/seagull");
  });

  describe("Step 7: Export stubs", () => {
    it("Email Report button shows alert when clicked", async () => {
      const alertSpy = jest.spyOn(window, "alert").mockImplementation(() => {});

      render(<WelderReportPage params={{ id: "mike-chen" }} />);
      await waitFor(() => {
        expect(screen.getByText(/75\/100/)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Email Report/i }));
      expect(alertSpy).toHaveBeenCalledWith("Email report — coming soon");

      alertSpy.mockRestore();
    });

    it("Download PDF button shows alert when clicked", async () => {
      const alertSpy = jest.spyOn(window, "alert").mockImplementation(() => {});

      render(<WelderReportPage params={{ id: "mike-chen" }} />);
      await waitFor(() => {
        expect(screen.getByText(/75\/100/)).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /Download PDF/i }));
      expect(alertSpy).toHaveBeenCalledWith("Download PDF — coming soon");

      alertSpy.mockRestore();
    });
  });
});
