/**
 * LiveAngleIndicator — 2D SVG angle display, no WebGL.
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { LiveAngleIndicator } from "@/components/welding/LiveAngleIndicator";

describe("LiveAngleIndicator", () => {
  it("renders current angle in degrees", () => {
    render(
      <LiveAngleIndicator currentAngle={45} riskLevel="ok" />
    );
    expect(screen.getByText("45°")).toBeInTheDocument();
  });

  it("shows target angle", () => {
    render(
      <LiveAngleIndicator currentAngle={50} targetAngle={45} riskLevel="ok" />
    );
    expect(screen.getByText("target 45°")).toBeInTheDocument();
  });

  it("uses SVG (no WebGL/Canvas) with accessible aria-label", () => {
    render(
      <LiveAngleIndicator currentAngle={45} riskLevel="ok" />
    );
    const svg = document.querySelector('svg[aria-label="Torch angle: 45 degrees"]');
    expect(svg).toBeInTheDocument();
  });
});
