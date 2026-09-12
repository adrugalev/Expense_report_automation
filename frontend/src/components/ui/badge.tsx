import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

const tones: Record<BadgeTone, string> = {
  neutral: "bg-surface-muted text-foreground",
  success: "bg-green-50 text-green-800 dark:bg-green-950/50 dark:text-green-300",
  warning: "bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300",
  danger: "bg-red-50 text-red-800 dark:bg-red-950/50 dark:text-red-300",
  info: "bg-primary-soft text-primary",
};

export function Badge({ tone = "neutral", className, ...props }: React.HTMLAttributes<HTMLSpanElement> & { tone?: BadgeTone }) {
  return <span className={cn("inline-flex rounded px-2 py-1 text-xs font-medium", tones[tone], className)} {...props} />;
}
