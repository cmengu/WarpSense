/**
 * LiveStatusLED — traffic light status display.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { LiveStatusLED } from "@/components/live/LiveStatusLED";

describe("LiveStatusLED", () => {
  it("shows NOMINAL when risk is ok", () => {
    render(<LiveStatusLED riskLevel="ok" />);
    expect(screen.getByText("NOMINAL")).toBeInTheDocument();
  });

  it("shows WARP WARNING when risk is warning", () => {
    render(<LiveStatusLED riskLevel="warning" />);
    expect(screen.getByText("WARP WARNING")).toBeInTheDocument();
  });

  it("shows WARP CRITICAL when risk is critical", () => {
    render(<LiveStatusLED riskLevel="critical" />);
    expect(screen.getByText("WARP CRITICAL")).toBeInTheDocument();
  });

  it("shows optional message when provided", () => {
    render(<LiveStatusLED riskLevel="warning" message="High heat detected" />);
    expect(screen.getByText("High heat detected")).toBeInTheDocument();
  });
});
