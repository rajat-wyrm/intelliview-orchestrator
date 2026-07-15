export default function Button({
  children,
  onClick,
  className = "",
  disabled = false,
  type = "button",
}) {
  return (
    <button
      type={type}
      className={className}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}