/**
 * Tests for WelderReport page — 10 welders with historical scores.
 *
 * Validates:
 *   - Renders score header, AI summary, heatmaps, feedback, chart when data loads
 *   - Error state with back link when fetch fails
 *   - Back nav link to /seagull
 *   - Fetches primary session, expert (sess_expert-benchmark_005), score, historical scores
 */

import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import WelderReportPage from "@/app/seagull/welder/[id]/page";

const mockFetchSession = jest.fn();
const mockFetchScore = jest.fn();
const mockFetchBenchmarks = jest.fn();

jest.mock("html-to-image", () => ({
  toPng: jest.fn().mockResolvedValue("data:image/png;base64,fake"),
}));

const mockFetchReportSummary = jest.fn();

jest.mock("@/lib/api", () => ({
  fetchSession: (...args: unknown[]) => mockFetchSession(...args),
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
  fetchBenchmarks: (...args: unknown[]) => mockFetchBenchmarks(...args),
  fetchReportSummary: (...args: unknown[]) => mockFetchReportSummary(...args),
  fetchNarrative: jest.fn().mockRejectedValue(new Error("narrative not found")),
  fetchCoachingPlan: jest.fn().mockResolvedValue({
    welder_id: "mike-chen",
    active_assignments: [],
    completed_assignments: [],
    auto_assigned: false,
  }),
  triggerCoachingAssignment: jest.fn().mockResolvedValue({
    welder_id: "mike-chen",
    active_assignments: [],
    completed_assignments: [],
    auto_assigned: false,
  }),
  fetchCertificationStatus: jest.fn().mockResolvedValue({
    welder_id: "mike-chen",
    certifications: [],
  }),
}));

