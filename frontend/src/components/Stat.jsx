"use client";

import { memo } from "react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

function Stat({
  label,
  value,
  hint,
  icon: Icon,
  trend,
  trendUp,
  className,
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-bg-card p-4",
        "transition-colors duration-200",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-muted">
          {label}
        </span>

        {Icon && (
          <Icon
            size={16}
            aria-hidden="true"
            className="text-muted"
          />
        )}
      </div>

      {/* Value */}
      <div className="mt-2 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        {value}
      </div>

      {/* Hint */}
      {hint && !trend && (
        <div className="mt-1 text-xs text-muted">
          {hint}
        </div>
      )}

      {/* Trend */}
      {trend != null && (
        <div
          className={cn(
            "mt-1.5 flex items-center gap-1 text-xs font-medium",
            trendUp
              ? "text-emerald-700 dark:text-emerald-400"
              : "text-rose-700 dark:text-rose-400"
          )}
        >
          {trendUp ? (
            <TrendingUp
              size={12}
              aria-hidden="true"
            />
          ) : (
            <TrendingDown
              size={12}
              aria-hidden="true"
            />
          )}

          <span>{trend}</span>
        </div>
      )}
    </div>
  );
}

export default memo(Stat);