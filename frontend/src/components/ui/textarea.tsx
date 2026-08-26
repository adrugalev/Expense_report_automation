import * as React from "react";
import { cn } from "@/lib/utils";

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-24 w-full resize-y rounded-md border border-border bg-surface px-3 py-2 text-sm placeholder:text-muted disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
