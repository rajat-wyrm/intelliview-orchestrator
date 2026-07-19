import React from "react";

export default function SortableHeader({
  label,
  column,
  sortBy,
  sortOrder,
  onSort,
}) {
  const isActive = sortBy === column;

  const handleClick = () => {
    if (!isActive) {
      onSort(column, "asc");
    } else if (sortOrder === "asc") {
      onSort(column, "desc");
    } else {
      onSort(null, null);
    }
  };

  return (
    <th
      onClick={handleClick}
      style={{
        cursor: "pointer",
        userSelect: "none",
        padding: "10px",
      }}
    >
      {label}

      {isActive && (
        <span style={{ marginLeft: "6px" }}>
          {sortOrder === "asc" ? "↑" : "↓"}
        </span>
      )}
    </th>
  );
}