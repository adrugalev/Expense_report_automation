"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, FileArchive, FileText, Plus, ReceiptText } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import type { ReportDetail } from "@/lib/types";
import { reportTypeLabels } from "@/lib/report-meta";
import { useUser } from "@/hooks/use-user";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ErrorState, LoadingState } from "@/components/states";

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: user } = useUser();
  const query = useQuery({ queryKey: ["report", params.id], queryFn: () => apiFetch<ReportDetail>(`/reports/${params.id}`) });
  if (query.isLoading) return <LoadingState rows={7} />;
  if (query.error || !query.data) return <ErrorState message={query.error?.message ?? "Отчёт не найден"} retry={() => query.refetch()} />;
  const report = query.data;
  return (
    <>
      <Link href={user?.role === "admin" ? "/reports/history" : "/reports/new"} className="mb-4 inline-flex items-center gap-2 text-sm text-muted hover:text-foreground"><ArrowLeft className="size-4" />{user?.role === "admin" ? "К истории" : "К новому отчёту"}</Link>
      <PageHeader title={reportTypeLabels[report.report_type]} description={`Создан ${new Intl.DateTimeFormat("ru-RU", { dateStyle: "long", timeStyle: "short" }).format(new Date(report.created_at))}`} action={<StatusBadge status={report.status} />} />
      {report.status === "completed" ? (
        <div className="space-y-7">
          <section className="border-y border-green-200 bg-green-50 px-4 py-4 dark:border-green-900 dark:bg-green-950/25">
            <h2 className="font-semibold text-green-900 dark:text-green-200">Документы успешно сформированы</h2>
            <p className="mt-1 text-sm text-green-800 dark:text-green-300">{user?.role === "admin" ? "Документы и использованные чеки сохранены в истории." : "Документы и использованные чеки готовы к скачиванию."}</p>
          </section>
          {report.warnings.length ? <section className="border-y border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/25 dark:text-amber-200">{report.warnings.join("; ")}</section> : null}
          <section>
            <div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-semibold">Документы</h2>{report.files.length > 1 ? <Button asChild variant="secondary"><a href={`/api/reports/${report.id}/files.zip`}><FileArchive className="size-4" />Скачать ZIP</a></Button> : null}</div>
            <div className="grid gap-3 lg:grid-cols-2">
              {report.files.map((file) => (
                <Card key={file.id} className="flex items-center gap-3 p-4">
                  <div className="grid size-10 place-items-center rounded-md bg-primary-soft text-primary"><FileText className="size-5" /></div>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{file.name}</p><p className="text-xs text-muted">{formatBytes(file.size)}</p></div>
                  <Button asChild size="icon" variant="secondary"><a href={file.download_url} aria-label={`Скачать ${file.name}`}><Download className="size-4" /></a></Button>
                </Card>
              ))}
            </div>
          </section>
          {report.receipt_files.length ? <section>
            <div className="mb-3"><h2 className="text-lg font-semibold">Использованные чеки</h2><p className="mt-1 text-sm text-muted">Исходные файлы и суммы, зафиксированные при формировании отчёта.</p></div>
            <div className="grid gap-3 lg:grid-cols-2">
              {report.receipt_files.map((file) => (
                <Card key={file.id} className="flex items-center gap-3 p-4">
                  <div className="grid size-10 place-items-center rounded-md bg-orange-50 text-orange-600 dark:bg-orange-950/35 dark:text-orange-400"><ReceiptText className="size-5" /></div>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{file.name}</p><p className="mt-0.5 text-sm font-semibold tabular-nums">{Number(file.amount).toLocaleString("ru-RU", { style: "currency", currency: "RUB" })}</p><p className="text-xs text-muted">{formatBytes(file.size)}</p></div>
                  <Button asChild size="icon" variant="secondary"><a href={file.download_url} aria-label={`Скачать чек ${file.name}`}><Download className="size-4" /></a></Button>
                </Card>
              ))}
            </div>
          </section> : null}
          <Button asChild><Link href="/reports/new"><Plus className="size-4" />Создать новый отчёт</Link></Button>
        </div>
      ) : report.status === "failed" ? <ErrorState message={report.error_message ?? "Документы не сформированы"} /> : <LoadingState rows={4} />}
    </>
  );
}
