"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import type { ReportList, ReportSummary } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { ReportTable } from "@/components/report-table";
import { ConfirmDialog } from "@/components/confirm-dialog";

export default function ReportHistoryPage() {
  const client = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const query = useQuery({ queryKey: ["reports"], queryFn: () => apiFetch<ReportList>("/reports?limit=200") });
  const remove = useMutation({
    mutationFn: (report: ReportSummary) => apiFetch<void>(`/reports/${report.id}`, { method: "DELETE" }),
    onSuccess: (_, report) => {
      setSelectedIds((current) => {
        const next = new Set(current);
        next.delete(report.id);
        return next;
      });
      client.invalidateQueries({ queryKey: ["reports"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Отчёт удалён");
    },
    onError: (error) => toast.error(error.message),
  });
  const removeSelected = useMutation({
    mutationFn: async (reportIds: string[]) => {
      const failedIds: string[] = [];
      for (const reportId of reportIds) {
        try {
          await apiFetch<void>(`/reports/${reportId}`, { method: "DELETE" });
        } catch {
          failedIds.push(reportId);
        }
      }
      return { deletedCount: reportIds.length - failedIds.length, failedIds };
    },
    onSuccess: ({ deletedCount, failedIds }) => {
      setSelectedIds(new Set(failedIds));
      client.invalidateQueries({ queryKey: ["reports"] });
      client.invalidateQueries({ queryKey: ["dashboard"] });
      if (deletedCount) toast.success(`Удалено отчётов: ${deletedCount}`);
      if (failedIds.length) toast.error(`Не удалось удалить отчётов: ${failedIds.length}`);
    },
    onError: (error) => toast.error(error.message),
  });

  const reports = query.data?.items ?? [];
  const selectedReportIds = reports.filter((report) => selectedIds.has(report.id)).map((report) => report.id);

  const toggleReport = (reportId: string) => setSelectedIds((current) => {
    const next = new Set(current);
    if (next.has(reportId)) next.delete(reportId);
    else next.add(reportId);
    return next;
  });
  const toggleAll = () => setSelectedIds((current) => {
    const allSelected = reports.length > 0 && reports.every((report) => current.has(report.id));
    return allSelected ? new Set() : new Set(reports.map((report) => report.id));
  });

  return (
    <>
      <PageHeader title="История" description="Сформированные комплекты доступны для повторного скачивания." action={reports.length ?
        <ConfirmDialog
          title="Удалить выбранные отчёты?"
          description={`Будут удалены выбранные отчёты (${selectedReportIds.length}) и все сформированные документы. Это действие нельзя отменить.`}
          onConfirm={() => removeSelected.mutate(selectedReportIds)}
          trigger={<Button variant="danger" size="sm" className="gap-1.5 px-2.5" disabled={!selectedReportIds.length || removeSelected.isPending}><Trash2 className="size-3.5" />Удалить выбранные{selectedReportIds.length ? ` (${selectedReportIds.length})` : ""}</Button>}
        />
      : undefined} />
      {query.isLoading ? <LoadingState rows={7} /> : query.error ? <ErrorState message={query.error.message} retry={() => query.refetch()} /> : reports.length ? <ReportTable reports={reports} deletingId={remove.variables?.id} selectedIds={selectedIds} onToggle={toggleReport} onToggleAll={toggleAll} onDelete={(report) => remove.mutate(report)} /> : <EmptyState title="История пуста" description="Здесь появятся успешно сформированные и незавершённые отчёты." action={<Button asChild><Link href="/reports/new">Создать первый отчёт</Link></Button>} />}
    </>
  );
}
