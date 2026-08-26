"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Laptop, Loader2, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { apiFetch } from "@/lib/api";
import type { EmployeeAccount } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/page-header";
import { ErrorState, LoadingState } from "@/components/states";

const modes = [
  { value: "light", label: "Светлая", icon: Sun },
  { value: "dark", label: "Тёмная", icon: Moon },
  { value: "system", label: "Системная", icon: Laptop },
];

const passwordSchema = z.object({
  password: z.string().min(8, "Минимум 8 символов").max(128, "Максимум 128 символов"),
  confirmation: z.string(),
}).refine((values) => values.password === values.confirmation, {
  path: ["confirmation"],
  message: "Пароли не совпадают",
});

type PasswordForm = z.infer<typeof passwordSchema>;

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

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<EmployeeAccount | null>(null);
  const [ownPasswordOpen, setOwnPasswordOpen] = useState(false);
  const accounts = useQuery({ queryKey: ["employee-accounts"], queryFn: () => apiFetch<EmployeeAccount[]>("/accounts/employees") });
  const password = useMutation({
    mutationFn: ({ employeeId, value }: { employeeId: string; value: string }) => apiFetch<EmployeeAccount>(`/accounts/employees/${employeeId}/password`, { method: "PUT", body: JSON.stringify({ password: value }) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employee-accounts"] });
      setSelected(null);
      toast.success("Пароль сотрудника обновлён");
    },
    onError: (error) => toast.error(error.message),
  });
  const ownPassword = useMutation({
    mutationFn: ({ currentPassword, newPassword }: { currentPassword: string; newPassword: string }) => apiFetch<void>("/auth/password", { method: "PUT", body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) }),
    onSuccess: () => {
      setOwnPasswordOpen(false);
      toast.success("Пароль администратора обновлён");
    },
    onError: (error) => toast.error(error.message),
  });
  return (
    <>
      <PageHeader title="Настройки" description="Управление доступом сотрудников и параметрами отображения." />
      <section className="max-w-4xl border-y border-border py-5">
        <h2 className="text-sm font-semibold">Учётные записи сотрудников</h2>
        <p className="mt-1 text-sm text-muted">Логином служит email из справочника. Сотрудник сможет формировать отчёты только от своего имени.</p>
        <div className="mt-4">
          {accounts.isLoading ? <LoadingState rows={5} /> : accounts.error ? <ErrorState message={accounts.error.message} retry={() => accounts.refetch()} /> : (
            <div className="divide-y divide-border border-y border-border">
              {(accounts.data ?? []).map((account) => (
                <div key={account.employee_id} className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center">
                  <div className="min-w-0 flex-1"><p className="text-sm font-medium">{account.full_name}</p><p className="truncate text-xs text-muted">{account.email ?? "Email не указан"} · {account.role === "admin" ? "администратор" : account.has_account ? "доступ настроен" : "доступ не настроен"}</p></div>
                  <Button variant="secondary" disabled={!account.email} onClick={() => { if (account.role === "admin") setOwnPasswordOpen(true); else setSelected(account); }}><KeyRound className="size-4" />{account.role === "admin" ? "Изменить свой пароль" : account.has_account ? "Изменить пароль" : "Задать пароль"}</Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
      <section className="mt-8 max-w-xl border-y border-border py-5">
        <h2 className="text-sm font-semibold">Тема интерфейса</h2>
        <div className="mt-3 grid grid-cols-3 gap-2" role="radiogroup" aria-label="Тема интерфейса">
          {modes.map(({ value, label, icon: Icon }) => (
            <button key={value} role="radio" aria-checked={theme === value} onClick={() => setTheme(value)} className={cn("flex h-20 flex-col items-center justify-center gap-2 rounded-md border border-border bg-surface text-sm hover:bg-surface-muted", theme === value && "border-primary bg-primary-soft text-primary")}>
              <Icon className="size-5" />{label}
            </button>
          ))}
        </div>
      </section>
      <PasswordDialog account={selected} pending={password.isPending} onClose={() => setSelected(null)} onSubmit={(value) => { if (selected) password.mutate({ employeeId: selected.employee_id, value }); }} />
      <OwnPasswordDialog open={ownPasswordOpen} pending={ownPassword.isPending} onClose={() => setOwnPasswordOpen(false)} onSubmit={(currentPassword, newPassword) => ownPassword.mutate({ currentPassword, newPassword })} />
    </>
  );
}
