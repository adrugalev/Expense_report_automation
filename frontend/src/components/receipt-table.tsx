"use client";

import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Plus, Trash2 } from "lucide-react";
import type { Receipt } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const column = createColumnHelper<Receipt>();

export function ReceiptTable({ receipts, onChange }: { receipts: Receipt[]; onChange: (receipts: Receipt[]) => void }) {
  const update = (index: number, key: keyof Receipt, value: string | null) => onChange(receipts.map((item, current) => current === index ? { ...item, [key]: value } : item));
  const columns = [
    column.accessor("file_name", { header: "Файл", size: 180, cell: ({ getValue }) => <span className="block max-w-44 truncate font-medium" title={getValue()}>{getValue()}</span> }),
    column.accessor("date", { header: "Дата", size: 150, cell: ({ row, getValue }) => <Input type="date" className="w-36" value={getValue() ?? ""} onChange={(event) => update(row.index, "date", event.target.value || null)} /> }),
    column.accessor("seller", { header: "Продавец", size: 220, cell: ({ row, getValue }) => <Input className="w-52" value={getValue() ?? ""} onChange={(event) => update(row.index, "seller", event.target.value || null)} /> }),
    column.accessor("address", { header: "Адрес", size: 300, cell: ({ row, getValue }) => <Input className="w-72" value={getValue() ?? ""} onChange={(event) => update(row.index, "address", event.target.value || null)} /> }),
    column.accessor("inn", { header: "ИНН", size: 150, cell: ({ row, getValue }) => <Input className="w-36" value={getValue() ?? ""} onChange={(event) => update(row.index, "inn", event.target.value || null)} /> }),
    column.accessor("amount", { header: "Сумма", size: 130, cell: ({ row, getValue }) => <Input inputMode="decimal" className="w-28" value={getValue()} onChange={(event) => update(row.index, "amount", event.target.value)} /> }),
    column.accessor("fiscal_document_number", { header: "ФД", size: 150, cell: ({ row, getValue }) => <Input className="w-36" value={getValue() ?? ""} onChange={(event) => update(row.index, "fiscal_document_number", event.target.value || null)} /> }),
    column.display({ id: "remove", size: 50, cell: ({ row }) => <Button type="button" variant="ghost" size="icon" aria-label="Удалить чек" onClick={() => onChange(receipts.filter((_, index) => index !== row.index))}><Trash2 className="size-4" /></Button> }),
  ];
  const table = useReactTable({ data: receipts, columns, getCoreRowModel: getCoreRowModel(), defaultColumn: { minSize: 80, maxSize: 420 } });
  const addManual = () => onChange([...receipts, { file_name: `Чек ${receipts.length + 1}`, date: null, seller: null, address: null, inn: null, amount: "1.00", expense_type: "прочее", comment: null, route: null, fiscal_number: null, check_number: null, shift_number: null, kkt_number: null, fiscal_document_number: null, fiscal_drive_number: null, fiscal_sign: null, payment_type: null, qr_raw: null }]);
  return (
    <div>
      <div className="mb-3 flex items-center justify-between"><h3 className="text-sm font-semibold">Распознанные данные</h3><Button type="button" size="sm" variant="secondary" onClick={addManual}><Plus className="size-4" />Добавить строку</Button></div>
      <div className="overflow-x-auto rounded-lg border border-border bg-surface">
        <table className="min-w-[1240px] text-left text-sm">
          <thead className="bg-surface-muted text-xs text-muted">{table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => <th key={header.id} className="h-10 px-3 font-medium" style={{ width: header.getSize() }}>{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>)}</thead>
          <tbody>{table.getRowModel().rows.length ? table.getRowModel().rows.map((row) => <tr key={row.id} className="border-t border-border align-top">{row.getVisibleCells().map((cell) => <td key={cell.id} className="px-2 py-2">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>) : <tr><td colSpan={columns.length} className="h-24 text-center text-sm text-muted">Добавьте чек или строку вручную</td></tr>}</tbody>
        </table>
      </div>
      {receipts.some((item) => item.comment) ? <div className="mt-3 border-l-2 border-warning pl-3 text-sm text-warning">{receipts.filter((item) => item.comment).map((item) => <p key={item.file_name}>{item.file_name}: {item.comment}</p>)}</div> : null}
    </div>
  );
}
