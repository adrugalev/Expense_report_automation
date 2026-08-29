"use client";

import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { ChevronRight, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";
import type { ReportSummary } from "@/lib/types";
import { reportTypeLabels } from "@/lib/report-meta";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/confirm-dialog";

const column = createColumnHelper<ReportSummary>();

function SelectionCheckbox({ checked, indeterminate = false, label, onChange }: { checked: boolean; indeterminate?: boolean; label: string; onChange: () => void }) {
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);

  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      aria-label={label}
      className="size-4 cursor-pointer accent-primary"
      onChange={onChange}
    />
  );
}

export function ReportTable({ reports, deletingId, selectedIds, onToggle, onToggleAll, onDelete }: {
  reports: ReportSummary[];
  deletingId?: string;
  selectedIds: Set<string>;
  onToggle: (reportId: string) => void;
  onToggleAll: () => void;
  onDelete: (report: ReportSummary) => void;
}) {
  const allSelected = reports.length > 0 && reports.every((report) => selectedIds.has(report.id));
  const someSelected = reports.some((report) => selectedIds.has(report.id));
  const columns = [
    column.display({ id: "select", header: () => <SelectionCheckbox checked={allSelected} indeterminate={someSelected && !allSelected} label={allSelected ? "Снять выбор со всех отчётов" : "Выбрать все отчёты"} onChange={onToggleAll} />, cell: ({ row }) => <SelectionCheckbox checked={selectedIds.has(row.original.id)} label={`Выбрать отчёт ${reportTypeLabels[row.original.report_type]}`} onChange={() => onToggle(row.original.id)} /> }),
    column.accessor("created_at", { header: "Дата", cell: ({ getValue }) => new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(new Date(getValue())) }),
    column.accessor("report_type", { header: "Тип", cell: ({ getValue }) => reportTypeLabels[getValue()] }),
    column.accessor("employee_name", { header: "Инициатор", cell: ({ getValue }) => getValue() || "—" }),
    column.accessor("total_amount", { header: "Сумма", cell: ({ getValue }) => `${Number(getValue()).toLocaleString("ru-RU", { minimumFractionDigits: 2 })} ₽` }),
    column.accessor("status", { header: "Статус", cell: ({ getValue }) => <StatusBadge status={getValue()} /> }),
    column.display({ id: "actions", cell: ({ row }) => <div className="flex justify-end gap-1"><Link className="inline-flex size-8 items-center justify-center rounded hover:bg-surface-muted" href={`/reports/${row.original.id}`} aria-label="Открыть отчёт"><ChevronRight className="size-4" /></Link><ConfirmDialog title="Удалить отчёт?" description={`Запись «${reportTypeLabels[row.original.report_type]}» и все сформированные документы будут удалены без возможности восстановления.`} onConfirm={() => onDelete(row.original)} trigger={<Button size="icon" variant="ghost" disabled={deletingId === row.original.id} aria-label="Удалить отчёт"><Trash2 className="size-4 text-danger" /></Button>} /></div> }),
  ];
  const table = useReactTable({ data: reports, columns, getCoreRowModel: getCoreRowModel() });
  return (
    <div className="overflow-x-auto border-y border-border">
      <table className="w-full min-w-[800px] text-left text-sm">
        <thead className="bg-surface-muted text-xs text-muted">
          {table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => <th key={header.id} className="h-10 px-3 font-medium">{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>)}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => <tr key={row.id} className="border-t border-border hover:bg-surface-muted/50">{row.getVisibleCells().map((cell) => <td key={cell.id} className="h-14 px-3">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}
        </tbody>
      </table>
    </div>
  );
}
