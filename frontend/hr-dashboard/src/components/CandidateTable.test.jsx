import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import CandidateTable from "./CandidateTable";

const mockCandidates = [
  { id: 1, name: "Priya Sharma", domain: "engineering", type: "fulltime", status: "pending", appliedDate: "2026-07-01" },
  { id: 2, name: "Aman Verma", domain: "design", type: "intern", status: "selected", appliedDate: "2026-07-05" },
];

describe("CandidateTable", () => {
  it("renders a row for each candidate", () => {
    render(<CandidateTable candidates={mockCandidates} />);
    expect(screen.getByText("Priya Sharma")).toBeInTheDocument();
    expect(screen.getByText("Aman Verma")).toBeInTheDocument();
  });

  it("renders the correct table headers", () => {
    render(<CandidateTable candidates={mockCandidates} />);
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Domain")).toBeInTheDocument();
    expect(screen.getByText("Type")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
    expect(screen.getByText("Applied Date")).toBeInTheDocument();
  });

  it("shows an empty state when there are no candidates", () => {
    render(<CandidateTable candidates={[]} />);
    expect(screen.getByText("No candidates found")).toBeInTheDocument();
  });

  it("shows an empty state when candidates is undefined", () => {
    render(<CandidateTable candidates={undefined} />);
    expect(screen.getByText("No candidates found")).toBeInTheDocument();
  });
});