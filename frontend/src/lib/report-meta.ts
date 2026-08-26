import type { ReportStatus, ReportType } from "@/lib/types";

export const reportTypeLabels: Record<ReportType, string> = {
  business_trip: "Командировка",
  representative_expenses: "Представительские расходы",
  gifts: "Подарки",
};

export const reportStatusLabels: Record<ReportStatus, string> = {
  processing: "Формируется",
  completed: "Готов",
  failed: "Ошибка",
};
