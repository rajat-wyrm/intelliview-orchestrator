"use client";

import { useEffect, useMemo, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { format, parseISO, subDays } from "date-fns";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ShieldAlert, Video, TrendingDown, TrendingUp, BarChart3 } from "lucide-react";
import Card from "@/components/Card";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ *
 * Theme tokens
 * Recharts renders raw SVG, so colours are passed as literals rather
 * than Tailwind classes. These mirror tailwind.config.ts exactly.
 * ------------------------------------------------------------------ */
const TOKEN = {
  accent: "#6366f1",
  accentLight: "#818cf8",
  danger: "#ef4444",
  border: "#27272a",
  muted: "#71717a",
};

// Ordered low-to-high so the stack and the legend read as a severity ramp.
const RISK_LEVELS = [
  { key: "safe", label: "Safe", color: "#10b981" },
  { key: "low", label: "Low", color: "#84cc16" },
  { key: "warning", label: "Warning", color: "#f59e0b" },
  { key: "flagged", label: "Flagged", color: "#f97316" },
  { key: "high", label: "High", color: "#ef4444" },
];

const RANGES = [
  { id: "7d", label: "7 days", days: 7 },
  { id: "30d", label: "30 days", days: 30 },
  { id: "90d", label: "90 days", days: 90 },
  { id: "all", label: "All", days: null },
];

const MOCK_DAYS = 90;

/* ------------------------------------------------------------------ *
 * Mock data
 * Seeded PRNG keeps the series stable across re-renders so charts
 * don't reshuffle on every filter change. Replace generateMockSeries()
 * with the real fetch when the analytics endpoint lands.
 * ------------------------------------------------------------------ */
