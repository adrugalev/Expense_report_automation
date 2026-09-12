"use client";

import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Plus, Trash2 } from "lucide-react";
import type { Receipt } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const column = createColumnHelper<Receipt>();
const compactInput = "h-8 min-w-0 w-full px-2 text-xs";

export function ReceiptTable({ receipts, onChange }: { receipts: Receipt[]; onChange: (receipts: Receipt[]) => void }) {
  const update = (index: number, key: keyof Receipt, value: string | null) => onChange(receipts.map((item, current) => current === index ? { ...item, [key]: value } : item));
  const columns = [
    column.accessor("file_name", { header: "Файл", cell: ({ getValue }) => <span className="block break-words text-[11px] font-medium leading-4" title={getValue()}>{getValue()}</span> }),
    column.accessor("date", { header: "Дата", cell: ({ row, getValue }) => <Input type="date" className={compactInput} value={getValue() ?? ""} onChange={(event) => update(row.index, "date", event.target.value || null)} /> }),
    column.accessor("seller", { header: "Продавец", cell: ({ row, getValue }) => <Input className={compactInput} value={getValue() ?? ""} onChange={(event) => update(row.index, "seller", event.target.value || null)} /> }),
    column.accessor("address", { header: "Адрес", cell: ({ row, getValue }) => <Input className={compactInput} value={getValue() ?? ""} onChange={(event) => update(row.index, "address", event.target.value || null)} /> }),
    column.accessor("inn", { header: "ИНН", cell: ({ row, getValue }) => <Input className={compactInput} value={getValue() ?? ""} onChange={(event) => update(row.index, "inn", event.target.value || null)} /> }),
    column.accessor("amount", { header: "Сумма", cell: ({ row, getValue }) => <Input inputMode="decimal" className={compactInput} value={getValue()} onChange={(event) => update(row.index, "amount", event.target.value)} /> }),
    column.accessor("fiscal_document_number", { header: "ФД", cell: ({ row, getValue }) => <Input className={compactInput} value={getValue() ?? ""} onChange={(event) => update(row.index, "fiscal_document_number", event.target.value || null)} /> }),
    column.display({ id: "remove", size: 50, cell: ({ row }) => <Button type="button" variant="ghost" size="icon" className="size-7" aria-label="Удалить чек" onClick={() => onChange(receipts.filter((_, index) => index !== row.index))}><Trash2 className="size-4" /></Button> }),
  ];
  const table = useReactTable({ data: receipts, columns, getCoreRowModel: getCoreRowModel(), defaultColumn: { minSize: 80, maxSize: 420 } });
  const addManual = () => onChange([...receipts, { file_name: `Чек ${receipts.length + 1}`, date: null, seller: null, address: null, inn: null, amount: "1.00", expense_type: "прочее", comment: null, route: null, fiscal_number: null, check_number: null, shift_number: null, kkt_number: null, fiscal_document_number: null, fiscal_drive_number: null, fiscal_sign: null, payment_type: null, qr_raw: null }]);
  return (
    <div data-testid="receipt-table">
      <div className="mb-3 flex items-center justify-between gap-3"><h3 className="text-sm font-semibold">Распознанные данные</h3><Button type="button" size="sm" variant="secondary" className="shrink-0" onClick={addManual}><Plus className="size-4" />Добавить строку</Button></div>
      <div className="hidden rounded-lg border border-border bg-surface xl:block">
        <table className="w-full table-fixed text-left text-xs">
          <colgroup><col className="w-[12%]" /><col className="w-[12%]" /><col className="w-[16%]" /><col className="w-[23%]" /><col className="w-[12%]" /><col className="w-[10%]" /><col className="w-[11%]" /><col className="w-[4%]" /></colgroup>
          <thead className="bg-surface-muted text-[11px] text-muted">{table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => <th key={header.id} className="h-9 px-2 font-medium">{flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>)}</thead>
          <tbody>{table.getRowModel().rows.length ? table.getRowModel().rows.map((row) => <tr key={row.id} className="border-t border-border align-middle">{row.getVisibleCells().map((cell) => <td key={cell.id} className={cell.column.id === "remove" ? "min-w-0 px-0.5 py-1.5" : "min-w-0 px-1.5 py-1.5"}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>) : <tr><td colSpan={columns.length} className="h-20 text-center text-xs text-muted">Добавьте чек или строку вручную</td></tr>}</tbody>
        </table>
      </div>
      <div className="divide-y divide-border rounded-lg border border-border bg-surface xl:hidden">
        {receipts.length ? receipts.map((receipt, index) => (
          <div key={`${receipt.file_name}-${index}`} className="p-3">
            <div className="flex items-start justify-between gap-3"><p className="min-w-0 break-words text-xs font-medium">{receipt.file_name}</p><Button type="button" variant="ghost" size="icon" className="-mr-1 -mt-1 shrink-0" aria-label="Удалить чек" onClick={() => onChange(receipts.filter((_, current) => current !== index))}><Trash2 className="size-4" /></Button></div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <label className="text-[11px] font-medium text-muted">Дата<Input type="date" className={`mt-1 ${compactInput}`} value={receipt.date ?? ""} onChange={(event) => update(index, "date", event.target.value || null)} /></label>
              <label className="text-[11px] font-medium text-muted">Сумма<Input inputMode="decimal" className={`mt-1 ${compactInput}`} value={receipt.amount} onChange={(event) => update(index, "amount", event.target.value)} /></label>
              <label className="text-[11px] font-medium text-muted">Продавец<Input className={`mt-1 ${compactInput}`} value={receipt.seller ?? ""} onChange={(event) => update(index, "seller", event.target.value || null)} /></label>
              <label className="text-[11px] font-medium text-muted">ИНН<Input className={`mt-1 ${compactInput}`} value={receipt.inn ?? ""} onChange={(event) => update(index, "inn", event.target.value || null)} /></label>
              <label className="text-[11px] font-medium text-muted sm:col-span-2">Адрес<Input className={`mt-1 ${compactInput}`} value={receipt.address ?? ""} onChange={(event) => update(index, "address", event.target.value || null)} /></label>
              <label className="text-[11px] font-medium text-muted sm:col-span-2">ФД<Input className={`mt-1 ${compactInput}`} value={receipt.fiscal_document_number ?? ""} onChange={(event) => update(index, "fiscal_document_number", event.target.value || null)} /></label>
            </div>
          </div>
        )) : <div className="grid h-20 place-items-center px-3 text-center text-xs text-muted">Добавьте чек или строку вручную</div>}
      </div>
      {receipts.some((item) => item.comment) ? <div className="mt-3 border-l-2 border-warning pl-3 text-sm text-warning">{receipts.filter((item) => item.comment).map((item) => <p key={item.file_name}>{item.file_name}: {item.comment}</p>)}</div> : null}
    </div>
  );
}
