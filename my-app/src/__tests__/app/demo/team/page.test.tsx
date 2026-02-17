/**
 * Tests for Demo Team Dashboard page.
 */

import { render, screen } from "@testing-library/react";
import DemoTeamDashboardPage from "@/app/demo/team/page";

describe("DemoTeamDashboardPage", () => {
  it("renders N cards from DEMO_WELDERS", () => {
    render(<DemoTeamDashboardPage />);
    expect(screen.getByText(/Team Dashboard — Demo/)).toBeInTheDocument();
    expect(screen.getByText(/Mike Chen/)).toBeInTheDocument();
    expect(screen.getByText(/Expert Benchmark/)).toBeInTheDocument();
    expect(screen.getAllByText(/View report →/).length).toBeGreaterThanOrEqual(
      2
    );
  });

  it("links point to /demo/team/[welderId]", () => {
    render(<DemoTeamDashboardPage />);
    const links = screen.getAllByRole("link");
    const hrefs = links.map((l) => l.getAttribute("href"));
    expect(hrefs).toContain("/demo/team/mike-chen");
    expect(hrefs).toContain("/demo/team/expert-benchmark");
  });

  it("shows scores 42 and 94", () => {
    render(<DemoTeamDashboardPage />);
    expect(screen.getByText(/42\/100/)).toBeInTheDocument();
    expect(screen.getByText(/94\/100/)).toBeInTheDocument();
  });
});
