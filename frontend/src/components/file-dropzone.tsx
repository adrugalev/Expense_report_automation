"use client";

import { CheckCircle2, FileText, Loader2, Trash2, UploadCloud } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import type { ReceiptRecognitionJobStart, ReceiptRecognitionJobStatus, ReceiptUpload } from "@/lib/types";
import { cn, formatBytes } from "@/lib/utils";
import { Button } from "@/components/ui/button";

type RecognitionProgress = {
  total: number;
  completed: number;
  currentName: string;
  startedAt: number;
  percent: number;
  stage: string;
};

const wait = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));
const INITIAL_STAGES = new Set(["Загрузка файла", "Начало обработки", "Проверка файла", "Файл сохранён"]);

export function FileDropzone({ uploads, onUploaded, onRemoved }: { uploads: ReceiptUpload[]; onUploaded: (upload: ReceiptUpload) => void; onRemoved: (upload: ReceiptUpload) => void }) {
  const [pending, setPending] = useState<string[]>([]);
  const [progress, setProgress] = useState<RecognitionProgress | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  useEffect(() => {
    if (!progress) return;
    const update = () => {
      const elapsed = Math.max(0, (Date.now() - progress.startedAt) / 1000);
      setElapsedSeconds(Math.floor(elapsed));
      const estimated = Math.min(94, Math.round(5 + 89 * (1 - Math.exp(-elapsed / 22))));
      setProgress((current) => {
        if (!current || current.percent >= 100 || estimated <= current.percent) return current;
        const stage = estimated >= 12 && INITIAL_STAGES.has(current.stage) ? "Распознавание чека" : current.stage;
        return { ...current, percent: estimated, stage };
      });
    };
    const timer = window.setInterval(update, 500);
    return () => window.clearInterval(timer);
  }, [progress]);
  const onDrop = useCallback(async (files: File[]) => {
    if (!files.length) return;
    setPending((items) => [...items, ...files.map((file) => file.name)]);
    setProgress({ total: files.length, completed: 0, currentName: files[0].name, startedAt: Date.now(), percent: 0, stage: "Загрузка файла" });
    for (const [index, file] of files.entries()) {
      setElapsedSeconds(0);
      setProgress({ total: files.length, completed: index, currentName: file.name, startedAt: Date.now(), percent: 0, stage: "Загрузка файла" });
      const body = new FormData();
      body.append("file", file);
      try {
        const started = await apiFetch<ReceiptRecognitionJobStart>("/uploads/receipts/jobs", { method: "POST", body });
        let upload: ReceiptUpload | null = null;
        while (!upload) {
          const job = await apiFetch<ReceiptRecognitionJobStatus>(`/uploads/receipts/jobs/${started.job_id}`);
          setProgress((current) => current?.currentName === file.name ? { ...current, percent: Math.max(current.percent, job.progress), stage: job.stage } : current);
          if (job.status === "failed") throw new Error(job.error || `Не удалось распознать ${file.name}`);
          if (job.status === "completed") {
            if (!job.result) throw new Error(`Сервер не вернул результат для ${file.name}`);
            upload = job.result;
            break;
          }
          await wait(500);
        }
        onUploaded(upload);
        toast.success(`${file.name}: чек распознан`);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : `Не удалось загрузить ${file.name}`);
      } finally {
        setPending((items) => items.filter((item) => item !== file.name));
        setProgress({ total: files.length, completed: index + 1, currentName: file.name, startedAt: Date.now(), percent: 100, stage: "Готово" });
      }
    }
    setElapsedSeconds(0);
    setProgress(null);
  }, [onUploaded]);
  const dropzone = useDropzone({ onDrop, accept: { "application/pdf": [".pdf"], "image/png": [".png"], "image/jpeg": [".jpg", ".jpeg"] }, maxSize: 15 * 1024 * 1024, multiple: true, disabled: Boolean(progress) });
  const remove = async (upload: ReceiptUpload) => {
    try {
      await apiFetch<void>(`/uploads/${upload.id}`, { method: "DELETE" });
      onRemoved(upload);
      toast.success(`${upload.original_name}: файл удалён`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Не удалось удалить файл");
    }
  };
  return (
    <div className="space-y-3">
      <div {...dropzone.getRootProps()} className={cn("flex min-h-36 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-border bg-surface px-5 text-center transition-colors hover:bg-surface-muted", dropzone.isDragActive && "border-primary bg-primary-soft")}>
        <input {...dropzone.getInputProps()} aria-label="Загрузить чеки" />
        <UploadCloud className="mb-3 size-7 text-primary" />
        <p className="text-sm font-medium">Перетащите чеки сюда или выберите файлы</p>
        <p className="mt-1 text-xs text-muted">PDF, PNG, JPG до 15 МБ</p>
      </div>
      {progress ? <div className="rounded-md border bg-surface px-4 py-3" aria-live="polite">
        <div className="flex items-start justify-between gap-4 text-sm"><p className="min-w-0"><span className="font-medium">Распознаётся {Math.min(progress.completed + 1, progress.total)} из {progress.total}</span><span className="block truncate text-xs text-muted">{progress.currentName}</span><span className="block text-xs text-primary">{progress.stage} · {progress.percent}%</span></p><span className="shrink-0 tabular-nums text-muted">{elapsedSeconds} с</span></div>
        <div className="relative mt-3 h-2 overflow-hidden rounded-full bg-surface-muted" role="progressbar" aria-label="Прогресс распознавания чеков" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(((progress.completed + progress.percent / 100) / progress.total) * 100)}>
          <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${((progress.completed + progress.percent / 100) / progress.total) * 100}%` }} />
        </div>
        <p className="mt-1.5 text-xs text-muted">Готово: {progress.completed} из {progress.total}. Прогресс обновляется по этапам обработки на сервере.</p>
      </div> : null}
      {[...uploads.map((upload) => ({ name: upload.original_name, size: upload.size, upload })), ...pending.map((name) => ({ name, size: 0, upload: null }))].map((item, index) => (
        <div key={`${item.name}-${index}`} className="flex min-h-14 items-center gap-3 border-b border-border px-1 py-2">
          <div className="grid size-9 place-items-center rounded-md bg-surface-muted">{item.upload ? <FileText className="size-4" /> : <Loader2 className="size-4 animate-spin" />}</div>
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{item.name}</p><p className="text-xs text-muted">{item.upload ? formatBytes(item.size) : item.name === progress?.currentName ? `${progress.stage}... ${elapsedSeconds} с` : "Ожидает очереди"}</p></div>
          {item.upload ? <><CheckCircle2 className="size-4 text-success" /><Button type="button" size="icon" variant="ghost" aria-label={`Удалить ${item.name}`} onClick={() => remove(item.upload!)}><Trash2 className="size-4" /></Button></> : null}
        </div>
      ))}
    </div>
  );
}
