import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StatsCards from "./StatsCards";

describe("StatsCards", () => {
  it("renders all four stat labels", () => {
    render(<StatsCards stats={{ total: 10, pending: 3, selected: 4, rejected: 3 }} />);
    expect(screen.getByText("Total Candidates")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Selected")).toBeInTheDocument();
    expect(screen.getByText("Rejected")).toBeInTheDocument();
  });

  it("displays the correct values", () => {
    render(<StatsCards stats={{ total: 10, pending: 5, selected: 4, rejected: 1 }} />);
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("falls back to 0 when stats is undefined", () => {
    render(<StatsCards stats={undefined} />);
    const zeros = screen.getAllByText("0");
    expect(zeros.length).toBe(4);
  });
});