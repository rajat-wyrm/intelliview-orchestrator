"use client";

import useSWR from "swr";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import Card from "@/components/Card";
import Stat from "@/components/Stat";
import { Skeleton, ErrorState, EmptyState } from "@/components/States";
import { endpoints } from "@/lib/api";

const RISK_COLORS = {
  Low: "#10b981",
  Medium: "#f59e0b",
  High: "#f97316",
  Critical: "#ef4444",
};

const TOOLTIP_STYLE = {
  contentStyle: { background: "#12121a", border: "1px solid #27272a", borderRadius: 8 },
  labelStyle: { color: "#e4e4e7" },
};

const AXIS_PROPS = { stroke: "#71717a", fontSize: 11 };

function ChartCard({ title, description, isEmpty, children }) {
  return (
    <Card title={title} description={description}>
      {isEmpty ? (
        <div className="py-8 text-center text-sm text-muted">No data available yet.</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          {children}
        </ResponsiveContainer>
      )}
    </Card>
  );
}

export default function AnalyticsPage() {
  const { data, error, isLoading, mutate } = useSWR("/analytics", () => endpoints.analytics(), {
    refreshInterval: 30000,
  });

  const isEmpty = !isLoading && !error && (!data || (data.kpis?.total_interviews ?? 0) === 0);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-50">Analytics</h1>
        <p className="text-sm text-muted">
          Hiring performance, score trends, and risk signals across all interviews.
        </p>
      </div>

      {error ? (
        <ErrorState error={error} onRetry={() => mutate()} />
      ) : isEmpty ? (
        <EmptyState
          title="No interview data yet"
          description="Analytics will appear here once interviews have been conducted."
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat
              label="Total interviews"
              value={isLoading ? <Skeleton className="h-7 w-12" /> : data.kpis.total_interviews}
            />
            <Stat
              label="Pass rate"
              value={
                isLoading ? (
                  <Skeleton className="h-7 w-16" />
                ) : (
                  `${data.kpis.pass_rate.toFixed(1)}%`
                )
              }
            />
            <Stat
              label="Average score"
              value={
                isLoading ? <Skeleton className="h-7 w-14" /> : data.kpis.average_score.toFixed(1)
              }
            />
            <Stat
              label="Total candidates"
              value={isLoading ? <Skeleton className="h-7 w-12" /> : data.kpis.total_candidates}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartCard
              title="Interview pass rate over time"
              description="Share of completed interviews that passed, by day."
              isEmpty={!isLoading && (data?.pass_rate_over_time?.length ?? 0) === 0}
            >
              {isLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <LineChart data={data.pass_rate_over_time}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="period" {...AXIS_PROPS} />
                  <YAxis {...AXIS_PROPS} unit="%" domain={[0, 100]} />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${v}%`, "Pass rate"]} />
                  <Line
                    type="monotone"
                    dataKey="pass_rate"
                    name="Pass rate"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              )}
            </ChartCard>

            <ChartCard
              title="Score distribution by position"
              description="Average evaluation score per interview position."
              isEmpty={!isLoading && (data?.score_by_position?.length ?? 0) === 0}
            >
              {isLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <BarChart data={data.score_by_position}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="position" {...AXIS_PROPS} interval={0} angle={-15} textAnchor="end" height={50} />
                  <YAxis {...AXIS_PROPS} domain={[0, 100]} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Bar dataKey="avg_score" name="Avg score" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              )}
            </ChartCard>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ChartCard
              title="Risk score distribution"
              description="Completed interviews bucketed by final risk score."
              isEmpty={!isLoading && (data?.risk_distribution?.every((b) => b.value === 0) ?? true)}
            >
              {isLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <PieChart>
                  <Pie
                    data={data.risk_distribution}
                    dataKey="value"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    innerRadius={50}
                    paddingAngle={2}
                  >
                    {data.risk_distribution.map((b) => (
                      <Cell key={b.label} fill={RISK_COLORS[b.label] ?? "#71717a"} />
                    ))}
                  </Pie>
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Legend wrapperStyle={{ fontSize: 12, color: "#a1a1aa" }} />
                </PieChart>
              )}
            </ChartCard>

            <ChartCard
              title="Average interview duration by month"
              description="Mean session length in minutes, by month."
              isEmpty={!isLoading && (data?.duration_by_month?.length ?? 0) === 0}
            >
              {isLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <BarChart data={data.duration_by_month}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="month" {...AXIS_PROPS} />
                  <YAxis {...AXIS_PROPS} unit="m" />
                  <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${v} min`, "Avg duration"]} />
                  <Bar
                    dataKey="average_duration_minutes"
                    name="Avg duration (min)"
                    fill="#818cf8"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              )}
            </ChartCard>
          </div>

          <Card
            title="Top performing candidates"
            description="Highest average interview scores across all sessions."
          >
            {isLoading ? (
              <Skeleton className="h-80 w-full" />
            ) : (data?.leaderboard?.length ?? 0) === 0 ? (
              <div className="py-8 text-center text-sm text-muted">No data available yet.</div>
            ) : (
              <ResponsiveContainer width="100%" height={Math.max(280, data.leaderboard.length * 40)}>
                <BarChart data={data.leaderboard} layout="vertical" margin={{ left: 24 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} {...AXIS_PROPS} />
                  <YAxis type="category" dataKey="name" width={140} {...AXIS_PROPS} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  <Bar dataKey="avg_score" name="Avg score" fill="#10b981" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
