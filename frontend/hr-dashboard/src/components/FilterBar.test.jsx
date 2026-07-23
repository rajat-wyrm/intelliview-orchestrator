import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import FilterBar from "./FilterBar";

const baseFilters = {
  search: "",
  domain: "",
  type: "",
  status: "",
  dateFrom: "",
  dateTo: "",
};

describe("FilterBar", () => {
  it("renders the search input and all dropdowns", () => {
    render(<FilterBar filters={baseFilters} onFilterChange={() => {}} />);
    expect(screen.getByPlaceholderText("Search candidates...")).toBeInTheDocument();
    expect(screen.getByText("All Domains")).toBeInTheDocument();
    expect(screen.getByText("All Types")).toBeInTheDocument();
    expect(screen.getByText("All Status")).toBeInTheDocument();
  });

  it("calls onFilterChange with updated search value when typing", () => {
    const handleChange = vi.fn();
    render(<FilterBar filters={baseFilters} onFilterChange={handleChange} />);
    const searchInput = screen.getByPlaceholderText("Search candidates...");
    fireEvent.change(searchInput, { target: { value: "Priya" } });
    expect(handleChange).toHaveBeenCalledWith({ ...baseFilters, search: "Priya" });
  });

  it("calls onFilterChange when domain dropdown changes", () => {
    const handleChange = vi.fn();
    render(<FilterBar filters={baseFilters} onFilterChange={handleChange} />);
    const domainSelect = screen.getByDisplayValue("All Domains");
    fireEvent.change(domainSelect, { target: { value: "engineering" } });
    expect(handleChange).toHaveBeenCalledWith({ ...baseFilters, domain: "engineering" });
  });
});