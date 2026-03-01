/**
 * Tests for Welder Roster (dashboard) — 10 welders with skill arcs.
 *
 * Validates:
 *   - Promise.allSettled: partial failures don't block working cards
 *   - Per-card error: "Score unavailable" when fetch fails
 *   - Loading state (skeleton cards)
 *   - Links to /replay/[sessionId], /seagull/welder/[id], /compare for non-expert
 *   - Score-based badge colours (red/amber/green)
 *   - Sort by score ascending (worst first)
 */

import { render, screen, waitFor } from "@testing-library/react";
import DashboardPage from "@/app/(app)/dashboard/page";

const mockFetchScore = jest.fn();

jest.mock("@/lib/api", () => ({
  fetchScore: (...args: unknown[]) => mockFetchScore(...args),
}));

describe("DashboardPage (Welder Roster)", () => {
  beforeEach(() => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      return Promise.resolve({ total: 75, rules: [] });
    });
  });

  it("shows loading state initially with skeleton", () => {
    render(<DashboardPage />);
    expect(screen.getByText(/Welder Roster/)).toBeInTheDocument();
  });

  it("renders 10 welder cards when fetches succeed", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    expect(screen.getByText(/Sara Okafor/)).toBeInTheDocument();
    expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
    expect(screen.getAllByText(/\/100/).length).toBeGreaterThanOrEqual(10);
  });

  it("links cards to /replay/[sessionId]", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    const links = screen.getAllByRole("link");
    const mikeReplayLink = links.find((l) => l.getAttribute("href") === "/replay/sess_mike-chen_005");
    expect(mikeReplayLink).toBeDefined();
  });

  it("links Full report to /seagull/welder/[id]", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    const allLinks = screen.getAllByRole("link");
    const fullReportLink = allLinks.find((l) => l.getAttribute("href") === "/seagull/welder/mike-chen");
    expect(fullReportLink).toBeDefined();
    expect(fullReportLink?.textContent).toMatch(/Full report/);
  });

  it("uses Promise.allSettled: one failure shows Score unavailable, others show score", async () => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId === "sess_mike-chen_005") {
        return Promise.reject(new Error("404"));
      }
      return Promise.resolve({ total: 95, rules: [] });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Score unavailable/)).toBeInTheDocument();
    });

    expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    expect(screen.getByText(/Score unavailable/)).toBeInTheDocument();
  });

  it("shows score-based badge colour (green for score ≥80)", async () => {
    mockFetchScore.mockImplementation(() =>
      Promise.resolve({ total: 85, rules: [] })
    );

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    const scoreBadges = screen.getAllByText("85/100");
    expect(scoreBadges[0]).toHaveClass("bg-green-100");
  });

  it("sorts cards by score ascending (worst first)", async () => {
    mockFetchScore.mockImplementation((sessionId: string) => {
      if (sessionId === "sess_tom-bradley_003") return Promise.resolve({ total: 55, rules: [] });
      if (sessionId === "sess_mike-chen_005") return Promise.resolve({ total: 75, rules: [] });
      return Promise.resolve({ total: 90, rules: [] });
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Tom Bradley/)).toBeInTheDocument();
    });

    const cards = screen.getAllByRole("heading", { level: 2 });
    expect(cards[0]).toHaveTextContent("Tom Bradley");
    expect(cards[1]).toHaveTextContent("Mike Chen");
  });

  it("Expert Benchmark card has no Compare to expert link", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
    });

    const compareLinks = screen
      .getAllByRole("link")
      .filter((l) => l.getAttribute("href")?.includes("/compare/"));
    expect(compareLinks).toHaveLength(9);
  });

  it("calls fetchScore for latest session only (one per welder)", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    });

    expect(mockFetchScore).toHaveBeenCalledWith("sess_mike-chen_005");
    expect(mockFetchScore).not.toHaveBeenCalledWith("sess_mike-chen_004");
  });
});
