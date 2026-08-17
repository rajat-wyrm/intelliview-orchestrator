/**
 * Reusable Input component.
 * Usage: <Input placeholder="Search..." value={value} onChange={setValue} />
 * type: "text" | "email" | "password" | "number" (default "text")
 */
export default function Input({
  value,
  onChange,
  placeholder = "",
  type = "text",
  disabled = false,
  className = "",
  ...rest
}) {
  const base =
    "w-full rounded-md border border-border bg-bg-card px-3 py-2 text-sm text-fg placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed";

  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className={`${base} ${className}`}
      {...rest}
    />
  );
}