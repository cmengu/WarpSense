/**
 * Tests for Seagull Team Dashboard (Step 6).
 *
 * Validates:
 *   - Promise.allSettled: partial failures don't block working cards
 *   - Per-card error: "Score unavailable" when fetch fails
 *   - Loading state
 *   - Links to welder reports
 */

import { render, screen, waitFor } from "@testing-library/react";
import SeagullDashboardPage from "@/app/seagull/page";

const mockFetchScore = jest.fn();

jest.mock("@/lib/api", () => ({
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
}));

describe("SeagullDashboardPage", () => {
  beforeEach(() => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId === "sess_novice_001") {
        return Promise.resolve({ total: 75, rules: [] });
      }
      if (sessionId === "sess_expert_001") {
        return Promise.resolve({ total: 95, rules: [] });
      }
      return Promise.reject(new Error("Not found"));
    });
  });

  it("shows loading state initially", () => {
    render(<SeagullDashboardPage />);
    expect(screen.getByText(/Loading scores/i)).toBeInTheDocument();
  });

  it("renders 2 cards with scores when both fetches succeed", async () => {
    render(<SeagullDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    expect(screen.getByText(/95\/100/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Mike Chen/i })).toHaveAttribute(
      "href",
      "/seagull/welder/mike-chen"
    );
    expect(
      screen.getByRole("link", { name: /Expert Benchmark/i })
    ).toHaveAttribute("href", "/seagull/welder/expert-benchmark");
  });

  it("uses Promise.allSettled: one failure shows Score unavailable, other shows score", async () => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId === "sess_novice_001") {
        return Promise.reject(new Error("404"));
      }
      return Promise.resolve({ total: 95, rules: [] });
    });

    render(<SeagullDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Score unavailable/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    expect(screen.getByText(/95\/100/)).toBeInTheDocument();
    expect(screen.getByText(/Score unavailable/)).toBeInTheDocument();
  });

  it("shows Score unavailable for both when both fetches fail", async () => {
    mockFetchScore.mockRejectedValue(new Error("Network error"));

    render(<SeagullDashboardPage />);

    await waitFor(() => {
      expect(screen.getAllByText(/Score unavailable/)).toHaveLength(2);
    });

    expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
  });

  it("calls fetchScore for each welder sessionId", async () => {
    render(<SeagullDashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/75\/100/)).toBeInTheDocument();
    });

    expect(mockFetchScore).toHaveBeenCalledWith("sess_novice_001");
    expect(mockFetchScore).toHaveBeenCalledWith("sess_expert_001");
  });
});
