
/**
 * Reusable Table component.
 * Usage:
 * <Table
 *   columns={[{ key: "name", label: "Name" }, { key: "status", label: "Status" }]}
 *   data={[{ name: "Alice", status: "Active" }, { name: "Bob", status: "Inactive" }]}
 * />
 */
export default function Table({ columns = [], data = [], className = "" }) {
  return (
    <div className={`overflow-x-auto rounded-md border border-border ${className}`}>
      <table className="w-full text-sm text-left">
        <thead className="bg-bg-card text-muted">
          <tr>
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-2 font-medium">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-t border-border hover:bg-bg-card/50">
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-2">
                  {row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}