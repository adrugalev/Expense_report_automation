import type { ReportStatus } from "@/lib/types";
import { reportStatusLabels } from "@/lib/report-meta";
import { Badge } from "@/components/ui/badge";

export function StatusBadge({ status }: { status: ReportStatus }) {
  const tone = status === "completed" ? "success" : status === "failed" ? "danger" : "warning";
  return <Badge tone={tone}>{reportStatusLabels[status]}</Badge>;
}
