import { useMemo, useState } from "react";
import SortableHeader from "./SortableHeader";

const candidates = [
  {
    id: 1,
    name: "Alice",
    score: 95,
    risk: "Low",
    date: "2026-07-19",
  },
  {
    id: 2,
    name: "Bob",
    score: 80,
    risk: "High",
    date: "2026-07-18",
  },
  {
    id: 3,
    name: "Charlie",
    score: 95,
    risk: "Medium",
    date: "2026-07-17",
  },
];

export default function CandidateTable() {
  const [sortState, setSortState] = useState({
    sortBy: null,
    sortOrder: null,
  });

  const handleSort = (sortBy, sortOrder) => {
    setSortState({
      sortBy,
      sortOrder,
    });
  };

  const sortedCandidates = useMemo(() => {
    if (!sortState.sortBy || !sortState.sortOrder) {
      return candidates;
    }

    return [...candidates].sort((a, b) => {
      const first = a[sortState.sortBy];
      const second = b[sortState.sortBy];

      if (first < second) {
        return sortState.sortOrder === "asc" ? -1 : 1;
      }

      if (first > second) {
        return sortState.sortOrder === "asc" ? 1 : -1;
      }

      return 0;
    });
  }, [sortState]);

  return (
    <table border="1" cellPadding="10">
      <thead>
        <tr>
          <SortableHeader
            label="Name"
            column="name"
            sortBy={sortState.sortBy}
            sortOrder={sortState.sortOrder}
            onSort={handleSort}
          />

          <SortableHeader
            label="Score"
            column="score"
            sortBy={sortState.sortBy}
            sortOrder={sortState.sortOrder}
            onSort={handleSort}
          />

          <SortableHeader
            label="Risk"
            column="risk"
            sortBy={sortState.sortBy}
            sortOrder={sortState.sortOrder}
            onSort={handleSort}
          />

          <SortableHeader
            label="Date"
            column="date"
            sortBy={sortState.sortBy}
            sortOrder={sortState.sortOrder}
            onSort={handleSort}
          />
        </tr>
      </thead>

      <tbody>
        {sortedCandidates.map((candidate) => (
          <tr key={candidate.id}>
            <td>{candidate.name}</td>
            <td>{candidate.score}</td>
            <td>{candidate.risk}</td>
            <td>{candidate.date}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}