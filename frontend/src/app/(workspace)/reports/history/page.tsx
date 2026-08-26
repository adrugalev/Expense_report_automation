"use client";

import { useQuery } from "@tanstack/react-query";
import { FilePlus2 } from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import type { ReportList } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, LoadingState } from "@/components/states";
import { ReportTable } from "@/components/report-table";

export default function ReportHistoryPage() {
  const query = useQuery({ queryKey: ["reports"], queryFn: () => apiFetch<ReportList>("/reports?limit=200") });
  return (
    <>
      <PageHeader title="История" description="Сформированные комплекты доступны для повторного скачивания." action={<Button asChild><Link href="/reports/new"><FilePlus2 className="size-4" />Новый отчёт</Link></Button>} />
      {query.isLoading ? <LoadingState rows={7} /> : query.error ? <ErrorState message={query.error.message} retry={() => query.refetch()} /> : query.data?.items.length ? <ReportTable reports={query.data.items} /> : <EmptyState title="История пуста" description="Здесь появятся успешно сформированные и незавершённые отчёты." action={<Button asChild><Link href="/reports/new">Создать первый отчёт</Link></Button>} />}
    </>
  );
}
