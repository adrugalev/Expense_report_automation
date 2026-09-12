"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { AppMeta } from "@/lib/types";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export function VersionDialog() {
  const { data } = useQuery({ queryKey: ["app-meta"], queryFn: () => apiFetch<AppMeta>("/meta") });
  if (!data) return null;
  return (
    <Dialog>
      <DialogTrigger className="text-left text-xs text-white/45 hover:text-white/75">{data.version}</DialogTrigger>
      <DialogContent>
        <DialogTitle>История версий</DialogTitle>
        <div className="mt-5 space-y-5">
          {data.history.map((entry) => (
            <section key={`${entry.date}-${entry.revision}`}>
              <h3 className="text-sm font-semibold">Версия {entry.revision} от {entry.date}</h3>
              <ul className="mt-2 space-y-1 text-sm text-muted">
                {entry.changes.map((change) => <li key={change}>• {change}</li>)}
              </ul>
            </section>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
