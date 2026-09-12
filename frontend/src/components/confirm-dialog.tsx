"use client";

import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export function ConfirmDialog({ trigger, title, description, onConfirm }: { trigger: React.ReactNode; title: string; description: string; onConfirm: () => void }) {
  return (
    <Dialog>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>{description}</DialogDescription>
        <div className="mt-6 flex justify-end gap-2">
          <DialogClose asChild><Button variant="secondary">Отмена</Button></DialogClose>
          <DialogClose asChild><Button variant="danger" onClick={onConfirm}>Удалить</Button></DialogClose>
        </div>
      </DialogContent>
    </Dialog>
  );
}