function mulberry32(seed) {
  let a = seed;
  return function next() {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function generateMockSeries(days = MOCK_DAYS, seed = 20260731) {
  const rand = mulberry32(seed);
  const today = new Date();

  return Array.from({ length: days }, (_, i) => {
    const date = subDays(today, days - 1 - i);
    const weekday = date.getDay();
    const isWeekend = weekday === 0 || weekday === 6;

    // Recruiters run far fewer interviews on weekends.
    const base = isWeekend ? 3 : 14;
    const interviewsConducted = Math.max(0, Math.round(base + rand() * base * 0.7));

    const riskBreakdown = { safe: 0, low: 0, warning: 0, flagged: 0, high: 0 };
    for (let n = 0; n < interviewsConducted; n += 1) {
      const roll = rand();
      if (roll < 0.46) riskBreakdown.safe += 1;
      else if (roll < 0.68) riskBreakdown.low += 1;
      else if (roll < 0.84) riskBreakdown.warning += 1;
      else if (roll < 0.94) riskBreakdown.flagged += 1;
      else riskBreakdown.high += 1;
    }

    const violationCount =
      riskBreakdown.warning +
      riskBreakdown.flagged * 2 +
      riskBreakdown.high * 4 +
      Math.round(rand() * 3);

    return {
      date: format(date, "yyyy-MM-dd"),
      violationCount,
      riskBreakdown,
      interviewsConducted,
    };
  });
}

/* ------------------------------------------------------------------ *
 * Helpers
 * ------------------------------------------------------------------ */
const sumBy = (rows, fn) => rows.reduce((total, row) => total + fn(row), 0);

function flatten(row) {
  return {
    date: row.date,
    violationCount: row.violationCount,
    interviewsConducted: row.interviewsConducted,
    ...row.riskBreakdown,
  };
}

function formatDay(value) {
  try {
    return format(parseISO(value), "MMM d");
  } catch {
    return value;
  }
}

function percentChange(current, previous) {
  if (!previous) return null;
  return ((current - previous) / previous) * 100;
}

/* ------------------------------------------------------------------ *
 * Presentational pieces
 * ------------------------------------------------------------------ */
function RangeFilter({ value, onChange }) {
  return (
    <div
      role="group"
      aria-label="Date range"
      className="inline-flex rounded-lg border border-border bg-bg-card p-0.5"
    >
      {RANGES.map((range) => {
        const selected = range.id === value;
        return (
          <button
            key={range.id}
            type="button"
            onClick={() => onChange(range.id)}
            aria-pressed={selected}
            className={cn(
              "rounded-md px-3 py-1 text-xs font-medium transition-colors",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
              selected
                ? "bg-accent/15 text-accent-light"
                : "text-muted hover:text-zinc-200",
            )}
          >
            {range.label}
          </button>
        );
      })}
    </div>
  );
}

function StatTile({ icon: Icon, label, value, delta, invert = false }) {
  const hasDelta = delta !== null && delta !== undefined && Number.isFinite(delta);
  const rising = hasDelta && delta > 0;
  // For violations, "up" is bad — invert flips the colour, not the arrow.
  const good = invert ? !rising : rising;
  const Arrow = rising ? TrendingUp : TrendingDown;

  return (
    <div className="rounded-xl border border-border bg-bg-panel p-4">
      <div className="flex items-center gap-2 text-muted">
        <Icon size={14} />
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="mt-2 font-mono text-2xl font-semibold text-zinc-100">
        {value.toLocaleString()}
      </p>
      {hasDelta ? (
        <p
          className={cn(
            "mt-1 flex items-center gap-1 text-xs",
            good ? "text-emerald-400" : "text-rose-400",
          )}
        >
          <Arrow size={12} />
          {Math.abs(delta).toFixed(1)}%
          <span className="text-muted">vs previous period</span>
        </p>
      ) : (
        <p className="mt-1 text-xs text-muted">No prior period to compare</p>
      )}
    </div>
  );
}

function ChartTooltip({ active, payload, label, total = false }) {
  if (!active || !payload?.length) return null;

  const rows = payload.filter((entry) => entry.value !== undefined && entry.value !== null);
  const stackTotal = total ? rows.reduce((sum, entry) => sum + entry.value, 0) : null;

  return (
    <div className="rounded-lg border border-border bg-bg-panel px-3 py-2 shadow-2xl">
      <p className="text-xs font-semibold text-zinc-100">{formatDay(label)}</p>
      <ul className="mt-1.5 space-y-1">
        {rows.map((entry) => (
          <li key={entry.dataKey} className="flex items-center gap-2 text-xs">
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: entry.color || entry.fill }}
            />
            <span className="text-muted">{entry.name}</span>
            <span className="ml-auto font-mono text-zinc-100">
              {entry.value.toLocaleString()}
            </span>
          </li>
        ))}
      </ul>
      {stackTotal !== null && (
        <p className="mt-1.5 border-t border-border pt-1.5 text-xs text-muted">
          Total <span className="font-mono text-zinc-200">{stackTotal.toLocaleString()}</span>
        </p>
      )}
    </div>
  );
}

function DonutTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const slice = payload[0];
  return (
    <div className="rounded-lg border border-border bg-bg-panel px-3 py-2 shadow-2xl">
      <div className="flex items-center gap-2 text-xs">
        <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: slice.payload.color }}
        />
        <span className="text-zinc-100">{slice.name}</span>
        <span className="ml-auto font-mono text-zinc-100">
          {slice.value.toLocaleString()}
        </span>
      </div>
      <p className="mt-1 text-xs text-muted">
        {slice.payload.share.toFixed(1)}% of interviews in range
      </p>
    </div>
  );
}

function ChartFrame({ children, className }) {
  return <div className={cn("h-64 w-full", className)}>{children}</div>;
}

function ChartSkeleton() {
  return (
    <div className="h-64 w-full animate-pulse rounded-lg bg-bg-card" aria-hidden="true" />
  );
}

function EmptyRange() {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-2 text-center">
      <BarChart3 size={24} className="text-muted" />
      <p className="text-sm text-zinc-300">No interviews in this range</p>
      <p className="text-xs text-muted">Pick a wider date range to see activity.</p>
    </div>
  );
}

const axisProps = {
  stroke: TOKEN.border,
  tick: { fill: TOKEN.muted, fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: TOKEN.border },
};

