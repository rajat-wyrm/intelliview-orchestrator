"use client";

import { memo } from "react";
import { cn } from "@/lib/utils";

function Card({
children,
title,
description,
action,
className,
}) {
return (
<section
className={cn(
"rounded-xl border border-border bg-bg-panel shadow-sm",
"transition-colors duration-200",
className
)}
>
{(title || description || action) && ( <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-4"> <div className="min-w-0">
{title && ( <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
{title} </h3>
)}


        {description && (
          <p className="mt-0.5 text-xs text-muted">
            {description}
          </p>
        )}
      </div>

      {action && (
        <div className="shrink-0">
          {action}
        </div>
      )}
    </header>
  )}

  <div className="p-5">
    {children}
  </div>
</section>
);
}

export default memo(Card);
