"use client";
import React from "react";

export default function SortableHeader({ label, sortKey, sortConfig, onSort }) {
  const isActive = sortConfig.key === sortKey;
  const direction = isActive ? sortConfig.direction : null;

  return (
    <th
      onClick={() => onSort(sortKey)}
      style={{ cursor: "pointer", userSelect: "none" }}
    >
      {label}{" "}
      {isActive && (
        <span>{direction === "asc" ? "🔼" : "🔽"}</span>
      )}
    </th>
  );
}