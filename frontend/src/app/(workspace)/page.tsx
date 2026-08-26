"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, FilePlus2, Files, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { DashboardData } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { ReportTable } from "@/components/report-table";

export default function DashboardPage() {
  const query = useQuery({ queryKey: ["dashboard"], queryFn: () => apiFetch<DashboardData>("/dashboard") });
  const metrics: Array<[string, number, LucideIcon]> = query.data ? [
    ["Всего отчётов", query.data.reports_total, Files],
    ["Готово", query.data.reports_completed, CheckCircle2],
    ["Сотрудников", query.data.employees_total, Users],
    ["Требуют внимания", query.data.reports_failed, Files],
  ] : [];
  return (
    <>
      <PageHeader title="Обзор" description="Текущие отчёты и быстрый доступ к основным операциям." action={<Button asChild><Link href="/reports/new"><FilePlus2 className="size-4" />Новый отчёт</Link></Button>} />
      {query.isLoading ? <LoadingState rows={6} /> : query.error ? <ErrorState message={query.error.message} retry={() => query.refetch()} /> : query.data ? (
        <div className="space-y-8">
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Показатели">
            {metrics.map(([label, value, Icon]) => (
              <Card key={String(label)} className="flex min-h-28 items-center justify-between p-4">
                <div><p className="text-sm text-muted">{String(label)}</p><p className="mt-2 text-2xl font-semibold">{String(value)}</p></div>
                <div className="grid size-9 place-items-center rounded-md bg-primary-soft text-primary"><Icon className="size-4" /></div>
              </Card>
            ))}
          </section>
          <section>
            <div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-semibold">Последние отчёты</h2><Link href="/reports/history" className="text-sm text-primary hover:underline">Вся история</Link></div>
            {query.data.recent_reports.length ? <ReportTable reports={query.data.recent_reports} /> : <EmptyState title="Отчётов пока нет" description="Создайте первый комплект документов, и он появится здесь." action={<Button asChild><Link href="/reports/new">Создать отчёт</Link></Button>} />}
          </section>
        </div>
      ) : null}
    </>
  );
}
