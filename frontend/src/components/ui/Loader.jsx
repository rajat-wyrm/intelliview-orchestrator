"use client";
import { memo } from "react";
import { cn } from "@/lib/utils";

/**
 * Shimmer — animated skeleton placeholder for loading states.
 *
 * @param {string} className — use width/height utilities to size it, e.g. "h-6 w-32"
 *
 * @example
 * <Shimmer className="h-8 w-24" />
 */
function Shimmer({ className }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md bg-bg-card",
        "before:absolute before:inset-0 before:-translate-x-full",
        "before:animate-[shimmer_1.6s_infinite]",
        "before:bg-gradient-to-r before:from-transparent before:via-white/[0.04] before:to-transparent",
        className
      )}
    />
  );
}

/**
 * Spinner — circular animated indicator for in-progress actions.
 *
 * @param {"sm"|"md"|"lg"} size
 * @param {string} className
 *
 * @example
 * <Spinner />
 * <Spinner size="lg" className="text-accent" />
 */
const SPINNER_SIZES = {
  sm: 14,
  md: 20,
  lg: 32,
};

function Spinner({ size = "md", className }) {
  const px = SPINNER_SIZES[size] ?? SPINNER_SIZES.md;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={px}
      height={px}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("animate-spin text-muted", className)}
      aria-label="Loading"
      role="status"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

/**
 * PageLoader — full-page centered spinner, useful for Suspense / route transitions.
 *
 * @example
 * <PageLoader />
 */
function PageLoader({ className }) {
  return (
    <div
      className={cn(
        "flex h-full min-h-[200px] w-full items-center justify-center",
        className
      )}
    >
      <Spinner size="lg" className="text-accent" />
    </div>
  );
}

const Shimmer_ = memo(Shimmer);
const Spinner_ = memo(Spinner);
const PageLoader_ = memo(PageLoader);

export default Shimmer_;
export { Shimmer_ as Shimmer, Spinner_ as Spinner, PageLoader_ as PageLoader };
