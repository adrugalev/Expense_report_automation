"use client";

import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Lock, LockOpen, Pencil, Trash2 } from "lucide-react";
import type { Employee, EmployeeAccount } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/confirm-dialog";

const column = createColumnHelper<Employee>();

export function EmployeeTable({ employees, accounts, editable, accountsLoading, onEdit, onDelete, onPassword }: {
  employees: Employee[];
  accounts: EmployeeAccount[];
  editable: boolean;
  accountsLoading: boolean;
  onEdit: (employee: Employee) => void;
  onDelete: (employee: Employee) => void;
  onPassword: (account: EmployeeAccount) => void;
}) {
  const accountsByEmployee = new Map(accounts.map((account) => [account.employee_id, account]));
  const columns = [
    column.accessor("full_name", { header: "ФИО", cell: ({ row, getValue }) => <div><p className="font-medium">{getValue()}</p><p className="text-xs text-muted">{row.original.email || "Email не указан"}</p></div> }),
    column.accessor("position", { header: "Должность" }),
    column.accessor("department", { header: "Подразделение" }),
    column.accessor("company", { header: "Компания", cell: ({ getValue }) => getValue() || "—" }),
    column.display({ id: "actions", cell: ({ row }) => {
      if (!editable) return null;
      const account = accountsByEmployee.get(row.original.id);
      const passwordLabel = account?.role === "admin" ? "Изменить свой пароль" : account?.has_account ? "Изменить пароль" : "Задать пароль";
      const hasPassword = Boolean(account?.has_account);
      const PasswordIcon = hasPassword ? Lock : LockOpen;
      const passwordUnavailable = accountsLoading || !account?.email;
      const passwordHint = accountsLoading ? "Данные доступа загружаются" : hasPassword ? "Пароль задан. Нажмите, чтобы изменить" : account?.email ? "Пароль не задан. Нажмите, чтобы назначить" : "Пароль не задан. Сначала укажите email сотрудника";
      return <div className="flex justify-end gap-1">
        <Button size="icon" variant="ghost" aria-label={passwordLabel} title={passwordHint} disabled={passwordUnavailable} onClick={() => { if (account) onPassword(account); }}><PasswordIcon className={hasPassword ? "size-4 text-success" : "size-4 text-warning"} /></Button>
        <Button size="icon" variant="ghost" aria-label="Редактировать" title="Редактировать сотрудника" onClick={() => onEdit(row.original)}><Pencil className="size-4" /></Button>
        <ConfirmDialog title="Удалить сотрудника?" description={`Сотрудник «${row.original.full_name}» будет удалён из справочника.`} onConfirm={() => onDelete(row.original)} trigger={<Button size="icon" variant="ghost" aria-label="Удалить" title="Удалить сотрудника"><Trash2 className="size-4 text-danger" /></Button>} />
      </div>;
    } }),
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
