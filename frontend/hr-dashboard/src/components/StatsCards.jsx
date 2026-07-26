"use client";
import Stat from "@/components/Stat";

function StatsCards({ stats }) {
  const cards = [
    { label: "Total Candidates", value: stats?.total ?? 0 },
    { label: "Pending", value: stats?.pending ?? 0 },
    { label: "Selected", value: stats?.selected ?? 0 },
    { label: "Rejected", value: stats?.rejected ?? 0 },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {cards.map((card) => (
        <Stat key={card.label} label={card.label} value={card.value} />
      ))}
    </div>
  );
}

export default StatsCards;