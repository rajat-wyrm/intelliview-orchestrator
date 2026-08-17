"use client";
import { memo, forwardRef } from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

const VARIANTS = {
  primary:
    "bg-accent text-white hover:bg-accent-dark active:scale-[0.98] shadow-sm",
  secondary:
    "border border-border bg-bg-card text-zinc-300 hover:border-accent/40 hover:text-zinc-100 active:scale-[0.98]",
  ghost:
    "text-muted hover:bg-bg-card hover:text-zinc-200 active:scale-[0.98]",
  danger:
    "border border-rose-500/30 bg-rose-500/10 text-rose-300 hover:border-rose-500/60 hover:bg-rose-500/20 active:scale-[0.98]",
};

const SIZES = {
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-8 px-3 text-xs gap-2",
  lg: "h-9 px-4 text-sm gap-2",
};

/**
 * Button — shared UI primitive.
 *
 * @param {"primary"|"secondary"|"ghost"|"danger"} variant
 * @param {"sm"|"md"|"lg"} size
 * @param {boolean} loading — shows a spinner and disables interaction
 * @param {React.ReactNode} icon — optional leading icon
 * @param {string} className — additional classes
 */
const Button = forwardRef(function Button(
  {
    children,
    variant = "secondary",
    size = "md",
    loading = false,
    icon,
    className,
    disabled,
    ...props
  },
  ref
) {
  const isDisabled = disabled || loading;
  return (
    <button
      ref={ref}
      disabled={isDisabled}
      aria-disabled={isDisabled}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/70",
        "disabled:pointer-events-none disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...props}
    >
      {loading ? (
        <Loader2 size={12} className="animate-spin shrink-0" />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      {children && <span>{children}</span>}
    </button>
  );
});

export default memo(Button);
export { Button };
