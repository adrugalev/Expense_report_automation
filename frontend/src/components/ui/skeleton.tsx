import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-[pulse-soft_1.4s_ease-in-out_infinite] rounded bg-surface-muted", className)} />;
}
