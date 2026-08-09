"use client";
/**
 * Reusable Card component.
 * Used in: page.jsx, analytics, candidates, interview, sessions, settings, workers
 */
import { memo } from "react";
import { cn } from "@/lib/utils";

function Card({ children, title, description, action, className }) {
  return (
    <section className={cn("rounded-xl border border-border bg-bg-panel shadow-sm", className)}>
      {(title || action) && (
        <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div>
            {title && <h3 className="text-sm font-semibold text-zinc-100">{title}</h3>}
            {description && <p className="mt-0.5 text-xs text-muted">{description}</p>}
          </div>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export default memo(Card);
