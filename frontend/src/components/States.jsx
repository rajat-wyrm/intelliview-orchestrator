"use client";
import { Shimmer } from "@/components/ui/Loader";
import { IllustrationEmpty, IllustrationError } from "@/components/Illustrations";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";

/**
 * Skeleton — shimmer placeholder for loading content.
 * @param {string} className — apply width/height classes, e.g. "h-6 w-32"
 */
function Skeleton({ className }) {
  return <Shimmer className={className} />;
}

/**
 * ErrorState — displays an error message with an optional retry button.
 * @param {Error} error
 * @param {function} onRetry
 */
function ErrorState({ error, onRetry }) {
  return (
    <div className="rounded-md border border-rose-500/30 bg-rose-500/5 p-4 text-sm text-rose-300">
      <div className="flex items-center gap-3">
        <IllustrationError className="h-12 w-16 shrink-0" />
        <div className="min-w-0 flex-1">
          <div className="font-medium">Something went wrong</div>
          <div className="mt-1 text-xs text-rose-400">{error?.message}</div>
          {onRetry && (
            <Button
              variant="danger"
              size="sm"
              onClick={onRetry}
              className="mt-2"
            >
              Retry
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * EmptyState — displays a placeholder when a list or data set is empty.
 * @param {string} title
 * @param {string} description
 */
function EmptyState({ title, description, className }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-md border border-dashed border-border py-10 text-center",
        className
      )}
    >
      <IllustrationEmpty className="mb-3 h-20 w-32" />
      <div className="text-sm font-medium text-zinc-300">{title}</div>
      {description && (
        <div className="mt-1 text-xs text-muted">{description}</div>
      )}
    </div>
  );
}

export { EmptyState, ErrorState, Skeleton };
