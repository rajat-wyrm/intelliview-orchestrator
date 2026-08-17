"use client";
import { memo } from "react";
import { cn } from "@/lib/utils";

/**
 * Table — a styled, accessible table primitive.
 *
 * Compose with Thead, Tbody, Tr, Th, and Td sub-components.
 *
 * @example
 * <Table>
 *   <Thead>
 *     <Tr>
 *       <Th>Name</Th>
 *       <Th>Status</Th>
 *     </Tr>
 *   </Thead>
 *   <Tbody>
 *     {rows.map(r => (
 *       <Tr key={r.id}>
 *         <Td>{r.name}</Td>
 *         <Td><StatusBadge status={r.status} /></Td>
 *       </Tr>
 *     ))}
 *   </Tbody>
 * </Table>
 */
function Table({ children, className }) {
  return (
    <div className={cn("w-full overflow-x-auto", className)}>
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}

function Thead({ children, className }) {
  return (
    <thead
      className={cn(
        "text-left text-xs uppercase tracking-wide text-muted",
        className
      )}
    >
      {children}
    </thead>
  );
}

function Tbody({ children, className }) {
  return <tbody className={className}>{children}</tbody>;
}

function Tr({ children, className, onClick }) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        "border-t border-border transition-colors",
        onClick && "cursor-pointer",
        "hover:bg-white/[0.03]",
        className
      )}
    >
      {children}
    </tr>
  );
}

function Th({ children, className }) {
  return (
    <th
      scope="col"
      className={cn("py-2 pr-4 font-medium last:pr-0", className)}
    >
      {children}
    </th>
  );
}

function Td({ children, className }) {
  return (
    <td className={cn("py-2.5 pr-4 last:pr-0", className)}>{children}</td>
  );
}

const Table_ = memo(Table);
const Thead_ = memo(Thead);
const Tbody_ = memo(Tbody);
const Tr_ = memo(Tr);
const Th_ = memo(Th);
const Td_ = memo(Td);

export default Table_;
export {
  Table_ as Table,
  Thead_ as Thead,
  Tbody_ as Tbody,
  Tr_ as Tr,
  Th_ as Th,
  Td_ as Td,
};