/* ------------------------------------------------------------------ *
 * MetricsDashboard
 * ------------------------------------------------------------------ */
function MetricsDashboard({ data, loading = false, className }) {
  const reduceMotion = useReducedMotion();
  const [rangeId, setRangeId] = useState("30d");
  const [mock, setMock] = useState(null);

  // Mock data is built after mount so the server and client render the
  // same markup — dates derived from `new Date()` differ across timezones
  // and would otherwise trip a hydration warning.
  useEffect(() => {
    if (data) return undefined;
    const timer = setTimeout(() => setMock(generateMockSeries()), 200);
    return () => clearTimeout(timer);
  }, [data]);

  const series = data ?? mock;
  const isLoading = loading || !series;

  const range = RANGES.find((r) => r.id === rangeId) ?? RANGES[1];

  const { current, previous } = useMemo(() => {
    if (!series) return { current: [], previous: [] };
    const sorted = [...series].sort((a, b) => a.date.localeCompare(b.date));
    if (range.days === null) return { current: sorted, previous: [] };
    return {
      current: sorted.slice(-range.days),
      previous: sorted.slice(-range.days * 2, -range.days),
    };
  }, [series, range.days]);

  const chartData = useMemo(() => current.map(flatten), [current]);

  const totals = useMemo(() => {
    const violations = sumBy(current, (r) => r.violationCount);
    const interviews = sumBy(current, (r) => r.interviewsConducted);
    const highRisk = sumBy(
      current,
      (r) => (r.riskBreakdown?.flagged ?? 0) + (r.riskBreakdown?.high ?? 0),
    );

    return {
      violations,
      interviews,
      highRisk,
      violationRate: interviews ? (violations / interviews) : 0,
      deltas: {
        violations: percentChange(violations, sumBy(previous, (r) => r.violationCount)),
        interviews: percentChange(interviews, sumBy(previous, (r) => r.interviewsConducted)),
        highRisk: percentChange(
          highRisk,
          sumBy(
            previous,
            (r) => (r.riskBreakdown?.flagged ?? 0) + (r.riskBreakdown?.high ?? 0),
          ),
        ),
      },
    };
  }, [current, previous]);

  const riskMix = useMemo(() => {
    const counts = RISK_LEVELS.map((level) => ({
      name: level.label,
      key: level.key,
      color: level.color,
      value: sumBy(current, (r) => r.riskBreakdown?.[level.key] ?? 0),
    }));
    const grandTotal = counts.reduce((sum, slice) => sum + slice.value, 0) || 1;
    return counts.map((slice) => ({ ...slice, share: (slice.value / grandTotal) * 100 }));
  }, [current]);

  const animate = !reduceMotion;
  const isEmpty = !isLoading && totals.interviews === 0;

  return (
    <div className={cn("space-y-4", className)}>
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-zinc-100">Interview analytics</h2>
          <p className="mt-0.5 text-xs text-muted">
            {range.days === null
              ? `All ${current.length} days of recorded activity`
              : `Last ${range.days} days`}
          </p>
        </div>
        <RangeFilter value={rangeId} onChange={setRangeId} />
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          icon={Video}
          label="Interviews conducted"
          value={totals.interviews}
          delta={totals.deltas.interviews}
        />
        <StatTile
          icon={ShieldAlert}
          label="Violations detected"
          value={totals.violations}
          delta={totals.deltas.violations}
          invert
        />
        <StatTile
          icon={ShieldAlert}
          label="Flagged or high risk"
          value={totals.highRisk}
          delta={totals.deltas.highRisk}
          invert
        />
        <div className="rounded-xl border border-border bg-bg-panel p-4">
          <div className="flex items-center gap-2 text-muted">
            <BarChart3 size={14} />
            <span className="text-xs font-medium">Violations per interview</span>
          </div>
          <p className="mt-2 font-mono text-2xl font-semibold text-zinc-100">
            {totals.violationRate.toFixed(2)}
          </p>
          <p className="mt-1 text-xs text-muted">Averaged across the selected range</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Violations over time" description="Total flags raised each day">
          {isLoading ? (
            <ChartSkeleton />
          ) : isEmpty ? (
            <EmptyRange />
          ) : (
            <ChartFrame>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                  <defs>
                    <linearGradient id="violationFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={TOKEN.danger} stopOpacity={0.35} />
                      <stop offset="100%" stopColor={TOKEN.danger} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={TOKEN.border} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={formatDay}
                    minTickGap={24}
                    {...axisProps}
                  />
                  <YAxis allowDecimals={false} width={44} {...axisProps} />
                  <Tooltip
                    cursor={{ stroke: TOKEN.border }}
                    content={<ChartTooltip />}
                  />
                  <Area
                    type="monotone"
                    dataKey="violationCount"
                    name="Violations"
                    stroke={TOKEN.danger}
                    strokeWidth={2}
                    fill="url(#violationFill)"
                    isAnimationActive={animate}
                    dot={false}
                    activeDot={{ r: 4, strokeWidth: 0 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </ChartFrame>
          )}
        </Card>

        <Card title="Interviews conducted" description="Completed sessions per day">
          {isLoading ? (
            <ChartSkeleton />
          ) : isEmpty ? (
            <EmptyRange />
          ) : (
            <ChartFrame>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                  <CartesianGrid stroke={TOKEN.border} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={formatDay}
                    minTickGap={24}
                    {...axisProps}
                  />
                  <YAxis allowDecimals={false} width={44} {...axisProps} />
                  <Tooltip
                    cursor={{ fill: "rgba(99,102,241,0.08)" }}
                    content={<ChartTooltip />}
                  />
                  <Bar
                    dataKey="interviewsConducted"
                    name="Interviews"
                    fill={TOKEN.accent}
                    radius={[3, 3, 0, 0]}
                    isAnimationActive={animate}
                    maxBarSize={22}
                  />
                </BarChart>
              </ResponsiveContainer>
            </ChartFrame>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card
          title="Risk distribution over time"
          description="Interviews by risk band, stacked per day"
          className="xl:col-span-2"
        >
          {isLoading ? (
            <ChartSkeleton />
          ) : isEmpty ? (
            <EmptyRange />
          ) : (
            <ChartFrame>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                  <CartesianGrid stroke={TOKEN.border} strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={formatDay}
                    minTickGap={24}
                    {...axisProps}
                  />
                  <YAxis allowDecimals={false} width={44} {...axisProps} />
                  <Tooltip
                    cursor={{ fill: "rgba(99,102,241,0.08)" }}
                    content={<ChartTooltip total />}
                  />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: 11, color: TOKEN.muted, paddingTop: 8 }}
                  />
                  {RISK_LEVELS.map((level, i) => (
                    <Bar
                      key={level.key}
                      dataKey={level.key}
                      name={level.label}
                      stackId="risk"
                      fill={level.color}
                      isAnimationActive={animate}
                      maxBarSize={22}
                      radius={i === RISK_LEVELS.length - 1 ? [3, 3, 0, 0] : undefined}
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </ChartFrame>
          )}
        </Card>

        <Card title="Risk mix" description="Share of interviews in the selected range">
          {isLoading ? (
            <ChartSkeleton />
          ) : isEmpty ? (
            <EmptyRange />
          ) : (
            <ChartFrame>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip content={<DonutTooltip />} />
                  <Pie
                    data={riskMix}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={54}
                    outerRadius={82}
                    paddingAngle={2}
                    stroke="none"
                    isAnimationActive={animate}
                  >
                    {riskMix.map((slice) => (
                      <Cell key={slice.key} fill={slice.color} />
                    ))}
                  </Pie>
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    layout="vertical"
                    align="right"
                    verticalAlign="middle"
                    wrapperStyle={{ fontSize: 11, color: TOKEN.muted }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </ChartFrame>
          )}
        </Card>
      </div>
    </div>
  );
}

export { MetricsDashboard, generateMockSeries, RISK_LEVELS };
export default MetricsDashboard;
