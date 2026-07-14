import React from "react";

function StatsCards({ stats }) {
  const cards = [
    { label: "Total Candidates", value: stats?.total ?? 0 },
    { label: "Pending", value: stats?.pending ?? 0 },
    { label: "Selected", value: stats?.selected ?? 0 },
    { label: "Rejected", value: stats?.rejected ?? 0 },
  ];

  return (
    <div className="stats-cards">
      {cards.map((card) => (
        <div className="stat-card" key={card.label}>
          <p className="stat-value">{card.value}</p>
          <p className="stat-label">{card.label}</p>
        </div>
      ))}
    </div>
  );
}

export default StatsCards;