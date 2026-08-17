/**
 * Reusable Button component.
 * Usage: <Button variant="primary" size="md" onClick={fn}>Save</Button>
 * Usage (icon-only): <Button variant="ghost" size="icon" aria-label="Refresh" onClick={fn}><RefreshCw size={12} /></Button>
 * variant: "primary" | "secondary" | "ghost"
 * size: "sm" | "md" | "lg" | "icon"
 */
export default function Button({ children, variant = "primary", size = "md", onClick, className = "", ...rest }) {
  const base = "rounded-md font-medium transition-colors";
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700",
    secondary: "bg-gray-200 text-gray-800 hover:bg-gray-300",
    ghost: "border border-border bg-bg-card text-muted hover:bg-gray-100",
  };
  const sizes = {
    sm: "px-2 py-1 text-sm",
    md: "px-4 py-2",
    lg: "px-6 py-3 text-lg",
    icon: "p-1.5",
  };

  return (
    <button onClick={onClick} className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...rest}>
      {children}
    </button>
  );
}