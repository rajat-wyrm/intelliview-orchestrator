"use client";
import React, { useState } from "react";
import SortableHeader from "../components/SortableHeader";

export default function Page() {
  const [workers, setWorkers] = useState([
    { id: 1, name: "Alice", role: "Engineer", salary: 60000 },
    { id: 2, name: "Bob", role: "Designer", salary: 50000 },
    { id: 3, name: "Charlie", role: "Manager", salary: 80000 },
  ]);

  const [sortConfig, setSortConfig] = useState({
    key: null,
    direction: "asc",
  });

  const handleSort = (key) => {
    let direction = "asc";

    if (sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }

    const sortedData = [...workers].sort((a, b) => {
      if (a[key] < b[key]) return direction === "asc" ? -1 : 1;
      if (a[key] > b[key]) return direction === "asc" ? 1 : -1;
      return 0;
    });

    setWorkers(sortedData);
    setSortConfig({ key, direction });
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>Workers Table</h2>

      <table border="1" cellPadding="10">
        <thead>
          <tr>
            <SortableHeader
              label="Name"
              sortKey="name"
              sortConfig={sortConfig}
              onSort={handleSort}
            />
            <SortableHeader
              label="Role"
              sortKey="role"
              sortConfig={sortConfig}
              onSort={handleSort}
            />
            <SortableHeader
              label="Salary"
              sortKey="salary"
              sortConfig={sortConfig}
              onSort={handleSort}
            />
          </tr>
        </thead>

        <tbody>
          {workers.map((worker) => (
            <tr key={worker.id}>
              <td>{worker.name}</td>
              <td>{worker.role}</td>
              <td>{worker.salary}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}