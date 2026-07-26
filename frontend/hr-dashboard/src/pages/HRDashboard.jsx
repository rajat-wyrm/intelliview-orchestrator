import React, { useState, useEffect } from "react";
import StatsCards from "../components/StatsCards";
import FilterBar from "../components/FilterBar";
import CandidateTable from "../components/CandidateTable";
import Pagination from "../components/Pagination";
import DashboardSkeleton from "../components/DashboardSkeleton";


// Bigger mock dataset so filtering actually has something to filter
const ALL_MOCK_CANDIDATES = [
  { id: 1, name: "Priya Sharma", domain: "engineering", type: "fulltime", status: "pending", appliedDate: "2026-07-01" },
  { id: 2, name: "Aman Verma", domain: "design", type: "intern", status: "selected", appliedDate: "2026-07-05" },
  { id: 3, name: "Rohit Singh", domain: "engineering", type: "intern", status: "rejected", appliedDate: "2026-06-20" },
  { id: 4, name: "Neha Gupta", domain: "marketing", type: "fulltime", status: "selected", appliedDate: "2026-06-28" },
  { id: 5, name: "Karan Mehta", domain: "design", type: "fulltime", status: "pending", appliedDate: "2026-07-03" },
  { id: 6, name: "Ananya Rao", domain: "engineering", type: "fulltime", status: "selected", appliedDate: "2026-06-15" },
  { id: 7, name: "Vikram Joshi", domain: "marketing", type: "intern", status: "pending", appliedDate: "2026-07-08" },
  { id: 8, name: "Sneha Iyer", domain: "engineering", type: "intern", status: "rejected", appliedDate: "2026-06-25" },
  { id: 9, name: "Arjun Nair", domain: "design", type: "intern", status: "selected", appliedDate: "2026-07-10" },
  { id: 10, name: "Divya Kapoor", domain: "marketing", type: "fulltime", status: "rejected", appliedDate: "2026-06-30" },
];

function HRDashboard() {
  const [filters, setFilters] = useState({
    search: "",
    domain: "",
    type: "",
    status: "",
    dateFrom: "",
    dateTo: "",
  });

  const [pagination, setPagination] = useState({
    currentPage: 1,
    limit: 5,
  });

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [candidates, setCandidates] = useState([]);
  const [stats, setStats] = useState(null);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    document.title = "HR Dashboard";
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [filters, pagination.currentPage]);

  const applyFilters = (data) => {
    return data.filter((c) => {
      if (filters.search && !c.name.toLowerCase().includes(filters.search.toLowerCase())) return false;
      if (filters.domain && c.domain !== filters.domain) return false;
      if (filters.type && c.type !== filters.type) return false;
      if (filters.status && c.status !== filters.status) return false;
      if (filters.dateFrom && c.appliedDate < filters.dateFrom) return false;
      if (filters.dateTo && c.appliedDate > filters.dateTo) return false;
      return true;
    });
  };

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // TODO: replace with real API call once backend endpoint is available
      // e.g. const res = await fetch(`/api/candidates?${new URLSearchParams({...filters, page: pagination.currentPage})}`);
      await new Promise((resolve) => setTimeout(resolve, 300)); // simulate network delay

      const filtered = applyFilters(ALL_MOCK_CANDIDATES);

      const start = (pagination.currentPage - 1) * pagination.limit;
      const pageData = filtered.slice(start, start + pagination.limit);

      const mockStats = {
        total: filtered.length,
        pending: filtered.filter((c) => c.status === "pending").length,
        selected: filtered.filter((c) => c.status === "selected").length,
        rejected: filtered.filter((c) => c.status === "rejected").length,
      };

      setCandidates(pageData);
      setStats(mockStats);
      setTotalPages(Math.max(1, Math.ceil(filtered.length / pagination.limit)));
    } catch (err) {
      setError("Failed to load dashboard data.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setPagination((prev) => ({ ...prev, currentPage: 1 }));
  };

  const handlePageChange = (newPage) => {
    setPagination((prev) => ({ ...prev, currentPage: newPage }));
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold text-zinc-100">HR Dashboard</h1>

      <StatsCards stats={stats} />

      <FilterBar filters={filters} onFilterChange={handleFilterChange} />

      {error && (
        <div className="hr-dashboard-error">
          {error}
          <button onClick={fetchDashboardData} className="hr-dashboard-retry-btn">
            Retry
          </button>
        </div>
      )}

      {isLoading ? (
        <DashboardSkeleton />
      ) : (
        <CandidateTable candidates={candidates} />
      )}

      <Pagination
        currentPage={pagination.currentPage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
      />
    </div>
  );
}

export default HRDashboard;