"use client";

import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Pencil, Trash2 } from "lucide-react";
import type { Employee } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/confirm-dialog";

const column = createColumnHelper<Employee>();

export function EmployeeTable({ employees, editable, onEdit, onDelete }: { employees: Employee[]; editable: boolean; onEdit: (employee: Employee) => void; onDelete: (employee: Employee) => void }) {
  const columns = [
    column.accessor("full_name", { header: "ФИО", cell: ({ row, getValue }) => <div><p className="font-medium">{getValue()}</p><p className="text-xs text-muted">{row.original.email || "Email не указан"}</p></div> }),
    column.accessor("position", { header: "Должность" }),
    column.accessor("department", { header: "Подразделение" }),
    column.accessor("company", { header: "Компания", cell: ({ getValue }) => getValue() || "—" }),
    column.display({ id: "actions", cell: ({ row }) => editable ? <div className="flex justify-end gap-1"><Button size="icon" variant="ghost" aria-label="Редактировать" onClick={() => onEdit(row.original)}><Pencil className="size-4" /></Button><ConfirmDialog title="Удалить сотрудника?" description={`Сотрудник «${row.original.full_name}» будет удалён из справочника.`} onConfirm={() => onDelete(row.original)} trigger={<Button size="icon" variant="ghost" aria-label="Удалить"><Trash2 className="size-4 text-danger" /></Button>} /></div> : null }),
  ];
  const table = useReactTable({ data: employees, columns, getCoreRowModel: getCoreRowModel() });
  return (
    <div className="overflow-x-auto border-y border-border">
      <table className="w-full min-w-[880px] text-left text-sm">
        <thead className="bg-surface-muted text-xs text-muted">{table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => <th className="h-10 px-3 font-medium" key={header.id}>{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>)}</thead>
        <tbody>{table.getRowModel().rows.map((row) => <tr className="border-t border-border" key={row.id}>{row.getVisibleCells().map((cell) => <td className="px-3 py-3" key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}
