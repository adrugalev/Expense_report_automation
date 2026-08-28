"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Loader2 } from "lucide-react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/lib/api";
import type { EmployeeAccount } from "@/lib/types";

const passwordSchema = z.object({
  password: z.string().min(8, "Минимум 8 символов").max(128, "Максимум 128 символов"),
  confirmation: z.string(),
}).refine((values) => values.password === values.confirmation, {
  path: ["confirmation"],
  message: "Пароли не совпадают",
});

const ownPasswordSchema = z.object({
  currentPassword: z.string().min(8, "Минимум 8 символов").max(128, "Максимум 128 символов"),
  newPassword: z.string().min(8, "Минимум 8 символов").max(128, "Максимум 128 символов"),
  confirmation: z.string(),
}).superRefine((values, context) => {
  if (values.newPassword !== values.confirmation) {
    context.addIssue({ code: "custom", path: ["confirmation"], message: "Пароли не совпадают" });
  }
  if (values.currentPassword === values.newPassword) {
    context.addIssue({ code: "custom", path: ["newPassword"], message: "Новый пароль должен отличаться от текущего" });
  }
});

type PasswordForm = z.infer<typeof passwordSchema>;
type OwnPasswordForm = z.infer<typeof ownPasswordSchema>;

function PasswordDialog({ account, pending, onClose, onSubmit }: {
  account: EmployeeAccount | null;
  pending: boolean;
  onClose: () => void;
  onSubmit: (password: string) => void;
}) {
  const form = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { password: "", confirmation: "" },
  });
  useEffect(() => form.reset(), [account, form]);
  return (
    <Dialog open={Boolean(account)} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-md">
        <DialogTitle>{account?.has_account ? "Изменить пароль" : "Настроить доступ"}</DialogTitle>
        <DialogDescription>{account?.full_name}<br />Логин: {account?.email ?? "email не указан"}</DialogDescription>
        <form className="mt-5 space-y-4" onSubmit={form.handleSubmit((values) => onSubmit(values.password))}>
          <label className="block text-sm font-medium">Новый пароль<Input className="mt-1.5" type="password" autoComplete="new-password" {...form.register("password")} /></label>
          {form.formState.errors.password ? <p className="text-xs text-danger">{form.formState.errors.password.message}</p> : null}
          <label className="block text-sm font-medium">Повторите пароль<Input className="mt-1.5" type="password" autoComplete="new-password" {...form.register("confirmation")} /></label>
          {form.formState.errors.confirmation ? <p className="text-xs text-danger">{form.formState.errors.confirmation.message}</p> : null}
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Отмена</Button><Button type="submit" disabled={pending}>{pending ? <Loader2 className="size-4 animate-spin" /> : <KeyRound className="size-4" />}Сохранить пароль</Button></div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function OwnPasswordDialog({ open, pending, onClose, onSubmit }: {
  open: boolean;
  pending: boolean;
  onClose: () => void;
  onSubmit: (currentPassword: string, newPassword: string) => void;
}) {
  const form = useForm<OwnPasswordForm>({
    resolver: zodResolver(ownPasswordSchema),
    defaultValues: { currentPassword: "", newPassword: "", confirmation: "" },
  });
  useEffect(() => { if (!open) form.reset(); }, [form, open]);
  return (
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen) onClose(); }}>
      <DialogContent className="max-w-md">
        <DialogTitle>Изменить свой пароль</DialogTitle>
        <DialogDescription>Для подтверждения укажите действующий пароль администратора.</DialogDescription>
        <form className="mt-5 space-y-4" onSubmit={form.handleSubmit((values) => onSubmit(values.currentPassword, values.newPassword))}>
          <label className="block text-sm font-medium">Текущий пароль<Input className="mt-1.5" type="password" autoComplete="current-password" {...form.register("currentPassword")} /></label>
          {form.formState.errors.currentPassword ? <p className="text-xs text-danger">{form.formState.errors.currentPassword.message}</p> : null}
          <label className="block text-sm font-medium">Новый пароль<Input className="mt-1.5" type="password" autoComplete="new-password" {...form.register("newPassword")} /></label>
          {form.formState.errors.newPassword ? <p className="text-xs text-danger">{form.formState.errors.newPassword.message}</p> : null}
          <label className="block text-sm font-medium">Повторите новый пароль<Input className="mt-1.5" type="password" autoComplete="new-password" {...form.register("confirmation")} /></label>
          {form.formState.errors.confirmation ? <p className="text-xs text-danger">{form.formState.errors.confirmation.message}</p> : null}
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Отмена</Button><Button type="submit" disabled={pending}>{pending ? <Loader2 className="size-4 animate-spin" /> : <KeyRound className="size-4" />}Сохранить пароль</Button></div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function EmployeePasswordDialogs({ account, onClose }: {
  account: EmployeeAccount | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const password = useMutation({
    mutationFn: ({ employeeId, value }: { employeeId: string; value: string }) => apiFetch<EmployeeAccount>(`/accounts/employees/${employeeId}/password`, { method: "PUT", body: JSON.stringify({ password: value }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employee-accounts"] });
      onClose();
      toast.success("Пароль сотрудника обновлён");
    },
    onError: (error) => toast.error(error.message),
  });
  const ownPassword = useMutation({
    mutationFn: ({ currentPassword, newPassword }: { currentPassword: string; newPassword: string }) => apiFetch<void>("/auth/password", { method: "PUT", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) }),
    onSuccess: () => {
      onClose();
      toast.success("Пароль администратора обновлён");
    },
    onError: (error) => toast.error(error.message),
  });

  const employeeAccount = account?.role === "admin" ? null : account;
  return <>
    <PasswordDialog account={employeeAccount} pending={password.isPending} onClose={onClose} onSubmit={(value) => { if (employeeAccount) password.mutate({ employeeId: employeeAccount.employee_id, value }); }} />
    <OwnPasswordDialog open={account?.role === "admin"} pending={ownPassword.isPending} onClose={onClose} onSubmit={(currentPassword, newPassword) => ownPassword.mutate({ currentPassword, newPassword })} />
  </>;
}
