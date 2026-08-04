"use client";

import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

function SearchInput({
  value,
  onChange,
  placeholder = "Search…",
  className,
  id = "search-input",
  ariaLabel = "Search",
}) {
  return (
    <div className={cn("relative", className)}>
      <Search
        size={16}
        aria-hidden="true"
        className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400"
      />

      <input
        id={id}
        type="search"
        role="searchbox"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={ariaLabel}
        autoComplete="off"
        spellCheck={false}
        className="w-full rounded-md border border-border bg-bg-card py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder:text-zinc-500 transition-colors focus:border-accent focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-bg-panel"
      />
    </div>
  );
}

export {
  SearchInput,
};