"use client";

import { memo } from "react";
import { cn, statusColor } from "@/lib/utils";

const STYLES = {
  success:
    "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40",
  warn:
    "bg-amber-500/15 text-amber-300 ring-amber-500/40",
  danger:
    "bg-rose-500/15 text-rose-300 ring-rose-500/40",
  muted:
    "bg-zinc-500/15 text-zinc-300 ring-zinc-500/40",
  accent:
    "bg-indigo-500/15 text-indigo-300 ring-indigo-500/40",
};

function Badge({
  children,
  variant = "muted",
  className,
  ariaLabel,
}) {
  return (
    <span
      role="status"
      aria-label={ariaLabel}
      className={cn(
        "inline-flex items-center justify-center rounded-full px-2.5 py-1 text-xs font-medium leading-none ring-1 ring-inset select-none",
        STYLES[variant],
        className
      )}
    >
      {children}
    </span>
  );
}

function StatusBadgeImpl({ status }) {
  if (!status) {
    return (
      <Badge
        variant="muted"
        ariaLabel="Status unavailable"
      >
        —
      </Badge>
    );
  }

  const formattedStatus = status.replace(/_/g, " ");

  return (
    <Badge
      variant={statusColor(status)}
      ariaLabel={`Status: ${formattedStatus}`}
    >
      {formattedStatus}
    </Badge>
  );
}

const Badge_ = memo(Badge);
const StatusBadge = memo(StatusBadgeImpl);

export { Badge_ as Badge, StatusBadge };
export default Badge_;