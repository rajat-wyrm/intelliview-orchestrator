"use client";
import { SearchInput } from "@/components/SearchInput";
import { cn } from "@/lib/utils";

const selectClass =
  "rounded-md border border-border bg-bg-card px-3 py-1.5 text-sm text-zinc-100 focus:border-accent focus:outline-none";
const dateClass =
  "rounded-md border border-border bg-bg-card px-3 py-1.5 text-sm text-zinc-100 focus:border-accent focus:outline-none";

function FilterBar({ filters, onFilterChange }) {
  const handleChange = (name, value) => {
    onFilterChange({ ...filters, [name]: value });
  };

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-bg-panel p-4">
      <SearchInput
        value={filters.search}
        onChange={(val) => handleChange("search", val)}
        placeholder="Search candidates..."
        className="w-full sm:w-56"
      />

      <select
        className={selectClass}
        value={filters.domain}
        onChange={(e) => handleChange("domain", e.target.value)}
      >
        <option value="">All Domains</option>
        <option value="engineering">Engineering</option>
        <option value="design">Design</option>
        <option value="marketing">Marketing</option>
      </select>

      <select
        className={selectClass}
        value={filters.type}
        onChange={(e) => handleChange("type", e.target.value)}
      >
        <option value="">All Types</option>
        <option value="fulltime">Full-time</option>
        <option value="intern">Intern</option>
      </select>

      <select
        className={selectClass}
        value={filters.status}
        onChange={(e) => handleChange("status", e.target.value)}
      >
        <option value="">All Status</option>
        <option value="pending">Pending</option>
        <option value="selected">Selected</option>
        <option value="rejected">Rejected</option>
      </select>

      <input
        type="date"
        className={dateClass}
        value={filters.dateFrom}
        onChange={(e) => handleChange("dateFrom", e.target.value)}
      />
      <input
        type="date"
        className={dateClass}
        value={filters.dateTo}
        onChange={(e) => handleChange("dateTo", e.target.value)}
      />
    </div>
  );
}

export default FilterBar;