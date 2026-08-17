"use client";
import { memo, forwardRef, useId } from "react";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Input — shared UI primitive.
 *
 * @param {string} label — optional label above the input
 * @param {string} error — error message shown below the input (red)
 * @param {string} hint — helper text shown below the input
 * @param {React.ReactNode} icon — optional leading icon (e.g. from lucide-react)
 * @param {string} className — additional classes applied to the outer wrapper
 * @param {string} inputClassName — additional classes applied to the <input> element
 */
const Input = forwardRef(function Input(
  { label, error, hint, icon, className, inputClassName, id: idProp, ...props },
  ref
) {
  const autoId = useId();
  const id = idProp ?? autoId;

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      {label && (
        <label
          htmlFor={id}
          className="text-xs font-medium text-zinc-300"
        >
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted">
            {icon}
          </span>
        )}
        <input
          ref={ref}
          id={id}
          className={cn(
            "w-full rounded-md border bg-bg-card py-1.5 text-sm text-zinc-100 placeholder:text-muted transition-colors",
            "focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent",
            error
              ? "border-rose-500/60 focus:ring-rose-500/40"
              : "border-border",
            icon ? "pl-8 pr-3" : "px-3",
            inputClassName
          )}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
          {...props}
        />
      </div>
      {error && (
        <p id={`${id}-error`} className="text-xs text-rose-400">
          {error}
        </p>
      )}
      {!error && hint && (
        <p id={`${id}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      )}
    </div>
  );
});

/**
 * SearchInput — thin wrapper over Input with a Search icon pre-wired.
 *
 * @param {string} value
 * @param {function} onChange — called with the string value (not the event)
 * @param {string} placeholder
 * @param {string} className
 */
const SearchInput = memo(function SearchInput({
  value,
  onChange,
  placeholder = "Search\u2026",
  className,
}) {
  return (
    <Input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      icon={<Search size={14} />}
      className={className}
    />
  );
});

const Input_ = memo(Input);
export default Input_;
export { Input_ as Input, SearchInput };
