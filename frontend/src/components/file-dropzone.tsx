"use client";

import { CheckCircle2, FileText, Loader2, Trash2, UploadCloud } from "lucide-react";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import type { ReceiptUpload } from "@/lib/types";
import { cn, formatBytes } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function FileDropzone({ uploads, onUploaded, onRemoved }: { uploads: ReceiptUpload[]; onUploaded: (upload: ReceiptUpload) => void; onRemoved: (upload: ReceiptUpload) => void }) {
  const [pending, setPending] = useState<string[]>([]);
  const onDrop = useCallback(async (files: File[]) => {
    for (const file of files) {
      setPending((items) => [...items, file.name]);
      const body = new FormData();
      body.append("file", file);
      try {
        const upload = await apiFetch<ReceiptUpload>("/uploads/receipts", { method: "POST", body });
        onUploaded(upload);
        toast.success(`${file.name}: чек распознан`);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : `Не удалось загрузить ${file.name}`);
      } finally {
        setPending((items) => items.filter((item) => item !== file.name));
      }
    }
  }, [onUploaded]);
  const dropzone = useDropzone({ onDrop, accept: { "application/pdf": [".pdf"], "image/png": [".png"], "image/jpeg": [".jpg", ".jpeg"] }, maxSize: 15 * 1024 * 1024, multiple: true });
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
      {[...uploads.map((upload) => ({ name: upload.original_name, size: upload.size, upload })), ...pending.map((name) => ({ name, size: 0, upload: null }))].map((item, index) => (
        <div key={`${item.name}-${index}`} className="flex min-h-14 items-center gap-3 border-b border-border px-1 py-2">
          <div className="grid size-9 place-items-center rounded-md bg-surface-muted">{item.upload ? <FileText className="size-4" /> : <Loader2 className="size-4 animate-spin" />}</div>
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{item.name}</p><p className="text-xs text-muted">{item.upload ? formatBytes(item.size) : "Распознавание..."}</p></div>
          {item.upload ? <><CheckCircle2 className="size-4 text-success" /><Button type="button" size="icon" variant="ghost" aria-label={`Удалить ${item.name}`} onClick={() => remove(item.upload!)}><Trash2 className="size-4" /></Button></> : null}
        </div>
      ))}
    </div>
  );
}
