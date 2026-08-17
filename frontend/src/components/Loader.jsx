
/**
 * Reusable Loader component.
 * Usage: <Loader size="md" />
 * Usage (with label): <Loader size="lg" label="Loading sessions..." />
 * size: "sm" | "md" | "lg"
 */
export default function Loader({ size = "md", label = "", className = "" }) {
  const sizes = {
    sm: "h-4 w-4 border-2",
    md: "h-6 w-6 border-2",
    lg: "h-10 w-10 border-4",
  };

  return (
    <div className={`flex items-center justify-center gap-2 ${className}`}>
      <div
        className={`${sizes[size]} animate-spin rounded-full border-border border-t-accent`}
        role="status"
        aria-label={label || "Loading"}
      />
      {label && <span className="text-sm text-muted">{label}</span>}
    </div>
  );
}