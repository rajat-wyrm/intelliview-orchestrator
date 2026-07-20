"use client";

import { memo } from "react";
import { cn, statusColor } from "@/lib/utils";

const STYLES = {
success:
"bg-emerald-500/10 text-emerald-700 ring-emerald-500/30 dark:text-emerald-400",

warn:
"bg-amber-500/10 text-amber-700 ring-amber-500/30 dark:text-amber-400",

danger:
"bg-rose-500/10 text-rose-700 ring-rose-500/30 dark:text-rose-400",

muted:
"bg-zinc-500/10 text-zinc-600 ring-zinc-500/30 dark:text-zinc-400",

accent:
"bg-indigo-500/10 text-indigo-700 ring-indigo-500/30 dark:text-indigo-400",
};

function Badge({
children,
variant = "muted",
className,
}) {
return (
<span
className={cn(
"inline-flex items-center rounded-full px-2 py-0.5",
"text-xs font-medium",
"ring-1 ring-inset",
"transition-colors duration-200",
STYLES[variant] || STYLES.muted,
className
)}
>
{children} </span>
);
}

function StatusBadgeImpl({ status }) {
const normalizedStatus =
typeof status === "string"
? status.replace(/_/g, " ")
: "Unknown";

return ( <Badge variant={statusColor(status)}>
{normalizedStatus} </Badge>
);
}

const Badge_ = memo(Badge);
const StatusBadge = memo(StatusBadgeImpl);

export {
Badge_ as Badge,
StatusBadge,
};

export default Badge_;
