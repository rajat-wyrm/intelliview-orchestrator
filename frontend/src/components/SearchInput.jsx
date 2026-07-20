"use client";

import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

export function SearchInput({
value,
onChange,
placeholder = "Search…",
className,
}) {
return (
<div className={cn("relative", className)}> <Search
     size={14}
     aria-hidden="true"
     className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted"
   />


  <input
    type="search"
    value={value}
    onChange={(event) => onChange(event.target.value)}
    placeholder={placeholder}
    aria-label={placeholder}
    className={cn(
      "w-full rounded-md border border-border bg-bg-card",
      "py-1.5 pl-8 pr-3",
      "text-sm text-zinc-900 dark:text-zinc-100",
      "placeholder:text-muted",
      "transition-colors duration-200",
      "hover:border-zinc-400 dark:hover:border-zinc-600",
      "focus:border-accent focus:outline-none",
      "focus:ring-2 focus:ring-accent/30"
    )}
  />
</div>

);
}