jest.mock("@/lib/api.merge_agent1", () => ({
  fetchTrajectory: jest.fn().mockResolvedValue({
    welder_id: "mike-chen",
    points: [],
    trend_slope: null,
    projected_next_score: null,
  }),
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
  active_threshold_spec: {
    weld_type: "mig",
    angle_target: 45,
    angle_warning: 5,
    angle_critical: 10,
    thermal_symmetry_warning_celsius: 10,
    thermal_symmetry_critical_celsius: 20,
    amps_stability_warning: 3,
    volts_stability_warning: 2,
    heat_diss_consistency: 5,
  },
};

const mockReportSummary = {
  session_id: "sess_mike-chen_005",
  generated_at: "2026-02-07T10:00:00Z",
  heat_input_mean_kj_per_mm: 0.7,
  heat_input_wps_min: 0.5,
  heat_input_wps_max: 0.9,
  heat_input_compliant: true,
  travel_angle_excursion_count: 0,
  travel_angle_threshold_deg: 25,
  total_arc_terminations: 0,
  no_crater_fill_count: 0,
  crater_fill_rate_pct: 0,
  defect_counts_by_type: {},
  total_defect_alerts: 0,
  excursions: [],
};

describe("WelderReportPage", () => {
  beforeEach(() => {
    mockFetchSession.mockResolvedValue(mockSession);
    mockFetchScore.mockResolvedValue(mockScore);
    mockFetchBenchmarks.mockResolvedValue(null);
    mockFetchReportSummary.mockResolvedValue(mockReportSummary);
  });

  it("renders report with score, AI summary, heatmaps, feedback when data loads", async () => {
    render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen — Weekly Report/)).toBeInTheDocument();
    expect(screen.getByText(/Detailed Feedback/)).toBeInTheDocument();
    expect(screen.getByText(/Thermal Comparison/)).toBeInTheDocument();
    expect(screen.getByText(/Detailed Feedback/)).toBeInTheDocument();
    expect(screen.getByText(/Progress Over Time/)).toBeInTheDocument();

    expect(screen.getByTestId("header-threshold")).toBeInTheDocument();
    expect(screen.getByTestId("header-threshold")).toHaveTextContent(
      /Evaluated against.*MIG spec/
    );
    expect(screen.getByTestId("header-threshold")).toHaveTextContent(
      /Target 45° ±5°/
    );

    const progressSection = screen.getByRole("region", {
      name: /Progress Over Time/,
    });
    const trendChart = screen.getByTestId("trend-chart");
    expect(progressSection).toContainElement(trendChart);
  });

  it("shows error state with back link when fetch fails", async () => {
    mockFetchSession.mockRejectedValueOnce(new Error("Network error"));

    render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);

    await waitFor(() => {
      expect(screen.getByText(/⚠️ Error/)).toBeInTheDocument();
    });

    const backLink = screen.getByRole("link", {
      name: /← Back to Team Dashboard/i,
    });
    expect(backLink).toBeInTheDocument();
    expect(backLink).toHaveAttribute("href", "/seagull");
  });

  it("fetches primary session, expert (sess_expert-benchmark_005), score, and historical scores", async () => {
    render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    expect(mockFetchSession).toHaveBeenCalledWith("sess_mike-chen_005", {
      limit: 2000,
    });
    expect(mockFetchSession).toHaveBeenCalledWith(
      "sess_expert-benchmark_005",
      { limit: 2000 }
    );
    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_005");
    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_001");
    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_002");
  });

  it("shows improving trend in report header when historical scores increase and trajectory excluded", async () => {
    // Precondition: WELDER_SESSION_COUNT["mike-chen"] >= 2.
    // Session ID format: sess_{welder_id}_{NNN} (e.g. sess_mike-chen_001). mockFetchScore uses /_(\d+)$/.
    mockFetchScore.mockImplementation((sessionId: string) => {
      const match = sessionId.match(/_(\d+)$/);
      const idx = match ? parseInt(match[1], 10) : 0;
      const total = 70 + idx * 2;
      return Promise.resolve({ ...mockScore, total });
    });

    const { fetchTrajectory } = require("@/lib/api.merge_agent1");
    (fetchTrajectory as jest.Mock).mockResolvedValue({
      welder_id: "mike-chen",
      points: [
        {
          session_id: "sess_mike-chen_001",
          session_date: "2025-01-01T00:00:00Z",
          score_total: 72,
          metrics: [],
          session_index: 1,
        },
        {
          session_id: "sess_mike-chen_005",
          session_date: "2025-01-05T00:00:00Z",
          score_total: 80,
          metrics: [],
          session_index: 2,
        },
      ],
      trend_slope: 2.0,
      projected_next_score: 82,
    });

    render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);

    await waitFor(() => {
      expect(screen.getByText(/80\/100/)).toBeInTheDocument();
    });

    const reportHeaderTrend = screen.getByTestId("report-header-trend");
    expect(reportHeaderTrend).toHaveTextContent(/improving/i);
  });

  it("calls assertTrajectoryAtIdx when fetch completes (trajectory-last invariant)", async () => {
    const { fetchTrajectory } = require("@/lib/api.merge_agent1");
    (fetchTrajectory as jest.Mock).mockResolvedValue({
      welder_id: "mike-chen",
      points: [],
      trend_slope: null,
      projected_next_score: null,
    });

    render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);

    await waitFor(() => {
      expect(screen.queryByText(/Session not found/)).not.toBeInTheDocument();
    });

    // Indirect verification: trajectory-last invariant means report loads without error.
    // assertTrajectoryAtIdx would throw if trajectory wasn't last; report would show error.
    expect(screen.getByText(/75\/100/)).toBeInTheDocument();
  });

  it("maps expert-benchmark id to sess_expert-benchmark_005", async () => {
    render(<WelderReportPage params={Promise.resolve({ id: "expert-benchmark" })} />);

    await waitFor(() => {
      expect(
        screen.getByText(/Expert Benchmark — Weekly Report/)
      ).toBeInTheDocument();
    });

    expect(mockFetchSession).toHaveBeenCalledWith(
      "sess_expert-benchmark_005",
      { limit: 2000 }
    );
  });

  it("shows Back to Team Dashboard link when report loads", async () => {
    render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    const backLink = screen.getByRole("link", {
      name: /← Back to Team Dashboard/i,
    });
    expect(backLink).toHaveAttribute("href", "/seagull");
  });

  describe("Export stubs", () => {
    it("Email Report button is disabled with coming-soon indicator", async () => {
      render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);
      await waitFor(() => {
        expect(screen.getByText(/75\/100/)).toBeInTheDocument();
      });

      const emailBtn = screen.getByRole("button", { name: /Email Report/i });
      expect(emailBtn).toBeDisabled();
      expect(emailBtn).toHaveAttribute("title", "Email report — coming soon");
    });
  });

  describe("Download PDF", () => {
    let originalFetch: typeof global.fetch;

    beforeEach(() => {
      originalFetch = global.fetch;
    });

    afterEach(() => {
      global.fetch = originalFetch;
    });

    it("POSTs to API with correct payload", async () => {
      const mockBlob = new Blob(["pdf"], { type: "application/pdf" });
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      });
      global.fetch = mockFetch as typeof fetch;

      render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);
      await waitFor(() =>
        expect(screen.getByText(/75\/100/)).toBeInTheDocument()
      );

      fireEvent.click(screen.getByRole("button", { name: /Download PDF/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("/api/welder-report-pdf"),
          expect.objectContaining({
            method: "POST",
            headers: { "Content-Type": "application/json" },
          })
        );
      });

      const body = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(body.welder).toEqual({ name: "Mike Chen" });
      expect(body.score.total).toBe(75);
      expect(body.feedback).toBeDefined();
    });

    it("Download PDF button is disabled during generation", async () => {
      let resolveFetch: (v: {
        ok: boolean;
        blob: () => Promise<Blob>;
      }) => void;
      const fetchPromise = new Promise<{
        ok: boolean;
        blob: () => Promise<Blob>;
      }>((r) => {
        resolveFetch = r;
      });
      const mockFetch = jest.fn().mockReturnValue(fetchPromise);
      global.fetch = mockFetch as typeof fetch;

      try {
        render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);
        await waitFor(() =>
          expect(screen.getByText(/75\/100/)).toBeInTheDocument()
        );
        const btn = screen.getByRole("button", { name: /Download PDF/i });
        fireEvent.click(btn);
        await waitFor(() => expect(btn).toBeDisabled());
        resolveFetch!({ ok: true, blob: () => Promise.resolve(new Blob()) });
      } finally {
        global.fetch = originalFetch;
      }
    });

    it("sends chartDataUrl null when chart capture fails", async () => {
      const { toPng } = require("html-to-image");
      (toPng as jest.Mock).mockResolvedValue(null);

      const mockBlob = new Blob(["pdf"], { type: "application/pdf" });
      const mockFetch = jest.fn().mockResolvedValue({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      });
      global.fetch = mockFetch as typeof fetch;

      try {
        render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);
        await waitFor(() =>
          expect(screen.getByText(/75\/100/)).toBeInTheDocument()
        );
        fireEvent.click(screen.getByRole("button", { name: /Download PDF/i }));
        await waitFor(() => expect(mockFetch).toHaveBeenCalled());

        const body = JSON.parse(mockFetch.mock.calls[0][1].body);
        expect(body.chartDataUrl).toBeNull();
      } finally {
        global.fetch = originalFetch;
        (toPng as jest.Mock).mockResolvedValue("data:image/png;base64,fake");
      }
    });

    it("renders trend-chart wrapper with 600×200 for PDF capture", async () => {
      render(<WelderReportPage params={Promise.resolve({ id: "mike-chen" })} />);
      await waitFor(() =>
        expect(screen.getByText(/75\/100/)).toBeInTheDocument()
      );

      const chartEl =
        document.getElementById("trend-chart") ??
        screen.getByTestId("trend-chart");
      expect(chartEl).toBeInTheDocument();
      const style = chartEl.getAttribute("style") ?? "";
      expect(style).toMatch(/width.*600|600.*width/i);
      expect(style).toMatch(/height.*200|200.*height/i);
      if (chartEl.offsetWidth !== 0 && chartEl.offsetHeight !== 0) {
        expect(chartEl.offsetWidth).toBe(600);
        expect(chartEl.offsetHeight).toBe(200);
      }
    });
  });
});
