import { PageHeader } from "@/components/page-header";
import { ReportForm } from "@/features/reports/report-form";

export default function NewReportPage() {
  return <><PageHeader title="Новый отчёт" description="Загрузите чеки, проверьте распознанные данные и сформируйте комплект документов." /><ReportForm /></>;
}
