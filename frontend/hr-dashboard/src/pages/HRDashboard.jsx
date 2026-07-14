import React, { useState, useEffect } from "react";
import StatsCards from "../components/StatsCards";
import FilterBar from "../components/FilterBar";
import CandidateTable from "../components/CandidateTable";
import Pagination from "../components/Pagination";
import DashboardSkeleton from "../components/DashboardSkeleton";

function HRDashboard() {
  // Page State - jaisa ticket mein diya tha
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
    limit: 10,
  });

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [candidates, setCandidates] = useState([]);
  const [stats, setStats] = useState(null);
  const [totalPages, setTotalPages] = useState(1);

  // Browser tab title set karna
  useEffect(() => {
    document.title = "HR Dashboard";
  }, []);

  // Jab bhi filters ya pagination change ho, data fetch karo
  useEffect(() => {
    fetchDashboardData();
  }, [filters, pagination.currentPage]);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // TODO: yahan real API call hoga (Python backend se)
      // Abhi ke liye dummy/mock data use kar rahe hain
      const mockCandidates = [
        { id: 1, name: "Priya Sharma", domain: "engineering", type: "fulltime", status: "pending", appliedDate: "2026-07-01" },
        { id: 2, name: "Aman Verma", domain: "design", type: "intern", status: "selected", appliedDate: "2026-07-05" },
      ];
      const mockStats = { total: 120, pending: 15, selected: 80, rejected: 25 };

      setCandidates(mockCandidates);
      setStats(mockStats);
      setTotalPages(5);
    } catch (err) {
      setError("Failed to load dashboard data.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters);
    setPagination((prev) => ({ ...prev, currentPage: 1 })); // filter change → page 1 pe reset
  };

  const handlePageChange = (newPage) => {
    setPagination((prev) => ({ ...prev, currentPage: newPage }));
  };

  return (
    <div className="hr-dashboard">
      <h1>HR Dashboard</h1>

      <StatsCards stats={stats} />

      <FilterBar filters={filters} onFilterChange={handleFilterChange} />

      {error && <p className="error-message">{error}</p>}

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