export default function Input({
  label,
  name,
  value,
  onChange,
  disabled = false,
  type = "text",
}) {
  return (
    <div className="form-group">
      <label>{label}</label>

      <input
        type={type}
        name={name}
        value={value}
        disabled={disabled}
        onChange={onChange}
      />
    </div>
  );
}