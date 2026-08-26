import { AlertCircle, FileText, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function LoadingState({ rows = 4 }: { rows?: number }) {
  return <div className="space-y-3" aria-label="Загрузка">{Array.from({ length: rows }, (_, i) => <Skeleton key={i} className="h-14 w-full" />)}</div>;
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center border-y border-border px-6 text-center">
      <FileText className="mb-4 size-8 text-muted" />
      <h2 className="text-base font-semibold">{title}</h2>
      <p className="mt-1 max-w-md text-sm text-muted">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center border-y border-red-200 px-6 text-center dark:border-red-900">
      <AlertCircle className="mb-3 size-7 text-danger" />
      <p className="text-sm">{message}</p>
      {retry ? <Button variant="secondary" className="mt-4" onClick={retry}><RefreshCw className="size-4" />Повторить</Button> : null}
    </div>
  );
}
