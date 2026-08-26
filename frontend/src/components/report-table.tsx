"use client";

import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import type { ReportSummary } from "@/lib/types";
import { reportTypeLabels } from "@/lib/report-meta";
import { StatusBadge } from "@/components/status-badge";

const column = createColumnHelper<ReportSummary>();
const columns = [
  column.accessor("created_at", { header: "Дата", cell: ({ getValue }) => new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(new Date(getValue())) }),
  column.accessor("report_type", { header: "Тип", cell: ({ getValue }) => reportTypeLabels[getValue()] }),
  column.accessor("employee_name", { header: "Инициатор", cell: ({ getValue }) => getValue() || "—" }),
  column.accessor("total_amount", { header: "Сумма", cell: ({ getValue }) => `${Number(getValue()).toLocaleString("ru-RU", { minimumFractionDigits: 2 })} ₽` }),
  column.accessor("status", { header: "Статус", cell: ({ getValue }) => <StatusBadge status={getValue()} /> }),
  column.display({ id: "open", cell: ({ row }) => <Link className="inline-flex size-8 items-center justify-center rounded hover:bg-surface-muted" href={`/reports/${row.original.id}`} aria-label="Открыть отчёт"><ChevronRight className="size-4" /></Link> }),
];

export function ReportTable({ reports }: { reports: ReportSummary[] }) {
  const table = useReactTable({ data: reports, columns, getCoreRowModel: getCoreRowModel() });
  return (
    <div className="overflow-x-auto border-y border-border">
      <table className="w-full min-w-[760px] text-left text-sm">
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
