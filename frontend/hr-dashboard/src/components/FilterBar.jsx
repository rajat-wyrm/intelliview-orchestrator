import React from "react";

function FilterBar({ filters, onFilterChange }) {
  const handleChange = (e) => {
    const { name, value } = e.target;
    onFilterChange({ ...filters, [name]: value });
  };

  return (
    <div className="filter-bar">
      <input
        type="text"
        name="search"
        placeholder="Search candidates..."
        value={filters.search}
        onChange={handleChange}
      />

      <select name="domain" value={filters.domain} onChange={handleChange}>
        <option value="">All Domains</option>
        <option value="engineering">Engineering</option>
        <option value="design">Design</option>
        <option value="marketing">Marketing</option>
      </select>

      <select name="type" value={filters.type} onChange={handleChange}>
        <option value="">All Types</option>
        <option value="fulltime">Full-time</option>
        <option value="intern">Intern</option>
      </select>

      <select name="status" value={filters.status} onChange={handleChange}>
        <option value="">All Status</option>
        <option value="pending">Pending</option>
        <option value="selected">Selected</option>
        <option value="rejected">Rejected</option>
      </select>

      <input
        type="date"
        name="dateFrom"
        value={filters.dateFrom}
        onChange={handleChange}
      />
      <input
        type="date"
        name="dateTo"
        value={filters.dateTo}
        onChange={handleChange}
      />
    </div>
  );
}

export default FilterBar;