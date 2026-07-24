"use client";
import { memo } from "react";
import { cn, statusColor } from "@/lib/utils";

const STYLES = {
  success: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/30",
  warn: "bg-amber-500/10 text-amber-400 ring-amber-500/30",
  danger: "bg-rose-500/10 text-rose-400 ring-rose-500/30",
  muted: "bg-zinc-500/10 text-zinc-400 ring-zinc-500/30",
  accent: "bg-indigo-500/10 text-indigo-400 ring-indigo-500/30",
};

function Badge({ children, variant = "muted", className }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        STYLES[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}

function StatusBadgeImpl({ status }) {
  if (!status) {
    return <Badge variant="muted">—</Badge>;
  }

  return (
    <Badge variant={statusColor(status)}>
      {status.replace(/_/g, " ")}
    </Badge>
  );
}

const Badge_ = memo(Badge);
const StatusBadge = memo(StatusBadgeImpl);

export { Badge_ as Badge, StatusBadge };
export default Badge_;
