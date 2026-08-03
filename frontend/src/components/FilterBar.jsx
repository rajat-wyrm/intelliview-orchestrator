"use client";

import { SearchInput } from "./SearchInput";

const domains = ["", "Python", "Java", "React"];
const types = ["", "Assessment", "Voice", "Both"];
const statuses = ["", "Scheduled", "Completed", "Missed"];

const defaultFilters = {
  search: "",
  domain: "",
  type: "",
  status: "",
  dateFrom: "",
  dateTo: "",
};

export default function FilterBar({
  filters = defaultFilters,
  onFilterChange,
}) {
  const updateFilter = (key, value) => {
    onFilterChange({
      ...filters,
      [key]: value,
    });
  };

  const clearFilters = () => {
    onFilterChange(defaultFilters);
  };

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-lg border border-border bg-bg-card p-4">

      <div className="min-w-[220px] flex-1">
        <label className="mb-1 block text-xs font-medium text-muted">
          Search
        </label>

        <SearchInput
          value={filters.search}
          onChange={(value) => updateFilter("search", value)}
          placeholder="Search candidate or email..."
        />
      </div>

      <div className="min-w-[160px]">
        <label className="mb-1 block text-xs font-medium text-muted">
          Domain
        </label>

        <select
          value={filters.domain}
          onChange={(e) => updateFilter("domain", e.target.value)}
          className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 focus:border-accent focus:outline-none"
        >
          <option value="">All Domains</option>

          {domains
            .filter(Boolean)
            .map((domain) => (
              <option key={domain} value={domain}>
                {domain}
              </option>
            ))}
        </select>
      </div>

      <div className="min-w-[160px]">
        <label className="mb-1 block text-xs font-medium text-muted">
          Type
        </label>

        <select
          value={filters.type}
          onChange={(e) => updateFilter("type", e.target.value)}
          className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 focus:border-accent focus:outline-none"
        >
          <option value="">All Types</option>

          {types
            .filter(Boolean)
            .map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
        </select>
      </div>

      <div className="min-w-[170px]">
        <label className="mb-1 block text-xs font-medium text-muted">
          Status
        </label>

        <select
          value={filters.status}
          onChange={(e) => updateFilter("status", e.target.value)}
          className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 focus:border-accent focus:outline-none"
        >
          <option value="">All Status</option>

          {statuses
            .filter(Boolean)
            .map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
        </select>
      </div>

      <div className="min-w-[170px]">
        <label className="mb-1 block text-xs font-medium text-muted">
          From
        </label>

        <input
          type="date"
          value={filters.dateFrom}
          onChange={(e) => updateFilter("dateFrom", e.target.value)}
          className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 focus:border-accent focus:outline-none"
        />
      </div>

      <div className="min-w-[170px]">
        <label className="mb-1 block text-xs font-medium text-muted">
          To
        </label>

        <input
          type="date"
          value={filters.dateTo}
          onChange={(e) => updateFilter("dateTo", e.target.value)}
          className="w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-zinc-100 focus:border-accent focus:outline-none"
        />
      </div>

      <div className="flex min-w-[150px] justify-end">
        <button
          type="button"
          onClick={clearFilters}
          className="rounded-md border border-border px-4 py-2 text-sm font-medium text-zinc-100 transition hover:border-accent hover:text-accent"
        >
          Clear All Filters
        </button>
      </div>
    </div>
  );
}